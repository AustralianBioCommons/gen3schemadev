from gen3schemadev.validators.rule_validator import RuleValidator
from gen3schemadev.utils import load_yaml, read_json
import pytest
import os

OFFICIAL_DICTIONARY = os.path.join(
    os.path.dirname(__file__), 'gen3_schema/examples/json', 'gen3_develop_schema.json'
)

# Files in a bundle that describe the dictionary rather than a node, plus the
# preset the CLI excludes by default.
NON_NODE_FILES = {'_definitions', '_settings', '_terms', 'core_metadata_collection'}


def _link(name, target):
    """Build a complete Gen3 link, so tests only state what they care about."""
    return {
        'name': name,
        'backref': f'{name}_backref',
        'label': 'derived_from',
        'target_type': target,
        'multiplicity': 'one_to_one',
        'required': False,
    }


@pytest.fixture
def nested_subgroup_schema():
    """
    A node whose links nest a subgroup inside a subgroup.

    Shaped like `submitted_copy_number` in the official Gen3 dictionary, which
    is the real schema that exposed the one-level unwrapping bug.
    """
    return {
        'id': 'nested_node',
        'category': 'clinical',
        'links': [{
            'exclusive': False,
            'required': True,
            'subgroup': [
                _link('core_metadata_collections', 'core_metadata_collection'),
                {
                    'exclusive': True,
                    'required': False,
                    'subgroup': [_link('aliquots', 'aliquot'), _link('read_groups', 'read_group')],
                },
            ],
        }],
        'properties': {
            'core_metadata_collections': {'type': 'string'},
            'aliquots': {'type': 'string'},
            'read_groups': {'type': 'string'},
        },
    }

@pytest.fixture
def fixture_lipidomic_pass_schema():
    file_path = os.path.join(os.path.dirname(__file__), 'gen3_schema/testing/yaml_pass', 'lipidomics_file.yaml')
    return load_yaml(file_path)

@pytest.fixture
def fixture_lipidomic_fail_schema():
    file_path = os.path.join(os.path.dirname(__file__), 'gen3_schema/testing/yaml_fail', 'lipidomics_file.yaml')
    return load_yaml(file_path)


def test_rule_validator_pass_init(fixture_lipidomic_pass_schema):
    rule_validator = RuleValidator(fixture_lipidomic_pass_schema)
    assert rule_validator.schema['id'] == "lipidomics_file"


def test_rule_validator_fail_init(fixture_lipidomic_fail_schema):
    rule_validator = RuleValidator(fixture_lipidomic_fail_schema)
    assert rule_validator.schema['id'] == "lipidomics_file"


@pytest.fixture
def fixture_rule_validator_pass(fixture_lipidomic_pass_schema):
    return RuleValidator(fixture_lipidomic_pass_schema)

@pytest.fixture
def fixture_rule_validator_fail(fixture_lipidomic_fail_schema):
    return RuleValidator(fixture_lipidomic_fail_schema)


def test_get_links(fixture_rule_validator_pass, fixture_rule_validator_fail):
    links = fixture_rule_validator_pass._get_links()
    assert len(links) == 2
    assert links[0]['name'] == 'samples'
    
    links_fail = fixture_rule_validator_fail._get_links()
    assert len(links_fail) == 1


def test_get_props(fixture_rule_validator_pass, fixture_rule_validator_fail):
    props = fixture_rule_validator_pass._get_props()
    assert len(props) == 7
    assert "samples" in props
    
    props_fail = fixture_rule_validator_fail._get_props()
    assert len(props_fail) == 6
    assert "type" in props_fail


def test_data_file_link_core_metadata_pass(fixture_rule_validator_pass):
    # Should NOT raise any exception (pass scenario)
    assert fixture_rule_validator_pass.data_file_link_core_metadata() is True


def test_data_file_link_core_metadata_fail(fixture_rule_validator_fail):
    # Should raise a ValueError (wrapped in RuntimeError)
    with pytest.raises(RuntimeError) as excinfo:
        fixture_rule_validator_fail.data_file_link_core_metadata()
    # Check message for context
    assert "core_metadata_collection" in str(excinfo.value)
    assert "must include a link" in str(excinfo.value)


def test_link_props_exist_pass(fixture_rule_validator_pass):
    # Should NOT raise any exception (pass scenario)
    assert fixture_rule_validator_pass.link_props_exist() is True


def test_link_props_exist_fail(fixture_rule_validator_fail):
    # Should raise a ValueError (wrapped in RuntimeError)
    with pytest.raises(RuntimeError) as excinfo:
        fixture_rule_validator_fail.link_props_exist()
    # Check message for context
    assert "is missing from the 'properties' section" in str(excinfo.value)


def test_props_must_have_type_pass(fixture_rule_validator_pass):
    # Should NOT raise any exception (pass scenario)
    assert fixture_rule_validator_pass.props_must_have_type() is True


def test_props_must_have_type_fail():
    # Construct schema that will fail (property missing 'type' and 'enum')
    bad_schema = {
        "id": "test_schema",
        "properties": {
            "foo": { "description": "bar" },  # Missing 'type' and 'enum'
            "baz": { "type": "string" },      # Good property
        },
    }
    rule_validator = RuleValidator(bad_schema)
    with pytest.raises(ValueError) as excinfo:
        rule_validator.props_must_have_type()
    assert "must have a value for 'type' or 'enum'" in str(excinfo.value)


@pytest.mark.parametrize("combinator", ["allOf", "anyOf", "oneOf"])
def test_props_must_have_type_skips_combinator_wrapped_ref(combinator):
    """
    Some dictionaries in the wild write properties with the $ref wrapped in
    a combinator list (allOf/anyOf/oneOf) and annotations beside it:

        atrial_fibrillation:
          description: "Self-reported atrial fibrillation."
          allOf:
          - $ref: "_definitions.yaml#/enum_yes_no"

    This is valid JSON Schema. Such a property has no top-level 'type',
    'enum', or '$ref' — its type comes from the referenced definition —
    so props_must_have_type must treat it like a reference (skip it)
    rather than raising "must have a value for 'type' or 'enum'".
    """
    schema = {
        "id": "test_schema",
        "properties": {
            "atrial_fibrillation": {
                "description": "Self-reported atrial fibrillation.",
                combinator: [{"$ref": "_definitions.yaml#/enum_yes_no"}],
            },
        },
    }
    rule_validator = RuleValidator(schema)
    assert rule_validator.props_must_have_type() is True


def test_props_must_have_type_skips_sibling_ref():
    """
    The normal Gen3 form puts the $ref at the top level of the property,
    optionally with sibling annotations such as 'description' (Gen3's
    resolver merges the siblings over the referenced definition). Such a
    property is a reference and must be skipped by the type/enum rule.
    """
    schema = {
        "id": "test_schema",
        "properties": {
            "sibling_prop": {
                "description": "Property documented beside its $ref.",
                "$ref": "_definitions.yaml#/enum_yes_no",
            },
        },
    }
    rule_validator = RuleValidator(schema)
    assert rule_validator.props_must_have_type() is True


def test_data_file_props_need_data_props():
    schema = {
        "id": "my_data_file",
        "category": "data_file",
        "properties": {
            "data_type": {"type": "string"},
            "data_format": {"type": "string"},
            "data_category": {"type": "string"},
            "other": {"type": "string"}
        }
    }
    rv = RuleValidator(schema)
    assert rv.data_file_props_need_data_props() is True

    # Not a data_file node: should pass (returns True, does not care about props)
    non_data_file_schema = {
        "id": "my_non_data_file",
        "category": "project",
        "properties": {
            "some_field": {"type": "string"}
        }
    }
    rv2 = RuleValidator(non_data_file_schema)
    assert rv2.data_file_props_need_data_props() is True

    # Failing: missing required property
    missing_data_type = {
        "id": "bad_data_file",
        "category": "data_file",
        "properties": {
            "data_format": {"type": "string"},
            "data_category": {"type": "string"}
            # missing 'data_type'
        }
    }
    rv3 = RuleValidator(missing_data_type)
    with pytest.raises(ValueError) as excinfo:
        rv3.data_file_props_need_data_props()
    assert "must include properties" in str(excinfo.value)
    assert "data_type" in str(excinfo.value)

    # Failing: missing all required props
    missing_all = {
        "id": "bad_data_file2",
        "category": "data_file",
        "properties": {
            "foo": {"type": "string"},
        }
    }
    rv4 = RuleValidator(missing_all)
    with pytest.raises(ValueError) as excinfo2:
        rv4.data_file_props_need_data_props()
    assert "must include properties" in str(excinfo2.value)
    assert "data_type" in str(excinfo2.value)
    assert "data_format" in str(excinfo2.value)
    assert "data_category" in str(excinfo2.value)


def test_type_array_needs_items_passes_on_arrays_with_items():
    schema = {
        "id": "array_test_schema",
        "properties": {
            "string_list": {
                "type": "array",
                "items": {"type": "string"}
            },
            "int_list": {
                "type": "array",
                "items": {"type": "integer"}
            },
            "foo": {"type": "string"}
        }
    }
    rv = RuleValidator(schema)
    assert rv.type_array_needs_items() is True


def test_type_array_needs_items_fails_when_missing_items():
    schema = {
        "id": "array_bad_schema",
        "properties": {
            "string_list": {
                "type": "array"
                # missing "items"
            },
            "foo": {"type": "string"}
        }
    }
    rv = RuleValidator(schema)
    with pytest.raises(ValueError) as excinfo:
        rv.type_array_needs_items()
    assert "must include an 'items' property" in str(excinfo.value)
    assert "string_list" in str(excinfo.value)
    assert "array_bad_schema" in str(excinfo.value)


def test_type_array_needs_items_ignores_non_array_properties():
    schema = {
        "id": "array_ok_schema",
        "properties": {
            "foo": {"type": "string"},
            "bar": {"type": "integer"},
            "flag": {"type": "boolean"}
        }
    }
    rv = RuleValidator(schema)
    assert rv.type_array_needs_items() is True


def test_type_array_needs_items_skips_refs():
    schema = {
        "id": "array_ref_schema",
        "properties": {
            "referenced_prop": {"$ref": "#/definitions/foo"},
            "another_array": {
                "type": "array",
                "items": {"type": "number"}
            }
        }
    }
    rv = RuleValidator(schema)
    # The $ref property should be ignored, should not raise
    assert rv.type_array_needs_items() is True


def test_core_metadata_required_link_passes_when_required_link_exists():
    schema = {
        "id": "core_metadata_collection",
        "links": [
            {
                "name": "projects",
                "backref": "core_metadata_collections",
                "label": "data_from",
                "target_type": "project",
                "multiplicity": "many_to_one",
                "required": True,
            }
        ]
    }
    rv = RuleValidator(schema)
    assert rv.core_metadata_required_link() is True


def test_core_metadata_required_link_fails_when_no_required_true():
    schema = {
        "id": "core_metadata_collection",
        "links": [
            {
                "name": "projects",
                "backref": "core_metadata_collections",
                "label": "data_from",
                "target_type": "project",
                "multiplicity": "many_to_one",
                # required omitted or set to False
            },
            {
                "name": "secondary",
                "required": False
            }
        ]
    }
    rv = RuleValidator(schema)
    with pytest.raises(ValueError) as excinfo:
        rv.core_metadata_required_link()
    assert "must include at least one required link" in str(excinfo.value)
    assert "core_metadata_collection" in str(excinfo.value)


def test_core_metadata_required_link_skips_if_not_core_metadata_collection():
    schema = {
        "id": "another_node",
        "links": [
            {
                "name": "some_link",
                "required": False
            }
        ]
    }
    rv = RuleValidator(schema)
    # Should silently pass since id is NOT core_metadata_collection
    assert rv.core_metadata_required_link() is True


def test_project_must_require_code_passes_when_code_in_required():
    """The project node in Gen3 must always have 'code' as a required property.
    This is because Gen3 uses 'code' as the unique project identifier internally.
    This test confirms validation passes when 'code' is present in the required list.
    """
    schema = {
        "id": "project",
        "required": ["code", "name", "programs", "dbgap_accession_number"],
        "properties": {
            "code": {"type": "string"},
            "name": {"type": "string"},
        },
    }
    rv = RuleValidator(schema)
    assert rv.project_must_require_code() is True


def test_project_must_require_code_fails_when_code_missing():
    """The project node must have 'code' in its required list.
    If a project schema omits 'code' from required, Gen3 will not function correctly
    because it relies on 'code' as the unique project identifier.
    This test confirms a ValueError is raised when 'code' is absent.
    """
    schema = {
        "id": "project",
        "required": ["name", "programs"],
        "properties": {
            "name": {"type": "string"},
        },
    }
    rv = RuleValidator(schema)
    with pytest.raises(ValueError) as excinfo:
        rv.project_must_require_code()
    assert "code" in str(excinfo.value)
    assert "project" in str(excinfo.value)


def test_project_must_require_code_skips_non_project_schemas():
    """The 'code' requirement only applies to the project node.
    Other nodes should not be affected by this rule.
    This test confirms non-project schemas are silently skipped.
    """
    schema = {
        "id": "sample",
        "required": ["submitter_id"],
        "properties": {
            "sample_id": {"type": "string"},
        },
    }
    rv = RuleValidator(schema)
    assert rv.project_must_require_code() is True


# ---------------------------------------------------------------------------
# Properties Gen3 itself supplies are not reserved
#
# `validate` used to reject any property named `type`, `id`, `state`,
# `submitter_id` and so on, as "reserved system property names". That list was
# essentially Gen3's own `ubiquitous_properties` block, so the rule rejected the
# dictionary Gen3 publishes as its own reference - and contradicted this tool's
# generator, which forces `submitter_id` and `type` into every node's `required`
# list. The rule was removed; these tests pin what replaced it.
# ---------------------------------------------------------------------------


def test_declaring_gen3_supplied_properties_is_accepted():
    """
    Input: a node declaring `type`, `state` and `submitter_id` as properties.

    Expected: validate() returns an empty list - no violations.

    Why it matters: 27 of the 28 node schemas in the official Gen3 dictionary
    declare a literal `type` property, and `aliquot` declares it alongside
    `systemProperties: [id, project_id, state, ...]`. This is ordinary Gen3
    practice, not a mistake, and rejecting it made validate unusable against
    real dictionaries.
    """
    schema = {
        'id': 'aliquot_like',
        'category': 'clinical',
        'properties': {
            'type': {'type': 'string'},
            'state': {'type': 'string'},
            'submitter_id': {'type': 'string'},
            'aliquot_quantity': {'type': 'number'},
        },
    }

    assert RuleValidator(schema).validate() == []


def test_data_file_node_may_declare_type_as_an_enum():
    """
    Input: a data_file node whose `type` property is an enum of the node name.

    Expected: no violations.

    Why it matters: this is how every data_file node in the official
    dictionary declares `type`. A narrower fix that only allowed
    `type: {type: string}` would have kept rejecting all of them.
    """
    schema = {
        'id': 'submitted_aligned_reads',
        'category': 'data_file',
        'links': [_link('core_metadata_collections', 'core_metadata_collection')],
        'properties': {
            'type': {'enum': ['submitted_aligned_reads']},
            'core_metadata_collections': {'type': 'string'},
            'data_type': {'type': 'string'},
            'data_format': {'type': 'string'},
            'data_category': {'type': 'string'},
        },
    }

    assert RuleValidator(schema).validate() == []


def test_the_official_gen3_dictionary_has_no_rule_violations():
    """
    Input: every node of the dictionary Gen3 publishes at
    dictionary-artifacts/datadictionary/develop/schema.json.

    Expected: not one rule violation across the whole dictionary.

    Why it matters: this is the reference dictionary Gen3 ships. If this tool
    rejects it, the tool is wrong, not the dictionary. Before this change
    validate died on the very first node. Kept at unit level rather than
    through the CLI so it needs no subprocess and stays fast.
    """
    bundle = read_json(OFFICIAL_DICTIONARY)

    violations = []
    for file_name, schema in bundle.items():
        if os.path.splitext(file_name)[0] in NON_NODE_FILES:
            continue
        violations.extend(RuleValidator(schema).validate())

    assert violations == []


# ---------------------------------------------------------------------------
# Nested link subgroups
# ---------------------------------------------------------------------------


def test_get_links_flattens_a_nested_subgroup(nested_subgroup_schema):
    """
    Input: a schema whose links nest a subgroup inside a subgroup.

    Expected: all three concrete links are returned, and every one has a name.

    Why it matters: the old code unwrapped only the outer level, leaving the
    inner group dict in the list. A group dict has no 'name', so the tool
    reported a missing property for a link called 'None' - an error naming
    something that does not appear anywhere in the user's file.
    """
    links = RuleValidator(nested_subgroup_schema)._get_links()

    assert sorted(link['name'] for link in links) == [
        'aliquots', 'core_metadata_collections', 'read_groups',
    ]
    assert all(link.get('name') for link in links)


def test_link_props_exist_accepts_links_inside_a_nested_subgroup(nested_subgroup_schema):
    """
    Input: the nested-subgroup schema, with a property for each of its links.

    Expected: the rule passes.

    Why it matters: this is the shape of `submitted_copy_number` in the
    official dictionary, and it was the only rule failure left there once the
    reserved-property rule was removed.
    """
    assert RuleValidator(nested_subgroup_schema).link_props_exist() is True


def test_link_props_exist_still_catches_a_missing_property_inside_a_nested_subgroup(
    nested_subgroup_schema,
):
    """
    Input: the same schema with the `read_groups` property deleted, so a link
    inside the nested subgroup has nothing backing it.

    Expected: the rule fails and names `read_groups`.

    Why it matters: flattening was added so nested links are checked properly,
    not so they stop being checked. Without this test, a bug that skipped
    nested links entirely would look identical to the fix.
    """
    del nested_subgroup_schema['properties']['read_groups']

    with pytest.raises(RuntimeError) as excinfo:
        RuleValidator(nested_subgroup_schema).link_props_exist()

    assert 'read_groups' in str(excinfo.value)
    assert "is missing from the 'properties' section" in str(excinfo.value)


def test_get_links_returns_links_beyond_the_first_entry():
    """
    Input: a schema with two top-level link entries, the first a subgroup.

    Expected: links from both entries are returned.

    Why it matters: the old code returned only `links[0]['subgroup']` and
    silently discarded everything after it, so a link defined in a second entry
    was never checked at all - a validator quietly not validating.
    """
    schema = {
        'id': 'two_entry_node',
        'links': [
            {'exclusive': False, 'required': True,
             'subgroup': [_link('samples', 'sample')]},
            _link('projects', 'project'),
        ],
    }

    links = RuleValidator(schema)._get_links()

    assert sorted(link['name'] for link in links) == ['projects', 'samples']


# ---------------------------------------------------------------------------
# Reporting every failure, not just the first
# ---------------------------------------------------------------------------


def test_validate_reports_every_broken_rule_not_just_the_first():
    """
    Input: a data_file node that both lacks a core_metadata_collections link
    and is missing the required data_ properties - two independent failures.

    Expected: validate() returns two violations, naming both rules.

    Why it matters: validate used to raise on the first failure, so a
    dictionary with six problems took six edit-run-edit cycles to fix, each run
    revealing only the next one. The rules are independent, so there is no
    reason to hide the rest.
    """
    schema = {
        'id': 'broken_file',
        'category': 'data_file',
        'links': [],
        'properties': {'file_name': {'type': 'string'}},
    }

    violations = RuleValidator(schema).validate()

    assert {v['rule'] for v in violations} == {
        'data_file_link_core_metadata', 'data_file_props_need_data_props',
    }
    assert all(v['schema'] == 'broken_file' for v in violations)


def test_validate_returns_nothing_for_a_clean_schema(fixture_rule_validator_pass):
    """
    Input: a schema that satisfies every rule.

    Expected: an empty list.

    Why it matters: the empty list is what the CLI treats as success. If a
    clean schema produced anything at all, every dictionary would fail.
    """
    assert fixture_rule_validator_pass.validate() == []


def test_validate_unwraps_the_legacy_runtime_error_wrapper():
    """
    Input: a data_file node with no core metadata link, checked through
    validate() rather than by calling the rule directly.

    Expected: the reported message is the underlying explanation, with no
    "Exception occurred while validating" wrapper text.

    Why it matters: two of the older rules re-wrap their own ValueError in a
    RuntimeError, which buried a clear sentence inside a nested traceback. The
    collector strips that layer so the reader sees the sentence that was
    written for them.
    """
    schema = {
        'id': 'wrapped',
        'category': 'data_file',
        'links': [],
        'properties': {
            'data_type': {'type': 'string'},
            'data_format': {'type': 'string'},
            'data_category': {'type': 'string'},
        },
    }

    violations = RuleValidator(schema).validate()

    assert len(violations) == 1
    assert 'must include a link' in violations[0]['message']
    assert 'Exception occurred while validating' not in violations[0]['message']
