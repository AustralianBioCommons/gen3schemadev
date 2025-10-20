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


def test_get_node_names(fixture_input_yaml_pass):
    node_names = get_node_names(fixture_input_yaml_pass)
    assert 'lipidomics_file' in node_names
    assert 'sample' in node_names
    assert 'project' in node_names
    assert 'assay' in node_names

def test_get_node_data(fixture_input_yaml_pass):
    node = get_node_data('lipidomics_file', fixture_input_yaml_pass)
    assert node.name == 'lipidomics_file'
    assert node.description == 'Info about lipidomics file'
    assert node.category.value == 'data_file'
    assert isinstance(node.properties, list)

def test_get_node_data_not_found(fixture_input_yaml_pass):
    with pytest.raises(ValueError) as excinfo:
        get_node_data('nonexistent_node', fixture_input_yaml_pass)
    assert "node 'nonexistent_node' not found in data.nodes" in str(excinfo.value)


def test_get_node_links(fixture_input_yaml_pass):
    links = get_node_links('lipidomics_file', fixture_input_yaml_pass)
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
    assert link_dict["required"] is False
    # label is None
    assert "label" in link_dict and link_dict["label"] is 'part_of'
    # The dict should not have unexpected keys
    expected_keys = {"name", "backref", "label", "target_type", "multiplicity", "required"}
    assert set(link_dict.keys()) == expected_keys



def test_convert_node_links():
    # Prepare a list of link dicts as would be returned by get_node_links
    links = [
        {"parent": "sample", "multiplicity": "many_to_one", "child": "lipidomics_file"},
        {"parent": "project", "multiplicity": "one_to_many", "child": "sample"},
    ]
    # Call the function
    result = convert_node_links(links, required=True)
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
    assert "label" in link0 and link0["label"] is 'part_of'

    # Check the structure of the second link
    link1 = result[1]
    assert link1["name"] == "projects"
    assert link1["backref"] == "samples"
    assert link1["target_type"] == "project"
    assert link1["multiplicity"] == "one_to_many"
    assert link1["required"] is True
    assert "label" in link1 and link1["label"] is 'part_of'

    # Test with required=False
    result2 = convert_node_links(links, required=False)
    assert all(link["required"] is False for link in result2)



def test_add_core_metadata_link():
    # Prepare a list of link dicts (as would be output from convert_node_links)
    links = [
        {
            "name": "samples",
            "backref": "lipidomics_files",
            "label": None,
            "target_type": "sample",
            "multiplicity": "many_to_one",
            "required": False,
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
    assert core_link["required"] is False
    assert "label" in core_link and core_link["label"] is 'part_of'
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
    group = group[0]
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
    group2 = group2[0]
    assert group2["exclusive"] is True
    assert group2["required"] is False
    assert group2["subgroup"] == links


def test_format_multiplicity_pass():
    # The updated function expects a string and returns "to_one" for *_to_one, "to_many" for *_to_many
    assert format_multiplicity("one_to_one") == "to_one"
    assert format_multiplicity("one_to_many") == "to_many"
    assert format_multiplicity("many_to_one") == "to_one"
    assert format_multiplicity("many_to_many") == "to_many"

    # # Test invalid input: not a string
    # import pytest
    # with pytest.raises(ValueError):
    #     format_multiplicity(123)

    # # Test invalid input: string not ending with _to_one or _to_many
    # with pytest.raises(ValueError):
    #     format_multiplicity("foo_bar")



def test_create_link_prop():
    # Test with a typical node and multiplicity
    prop = create_link_prop("sample", "one_to_many")
    assert isinstance(prop, dict)
    # The key should be the link_suffix of "sample", which is "samples"
    assert "samples" in prop
    # The value should be a dict with a $ref key
    assert isinstance(prop["samples"], dict)
    assert "$ref" in prop["samples"]
    assert prop["samples"]["$ref"] == "_definitions.yaml#/to_many"

    # Test with another node and multiplicity
    prop2 = create_link_prop("core_metadata_collection", "one_to_one")
    assert "core_metadata_collections" in prop2
    assert prop2["core_metadata_collections"]["$ref"] == "_definitions.yaml#/to_one"

    # Test that only one key exists in the returned dict
    assert len(prop) == 1
    assert len(prop2) == 1

    # Test with unusual node name
    prop3 = create_link_prop("weird_node", "many_to_one")
    assert "weird_nodes" in prop3
    assert prop3["weird_nodes"]["$ref"] == "_definitions.yaml#/to_one"



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


def test_strip_required_field():
    # Test that strip_required_field removes 'required' from property dicts
    input_props = [
        {
            "project_id": {
                "type": "string",
                "description": "Synthetic_Dataset_1",
                "required": True,
                "enums": None
            }
        },
        {
            "description": {
                "type": "string",
                "description": "Project containing synthetic data",
                "required": False,
                "enums": None
            }
        }
    ]
    expected = [
        {
            "project_id": {
                "type": "string",
                "description": "Synthetic_Dataset_1",
                "enums": None
            }
        },
        {
            "description": {
                "type": "string",
                "description": "Project containing synthetic data",
                "enums": None
            }
        }
    ]
    result = strip_required_field(input_props)
    assert result == expected

    # Test that it works with an empty list
    assert strip_required_field([]) == []

    # Test that it leaves dicts without 'required' unchanged
    input2 = [
        {"foo": {"type": "integer", "description": "bar"}}
    ]
    expected2 = [
        {"foo": {"type": "integer", "description": "bar"}}
    ]
    assert strip_required_field(input2) == expected2

    # Test that it leaves non-dict items unchanged
    input3 = [
        {"foo": {"type": "string", "required": True}},
        "not_a_dict"
    ]
    expected3 = [
        {"foo": {"type": "string"}},
        "not_a_dict"
    ]
    assert strip_required_field(input3) == expected3


def test_get_required_prop_names():
    # Typical case: some required, some not
    props_list = [
        {
            "project_id": {
                "type": "string",
                "description": "Synthetic_Dataset_1",
                "required": True,
                "enums": None
            }
        },
        {
            "description": {
                "type": "string",
                "description": "Project containing synthetic data",
                "required": False,
                "enums": None
            }
        },
        {
            "foo": {
                "type": "integer"
                # no 'required' key
            }
        }
    ]
    result = get_required_prop_names(props_list)
    assert result == ["project_id"]

    # All required
    props_list2 = [
        {"a": {"type": "string", "required": True}},
        {"b": {"type": "number", "required": True}}
    ]
    assert set(get_required_prop_names(props_list2)) == {"a", "b"}

    # None required
    props_list3 = [
        {"x": {"type": "string", "required": False}},
        {"y": {"type": "number"}}
    ]
    assert get_required_prop_names(props_list3) == []

    # Empty list
    assert get_required_prop_names([]) == []

    # Non-dict in list should be ignored
    props_list4 = [
        {"z": {"type": "string", "required": True}},
        "not_a_dict"
    ]
    assert get_required_prop_names(props_list4) == ["z"]

    # Dict with non-dict value should be ignored
    props_list5 = [
        {"z": "not_a_dict"}
    ]
    assert get_required_prop_names(props_list5) == []



def test_format_enum_basic():
    # Standard enum property
    prop_dict = {
        "sample_tube_type": {
            "type": "enum",
            "description": "Sample tube type (enum)",
            "required": False,
            "enums": ["EDTA", "Heparin", "Citrate"]
        }
    }
    result = format_enum(prop_dict)
    assert result == {
        "sample_tube_type": {
            "description": "Sample tube type (enum)",
            "enum": ["EDTA", "Heparin", "Citrate"]
        }
    }

def test_format_enum_no_enums():
    # Property with no enums key
    prop_dict = {
        "foo": {
            "type": "string",
            "description": "A string property",
            "required": True
        }
    }
    result = format_enum(prop_dict)
    assert result == {
        "foo": {
            "type": "string",
            "description": "A string property",
            "required": True
        }
    }

def test_format_enum_enums_none():
    # Property with enums=None
    prop_dict = {
        "bar": {
            "type": "enum",
            "description": "Bar enum",
            "required": False,
            "enums": None
        }
    }
    result = format_enum(prop_dict)
    assert result == {
        "bar": {
            "type": "enum",
            "description": "Bar enum",
            "required": False
        }
    }

def test_format_enum_invalid_input():
    # More than one key in dict
    prop_dict = {
        "a": {"type": "enum", "description": "desc", "enums": ["A"]},
        "b": {"type": "enum", "description": "desc", "enums": ["B"]}
    }
    with pytest.raises(RuntimeError) as excinfo:
        format_enum(prop_dict)
    assert "Expected a single property dictionary" in str(excinfo.value)

def test_format_enum_missing_description():
    # Property with enums but missing description
    prop_dict = {
        "baz": {
            "type": "enum",
            "required": True,
            "enums": ["X", "Y"]
        }
    }
    # Should raise KeyError when trying to access value['description']
    with pytest.raises(RuntimeError) as excinfo:
        format_enum(prop_dict)
    assert "description" in str(excinfo.value)



def test_construct_prop_lipidomics_file(fixture_input_yaml_pass):
    result = construct_props("lipidomics_file", fixture_input_yaml_pass)
    expected = {
        "$ref": "_definitions.yaml#/data_file_properties",
        "samples": {"$ref": "_definitions.yaml#/to_many"},
        "assays": {"$ref": "_definitions.yaml#/to_many"},
        "core_metadata_collections": {"$ref": "_definitions.yaml#/to_one"},
        'cv': {'description': 'Coefficient of variation (%)', 'type': 'number'}
        
    }
    assert result == expected

def test_construct_prop_project(fixture_input_yaml_pass):
    result = construct_props("project", fixture_input_yaml_pass)
    expected = {
        "$ref": "_definitions.yaml#/ubiquitous_properties",
        "project_id": {
            "type": "string",
            "description": "Synthetic_Dataset_1"
        },
        "description": {
            "type": "string",
            "description": "Project containing synthetic data"
        }
    }
    assert result == expected

def test_construct_prop_sample(fixture_input_yaml_pass):
    result = construct_props("sample", fixture_input_yaml_pass)
    expected = {
        "$ref": "_definitions.yaml#/ubiquitous_properties",
        "sample_id": {
            "type": "string",
            "description": "Sample ID (string)"
        },
        "sample_count": {
            "type": "integer",
            "description": "Number of aliquots (integer)"
        },
        "sample_volume": {
            "type": "number",
            "description": "Volume in microliters (number/float)"
        },
        "is_viable": {
            "type": "boolean",
            "description": "Is the sample viable? (boolean)"
        },
        "collection_date": {
            "$ref": "_definitions.yaml#/datetime"
        },
        "sample_tube_type": {
            "description": "Sample tube type (enum)",
            "enum": [
                "EDTA",
                "Heparin",
                "Citrate"
            ]
        },
        "notes": {
            "type": "string",
            "description": "Free text notes (string)"
        },
        "projects": {
            "$ref": "_definitions.yaml#/to_many"
        }
    }
    assert result == expected


def test_get_category(fixture_input_yaml_pass):
    result = get_category("lipidomics_file", fixture_input_yaml_pass)
    expected = "data_file"
    assert result == expected


def test_get_node_value(fixture_input_yaml_pass):
    assert 'Info about lipidomics file' == get_node_value("lipidomics_file", 'description', fixture_input_yaml_pass)


def test_is_file_node(fixture_input_yaml_pass):
    assert is_file_node("lipidomics_file", fixture_input_yaml_pass)
    assert not is_file_node("sample", fixture_input_yaml_pass)

@pytest.fixture
def fixture_expected_output_lipid():
    output = {
        '$schema': 'http://json-schema.org/draft-04/schema#',
        'id': 'lipidomics_file',
        'title': 'lipidomics_file',
        'type': 'object',
        'namespace': 'https://link-to-data-portal/',
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
        'required': ['cv', 'submitter_id', 'type'],
        'links': [{
            'exclusive': False,
            'required': True,
            'subgroup': [
                {
                    'name': 'samples',
                    'backref': 'lipidomics_files',
                    'label': 'part_of',
                    'target_type': 'sample',
                    'multiplicity': 'one_to_many',
                    'required': True
                },
                {
                    'name': 'assays',
                    'backref': 'lipidomics_files',
                    'label': 'part_of',
                    'target_type': 'assay',
                    'multiplicity': 'one_to_many',
                    'required': True
                },
                {
                    'name': 'core_metadata_collections',
                    'backref': 'lipidomics_files',
                    'label': 'part_of',
                    'target_type': 'core_metadata_collection',
                    'multiplicity': 'one_to_one',
                    'required': False
                }
            ]
        }],
        'properties': {
            '$ref': '_definitions.yaml#/data_file_properties',
            'samples': {'$ref': '_definitions.yaml#/to_many'},
            'assays': {'$ref': '_definitions.yaml#/to_many'},
            'core_metadata_collections': {'$ref': '_definitions.yaml#/to_one'},
            'cv': {'description': 'Coefficient of variation (%)', 'type': 'number'}
        },
        'additionalProperties': False
    }
    return output

def test_populate_output(fixture_input_yaml_pass, fixture_expected_output_lipid, fixture_converter_template):
    result = populate_template("lipidomics_file", fixture_input_yaml_pass, fixture_converter_template)
    expected = fixture_expected_output_lipid
    assert isinstance(result, dict)
    assert result == expected

