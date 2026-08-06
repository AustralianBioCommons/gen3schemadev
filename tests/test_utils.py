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



# ---------------------------------------------------------------------------
# Schema resolution
#
# Two defects lived here. The library resolves node schemas against the
# definitions alone, so any node referencing _terms.yaml directly failed - and
# those failures are logged and swallowed, so the caller silently received a
# subset. On the official Gen3 dictionary that was 10 nodes out of 29, each
# reported as a success while the other 19 went unmentioned. Separately, a
# reference to a term that does not exist crashed the whole command with a bare
# KeyError.
# ---------------------------------------------------------------------------

import json as _json

import pytest

from gen3schemadev.utils import (
    SchemaResolutionError, is_documentation_ref, resolve_schema,
)


def _write_bundle(tmp_path, bundle, name="bundle.json"):
    """Write a bundle to disk and return its path, since resolve_schema takes a file."""
    path = tmp_path / name
    path.write_text(_json.dumps(bundle))
    return str(path)


def _minimal_bundle():
    """A two-file bundle with one node that references a term directly."""
    return {
        '_definitions.yaml': {'state': {'type': 'string'}},
        '_terms.yaml': {'sample_term': {'description': 'What a sample is.'}},
        'sample.yaml': {
            'id': 'sample',
            'properties': {
                'state': {'$ref': '_definitions.yaml#/state'},
                'described': {'type': 'string', 'term': {'$ref': '_terms.yaml#/sample_term'}},
            },
        },
    }


def test_nodes_that_reference_terms_directly_are_resolved(tmp_path):
    """
    Input: a bundle whose node references _terms.yaml directly.

    Expected: the node appears in the resolved output, with the term's content
    merged in.

    Why it matters: the underlying library resolves nodes against the resolved
    definitions only, so a node like this raised a KeyError that the library
    logged and swallowed. The node then simply never appeared, and validate
    reported success for the nodes that did - so a dictionary could pass with
    most of it unchecked.
    """
    path = _write_bundle(tmp_path, _minimal_bundle())

    resolved = resolve_schema(schema_path=path)

    assert 'sample.yaml' in resolved
    assert resolved['sample.yaml']['properties']['described']['term']['description'] == (
        'What a sample is.'
    )


def test_a_dangling_term_reference_is_tolerated(tmp_path):
    """
    Input: a bundle whose node points a `term` at a key _terms.yaml lacks.

    Expected: resolution succeeds and the node is returned; the unresolvable
    term is simply absent.

    Why it matters: a `term` is an ontology pointer used for documentation, not
    a JSON Schema keyword, so nothing about the shape of the data depends on
    it. The dictionary Gen3 publishes carries exactly one of these, and
    refusing to validate because of it would mean refusing to validate the
    reference dictionary.
    """
    bundle = _minimal_bundle()
    bundle['sample.yaml']['properties']['described']['term'] = {'$ref': '_terms.yaml#/missing'}
    path = _write_bundle(tmp_path, bundle)

    resolved = resolve_schema(schema_path=path)

    assert 'sample.yaml' in resolved
    assert 'term' not in resolved['sample.yaml']['properties']['described']


def test_a_dangling_reference_outside_a_term_block_is_fatal(tmp_path):
    """
    Input: a bundle whose node property references a definition that does not
    exist - not inside a `term` block.

    Expected: SchemaResolutionError, naming the missing reference.

    Why it matters: tolerance is specific to documentation. A missing schema
    definition changes what the data is allowed to be, so it must not be swept
    up by the same leniency. Without this test, "tolerate dangling terms" could
    quietly become "tolerate anything".
    """
    bundle = _minimal_bundle()
    bundle['sample.yaml']['properties']['state'] = {'$ref': '_definitions.yaml#/nonexistent'}
    path = _write_bundle(tmp_path, bundle)

    with pytest.raises(SchemaResolutionError) as excinfo:
        resolve_schema(schema_path=path)

    assert '_definitions.yaml#/nonexistent' in str(excinfo.value)


def test_every_node_in_the_official_gen3_dictionary_resolves():
    """
    Input: the dictionary Gen3 publishes as its reference.

    Expected: all 28 node schemas resolve.

    Why it matters: this dictionary is the reason the change exists. Before it,
    resolution crashed outright on the dangling term; simulating past that,
    only 10 of 29 entries survived and the rest were silently dropped.
    """
    path = os.path.join(
        os.path.dirname(__file__), 'gen3_schema/examples/json', 'gen3_develop_schema.json'
    )

    resolved = resolve_schema(schema_path=path)

    assert len(resolved) == 28
    assert 'submitted_copy_number.yaml' in resolved


@pytest.mark.parametrize("path,expected", [
    ("file_format.term", True),
    ("properties.described.term", True),
    ("properties.described.terms[0]", True),
    ("properties.state", False),
    ("term_of_office.description", False),
])
def test_is_documentation_ref_only_matches_whole_term_segments(path, expected):
    """
    Input: dotted paths, some inside a `term` block and some merely containing
    the letters "term".

    Expected: only the real term blocks are treated as documentation.

    Why it matters: this predicate decides whether a broken reference is
    survivable or fatal. A sloppy substring match would let a property called
    `term_of_office` make a genuine schema error non-fatal.
    """
    assert is_documentation_ref(path) is expected
