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
    assert len(props_fail) == 7
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
