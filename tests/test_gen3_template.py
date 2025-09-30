import os
import tempfile
import yaml
import pytest
from unittest.mock import patch
from gen3schemadev.schema.gen3_template import generate_gen3_template
from gen3schemadev.utils import load_yaml

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
                "description": "Version of the entity.",
                "default": "1.0.0"
            },
            "id": {
                "type": "string",
                "description": "Unique identifier for the entity."
            },
            "title": {
                "type": "string",
                "description": "Name of the entity.",
                "default": "default_entity_title"
            }
        }
    }
    return metaschema_content

def test_generate_gen3_template_output(fixture_minimum_metaschema):
    metaschema_dict = fixture_minimum_metaschema
    dummy_path = "dummy_path.yml"
    with patch("gen3schemadev.schema.gen3_template.load_yaml", return_value=metaschema_dict):
        result = generate_gen3_template(dummy_path)
    expected = {
        '$schema': 'http://json-schema.org/draft-04/schema#',
        'version': "1.0.0",
        'id': None,
        'title': "default_entity_title"
    }
    # Only keys present in the metaschema properties will be in the result
    # So update expected to only those keys
    assert result == expected

