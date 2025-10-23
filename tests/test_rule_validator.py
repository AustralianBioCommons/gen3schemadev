from gen3schemadev.validators.rule_validator import RuleValidator
from gen3schemadev.utils import load_yaml
import pytest
import os

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


def test_props_cannot_be_system_props_pass(fixture_rule_validator_pass):
    # Should NOT raise any exception (pass scenario)
    assert fixture_rule_validator_pass.props_cannot_be_system_props() is True


def test_props_cannot_be_system_props_fail(fixture_rule_validator_fail):
    # Should raise a ValueError (wrapped in RuntimeError)
    with pytest.raises(RuntimeError) as excinfo:
        fixture_rule_validator_fail.props_cannot_be_system_props()
    # Check message for context
    assert "uses a reserved system property name" in str(excinfo.value)


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
