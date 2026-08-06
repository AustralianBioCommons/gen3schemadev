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

def test_generate_program_template_reads_program_yaml():
    result = generate_program_template()
    assert isinstance(result, dict)
    assert "id" in result
    assert result.get("id") == "program"

# ---------------------------------------------------------------------------
# Shared property name sets
#
# These names drive the warning shown when a user's input declares a property
# that _definitions.yaml already supplies. They are read from the packaged
# definitions rather than hardcoded, because a hardcoded list is exactly how
# the old "reserved system property" rule drifted into banning names that Gen3
# uses on every node.
# ---------------------------------------------------------------------------

from gen3schemadev.schema.gen3_template import shared_property_names


def test_shared_property_names_matches_the_packaged_definitions():
    """
    Input: the 'ubiquitous_properties' block of the packaged _definitions.yaml.

    Expected: exactly the seven property names Gen3 gives every node.

    Why it matters: if this set drifts from the definitions actually written
    into a dictionary, the warning either misses real shadowing or invents it.
    Deriving it from the same file that is generated is what keeps the two
    honest.
    """
    assert shared_property_names('ubiquitous_properties') == {
        'type', 'id', 'submitter_id', 'state', 'project_id',
        'created_datetime', 'updated_datetime',
    }


def test_shared_property_names_follows_the_data_file_block_ref():
    """
    Input: the 'data_file_properties' block.

    Expected: a strict superset of the ubiquitous names, also containing
    file-specific ones such as file_name and md5sum.

    Why it matters: data_file_properties supplies the ubiquitous names through
    a nested '$ref: #/ubiquitous_properties' rather than listing them. Reading
    only the block's own keys would miss 'type' and 'id', so the warning would
    go quiet on exactly the file nodes most likely to declare them.
    """
    ubiquitous = shared_property_names('ubiquitous_properties')
    data_file = shared_property_names('data_file_properties')

    assert ubiquitous < data_file
    assert {'file_name', 'md5sum', 'file_state'} <= data_file


def test_shared_property_names_is_empty_for_an_unknown_block():
    """
    Input: a block name that is not in _definitions.yaml.

    Expected: an empty set rather than an exception.

    Why it matters: this runs during generate. A KeyError here would turn a
    missing definition into a crash in the middle of writing a dictionary.
    """
    assert shared_property_names('no_such_block') == set()


def test_shared_property_names_terminates_on_a_cyclic_definition(monkeypatch):
    """
    Input: a definitions block that references itself.

    Expected: the call returns instead of recursing forever.

    Why it matters: the lookup follows '$ref' chains, and a dictionary is a
    user-supplied file. A cycle in it should not hang generation with no
    output and no explanation.
    """
    import gen3schemadev.schema.gen3_template as template

    monkeypatch.setattr(template, 'generate_def_template', lambda: {
        'loop_a': {'$ref': '#/loop_b', 'a_prop': {'type': 'string'}},
        'loop_b': {'$ref': '#/loop_a', 'b_prop': {'type': 'string'}},
    })

    assert shared_property_names('loop_a') == {'a_prop', 'b_prop'}
