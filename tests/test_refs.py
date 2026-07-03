"""
Tests for gen3schemadev.refs — the transform that makes ``$ref`` properties
safe under JSON Schema draft-04.

Background for these tests: Gen3 data dictionaries are resolved with
draft-04 semantics, where a ``$ref`` inside an object REPLACES the whole
object — any sibling keyword (``description``, ``termDef``, ``term``, ...)
is silently ignored. A property written as::

    atrial_fibrillation:
      description: "Self-reported atrial fibrillation."
      $ref: "_definitions.yaml#/enum_yes_no"

therefore shows up as "No Description" in the data-dictionary viewer. The
fix is to move the ``$ref`` into an ``allOf`` list so the annotations become
siblings of ``allOf`` (which draft-04 keeps) instead of siblings of ``$ref``
(which draft-04 drops)::

    atrial_fibrillation:
      description: "Self-reported atrial fibrillation."
      allOf:
      - $ref: "_definitions.yaml#/enum_yes_no"

The transform must be conservative: bare refs (nothing to lose), refs
already inside allOf/anyOf/oneOf (already fixed), and the Gen3
properties-merge construct (a ``$ref`` KEY directly inside ``properties:``)
must never be touched, and running the fix twice must change nothing.
"""

import copy

from gen3schemadev.refs import (
    ALREADY_WRAPPED,
    BARE_REF,
    NO_REF,
    PROPERTIES_MERGE,
    WRAPPED,
    fix_schema,
    fix_yaml_dir,
    wrap_ref_siblings,
)
from gen3schemadev.utils import load_yaml, write_yaml


def test_wrap_ref_siblings_preserves_description():
    """
    Input: a property with a description sitting as a direct sibling of
    $ref (the broken draft-04 pattern). Expected output: the description
    stays top-level and the $ref moves into allOf, so nothing is lost when
    Gen3 resolves the schema.
    """
    prop = {
        "description": "Self-reported atrial fibrillation.",
        "$ref": "_definitions.yaml#/enum_yes_no",
    }
    new_prop, action = wrap_ref_siblings(prop)
    assert action == WRAPPED
    assert new_prop == {
        "description": "Self-reported atrial fibrillation.",
        "allOf": [{"$ref": "_definitions.yaml#/enum_yes_no"}],
    }


def test_wrap_ref_siblings_preserves_multiple_annotations_and_order():
    """
    Input: a property with several sibling annotations (systemAlias,
    description, termDef) around a $ref. Expected output: every annotation
    is kept byte-for-byte, in its original order, with allOf appended last.
    Key order matters because the YAML files are committed and reviewed —
    annotations-first keeps diffs and files readable.
    """
    prop = {
        "systemAlias": "node_id",
        "description": "UUID for the project.",
        "termDef": {"term": "UUID", "source": "NCIt"},
        "$ref": "_definitions.yaml#/UUID",
    }
    new_prop, action = wrap_ref_siblings(prop)
    assert action == WRAPPED
    assert list(new_prop.keys()) == ["systemAlias", "description", "termDef", "allOf"]
    assert new_prop["systemAlias"] == "node_id"
    assert new_prop["description"] == "UUID for the project."
    assert new_prop["termDef"] == {"term": "UUID", "source": "NCIt"}
    assert new_prop["allOf"] == [{"$ref": "_definitions.yaml#/UUID"}]


def test_wrap_ref_siblings_leaves_bare_ref():
    """
    Input: a property that is ONLY a $ref, e.g. a link property like
    {"$ref": "_definitions.yaml#/to_one"}. There are no siblings for
    draft-04 to drop, so wrapping would add noise for no benefit — the
    property must be returned unchanged.
    """
    prop = {"$ref": "_definitions.yaml#/to_one"}
    new_prop, action = wrap_ref_siblings(prop)
    assert action == BARE_REF
    assert new_prop is prop


def test_wrap_ref_siblings_idempotent_on_already_wrapped():
    """
    Feeding the output of a wrap back into the transform must return it
    unchanged. This is the idempotency guarantee: running fix-refs a second
    time over an already-fixed dictionary produces zero edits, so the
    command is safe to re-run (e.g. in CI or after a partial fix).
    """
    original = {
        "description": "Self-reported atrial fibrillation.",
        "$ref": "_definitions.yaml#/enum_yes_no",
    }
    wrapped_once, _ = wrap_ref_siblings(original)
    wrapped_twice, action = wrap_ref_siblings(copy.deepcopy(wrapped_once))
    assert action == ALREADY_WRAPPED
    assert wrapped_twice == wrapped_once


def test_wrap_ref_siblings_appends_to_existing_allof():
    """
    Edge case: a property that already has an allOf list AND a top-level
    $ref beside it. The $ref must be appended to the existing allOf, not
    overwrite it, so no existing constraint is lost.
    """
    prop = {
        "description": "A constrained value.",
        "allOf": [{"minimum": 0}],
        "$ref": "_definitions.yaml#/positive_int",
    }
    new_prop, action = wrap_ref_siblings(prop)
    assert action == WRAPPED
    assert new_prop["allOf"] == [
        {"minimum": 0},
        {"$ref": "_definitions.yaml#/positive_int"},
    ]


def test_wrap_ref_siblings_no_ref_untouched():
    """
    An ordinary property with no $ref anywhere (e.g. a plain string field)
    must pass through unchanged with the NO_REF action, so the transform
    can be applied blindly to every property in a schema.
    """
    prop = {"type": "string", "description": "Free text notes"}
    new_prop, action = wrap_ref_siblings(prop)
    assert action == NO_REF
    assert new_prop is prop


def test_fix_schema_skips_properties_merge_ref():
    """
    Gen3 schemas merge shared properties by placing a ``$ref`` KEY directly
    inside the ``properties:`` block::

        properties:
          $ref: _definitions.yaml#/ubiquitous_properties
          my_prop: {...}

    This is a property-merge construct, not a property definition — wrapping
    it would break every node in the dictionary. fix_schema must leave it
    exactly as-is and record it as PROPERTIES_MERGE, while still fixing the
    real properties around it.
    """
    schema = {
        "id": "subject",
        "properties": {
            "$ref": "_definitions.yaml#/ubiquitous_properties",
            "atrial_fibrillation": {
                "description": "Self-reported atrial fibrillation.",
                "$ref": "_definitions.yaml#/enum_yes_no",
            },
        },
    }
    new_schema, changes = fix_schema(schema)
    assert new_schema["properties"]["$ref"] == "_definitions.yaml#/ubiquitous_properties"
    assert new_schema["properties"]["atrial_fibrillation"] == {
        "description": "Self-reported atrial fibrillation.",
        "allOf": [{"$ref": "_definitions.yaml#/enum_yes_no"}],
    }
    actions = {name: action for name, action, _ in changes}
    assert actions["$ref"] == PROPERTIES_MERGE
    assert actions["atrial_fibrillation"] == WRAPPED


def test_fix_schema_leaves_nested_term_ref_untouched():
    """
    A property may carry a nested annotation object that is itself a bare
    ref, e.g. ``term: {$ref: _terms.yaml#/x}``. The property has no
    TOP-LEVEL $ref, so nothing is dropped by draft-04 at the property level
    and fix_schema must not rewrite it.
    """
    schema = {
        "properties": {
            "age": {
                "type": "integer",
                "term": {"$ref": "_terms.yaml#/age"},
            }
        }
    }
    new_schema, changes = fix_schema(schema)
    assert new_schema["properties"]["age"] == {
        "type": "integer",
        "term": {"$ref": "_terms.yaml#/age"},
    }
    assert changes == []


def _write_mini_dictionary(dirpath):
    """
    Build a three-file mini dictionary in dirpath:
    - subject.yaml: one broken property (description beside $ref) and one
      bare-ref link property.
    - sample.yaml: only bare refs and plain properties (nothing to fix).
    - _definitions.yaml: shared definitions, which must never be rewritten
      (a description added there would leak into every referencing property).
    """
    subject = {
        "id": "subject",
        "properties": {
            "$ref": "_definitions.yaml#/ubiquitous_properties",
            "atrial_fibrillation": {
                "description": "Self-reported atrial fibrillation.",
                "$ref": "_definitions.yaml#/enum_yes_no",
            },
            "projects": {"$ref": "_definitions.yaml#/to_one_project"},
        },
    }
    sample = {
        "id": "sample",
        "properties": {
            "$ref": "_definitions.yaml#/ubiquitous_properties",
            "subjects": {"$ref": "_definitions.yaml#/to_one"},
            "notes": {"type": "string", "description": "Free text notes"},
        },
    }
    definitions = {
        "enum_yes_no": {"enum": ["yes", "no"]},
        "to_one": {"type": "object"},
    }
    write_yaml(subject, str(dirpath / "subject.yaml"))
    write_yaml(sample, str(dirpath / "sample.yaml"))
    write_yaml(definitions, str(dirpath / "_definitions.yaml"))


def test_fix_yaml_dir_end_to_end(tmp_path):
    """
    Run fix_yaml_dir over a mini dictionary and check the full contract:
    the broken property is rewritten on disk into the allOf form, bare refs
    and _definitions.yaml are untouched, and a SECOND run reports zero
    wrapped properties and leaves every file byte-identical (idempotency).
    """
    _write_mini_dictionary(tmp_path)

    reports = fix_yaml_dir(str(tmp_path))
    by_path = {r["path"]: r for r in reports}

    # subject.yaml: the broken property was wrapped and the file rewritten
    assert by_path["subject.yaml"]["rewritten"] is True
    fixed = load_yaml(str(tmp_path / "subject.yaml"))
    assert fixed["properties"]["atrial_fibrillation"] == {
        "description": "Self-reported atrial fibrillation.",
        "allOf": [{"$ref": "_definitions.yaml#/enum_yes_no"}],
    }
    assert fixed["properties"]["$ref"] == "_definitions.yaml#/ubiquitous_properties"
    assert fixed["properties"]["projects"] == {"$ref": "_definitions.yaml#/to_one_project"}

    # sample.yaml had nothing to fix, _definitions.yaml was skipped entirely
    assert by_path["sample.yaml"]["rewritten"] is False
    assert by_path["_definitions.yaml"]["skipped_file"] == "definitions/terms/settings file"

    # Second run: nothing left to wrap, no file rewritten
    contents_before = {p.name: p.read_bytes() for p in tmp_path.glob("*.yaml")}
    second_reports = fix_yaml_dir(str(tmp_path))
    assert all(r["rewritten"] is False for r in second_reports)
    total_wrapped = sum(
        1 for r in second_reports for _, action, _ in r["changes"] if action == WRAPPED
    )
    assert total_wrapped == 0
    contents_after = {p.name: p.read_bytes() for p in tmp_path.glob("*.yaml")}
    assert contents_after == contents_before


def test_fix_yaml_dir_dry_run(tmp_path):
    """
    With dry_run=True the report must still list what WOULD be wrapped
    (so a user can preview which files get reserialized — PyYAML rewriting
    drops comments), but every file on disk must stay byte-identical.
    """
    _write_mini_dictionary(tmp_path)
    contents_before = {p.name: p.read_bytes() for p in tmp_path.glob("*.yaml")}

    reports = fix_yaml_dir(str(tmp_path), dry_run=True)
    by_path = {r["path"]: r for r in reports}
    subject_actions = {name: action for name, action, _ in by_path["subject.yaml"]["changes"]}
    assert subject_actions["atrial_fibrillation"] == WRAPPED
    assert by_path["subject.yaml"]["rewritten"] is False

    contents_after = {p.name: p.read_bytes() for p in tmp_path.glob("*.yaml")}
    assert contents_after == contents_before
