"""Diagnostics for ``$ref`` usage in Gen3 data dictionaries.

Gen3's resolver merges a property's sibling keys over the referenced
definition, so writing annotations next to a ``$ref`` is the normal,
working form::

    atrial_fibrillation:
      description: "Self-reported atrial fibrillation."
      $ref: "_definitions.yaml#/enum_yes_no"

The real hazard is a ``description: null`` placeholder inside a shared
definition (commonly the enum definitions in ``_definitions.yaml``): the
Gen3 metaschema requires ``description`` to be a string, and the null shows
up as "No Description" in the data-dictionary viewer and fails metaschema
validation on resolved node schemas — far from the definition that carries
it. ``find_null_descriptions`` reports every such placeholder by path so
the root cause is named up front.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

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


def _ref_target_exists(ref: str, bundle: dict, source: str) -> bool:
    """
    Return True if ``ref`` points at something that exists in ``bundle``.

    A ref of the form ``file.yaml#/a/b`` is looked up in the bundle by
    filename; a bare ``#/a/b`` is looked up inside the schema that carries it,
    which is why ``source`` is needed.
    """
    file_part, _, key_part = ref.partition("#")
    file_part = file_part.strip()
    target = bundle.get(file_part) if file_part else bundle.get(source)
    if target is None:
        return False
    for part in key_part.strip("/").split("/"):
        if not part:
            continue
        if not isinstance(target, dict) or part not in target:
            return False
        target = target[part]
    return True


def _walk_refs(bundle: dict, node, path: str, source: str) -> list:
    """Recursively collect dangling ``$ref`` hits under ``node``."""
    hits = []
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and not _ref_target_exists(ref, bundle, source):
            hits.append((source, path.lstrip("."), ref))
        for key, value in node.items():
            hits.extend(_walk_refs(bundle, value, f"{path}.{key}", source))
    elif isinstance(node, list):
        for i, item in enumerate(node):
            hits.extend(_walk_refs(bundle, item, f"{path}[{i}]", source))
    return hits


def find_dangling_refs(bundle: dict) -> list:
    """
    Find every ``$ref`` in a bundled dictionary whose target does not exist.

    The resolver this tool ships raises a bare ``KeyError`` naming only the
    missing key - ``'file_format'`` - with no indication of which file or which
    property asked for it, which leaves the reader grepping ninety definitions.
    This walks the bundle up front and names all three, so they can go straight
    to the line.

    Args:
        bundle: The whole bundled dictionary, keyed by filename.

    Returns:
        A list of ``(source_file, dotted_path, ref)`` tuples. Paths use the
        same ``.key`` and ``[i]`` notation as :func:`find_null_descriptions`.
    """
    hits = []
    for name, schema in bundle.items():
        hits.extend(_walk_refs(bundle, schema, "", name))
    return hits


def find_null_descriptions(node, path: str = "") -> list:
    """
    Recursively find every ``description`` key whose value is null.

    The Gen3 metaschema requires ``description`` to be a string, so a
    ``description: null`` placeholder (common in generated shared
    definitions) is invalid. Because the property's own description merges
    over the definition's during resolution, the null often stays hidden
    until it surfaces on some resolved node schema — where the resulting
    metaschema failure points far away from the definition that caused it.

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
