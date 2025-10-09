import pytest
from gen3schemadev.validators.input_validator import validate_input_yaml, load_yaml


@pytest.fixture
def fixture_input_yaml_pass():
    return "tests/input_example.yml"

@pytest.fixture
def fixture_input_yaml_fail():
    return "tests/input_example_fail.yml"

def test_load_yaml(fixture_input_yaml_pass):
    file_path = fixture_input_yaml_pass
    data = load_yaml(file_path)
    assert data is not None
    assert data.get("version") == "0.1.0"
    assert data.get("url") == "https://link-to-data-portal"



def test_validate_input_yaml(fixture_input_yaml_pass):
    file_path = fixture_input_yaml_pass
    data = validate_input_yaml(file_path)
    assert data is not None


from pydantic import ValidationError

def test_validate_input_yaml_fail(fixture_input_yaml_fail):
    file_path = fixture_input_yaml_fail
    with pytest.raises(ValidationError) as exc_info:
        validate_input_yaml(file_path)
    errors = str(exc_info.value)
    # Check for version pattern error
    assert "version" in errors  # version: 'v0.1.0' does not match pattern
    # Check for invalid URL error
    assert "url" in errors  # url: 'link-to-data-portal' is not a valid URL
    # Check for invalid multiplicity value in links
    assert "links.0.multiplicity" in errors  # multiplicity: 'one_to_heaps' is not allowed
    # Check for invalid category value in nodes
    assert "nodes.0.category" in errors  # category: 'random_file' is not allowed