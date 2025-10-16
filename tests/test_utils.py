import os
import tempfile
import yaml
import json
import pytest
import logging
from gen3schemadev.utils import *

def test_load_yaml():
    data = {"foo": "bar"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as tf:
        yaml.safe_dump(data, tf)
        path = tf.name
    try:
        assert load_yaml(path) == data
    finally:
        os.remove(path)

def test_load_yaml_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_yaml("no_such_file.yml")

def test_write_yaml_and_load_yaml():
    data = {"a": 1}
    with tempfile.NamedTemporaryFile(mode="r", suffix=".yml", delete=False) as tf:
        path = tf.name
    try:
        write_yaml(data, path)
        assert load_yaml(path) == data
    finally:
        os.remove(path)

def test_read_json():
    data = {"foo": [1, 2]}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
        json.dump(data, tf)
        path = tf.name
    try:
        assert read_json(path) == data
    finally:
        os.remove(path)

def test_read_json_file_not_found():
    with pytest.raises(FileNotFoundError):
        read_json("no_such_file.json")

def test_write_json_and_read_json():
    data = {"a": 2}
    with tempfile.NamedTemporaryFile(mode="r", suffix=".json", delete=False) as tf:
        path = tf.name
    try:
        write_json(data, path)
        assert read_json(path) == data
    finally:
        os.remove(path)

def test_bundle_yamls():
    path_of_files = os.path.dirname(__file__)
    yaml_dir = os.path.join(path_of_files, 'gen3_schema/examples/yaml')
    bundle = bundle_yamls(yaml_dir)
    assert "demographic.yaml" in bundle
    assert "subject.yaml" in bundle

def test_bundle_yamls_no_yamls():
    path_of_files = os.path.dirname(__file__)
    yaml_dir = os.path.join(path_of_files, 'gen3_schema/examples/json')
    with pytest.raises(Exception) as excinfo:
        bundle_yamls(yaml_dir)
    assert "No YAML files found in directory" in str(excinfo.value)

def test_resolve_schema_yaml_dir():
    path_of_files = os.path.dirname(__file__)
    schema_dir = os.path.join(path_of_files, "gen3_schema/examples/yaml")
    schema = resolve_schema(schema_dir=schema_dir)
    assert isinstance(schema, dict)
    assert len(schema) == 10

def test_resolve_schema_bundled_file():
    path_of_files = os.path.dirname(__file__)
    schema_file = os.path.join(path_of_files, "gen3_schema/testing/schema_dev_pass.json")
    schema = resolve_schema(schema_path=schema_file)
    assert isinstance(schema, dict)
    assert len(schema) == 10

@pytest.fixture
def fixture_resolved_schema_pass():
    """
    Fixture that returns a resolved Gen3 schema loaded from a bundled JSON file.
    """
    path_of_files = os.path.dirname(__file__)
    schema_file = os.path.join(path_of_files, "gen3_schema/testing/schema_dev_pass.json")
    schema = resolve_schema(schema_path=schema_file)
    return schema

@pytest.fixture
def fixture_resolved_schema_yaml_dir():
    """
    Fixture that returns a resolved Gen3 schema loaded from a directory of YAML files.
    """
    path_of_files = os.path.dirname(__file__)
    schema_file = os.path.join(path_of_files, "gen3_schema/examples/yaml/resolved")
    schema = resolve_schema(schema_dir=schema_file)
    return schema

