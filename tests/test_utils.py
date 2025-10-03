import os
import tempfile
import yaml
import json
import pytest

from gen3schemadev.utils import load_yaml, write_yaml, read_json, write_json, bundle_yamls

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
    yaml_dir = os.path.join(path_of_files, '../examples/schema/yaml')
    bundle = bundle_yamls(yaml_dir)
    assert "demographic" in bundle
    assert "subject" in bundle

def test_bundle_yamls_no_yamls():
    path_of_files = os.path.dirname(__file__)
    yaml_dir = os.path.join(path_of_files, '../examples/schema/json')
    with pytest.raises(Exception) as excinfo:
        bundle_yamls(yaml_dir)
    assert "No YAML files found in directory" in str(excinfo.value)