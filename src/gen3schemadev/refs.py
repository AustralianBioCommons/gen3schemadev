"""Utilities for making ``$ref`` properties safe under JSON Schema draft-04.

Gen3 compiles data dictionaries with draft-04 semantics, where any keyword
sitting as a direct sibling of ``$ref`` is ignored during resolution. A
property written as::

    atrial_fibrillation:
      description: "Self-reported atrial fibrillation."
      $ref: "_definitions.yaml#/enum_yes_no"

loses its ``description`` (and ``termDef``, ``term``, etc.) when resolved by
strict tooling such as dictionaryutils, so the data-dictionary viewer shows
"No Description". The fix is structural: keep the annotations at the top
level and move the ``$ref`` into an ``allOf`` list::

    atrial_fibrillation:
      description: "Self-reported atrial fibrillation."
      allOf:
      - $ref: "_definitions.yaml#/enum_yes_no"

This module is the single source of truth for that transformation. It is
used by the schema generator (``converter.format_datetime``), the rule
validator, and the ``gen3schemadev fix-refs`` CLI command.
"""

from __future__ import annotations

import fnmatch
import logging
import os

logger = logging.getLogger(__name__)

# Actions recorded for each property examined by the transform.
WRAPPED = "wrapped"
BARE_REF = "bare-ref"
ALREADY_WRAPPED = "already-wrapped"
NO_REF = "no-ref"
PROPERTIES_MERGE = "properties-merge"

# Human-readable reasons for skipped properties, keyed by action.
SKIP_REASONS = {
    BARE_REF: "bare $ref, no siblings to preserve",
    ALREADY_WRAPPED: "already wrapped in allOf/anyOf/oneOf",
    PROPERTIES_MERGE: "$ref key in 'properties' is a Gen3 properties-merge",
}

_COMBINATORS = ("allOf", "anyOf", "oneOf")


def has_ref(prop) -> bool:
    """
    Return True if a property definition references another schema, either
    via a top-level ``$ref`` or via a ``$ref`` inside an allOf/anyOf/oneOf
    list item.
    """
    if not isinstance(prop, dict):
        return False
    if "$ref" in prop:
        return True
    for combinator in _COMBINATORS:
        items = prop.get(combinator)
        if isinstance(items, list):
            if any(isinstance(item, dict) and "$ref" in item for item in items):
                return True
    return False


def wrap_ref_siblings(prop, prop_name: str = "") -> "tuple":
    """
    Rewrite a single property definition so sibling annotations survive
    draft-04 ``$ref`` resolution.

    Returns a ``(new_prop, action)`` tuple. The transformation only fires
    when the property dict has a top-level ``$ref`` alongside at least one
    other key; in that case the siblings keep their original order and the
    ``$ref`` moves into an ``allOf`` list appended last. All other shapes
    are returned unchanged:

    - not a dict, or no ``$ref`` anywhere -> ``NO_REF``
    - ``$ref`` only inside allOf/anyOf/oneOf -> ``ALREADY_WRAPPED`` (idempotent)
    - ``{"$ref": ...}`` with no siblings -> ``BARE_REF`` (nothing is lost)
    """
    if not isinstance(prop, dict) or not has_ref(prop):
        return prop, NO_REF

    if "$ref" not in prop:
        return prop, ALREADY_WRAPPED

    if len(prop) == 1:
        return prop, BARE_REF

    new_prop = {k: v for k, v in prop.items() if k != "$ref"}
    if isinstance(new_prop.get("allOf"), list):
        # Rare edge: the property already has an allOf next to the $ref.
        # Append rather than overwrite so existing constraints are kept.
        new_prop["allOf"] = new_prop["allOf"] + [{"$ref": prop["$ref"]}]
    else:
        new_prop["allOf"] = [{"$ref": prop["$ref"]}]
    logger.debug(f"Wrapped $ref of property '{prop_name}' in allOf.")
    return new_prop, WRAPPED


def fix_schema(schema: dict) -> "tuple":
    """
    Apply ``wrap_ref_siblings`` to every property of a node schema.

    Only the direct values of ``schema["properties"]`` are examined:
    sibling-``$ref`` annotations occur at the property level in Gen3 node
    schemas, and a shallow walk cannot accidentally rewrite the Gen3
    properties-merge construct (a ``$ref`` *key* directly inside the
    ``properties`` block), which is recorded as ``PROPERTIES_MERGE`` and
    left untouched.

    Returns ``(new_schema, changes)`` where changes is a list of
    ``(prop_name, action, preserved_keys)`` tuples. ``preserved_keys`` names
    the sibling annotation keys kept for ``WRAPPED`` entries and is an empty
    tuple otherwise.
    """
    changes = []
    props = schema.get("properties") if isinstance(schema, dict) else None
    if not isinstance(props, dict):
        return schema, changes

    new_props = {}
    for prop_name, prop in props.items():
        if prop_name == "$ref":
            new_props[prop_name] = prop
            changes.append((prop_name, PROPERTIES_MERGE, ()))
            continue
        new_prop, action = wrap_ref_siblings(prop, prop_name)
        new_props[prop_name] = new_prop
        preserved = ()
        if action == WRAPPED:
            preserved = tuple(k for k in prop.keys() if k != "$ref")
        if action != NO_REF:
            changes.append((prop_name, action, preserved))

    new_schema = dict(schema)
    new_schema["properties"] = new_props
    return new_schema, changes


def find_null_descriptions(node, path: str = "") -> list:
    """
    Recursively find every ``description`` key whose value is null.

    The Gen3 metaschema requires ``description`` to be a string, so a
    ``description: null`` placeholder (common in generated shared
    definitions) is invalid. With a direct ``$ref`` the resolver happens to
    mask it — the referencing property's own description merges over the
    definition's null — but a bare or allOf-wrapped ref exposes the null in
    the resolved node schema, where metaschema validation fails far away
    from the definition that caused it.

    Returns a list of dotted paths to each offender, with list items shown
    as ``[i]`` (e.g. ``"enum_yes_no.description"``,
    ``"properties.status.anyOf[0].description"``). Non-dict/list input
    yields an empty list.
    """
    hits = []
    if isinstance(node, dict):
        for key, value in node.items():
            key_path = f"{path}.{key}" if path else str(key)
            if key == "description" and value is None:
                hits.append(key_path)
            else:
                hits.extend(find_null_descriptions(value, key_path))
    elif isinstance(node, list):
        for i, item in enumerate(node):
            hits.extend(find_null_descriptions(item, f"{path}[{i}]"))
    return hits


def scan_dir_null_descriptions(yaml_dir: str) -> list:
    """
    Scan every YAML file under ``yaml_dir`` (recursively) for null-valued
    ``description`` keys.

    Unlike ``fix_yaml_dir``, underscore files (``_definitions.yaml``,
    ``_terms.yaml``, ...) are INCLUDED — shared definitions are where the
    null placeholders usually live, and where they do the most damage
    because every referencing property inherits them on resolution.

    Returns ``"relpath: dotted.path"`` strings, one per offender.
    """
    from gen3schemadev.utils import load_yaml

    hits = []
    for root, _dirs, files in os.walk(yaml_dir):
        for fname in sorted(files):
            if not (fnmatch.fnmatch(fname, "*.yaml") or fnmatch.fnmatch(fname, "*.yml")):
                continue
            path = os.path.join(root, fname)
            rel_path = os.path.relpath(path, yaml_dir)
            schema = load_yaml(path)
            for hit in find_null_descriptions(schema):
                hits.append(f"{rel_path}: {hit}")
    return hits


def fix_yaml_dir(yaml_dir: str, dry_run: bool = False) -> list:
    """
    Rewrite every YAML node schema under ``yaml_dir`` (recursively) so that
    ``$ref`` sibling annotations survive draft-04 resolution.

    Files whose basename starts with an underscore (``_definitions.yaml``,
    ``_terms.yaml``, ``_settings.yaml``) are skipped entirely: adding
    structure or descriptions to shared definitions would force them onto
    every referencing property. Files with no changes are never rewritten,
    which keeps the operation idempotent. With ``dry_run=True`` nothing is
    written at all.

    Returns a list of per-file report dicts::

        {"path": <relative path>, "skipped_file": <reason or None>,
         "changes": [(prop_name, action, preserved_keys), ...],
         "rewritten": <bool>}
    """
    from gen3schemadev.utils import load_yaml, write_yaml

    reports = []
    for root, _dirs, files in os.walk(yaml_dir):
        for fname in sorted(files):
            if not (fnmatch.fnmatch(fname, "*.yaml") or fnmatch.fnmatch(fname, "*.yml")):
                continue
            path = os.path.join(root, fname)
            rel_path = os.path.relpath(path, yaml_dir)

            if fname.startswith("_"):
                reports.append({
                    "path": rel_path,
                    "skipped_file": "definitions/terms/settings file",
                    "changes": [],
                    "rewritten": False,
                })
                continue

            schema = load_yaml(path)
            if not isinstance(schema, dict):
                reports.append({
                    "path": rel_path,
                    "skipped_file": "not a mapping, no properties to fix",
                    "changes": [],
                    "rewritten": False,
                })
                continue

            new_schema, changes = fix_schema(schema)
            wrapped = [c for c in changes if c[1] == WRAPPED]
            rewritten = False
            if wrapped and not dry_run:
                write_yaml(new_schema, path)
                rewritten = True

            reports.append({
                "path": rel_path,
                "skipped_file": None,
                "changes": changes,
                "rewritten": rewritten,
            })
    return reports
