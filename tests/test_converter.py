import pytest
from gen3schemadev.schema.gen3_template import *
from gen3schemadev.utils import *
from gen3schemadev.schema.input_schema import DataModel
from gen3schemadev.converter import *

@pytest.fixture
def fixture_converter_template():
    metaschema = get_metaschema()
    return generate_gen3_template(metaschema)

@pytest.fixture
def fixture_input_yaml_pass():
    data = load_yaml("tests/input_example.yml")
    return DataModel.model_validate(data)


def test_get_entity_data(fixture_input_yaml_pass):
    entity = get_entity_data('lipidomics_file', fixture_input_yaml_pass)
    assert entity.name == 'lipidomics_file'
    assert entity.description == 'Info about lipidomics file'
    assert entity.category.value == 'data_file'
    assert isinstance(entity.properties, list)

def test_get_entity_data_not_found(fixture_input_yaml_pass):
    with pytest.raises(ValueError) as excinfo:
        get_entity_data('nonexistent_entity', fixture_input_yaml_pass)
    assert "Entity 'nonexistent_entity' not found in data.entities" in str(excinfo.value)


def test_get_entity_links(fixture_input_yaml_pass):
    links = get_entity_links('lipidomics_file', fixture_input_yaml_pass)
    assert len(links) == 2
    assert dict(links[0]) == {'parent': 'sample', 'multiplicity': 'one_to_many', 'child': 'lipidomics_file'}



def test_create_core_metadata_link():
    child_name = "lipidomics_file"
    link_dict = create_core_metadata_link(child_name)
    assert isinstance(link_dict, dict)
    assert link_dict["name"] == "core_metadata_collections"
    assert link_dict["backref"] == "lipidomics_files"
    assert link_dict["target_type"] == "core_metadata_collection"
    assert link_dict["multiplicity"] == "one_to_one"
    assert link_dict["required"] is True
    # label is None
    assert "label" in link_dict and link_dict["label"] is None
    # The dict should not have unexpected keys
    expected_keys = {"name", "backref", "label", "target_type", "multiplicity", "required"}
    assert set(link_dict.keys()) == expected_keys



def test_convert_entity_links():
    # Prepare a list of link dicts as would be returned by get_entity_links
    links = [
        {"parent": "sample", "multiplicity": "many_to_one", "child": "lipidomics_file"},
        {"parent": "project", "multiplicity": "one_to_many", "child": "sample"},
    ]
    # Call the function
    result = convert_entity_links(links, required=True)
    # Should return a list of dicts, one for each input link
    assert isinstance(result, list)
    assert len(result) == 2
    # Check the structure of the first link
    link0 = result[0]
    assert link0["name"] == "samples"
    assert link0["backref"] == "lipidomics_files"
    assert link0["target_type"] == "sample"
    assert link0["multiplicity"] == "many_to_one"
    assert link0["required"] is True
    assert "label" in link0 and link0["label"] is None

    # Check the structure of the second link
    link1 = result[1]
    assert link1["name"] == "projects"
    assert link1["backref"] == "samples"
    assert link1["target_type"] == "project"
    assert link1["multiplicity"] == "one_to_many"
    assert link1["required"] is True
    assert "label" in link1 and link1["label"] is None

    # Test with required=False
    result2 = convert_entity_links(links, required=False)
    assert all(link["required"] is False for link in result2)



def test_add_core_metadata_link():
    # Prepare a list of link dicts (as would be output from convert_entity_links)
    links = [
        {
            "name": "samples",
            "backref": "lipidomics_files",
            "label": None,
            "target_type": "sample",
            "multiplicity": "many_to_one",
            "required": True,
        }
    ]
    child_name = "lipidomics_file"
    # Call the function
    result = add_core_metadata_link(links, child_name)
    # Should return a new list with one more element
    assert isinstance(result, list)
    assert len(result) == 2
    # The first element should be the original link
    assert result[0] == links[0]
    # The second element should be the core metadata link
    core_link = result[1]
    assert isinstance(core_link, dict)
    assert core_link["name"] == "core_metadata_collections"
    assert core_link["backref"] == "lipidomics_files"
    assert core_link["target_type"] == "core_metadata_collection"
    assert core_link["multiplicity"] == "one_to_one"
    assert core_link["required"] is True
    assert "label" in core_link and core_link["label"] is None
    # The dict should not have unexpected keys
    expected_keys = {"name", "backref", "label", "target_type", "multiplicity", "required"}
    assert set(core_link.keys()) == expected_keys


def test_create_link_group():
    # Prepare a list of link dicts
    links = [
        {
            "name": "samples",
            "backref": "lipidomics_files",
            "label": None,
            "target_type": "sample",
            "multiplicity": "many_to_one",
            "required": True,
        },
        {
            "name": "core_metadata_collections",
            "backref": "lipidomics_files",
            "label": None,
            "target_type": "core_metadata_collection",
            "multiplicity": "one_to_one",
            "required": True,
        }
    ]
    # Call the function with default exclusive and required
    group = create_link_group(links)
    assert isinstance(group, dict)
    assert "exclusive" in group
    assert "required" in group
    assert "subgroup" in group
    assert group["exclusive"] is False
    assert group["required"] is True
    assert isinstance(group["subgroup"], list)
    assert group["subgroup"] == links

    # Call the function with exclusive=True, required=False
    group2 = create_link_group(links, exclusive=True, required=False)
    assert group2["exclusive"] is True
    assert group2["required"] is False
    assert group2["subgroup"] == links


def test_create_link_prop():
    # Test with a typical entity and multiplicity
    prop = create_link_prop("sample", "one_to_many")
    assert isinstance(prop, dict)
    # The key should be the link_suffix of "sample", which is "samples"
    assert "samples" in prop
    # The value should be a dict with a $ref key
    assert isinstance(prop["samples"], dict)
    assert "$ref" in prop["samples"]
    assert prop["samples"]["$ref"] == "_definitions.yaml#/one_to_many"

    # Test with another entity and multiplicity
    prop2 = create_link_prop("core_metadata_collection", "one_to_one")
    assert "core_metadata_collections" in prop2
    assert prop2["core_metadata_collections"]["$ref"] == "_definitions.yaml#/one_to_one"

    # Test that only one key exists in the returned dict
    assert len(prop) == 1
    assert len(prop2) == 1

    # Test with unusual entity name
    prop3 = create_link_prop("weird_entity", "many_to_one")
    assert "weird_entitys" in prop3
    assert prop3["weird_entitys"]["$ref"] == "_definitions.yaml#/many_to_one"



def test_get_properties(fixture_input_yaml_pass):
    result = get_properties("project", fixture_input_yaml_pass)
    expected = [
        {
            'project_id': {
                'type': 'string',
                'description': 'Synthetic_Dataset_1',
                'required': True,
                'enums': None
            }
        },
        {
            'description': {
                'type': 'string',
                'description': 'Project containing synthetic data',
                'required': False,
                'enums': None
            }
        }
    ]

    assert isinstance(result, list)
    assert len(result) == 2
    assert result == expected




def test_construct_prop(fixture_input_yaml_pass):
    result = construct_props("lipidomics_file", fixture_input_yaml_pass)
    expected = {
        'samples': {'$ref': '_definitions.yaml#/one_to_many'},
        'assays': {'$ref': '_definitions.yaml#/one_to_many'}
    }
    assert result == expected


def test_get_category(fixture_input_yaml_pass):
    result = get_category("lipidomics_file", fixture_input_yaml_pass)
    expected = "data_file"
    assert result == expected


def test_get_entity_value(fixture_input_yaml_pass):
    assert 'Info about lipidomics file' == get_entity_value("lipidomics_file", 'description', fixture_input_yaml_pass)


def test_is_file_entity(fixture_input_yaml_pass):
    assert is_file_entity("lipidomics_file", fixture_input_yaml_pass)
    assert not is_file_entity("sample", fixture_input_yaml_pass)

@pytest.fixture
def fixture_expected_output_lipid():
    output = {
        '$schema': 'http://json-schema.org/draft-04/schema#',
        'version': None,
        'id': 'lipidomics_file',
        'title': None,
        'type': 'object',
        'namespace': None,
        'category': 'data_file',
        'program': '*',
        'project': '*',
        'description': 'Info about lipidomics file',
        'submittable': True,
        'validators': None,
        'systemProperties': [
            'id',
            'project_id',
            'state',
            'created_datetime',
            'updated_datetime'
        ],
        'uniqueKeys': [
            ['id'],
            ['project_id', 'submitter_id']
        ],
        'required': ['submitter_id', 'type'],
        'links': {
            'exclusive': False,
            'required': True,
            'subgroup': [
                {
                    'name': 'samples',
                    'backref': 'lipidomics_files',
                    'label': None,
                    'target_type': 'sample',
                    'multiplicity': 'one_to_many',
                    'required': True
                },
                {
                    'name': 'assays',
                    'backref': 'lipidomics_files',
                    'label': None,
                    'target_type': 'assay',
                    'multiplicity': 'one_to_many',
                    'required': True
                },
                {
                    'name': 'core_metadata_collections',
                    'backref': 'lipidomics_files',
                    'label': None,
                    'target_type': 'core_metadata_collection',
                    'multiplicity': 'one_to_one',
                    'required': True
                }
            ]
        },
        'properties': {
            'samples': {'$ref': '_definitions.yaml#/one_to_many'},
            'assays': {'$ref': '_definitions.yaml#/one_to_many'}
        }
    }
    return output

def test_populate_output(fixture_input_yaml_pass, fixture_expected_output_lipid, fixture_converter_template):
    result = populate_template("lipidomics_file", fixture_input_yaml_pass, fixture_converter_template)
    expected = fixture_expected_output_lipid
    assert isinstance(result, dict)
    assert result == expected

