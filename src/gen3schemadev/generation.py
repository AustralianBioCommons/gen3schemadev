"""
Dictionary generation: planning, preset merging, drift detection, and writing.

The central design decision here is that generation happens entirely in memory
before a single file is touched. `build_dictionary` either returns a complete
set of files or raises, so a malformed node cannot leave half a dictionary on
disk. Everything else in this module - refusing to overwrite, `--check`, orphan
detection - is built on top of that complete in-memory picture.
"""

import copy
import logging
import os

import yaml

from gen3schemadev.converter import get_node_names, populate_template, construct_props
from gen3schemadev.schema.gen3_template import (
    generate_def_template,
    generate_setting_template,
    generate_terms_template,
    generate_core_metadata_template,
    generate_project_template,
    generate_program_template,
)
from gen3schemadev.utils import write_yaml

logger = logging.getLogger(__name__)

# Files written from packaged templates rather than from the user's nodes.
# They are never treated as orphans.
FRAMEWORK_FILES = ('_definitions.yaml', '_settings.yaml', '_terms.yaml')

# Presets a node may extend, and the loader that supplies each one.
PRESET_LOADERS = {
    'program': generate_program_template,
    'project': generate_project_template,
    'core_metadata_collection': generate_core_metadata_template,
}

# Node-level keys that a declaring node may override on a preset. `properties`
# is merged rather than replaced, so it is handled separately.
_MERGEABLE_NODE_KEYS = (
    'description', 'category', 'submittable', 'validators',
    'systemProperties', 'uniqueKeys', 'required', 'namespace',
    'program', 'project',
)


def load_preset(name):
    """
    Load a packaged preset schema by name.

    Args:
        name: One of the keys in PRESET_LOADERS.

    Returns:
        A deep copy of the preset, safe for the caller to mutate.

    Raises:
        ValueError: If the preset is not one gen3schemadev ships.
    """
    if name not in PRESET_LOADERS:
        raise ValueError(
            f"Unknown preset '{name}'. Available presets: {', '.join(sorted(PRESET_LOADERS))}"
        )
    return copy.deepcopy(PRESET_LOADERS[name]())


def merge_onto_preset(node_model, node_name, validated_model):
    """
    Merge a declared node onto the packaged preset it extends.

    Only what the author actually wrote overrides the preset. Everything else is
    inherited, which is the whole point: presets carry node-level settings that
    Gen3 microservices rely on and that the input language cannot express -
    project's release-related systemProperties, its uniqueKeys on `code`, and the
    DUO ontology terms on consent_codes. A node that adds two properties must not
    silently drop any of that.

    Args:
        node_model: The validated input node declaring `extends`.
        node_name: The node's name.
        validated_model: The whole validated data model, for link lookups.

    Returns:
        A tuple of (merged schema dict, summary dict describing the merge).
    """
    preset = load_preset(node_model.extends)

    # exclude_unset tells us precisely which keys the author typed, as opposed
    # to which merely have defaults. Without it every unwritten field would
    # look like a deliberate override.
    declared = node_model.model_dump(
        by_alias=True, exclude_none=True, exclude_unset=True
    )

    overridden = []
    for key in _MERGEABLE_NODE_KEYS:
        if key in declared:
            preset[key] = declared[key]
            overridden.append(key)

    added = []
    if node_model.properties:
        # construct_props builds the $ref and link properties too; the preset
        # already has its own, so take only the properties this node declares.
        generated_props = construct_props(node_name, validated_model)
        declared_names = {p.name for p in node_model.properties}
        preset.setdefault('properties', {})
        for prop_name in declared_names:
            if prop_name in generated_props:
                preset['properties'][prop_name] = generated_props[prop_name]
                added.append(prop_name)

    if 'required' in declared:
        preset['required'] = list(dict.fromkeys([*declared['required'], 'submitter_id', 'type']))

    inherited = [k for k in _MERGEABLE_NODE_KEYS if k in preset and k not in overridden]
    summary = {
        'preset': node_model.extends,
        'inherited': inherited,
        'overridden': overridden,
        'added': added,
    }
    return preset, summary


def build_dictionary(validated_model, converter_template, only=None):
    """
    Build every file the dictionary consists of, in memory.

    Nothing is written here. If any node fails to build, the caller still has
    whatever was on disk before, untouched.

    Args:
        validated_model: The validated input data model.
        converter_template: Node template derived from the metaschema.
        only: Optional collection of node names to build. Framework and preset
            files are skipped when set, so a targeted regeneration touches
            nothing else.

    Returns:
        A tuple of (files dict keyed by filename, list of merge summaries).

    Raises:
        ValueError: If `only` names nodes the input does not define.
    """
    node_names = get_node_names(validated_model)
    nodes_by_name = {n.name: n for n in validated_model.nodes}

    if only is not None:
        unknown = set(only) - set(node_names)
        if unknown:
            raise ValueError(
                f"--only named nodes not present in the input: {sorted(unknown)}"
            )
        targets = [n for n in node_names if n in set(only)]
    else:
        targets = list(node_names)

    files = {}
    summaries = []

    for name in targets:
        node_model = nodes_by_name.get(name)
        if node_model is not None and node_model.extends:
            merged, summary = merge_onto_preset(node_model, name, validated_model)
            summary['node'] = name
            summaries.append(summary)
            files[f"{name}.yaml"] = merged
        else:
            files[f"{name}.yaml"] = populate_template(
                name, validated_model, converter_template
            )

    # A targeted regeneration deliberately stops here: rewriting the framework
    # files would defeat the point of --only.
    if only is not None:
        return files, summaries

    definitions = generate_def_template()
    if validated_model.definitions:
        # Repo-supplied definitions are merged in so custom enums and refs
        # survive regeneration instead of being clobbered by the template.
        definitions = _deep_merge(definitions, validated_model.definitions)
    files['_definitions.yaml'] = definitions

    settings = generate_setting_template()
    settings['_dict_version'] = validated_model.version
    files['_settings.yaml'] = settings
    files['_terms.yaml'] = generate_terms_template()

    # Presets are only injected when the input has not declared the node
    # itself. This now applies to core_metadata_collection too, which was
    # previously written unconditionally and silently discarded any
    # user-declared version.
    for preset_name, loader in PRESET_LOADERS.items():
        if preset_name not in node_names:
            files[f"{preset_name}.yaml"] = loader()

    return files, summaries


def _deep_merge(base, overlay):
    """
    Recursively merge overlay into a copy of base; overlay wins on conflict.

    Args:
        base: The starting mapping.
        overlay: Values to layer on top.

    Returns:
        A new merged dict; neither input is mutated.
    """
    result = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def serialise(content):
    """
    Render a schema exactly as `write_yaml` would write it.

    Keeping this in step with utils.write_yaml is what lets --check compare
    against the real bytes rather than an approximation of them.

    Args:
        content: The schema dict.

    Returns:
        The YAML text that would be written to disk.
    """
    return yaml.safe_dump(content, sort_keys=False, indent=2)


def existing_yaml_files(output_dir):
    """
    List the YAML filenames already present in an output directory.

    Args:
        output_dir: Directory to inspect.

    Returns:
        A set of filenames, empty if the directory does not exist.
    """
    if not os.path.isdir(output_dir):
        return set()
    return {
        f for f in os.listdir(output_dir)
        if f.endswith(('.yaml', '.yml'))
    }


def plan_write(files, output_dir):
    """
    Work out what writing these files would do to a directory.

    Args:
        files: The in-memory dictionary from build_dictionary.
        output_dir: Target directory.

    Returns:
        A dict with 'overwrite', 'create' and 'orphans' filename lists.
    """
    present = existing_yaml_files(output_dir)
    generated = set(files)
    return {
        'overwrite': sorted(present & generated),
        'create': sorted(generated - present),
        'orphans': sorted(present - generated),
    }


def find_orphans(files, output_dir):
    """
    Find YAML files present on disk that this input does not produce.

    Framework files are excluded: they come from packaged templates, so their
    presence says nothing about drift.

    Args:
        files: The in-memory dictionary from build_dictionary.
        output_dir: Directory to inspect.

    Returns:
        A sorted list of orphan filenames.
    """
    present = existing_yaml_files(output_dir)
    return sorted(present - set(files) - set(FRAMEWORK_FILES))


def diff_against_disk(files, output_dir):
    """
    Compare the generated dictionary with what is committed on disk.

    The question being answered is "would regenerating change this file?", so
    the comparison is against the exact text generation would write. Comparing
    parsed YAML instead would look more forgiving but would miss real hand
    edits - a comment added by a developer survives parsing unchanged, yet is
    destroyed the moment anyone regenerates.

    Args:
        files: The in-memory dictionary from build_dictionary.
        output_dir: Directory to compare against.

    Returns:
        A dict with 'changed', 'missing' and 'orphans' filename lists.
    """
    changed = []
    missing = []
    for filename, content in files.items():
        path = os.path.join(output_dir, filename)
        if not os.path.exists(path):
            missing.append(filename)
            continue
        try:
            with open(path, 'r') as handle:
                on_disk = handle.read()
        except OSError:
            changed.append(filename)
            continue
        if on_disk != serialise(content):
            changed.append(filename)
    return {
        'changed': sorted(changed),
        'missing': sorted(missing),
        'orphans': find_orphans(files, output_dir),
    }


def write_dictionary(files, output_dir):
    """
    Write a fully-built dictionary to disk.

    Args:
        files: The in-memory dictionary from build_dictionary.
        output_dir: Target directory, created if absent.

    Returns:
        The sorted list of filenames written.
    """
    os.makedirs(output_dir, exist_ok=True)
    for filename, content in sorted(files.items()):
        write_yaml(content, os.path.join(output_dir, filename))
    return sorted(files)
