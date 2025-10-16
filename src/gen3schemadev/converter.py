"""
Gen3 Schema Generation Module

This module provides utilities for converting node and link data into Gen3 schema format.
It handles node properties, links, and special cases like file nodes that require
core metadata collections.

Expected Data Structure:
    The input data should be a Pydantic model with:
    - nodes: List of node objects with attributes: name, description, category, properties, links
    - links: List of link objects with attributes: child, parent, multiplicity
"""

from dataclasses import dataclass, asdict
from typing import Protocol, runtime_checkable, Dict, Any, List
import logging


logger = logging.getLogger(__name__)


# Protocol definitions for type safety
@runtime_checkable
class nodeProtocol(Protocol):
    """Protocol defining the structure of an node object."""
    name: str
    description: str
    category: str
    properties: list
    links: list

    def model_dump(self) -> dict:
        """Convert node to dictionary."""
        ...


@runtime_checkable
class LinkProtocol(Protocol):
    """Protocol defining the structure of a link object."""
    child: str
    parent: str
    multiplicity: str

    def model_dump(self) -> dict:
        """Convert link to dictionary."""
        ...


@runtime_checkable
class DataSourceProtocol(Protocol):
    """Protocol defining the expected structure of input data."""
    nodes: list[nodeProtocol]
    links: list[LinkProtocol]


# Data classes
@dataclass
class node:
    """Represents a Gen3 node with its metadata and relationships."""
    name: str
    description: str
    category: str
    properties: list
    links: list

    def to_dict(self) -> dict:
        """Convert node to dictionary representation."""
        return asdict(self)


@dataclass
class LinkObj:
    """Represents a link between two nodes in Gen3 schema."""
    name: str
    backref: str
    label: str | None
    target_type: str
    multiplicity: str
    required: bool

    def to_dict(self) -> dict:
        """Convert link to dictionary representation."""
        return asdict(self)


@dataclass
class LinkGroup:
    """Represents a group of links with specific constraints."""
    exclusive: bool
    required: bool
    subgroup: list[dict]

    def to_dict(self) -> dict:
        """Convert link group to dictionary representation."""
        return asdict(self)


# Utility functions
def link_suffix(word: str, suffix='s') -> str:
    """
    Adds link suffix to a singular word.

    Args:
        word: The singular word to suffix

    Returns:
        The work with the suffix
    """
    return word + suffix

def get_node_names(data: DataSourceProtocol) -> list[str]:
    """
    Retrieve a list of node names from the data structure.

    Args:
        data: The data structure containing nodes.

    Returns:
        A list of node names.
    """
    return [node.name for node in data.nodes]


def get_node_data(node: str, data: DataSourceProtocol) -> nodeProtocol:
    """
    Retrieve the node object for a given node name from the data structure.

    Args:
        node: The name of the node to retrieve.
        data: The data structure containing nodes.

    Returns:
        The node object matching the given name.

    Raises:
        ValueError: If the node is not found in data.nodes.
        AttributeError: If the data structure is invalid.
    """
    if not hasattr(data, 'nodes'):
        raise AttributeError("Data structure missing 'nodes' attribute")

    try:
        for ent in data.nodes:
            if ent.name == node:
                return ent
        raise ValueError(f"node '{node}' not found in data.nodes")
    except AttributeError as e:
        raise AttributeError(f"Invalid data structure: {e}")


def get_node_links(node: str, data: DataSourceProtocol) -> list[dict]:
    """
    Retrieve all links where the given node is the child.

    Args:
        node: The name of the node (child) to find links for.
        data: The data structure containing links.

    Returns:
        A list of link dictionaries where the node is the child.

    Raises:
        AttributeError: If the data structure is invalid.
    """
    if not hasattr(data, 'links'):
        raise AttributeError("Data structure missing 'links' attribute")

    links = data.links
    node_links = []
    for link in links:
        if link.child == node:
            node_links.append(link.model_dump())
    return node_links


def create_core_metadata_link(child_name: str) -> dict:
    """
    Create a link dictionary for core metadata collections.

    This is used for file nodes that must be linked to a core_metadata_collection.

    Args:
        child_name: The name of the child node.

    Returns:
        A dictionary representing the core metadata link.
    """
    link_obj = LinkObj(
        name=link_suffix("core_metadata_collection"),
        backref=link_suffix(child_name),
        label=None,
        target_type="core_metadata_collection",
        multiplicity="one_to_one",
        required=True
    )
    return link_obj.to_dict()


def convert_node_links(links: list[dict], required: bool = True) -> list[dict]:
    """
    Convert a list of link dictionaries into the Gen3 schema 'links' format.

    Args:
        links: A list of link dictionaries for the node.
        required: Whether the links are required (default: True).

    Returns:
        A list of formatted link dictionaries for the Gen3 schema.
    """
    link_list = []
    for link in links:
        link_obj = LinkObj(
            name=link_suffix(link['parent']),
            backref=link_suffix(link['child']),
            label=None,
            target_type=link['parent'],
            multiplicity=link['multiplicity'],
            required=required
        )
        link_list.append(link_obj.to_dict())

    return link_list


def add_core_metadata_link(links: list[dict], child_name: str) -> list[dict]:
    """
    Add a core metadata link to an existing list of links for file nodes.

    Args:
        links: Existing list of link dictionaries.
        child_name: The name of the child node.

    Returns:
        Updated list of link dictionaries including core metadata link.
    """
    core_link = create_core_metadata_link(child_name)
    return links + [core_link]


def create_link_group(links: list[dict], exclusive: bool = False, required: bool = True) -> list[dict]:
    """
    Create a link group structure from a list of links.

    Args:
        links: List of link dictionaries to group.
        exclusive: Whether the links are mutually exclusive.
        required: Whether at least one link is required.

    Returns:
        A list containing a dictionary representing the link group.
    """
    group = LinkGroup(
        exclusive=exclusive,
        required=required,
        subgroup=links
    )
    return [group.to_dict()]


def format_multiplicity(multiplicity: str) -> str:
    """
    For gen3 link properties, definitions for one_to_many links 
    are referenced as to_many. The def, says it is an array with
    a min length of 1. And for one_to_one, it is referenced as to_one
    with a max array length of 1. It does not matter if it is many_to 
    or one_to since that is implied by the number of submitter_ids for 
    the node.

    Args:
        multiplicity: The multiplicity of the link (e.g., 'one_to_one', 'one_to_many').

    Returns:
        The formatted multiplicity string.
    """
    # Map all *_to_one to "to_one", all *_to_many to "to_many"
    if not isinstance(multiplicity, str):
        logger.error(f"Multiplicity must be a string, got {type(multiplicity)}")
        raise ValueError(f"Multiplicity must be a string, got {type(multiplicity)}")
    if multiplicity.endswith("_to_one"):
        return "to_one"
    elif multiplicity.endswith("_to_many"):
        return "to_many"
    else:
        logger.error(f"Invalid multiplicity: {multiplicity}")
        raise ValueError(f"Invalid multiplicity: {multiplicity}")

def create_link_prop(target_node: str, multiplicity: str) -> dict:
    """
    Create a property dictionary for a link to another node.

    Args:
        target_node: The name of the target node.
        multiplicity: The multiplicity of the link (e.g., 'one_to_one', 'one_to_many').

    Returns:
        A dictionary representing the link property for the schema.
    """
    link_prop = {
        link_suffix(target_node): {
            "$ref": f"_definitions.yaml#/{format_multiplicity(multiplicity)}"
        }
    }
    return link_prop


def get_properties(node_name: str, data: DataSourceProtocol) -> list[dict]:
    """
    Retrieve the list of property dictionaries for a given node.

    Args:
        node_name: The name of the node.
        data: The data structure containing nodes.

    Returns:
        A list of property dictionaries, or an empty list if no properties found.

    Raises:
        ValueError: If the node is not found.
    """
    ent = get_node_data(node_name, data)
    props = ent.properties
    
    output = []
    if props:
        for prop in props:
            pdict = {
                prop.name: {k: v for k, v in prop.model_dump().items() if k != "name"}
            }
            
            output.append(pdict)
            
    else:
        logger.debug(f"No properties found for node '{node_name}'")
    
    return output


def strip_required_field(props_list: list[dict]) -> list[dict]:
    """
    Remove the 'required' field from all property dicts in the input list.
    Can use the output of get_properties() for this function

    Args:
        props_list (list): A list of property dictionaries, where each dictionary has a single key
            (the property name) and its value is a dictionary describing the property. For example:
                [
                    {
                        "project_id": {
                            "type": "string",
                            "description": "Synthetic_Dataset_1",
                            "required": True,
                            "enums": None
                        }
                    },
                    ...
                ]

    Returns:
        list: A new list with the same structure as props_list, but with the 'required'
            field removed from each property's dictionary (if present).

    Note:
        This function expects a list of property definitions as typically returned by
        get_properties() in the Gen3 schema conversion workflow.
        If you are working with a DataSourceProtocol object, you should first extract the
        properties list using the appropriate function.
    """
    new_list = []
    for prop in props_list:
        if isinstance(prop, dict):
            # Each prop is {property_name: property_dict}
            new_prop = {}
            for k, v in prop.items():
                if isinstance(v, dict):
                    v = {key: val for key, val in v.items() if key != 'required'}
                new_prop[k] = v
            new_list.append(new_prop)
        else:
            new_list.append(prop)
    return new_list

def get_required_prop_names(props_list: list[dict]) -> List[str]:
    """
    Given a list of property dicts (as from get_properties), return a list of property names
    where the property dict has 'required': True. Can use the output of get_properties() for this function.

    Args:
        props_list (list): A list of property dictionaries, where each dictionary has a single key
            (the property name) and its value is a dictionary describing the property. For example:
                [
                    {
                        "project_id": {
                            "type": "string",
                            "description": "Synthetic_Dataset_1",
                            "required": True,
                            "enums": None
                        }
                    },
                    ...
                ]

    Returns:
        List[str]: List of property names with required True.
    """
    required_names = []
    for prop in props_list:
        if isinstance(prop, dict):
            for k, v in prop.items():
                if isinstance(v, dict) and v.get("required") is True:
                    required_names.append(k)
    return required_names


def format_enum(prop_dict: dict) -> dict:
    """
    Format an enum property dictionary for use in a Gen3 schema.

    Example:
        {'sample_tube_type': {'type': 'enum',
           'description': 'Sample tube type (enum)',
           'required': False,
           'enums': ['EDTA', 'Heparin', 'Citrate']
           }
        }

    Args:
        prop_dict (dict): The dictionary representing the enum property.

    Returns:
        dict: The formatted dictionary for use in a Gen3 schema.
    """
    try:
        if len(prop_dict) != 1:
            raise ValueError("Expected a single property dictionary")
        
        first_key = next(iter(prop_dict))
        value = prop_dict[first_key]
        formatted_props = {}
        
        if 'enums' in value and value['enums'] is not None:
            formatted_props['description'] = value['description']
            formatted_props['enum'] = value['enums']
        else:
            # Remove the 'enums' key from value if present
            value = value.copy()
            value.pop('enums', None)
            formatted_props = value
        
        output = {first_key: formatted_props}
        return output
    except Exception as e:
        # You may want to log the error or handle it differently depending on your use case
        raise RuntimeError(f"Error formatting enum property: {e}") from e


def format_datetime(prop_dict: dict) -> dict:
    """
    Formats a property dictionary with a 'type' of 'datetime' to use a $ref
    to the Gen3 _definitions.yaml#/datetime definition.

    If the property is not of type 'datetime', returns the property unchanged.

    Example input:
        {
            "collection_date": {
                "type": "datetime",
                "description": "Date and time of collection (datetime)"
            }
        }

    Example output:
        {
            "collection_date": {
                "$ref": "_definitions.yaml#/datetime"
            }
        }

    Args:
        prop_dict (dict): A dictionary with a single property as key and its attributes as value.

    Returns:
        dict: The formatted property dictionary suitable for Gen3 schema usage.

    Raises:
        ValueError: If the input dictionary does not contain exactly one property.
        RuntimeError: If an error occurs during formatting.
    """
    try:
        if len(prop_dict) != 1:
            raise ValueError("Expected a single property dictionary")
        
        first_key = next(iter(prop_dict))
        value = prop_dict[first_key]
        formatted_props = {}
        
        if 'type' in value and value['type'] == 'datetime':
            formatted_props['$ref'] = "_definitions.yaml#/datetime"
        else:
            formatted_props = value
        
        output = {first_key: formatted_props}
        return output
    except Exception as e:
        # You may want to log the error or handle it differently depending on your use case
        raise RuntimeError(f"Error formatting datetime property: {e}") from e


def construct_props(node_name: str, data: DataSourceProtocol) -> dict:
    """
    Construct the 'properties' section for a Gen3 schema node.

    This combines the node's own properties and any link properties.

    Args:
        node_name: The name of the node.
        data: The data structure containing nodes and links.

    Returns:
        A dictionary of all properties (including links) for the node.

    Raises:
        ValueError: If the node is not found.
    """
    links = get_node_links(node_name, data)
    props = get_properties(node_name, data)
    props = strip_required_field(props)
    node_data = get_node_data(node_name, data)
    category = node_data.category

    # Flatten property dicts into a single dict
    props_dict = {}
    # add ubiquitous property ref
    props_dict['$ref'] = "_definitions.yaml#/ubiquitous_properties"
    for prop in props:
        if isinstance(prop, dict):
            prop = format_enum(prop)
            prop = format_datetime(prop)
            props_dict.update(prop)

    # Add link properties
    for link in links:
        link_prop = create_link_prop(link['parent'], link['multiplicity'])
        props_dict.update(link_prop)

    # if it's an Enum, add the enum values
    if category == "data_file":
        props_dict['core_metadata_collections'] = {"$ref": "_definitions.yaml#/to_one"}
        props_dict['$ref'] = "_definitions.yaml#/data_file_properties"

    return props_dict


def get_category(node_name: str, data: DataSourceProtocol) -> str:
    """
    Get the category value for a given node.

    Args:
        node_name: The name of the node.
        data: The data structure containing nodes.

    Returns:
        The category value (as a string).

    Raises:
        ValueError: If the node is not found.
    """
    ent = get_node_data(node_name, data)
    category = ent.category
    
    # If it's an Enum, get its value; otherwise, return as is
    if hasattr(category, "value"):
        return category.value
    return category


def get_node_value(node_name: str, key: str, data: DataSourceProtocol) -> str | list | dict | None:
    """
    Return the value of a single key within an node object.

    Args:
        node_name: The name of the node to retrieve.
        key: The key whose value is to be returned.
        data: The data structure containing nodes.

    Returns:
        The value associated with the specified key in the node object.

    Raises:
        ValueError: If the node is not found.
        KeyError: If the key doesn't exist in the node.
    """
    ent = get_node_data(node_name, data)
    node_dict = ent.model_dump()
    
    if key not in node_dict:
        raise KeyError(f"Key '{key}' not found in node '{node_name}'")
    
    return node_dict[key]


def is_file_node(node_name: str, data: DataSourceProtocol) -> bool:
    """
    Determine if an node is a file node (category: data_file).

    Args:
        node_name: The name of the node.
        data: The data structure containing nodes.

    Returns:
        True if the node is a file node, False otherwise.
    """
    try:
        category_value = get_node_value(node_name, 'category', data)
        return category_value == 'data_file'
    except (ValueError, KeyError):
        return False


def populate_template(node_name: str, input_data: DataSourceProtocol, template: dict) -> dict:
    """
    Populate a Gen3 schema template dictionary with values from a Pydantic data model.

    This function takes an node name, a Pydantic model instance containing node data,
    and a Gen3 schema template dictionary. It fills a copy of the template with values
    from the input data, applying special logic for certain keys (e.g., 'name', 'category',
    'properties', 'links').

    Args:
        node_name: The name of the node to populate in the template.
        input_data: A Pydantic model instance containing the node's data.
        template: A Gen3 schema template dictionary to be populated.

    Returns:
        A new Gen3 schema template dictionary populated with values from the input data.

    Raises:
        ValueError: If the node is not found in input_data.
    """
    ent = get_node_data(node_name, input_data)
    ent_dict = ent.model_dump()
    output_schema = template.copy()
    namespace = str(input_data.model_dump()['url'])
    
    # add node name as title
    output_schema['title'] = ent.name
    output_schema['namespace'] = namespace
    
    # Check if node is a file category
    file_node = is_file_node(node_name, input_data)
    
    # Populate template with node data
    for key, value in ent_dict.items():
        if key == 'name':
            output_schema['id'] = value
        elif key == 'category':
            output_schema[key] = get_category(node_name, input_data)
        elif key == 'properties':
            output_schema[key] = construct_props(node_name, input_data)
        elif key in output_schema:
            output_schema[key] = value
        else:
            logger.debug(f"Key '{key}' from node '{node_name}' not found in template")
    
    # add required props
    props = get_properties(node_name, input_data)
    required_props = get_required_prop_names(props)
    if required_props:
        required_props.append('submitter_id')
        required_props.append('type')
        output_schema['required'] = required_props
    
    # Process and add links
    links = get_node_links(node_name, input_data)
    converted_links = convert_node_links(links)
    
    # Add core metadata link for file nodes
    if file_node and links:
        converted_links = add_core_metadata_link(converted_links, links[0]['child'])
    
    # Create link group if multiple links exist
    if len(converted_links) > 1:
        output_schema['links'] = create_link_group(converted_links)
    else:
        output_schema['links'] = converted_links
    
    return output_schema
