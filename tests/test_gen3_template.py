import os
import tempfile
import yaml
import pytest
from unittest.mock import patch
from gen3schemadev.schema.gen3_template import generate_gen3_template
from gen3schemadev.utils import load_yaml
from gen3schemadev.schema.gen3_template import *

def test_read_template_yaml():
    result = read_template_yaml('_settings.yaml')
    assert isinstance(result, dict)
    assert "enable_case_cache" in result

def test_get_metaschema():
    metaschema = get_metaschema()
    assert isinstance(metaschema, dict)
    assert "properties" in metaschema

@pytest.fixture
def fixture_minimum_metaschema():
    """
    Fixture that reads the metaschema YAML file and yields its path.
    """
    metaschema_content = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "properties": {
            "version": {
                "type": "string",
                "description": "Version of the node.",
                "default": "1.0.0"
            },
            "id": {
                "type": "string",
                "description": "Unique identifier for the node."
            },
            "title": {
                "type": "string",
                "description": "Name of the node.",
                "default": "default_node_title"
            }
        }
    }
    return metaschema_content

def test_generate_gen3_template_output(fixture_minimum_metaschema):
    metaschema_dict = fixture_minimum_metaschema
    result = generate_gen3_template(metaschema_dict)
    expected = {
        '$schema': 'http://json-schema.org/draft-04/schema#',
        'version': "1.0.0",
        'id': None,
        'title': "default_node_title"
    }
    # Only keys present in the metaschema properties will be in the result
    # So update expected to only those keys
    assert result == expected




def test_read_template_yaml_reads_yaml_file(tmp_path):
    # Create a temporary YAML file
    yaml_content = {"foo": "bar", "baz": [1, 2, 3]}
    file_path = tmp_path / "template.yml"
    with open(file_path, "w") as f:
        yaml.dump(yaml_content, f)
    # Patch __file__ to point to a dummy module in tmp_path
    import gen3schemadev.schema.gen3_template as gen3_template_mod
    orig_file = gen3_template_mod.__file__
    gen3_template_mod.__file__ = str(tmp_path / "dummy.py")
    try:
        # Place the file in a schema_templates subdir
        schema_templates = tmp_path / "schema_templates"
        schema_templates.mkdir()
        yaml_file = schema_templates / "template.yml"
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_content, f)
        result = read_template_yaml("template.yml")
        assert result == yaml_content
    finally:
        gen3_template_mod.__file__ = orig_file

def test_generate_def_template_reads_definitions_yaml():
    result = generate_def_template()
    # The result should be a dict and contain some known keys
    assert isinstance(result, dict)
    assert "UUID" in result or "id" in result

def test_generate_setting_template_reads_settings_yaml():
    result = generate_setting_template()
    assert isinstance(result, dict)
    assert "enable_case_cache" in result

def test_generate_terms_template_reads_terms_yaml():
    result = generate_terms_template()
    assert isinstance(result, dict)
    assert "id" in result
    # Should contain at least one term definition
    assert any(isinstance(v, dict) and "description" in v for k, v in result.items() if k != "id")

def test_generate_core_metadata_template_reads_core_metadata_yaml():
    result = generate_core_metadata_template()
    assert isinstance(result, dict)
    assert "id" in result
    assert result.get("id") == "core_metadata_collection"

def test_generate_project_template_reads_project_yaml():
    result = generate_project_template()
    assert isinstance(result, dict)
    assert "id" in result
    assert result.get("id") == "project"