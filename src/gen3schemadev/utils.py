import json
import os
import yaml
from jsonschema import validate
import logging
from gen3_validator.resolve_schema import ResolveSchema
import tempfile

from gen3schemadev.refs import find_dangling_refs


logger = logging.getLogger(__name__)

def create_dir_if_not_exists(dir_path):
    base_path = os.path.dirname(dir_path)
    if not os.path.exists(base_path):
        os.makedirs(base_path)
        logger.info(f"Created directory: {base_path}")

def load_yaml(file_path):
    """
    Loads a YAML file and returns its contents.
    Logs success or error messages.
    """
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
            logger.info(f"Successfully loaded YAML file: {file_path}")
            return data
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error in file {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading YAML file {file_path}: {e}")
        raise

def write_yaml(data, file_path):
    """
    Writes a Python object to a YAML file.
    Logs success or error messages.
    """
    try:
        dir_path = os.path.dirname(file_path)
        if dir_path:
            create_dir_if_not_exists(file_path)
        with open(file_path, 'w') as f:
            yaml.safe_dump(data, f, sort_keys=False, indent=2)
            logger.info(f"Successfully wrote YAML file: {file_path}")
    except Exception as e:
        logger.error(f"Failed to write YAML file {file_path}: {e}")
        raise

def read_json(file_path):
    """
    Reads a JSON file and returns its contents.
    Logs success or error messages.
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            logger.info(f"Successfully loaded JSON file: {file_path}")
            return data
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error in file {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading JSON file {file_path}: {e}")
        raise

def write_json(data, file_path):
    """
    Writes a Python object to a JSON file.
    Logs success or error messages.
    """
    try:
        dir_path = os.path.dirname(file_path)
        if dir_path:
            create_dir_if_not_exists(file_path)
        with open(file_path, 'w') as f:
            json.dump(data, f)
            logger.info(f"Successfully wrote JSON file: {file_path}")
    except Exception as e:
        logger.error(f"Failed to write JSON file {file_path}: {e}")
        raise

def bundle_yamls(input_dir: str) -> dict:
    """
    Bundles all YAML files in a directory into a single dictionary.

    Files are read in sorted order so the bundle is byte-identical wherever it is
    built. os.listdir returns entries in filesystem order, which differs between
    machines, so an unsorted bundle of an unchanged dictionary produced different
    JSON on a contributor's laptop than on a Linux CI runner - identical content,
    different key order, and a spurious diff on every commit.

    Only the top level is sorted. Property order inside each schema comes from
    the YAML document and is meaningful, so it is left as authored.
    """
    bundle = {}
    yamls_found = 0
    for file_name in sorted(os.listdir(input_dir)):
        if file_name.endswith('.yaml') or file_name.endswith('.yml'):
            yamls_found += 1
            file_path = os.path.join(input_dir, file_name)
            bundle[file_name] = load_yaml(file_path)
    if yamls_found == 0:
        raise Exception(f"No YAML files found in directory: {input_dir}")
    return bundle


class SchemaResolutionError(Exception):
    """Raised when a bundled dictionary cannot be resolved into node schemas."""


# Files in a bundle that describe the dictionary rather than a node. They are
# resolution inputs, not things to resolve, and carry no 'id'.
_NON_NODE_FILES = ('_definitions.yaml', '_terms.yaml', '_settings.yaml')


def is_documentation_ref(path: str) -> bool:
    """
    Return True if a ``$ref`` at ``path`` sits inside a ``term`` block.

    A ``term`` is an ontology/documentation pointer, not a JSON Schema
    keyword - nothing about the shape of the data depends on it. So a ``term``
    pointing at a definition that does not exist is worth reporting but is not
    a reason to refuse to validate the dictionary. The official Gen3
    dictionary ships exactly one of these.
    """
    segments = (part.split('[')[0] for part in path.split('.'))
    return any(segment in ('term', 'terms') for segment in segments)


def _strip_refs(node, refs: set):
    """Return a copy of ``node`` with every dict holding one of ``refs`` removed."""
    if isinstance(node, dict):
        return {
            key: _strip_refs(value, refs)
            for key, value in node.items()
            if not (isinstance(value, dict) and value.get('$ref') in refs)
        }
    if isinstance(node, list):
        return [_strip_refs(item, refs) for item in node]
    return node


def resolve_schema(schema_dir: str = None, schema_path: str = None) -> dict:
    """
    Load and resolve a Gen3 JSON schema from either a directory of YAML files or a bundled JSON file.

    If `schema_dir` is provided, all YAML files in the directory are bundled into a temporary JSON file,
    which is then resolved. If `schema_path` is provided, it is used directly.

    Two things are done here that the underlying resolver does not do:

    1. Every node is resolved against the terms *and* the resolved definitions.
       The library resolves nodes against the definitions alone, so any node
       referencing ``_terms.yaml`` directly failed - and those failures are
       logged and swallowed, so the caller silently received a subset. On the
       official Gen3 dictionary that was 10 nodes out of 29, each reported as a
       success while the other 19 went unmentioned.
    2. A dangling reference inside a ``term`` block is dropped rather than
       being fatal, because a term is documentation. Any other dangling
       reference raises :class:`SchemaResolutionError` naming it, instead of
       the bare ``KeyError`` the library raises.

    Returns:
        dict: Resolved node schemas keyed by ``"<id>.yaml"``.

    Raises:
        SchemaResolutionError: If a non-documentation reference cannot be resolved.
        Exception: If neither `schema_dir` nor `schema_path` is provided.
    """
    temp_file_path = None
    if schema_dir:
        bundled_schema = bundle_yamls(schema_dir)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", dir=".", delete=False) as tf:
            json.dump(bundled_schema, tf)
            temp_file_path = tf.name
            schema_path = temp_file_path

    try:
        resolver = ResolveSchema(schema_path)
        resolver.parse_schema()
        bundle = resolver.schema

        dangling = find_dangling_refs(bundle)
        fatal = [hit for hit in dangling if not is_documentation_ref(hit[1])]
        if fatal:
            detail = "; ".join(f"{src}: {path} -> {ref}" for src, path, ref in fatal)
            raise SchemaResolutionError(detail)

        if dangling:
            # Documentation-only, so drop the term and carry on. The caller
            # reports these; see cli.py.
            bundle = _strip_refs(bundle, {ref for _, _, ref in dangling})

        try:
            definitions = resolver.resolve_references(
                bundle['_definitions.yaml'], bundle['_terms.yaml']
            )
            references = {**bundle['_terms.yaml'], **definitions}
            output = {}
            for file_name, schema in bundle.items():
                if file_name in _NON_NODE_FILES:
                    continue
                resolved = resolver.resolve_references(schema, references)
                schema_id = resolved.get('id')
                if schema_id:
                    output[f"{schema_id}.yaml"] = resolved
        except KeyError as exc:
            raise SchemaResolutionError(str(exc).strip("'")) from exc

        return output
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

