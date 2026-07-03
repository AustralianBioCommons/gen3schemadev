"""
End-to-end proof that a dictionary rewritten by ``fix-refs`` still compiles.

Background: the ``fix-refs`` command rewrites properties that have
annotations (``description``, ``termDef``, ...) sitting as direct siblings
of a ``$ref`` — a pattern that JSON Schema draft-04 silently drops — into
the safe form where the ``$ref`` lives inside an ``allOf`` list. A fix like
this is only acceptable if the rewritten dictionary still passes the
project's full validation pipeline, which is exactly what ``gen3schemadev
validate`` runs:

1. ``RuleValidator`` — Gen3-specific business rules per node schema,
2. ``resolve_schema`` — inlines every ``$ref`` via gen3-validator,
3. ``validate_schema_with_metaschema`` — checks each resolved schema
   against the Gen3 metaschema (draft-04 based).

This test copies the committed legacy-form example dictionary (which still
contains old-style sibling refs, e.g. project.yaml's ``id``), runs the
fixer over it, and then pushes the result through all three stages. If any
stage raises, the fix would break real dictionaries.
"""

import os
import shutil

import pytest

from gen3schemadev.refs import fix_yaml_dir
from gen3schemadev.schema.gen3_template import get_metaschema
from gen3schemadev.utils import load_yaml, resolve_schema
from gen3schemadev.validators.metaschema_validator import validate_schema_with_metaschema
from gen3schemadev.validators.rule_validator import RuleValidator

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "gen3_schema", "examples", "yaml")

# Same exclusion list the `validate` CLI command uses for rule validation:
# these are shared/auxiliary schemas, not user-defined node schemas.
RULE_VALIDATION_EXCLUDE = {
    "_definitions",
    "_settings",
    "_terms",
    "core_metadata_collection",
}


@pytest.fixture
def fixed_dictionary(tmp_path):
    """
    A copy of the committed example dictionary (legacy form, sibling $refs
    included) after one pass of fix_yaml_dir. Only the top-level YAML files
    are copied — the resolved/ subdirectory holds resolver outputs, not
    node schemas.
    """
    for fname in os.listdir(EXAMPLES_DIR):
        src = os.path.join(EXAMPLES_DIR, fname)
        if os.path.isfile(src) and fname.endswith((".yaml", ".yml")):
            shutil.copy(src, tmp_path / fname)
    fix_yaml_dir(str(tmp_path))
    return tmp_path


def test_fixed_dictionary_passes_full_validation(fixed_dictionary, monkeypatch):
    """
    Input: the example dictionary after fix-refs. Expected: every node
    schema passes RuleValidator, the whole dictionary resolves without
    errors, and every resolved schema validates against the Gen3
    metaschema — i.e. the fixed dictionary still compiles end to end.

    monkeypatch.chdir is needed because resolve_schema writes its temporary
    bundle into the current working directory.
    """
    # Stage 1: business rules per node schema. The committed example
    # project.yaml already fails one pre-existing rule before any fix
    # (consent_codes is 'type: array' without 'items'), so the contract
    # asserted here is: fix-refs must never turn a passing schema into a
    # failing one.
    for fname in sorted(os.listdir(str(fixed_dictionary))):
        schema_name = os.path.splitext(fname)[0]
        if schema_name in RULE_VALIDATION_EXCLUDE:
            continue
        legacy_schema = load_yaml(os.path.join(EXAMPLES_DIR, fname))
        try:
            RuleValidator(legacy_schema).validate()
        except Exception:
            continue  # already failed before the fix; not a regression
        fixed_schema = load_yaml(str(fixed_dictionary / fname))
        RuleValidator(fixed_schema).validate()

    # Stage 2: resolve all $refs (draft-04 inlining via gen3-validator)
    monkeypatch.chdir(str(fixed_dictionary))
    resolved = resolve_schema(schema_dir=str(fixed_dictionary))
    assert resolved, "resolver returned an empty dictionary"

    # Stage 3: metaschema validation of every resolved schema
    metaschema = get_metaschema()
    for schema_name, schema in resolved.items():
        validate_schema_with_metaschema(schema, metaschema=metaschema)


def test_fix_rewrites_legacy_project_id(fixed_dictionary):
    """
    Spot-check the actual transformation on real fixture content: the
    example project.yaml carries the legacy pattern
    ``id: {$ref: UUID, systemAlias: node_id, description: ...}``. After
    fix-refs, the annotations must survive as siblings of allOf and the
    $ref target must be byte-for-byte unchanged inside allOf.
    """
    legacy = load_yaml(os.path.join(EXAMPLES_DIR, "project.yaml"))
    fixed = load_yaml(str(fixed_dictionary / "project.yaml"))

    legacy_id = legacy["properties"]["id"]
    assert "$ref" in legacy_id, "fixture no longer exercises the legacy pattern"

    fixed_id = fixed["properties"]["id"]
    assert "$ref" not in fixed_id
    assert fixed_id["allOf"] == [{"$ref": legacy_id["$ref"]}]
    for key, value in legacy_id.items():
        if key != "$ref":
            assert fixed_id[key] == value
