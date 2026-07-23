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
    """
    Input: a node that is the child of two declared links, where neither link
    declares `required`.

    Expected: both links are returned, and each carries `required: True` from
    the model default.

    Why it matters: links are read straight off the validated model, so a link
    now arrives with its own `required` value rather than having one stamped on
    later. The default is True because that is what the generator emitted before
    the field was declarable — which is what keeps every existing dictionary
    regenerating unchanged.
    """
    links = get_node_links('lipidomics_file', fixture_input_yaml_pass)
    assert len(links) == 2
    assert dict(links[0]) == {
        'parent': 'sample',
        'multiplicity': 'one_to_many',
        'child': 'lipidomics_file',
        'required': True,
    }



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
    assert link0["multiplicity"] == "one_to_many"
    assert link0["required"] is True
    assert "label" in link0 and link0["label"] is 'part_of'

    # Check the structure of the second link
    link1 = result[1]
    assert link1["name"] == "projects"
    assert link1["backref"] == "samples"
    assert link1["target_type"] == "project"
    assert link1["multiplicity"] == "many_to_one"
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


def test_create_link_prop_project():
    """
    When a node links to 'project', the property $ref must use the special
    'to_one_project' or 'to_many_project' definition rather than the generic
    'to_one'/'to_many'. This is because 'project' uses a different foreign key
    schema (foreign_key_project, identified by 'id' or 'code') compared to
    the standard foreign_key (identified by 'id' or 'submitter_id').
    """
    prop_one = create_link_prop("project", "one_to_one")
    assert "projects" in prop_one
    assert prop_one["projects"]["$ref"] == "_definitions.yaml#/to_one_project"

    prop_many = create_link_prop("project", "one_to_many")
    assert "projects" in prop_many
    assert prop_many["projects"]["$ref"] == "_definitions.yaml#/to_many_project"

    prop_many2 = create_link_prop("project", "many_to_many")
    assert "projects" in prop_many2
    assert prop_many2["projects"]["$ref"] == "_definitions.yaml#/to_many_project"

    prop_one2 = create_link_prop("project", "many_to_one")
    assert "projects" in prop_one2
    assert prop_one2["projects"]["$ref"] == "_definitions.yaml#/to_one_project"



def test_get_properties(fixture_input_yaml_pass):
    """
    Input: two properties, neither of which declares any optional annotation
    (no enums, no default, no format).

    Expected: each property carries only the keys it actually set. Annotations
    the author left unset are absent entirely rather than present-and-null.

    Why it matters: a property may now declare several optional annotations
    (default, format, items, enumDef, pattern, term). If unset ones were carried
    through as None they would either litter the generated schema with nulls or
    force every downstream formatter to filter them. Dropping them here, at the
    single point where properties are read off the model, keeps that concern in
    one place. Note this only affects the intermediate representation — the
    formatters already discarded a null `enums`, so the generated Gen3 schema is
    unchanged.
    """
    result = get_properties("lipidomics_file", fixture_input_yaml_pass)
    expected = [
        {
            "cv": {
                "type": "number",
                "description": "Coefficient of variation (%)",
                "required": True
            }
        },
        {
            "lipid_species": {
                "type": "array",
                "description": "List of lipid species",
                "required": False
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


def test_format_datetime_keeps_description_as_ref_sibling():
    """
    A datetime property is converted to a $ref to the shared
    _definitions.yaml#/datetime definition. Gen3's resolver merges a
    property's sibling keys over the referenced definition, so the
    property's description must be kept as a sibling of the $ref — dropping
    it (as older versions did) loses the user's documentation, and the
    data-dictionary viewer would show "No Description".
    """
    prop_dict = {
        "collection_date": {
            "type": "datetime",
            "description": "Date and time of collection (datetime)"
        }
    }
    expected = {
        "collection_date": {
            "description": "Date and time of collection (datetime)",
            "$ref": "_definitions.yaml#/datetime"
        }
    }
    assert format_datetime(prop_dict) == expected


def test_format_datetime_bare_ref_without_annotations():
    """
    A datetime property with no annotations (only 'type') carries nothing
    to preserve, so it becomes a plain bare $ref.
    """
    prop_dict = {"processed_at": {"type": "datetime"}}
    expected = {"processed_at": {"$ref": "_definitions.yaml#/datetime"}}
    assert format_datetime(prop_dict) == expected


def test_format_datetime_passthrough_non_datetime():
    """
    format_datetime must only rewrite properties of type 'datetime'; any
    other property must pass through completely unchanged so the formatter
    can be safely applied to every property in a node.
    """
    prop_dict = {"notes": {"type": "string", "description": "Free text"}}
    assert format_datetime(prop_dict) == prop_dict


def test_construct_prop_lipidomics_file(fixture_input_yaml_pass):
    result = construct_props("lipidomics_file", fixture_input_yaml_pass)
    expected = {
        "$ref": "_definitions.yaml#/data_file_properties",
        "samples": {"$ref": "_definitions.yaml#/to_one"},
        "assays": {"$ref": "_definitions.yaml#/to_one"},
        "core_metadata_collections": {"$ref": "_definitions.yaml#/to_one"},
        'cv': {'description': 'Coefficient of variation (%)', 'type': 'number'}
        ,
        "data_category": {
            "description": "Broad categorization of the contents of the data file.",
            "enum": ['data_category_1', 'data_category_2', 'data_category_3']
        },
        "data_format": {
            "description": "The format of the data in this data file",
            "enum": ['data_format_1', 'data_format_2', 'data_format_3']
        },
        "data_type": {
            "description": "The type of data in this data file",
            "enum": ['data_type_1', 'data_type_2', 'data_type_3']
        },
        "lipid_species": {
            "description": "List of lipid species",
            "items": {
                "type": "string"
            },
            "type": "array"
        }
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
        },
        "programs": {'$ref': '_definitions.yaml#/to_one'},
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
            "description": "Date and time of collection (datetime)",
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
            "$ref": "_definitions.yaml#/to_one_project"
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
                    'multiplicity': 'many_to_one',
                    'required': True
                },
                {
                    'name': 'assays',
                    'backref': 'lipidomics_files',
                    'label': 'part_of',
                    'target_type': 'assay',
                    'multiplicity': 'many_to_one',
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
            'samples': {'$ref': '_definitions.yaml#/to_one'},
            'assays': {'$ref': '_definitions.yaml#/to_one'},
            'core_metadata_collections': {'$ref': '_definitions.yaml#/to_one'},
            'cv': {'description': 'Coefficient of variation (%)', 'type': 'number'},
            "data_category": {
                "description": "Broad categorization of the contents of the data file.",
                "enum": ['data_category_1', 'data_category_2', 'data_category_3']
            },
            "data_format": {
                "description": "The format of the data in this data file",
                "enum": ['data_format_1', 'data_format_2', 'data_format_3']
            },
            "data_type": {
                "description": "The type of data in this data file",
                "enum": ['data_type_1', 'data_type_2', 'data_type_3']
            },
            "lipid_species": {
                "description": "List of lipid species",
                "items": {
                    "type": "string"
                },
                "type": "array"
            }
        },
        'additionalProperties': False
    }
    return output

def test_populate_output(fixture_input_yaml_pass, fixture_expected_output_lipid, fixture_converter_template):
    result = populate_template("lipidomics_file", fixture_input_yaml_pass, fixture_converter_template)
    expected = fixture_expected_output_lipid
    assert isinstance(result, dict)
    assert result == expected


# ---------------------------------------------------------------------------
# Regression tests for issue: auto-injected file-node properties overwrote
# user-defined properties in input.yaml.
#
# Before the fix, `construct_props` unconditionally assigned hardcoded
# placeholder enums for `data_category`, `data_format`, and `data_type` (and
# `core_metadata_collections`) on any node with category `data_file`, even
# when the user had already declared those properties themselves.
# ---------------------------------------------------------------------------

@pytest.fixture
def fixture_input_yaml_file_props_defined():
    """Input model where the user has explicitly declared data_* enums on a
    data_file node. Exercises the preserve-user-definition path."""
    data = load_yaml("tests/input_example_file_props.yml")
    return DataModel.model_validate(data)


def test_construct_props_preserves_user_data_format_enum(fixture_input_yaml_file_props_defined):
    """Canonical regression test for the reported bug.

    A user declaring `data_format` with enums [csv, txt] on a data_file node
    expects those enum values to survive `construct_props`. Previously they
    were silently replaced with ['data_format_1', 'data_format_2', 'data_format_3'],
    which made the input.yaml declaration meaningless.
    """
    props = construct_props("lipidomics_file", fixture_input_yaml_file_props_defined)
    assert props["data_format"] == {
        "description": "File format for lipidomics output",
        "enum": ["csv", "txt"],
    }


def test_construct_props_preserves_user_data_category_enum(fixture_input_yaml_file_props_defined):
    """Same bug, different property. `data_category` is the second of the
    three file-node properties that were being overwritten; this locks in
    that the fix covers all three, not just `data_format`."""
    props = construct_props("lipidomics_file", fixture_input_yaml_file_props_defined)
    assert props["data_category"] == {
        "description": "Category of lipidomics data",
        "enum": ["proteomics", "metabolomics"],
    }


def test_construct_props_preserves_user_data_type_enum(fixture_input_yaml_file_props_defined):
    """Same bug, `data_type`. Completes the coverage of the three
    explicitly-reported file-node properties."""
    props = construct_props("lipidomics_file", fixture_input_yaml_file_props_defined)
    assert props["data_type"] == {
        "description": "Type of lipidomics measurement",
        "enum": ["raw", "processed"],
    }


def test_construct_props_preserves_user_core_metadata_collections(fixture_input_yaml_file_props_defined):
    """Extends the same fix to `core_metadata_collections`, which
    `construct_props` also assigned unconditionally for data_file nodes.
    If the user declares their own shape for it, it must survive — no
    hidden $ref replacement."""
    props = construct_props("lipidomics_file", fixture_input_yaml_file_props_defined)
    assert props["core_metadata_collections"] == {
        "description": "Custom core metadata link sentinel",
        "enum": ["custom_a", "custom_b"],
    }


def test_construct_props_injects_defaults_when_user_omits(fixture_input_yaml_pass):
    """Fallback-path regression: if the user does NOT declare data_* properties,
    the hardcoded placeholder enums must still be injected. This guards against
    a naive fix that would simply delete the defaults — a change that would
    silently break every existing project relying on them."""
    props = construct_props("lipidomics_file", fixture_input_yaml_pass)
    assert props["data_category"] == {
        "description": "Broad categorization of the contents of the data file.",
        "enum": ["data_category_1", "data_category_2", "data_category_3"],
    }
    assert props["data_format"] == {
        "description": "The format of the data in this data file",
        "enum": ["data_format_1", "data_format_2", "data_format_3"],
    }
    assert props["data_type"] == {
        "description": "The type of data in this data file",
        "enum": ["data_type_1", "data_type_2", "data_type_3"],
    }
    assert props["core_metadata_collections"] == {"$ref": "_definitions.yaml#/to_one"}


def test_populate_template_roundtrip_preserves_user_enums(
    fixture_input_yaml_file_props_defined, fixture_converter_template
):
    """End-to-end test through `populate_template`, which is what the CLI's
    generate command calls per-node before writing YAML to disk. Ensures
    the preserve-user-definition fix holds through the full pipeline, not
    just `construct_props` in isolation."""
    result = populate_template(
        "lipidomics_file",
        fixture_input_yaml_file_props_defined,
        fixture_converter_template,
    )
    properties = result["properties"]
    assert properties["data_format"] == {
        "description": "File format for lipidomics output",
        "enum": ["csv", "txt"],
    }
    assert properties["data_category"] == {
        "description": "Category of lipidomics data",
        "enum": ["proteomics", "metabolomics"],
    }
    assert properties["data_type"] == {
        "description": "Type of lipidomics measurement",
        "enum": ["raw", "processed"],
    }
