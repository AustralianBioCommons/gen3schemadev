"""
Gen3 Schema Generation Module

This module provides utilities for converting entity and link data into Gen3 schema format.
It handles entity properties, links, and special cases like file entities that require
core metadata collections.

Expected Data Structure:
    The input data should be a Pydantic model with:
    - entities: List of entity objects with attributes: name, description, category, properties, links
    - links: List of link objects with attributes: child, parent, multiplicity
"""

from dataclasses import dataclass, asdict
from typing import Protocol, runtime_checkable, Dict, Any, List
import logging

# Set up basic logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# Protocol definitions for type safety
@runtime_checkable
class EntityProtocol(Protocol):
    """Protocol defining the structure of an entity object."""
    name: str
    description: str
    category: str
    properties: list
    links: list

    def model_dump(self) -> dict:
        """Convert entity to dictionary."""
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
    entities: list[EntityProtocol]
    links: list[LinkProtocol]


# Data classes
@dataclass
class Entity:
    """Represents a Gen3 entity with its metadata and relationships."""
    name: str
    description: str
    category: str
    properties: list
    links: list

    def to_dict(self) -> dict:
        """Convert entity to dictionary representation."""
        return asdict(self)


@dataclass
class LinkObj:
    """Represents a link between two entities in Gen3 schema."""
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

def get_entity_names(data: DataSourceProtocol) -> list[str]:
    """
    Retrieve a list of entity names from the data structure.

    Args:
        data: The data structure containing entities.

    Returns:
        A list of entity names.
    """
    return [entity.name for entity in data.entities]


def get_entity_data(entity: str, data: DataSourceProtocol) -> EntityProtocol:
    """
    Retrieve the Entity object for a given entity name from the data structure.

    Args:
        entity: The name of the entity to retrieve.
        data: The data structure containing entities.

    Returns:
        The Entity object matching the given name.

    Raises:
        ValueError: If the entity is not found in data.entities.
        AttributeError: If the data structure is invalid.
    """
    if not hasattr(data, 'entities'):
        raise AttributeError("Data structure missing 'entities' attribute")

    try:
        for ent in data.entities:
            if ent.name == entity:
                return ent
        raise ValueError(f"Entity '{entity}' not found in data.entities")
    except AttributeError as e:
        raise AttributeError(f"Invalid data structure: {e}")


def get_entity_links(entity: str, data: DataSourceProtocol) -> list[dict]:
    """
    Retrieve all links where the given entity is the child.

    Args:
        entity: The name of the entity (child) to find links for.
        data: The data structure containing links.

    Returns:
        A list of link dictionaries where the entity is the child.

    Raises:
        AttributeError: If the data structure is invalid.
    """
    if not hasattr(data, 'links'):
        raise AttributeError("Data structure missing 'links' attribute")

    links = data.links
    entity_links = []
    for link in links:
        if link.child == entity:
            entity_links.append(link.model_dump())
    return entity_links


def create_core_metadata_link(child_name: str) -> dict:
    """
    Create a link dictionary for core metadata collections.

    This is used for file entities that must be linked to a core_metadata_collection.

    Args:
        child_name: The name of the child entity.

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


def convert_entity_links(links: list[dict], required: bool = True) -> list[dict]:
    """
    Convert a list of link dictionaries into the Gen3 schema 'links' format.

    Args:
        links: A list of link dictionaries for the entity.
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
    Add a core metadata link to an existing list of links for file entities.

    Args:
        links: Existing list of link dictionaries.
        child_name: The name of the child entity.

    Returns:
        Updated list of link dictionaries including core metadata link.
    """
    core_link = create_core_metadata_link(child_name)
    return links + [core_link]


def create_link_group(links: list[dict], exclusive: bool = False, required: bool = True) -> dict:
    """
    Create a link group structure from a list of links.

    Args:
        links: List of link dictionaries to group.
        exclusive: Whether the links are mutually exclusive.
        required: Whether at least one link is required.

    Returns:
        A dictionary representing the link group.
    """
    group = LinkGroup(
        exclusive=exclusive,
        required=required,
        subgroup=links
    )
    return group.to_dict()


def create_link_prop(target_entity: str, multiplicity: str) -> dict:
    """
    Create a property dictionary for a link to another entity.

    Args:
        target_entity: The name of the target entity.
        multiplicity: The multiplicity of the link (e.g., 'one_to_one', 'one_to_many').

    Returns:
        A dictionary representing the link property for the schema.
    """
    link_prop = {
        link_suffix(target_entity): {
            "$ref": f"_definitions.yaml#/{multiplicity}"
        }
    }
    return link_prop


def get_properties(entity_name: str, data: DataSourceProtocol) -> list[dict]:
    """
    Retrieve the list of property dictionaries for a given entity.

    Args:
        entity_name: The name of the entity.
        data: The data structure containing entities.

    Returns:
        A list of property dictionaries, or an empty list if no properties found.

    Raises:
        ValueError: If the entity is not found.
    """
    ent = get_entity_data(entity_name, data)
    props = ent.properties
    
    output = []
    if props:
        for prop in props:
            pdict = {
                prop.name: {k: v for k, v in prop.model_dump().items() if k != "name"}
            }
            
            output.append(pdict)
            
    else:
        logger.debug(f"No properties found for entity '{entity_name}'")
    
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
           'enums': [{'name': 'EDTA'}, {'name': 'Heparin'}, {'name': 'Citrate'}]
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


def construct_props(entity_name: str, data: DataSourceProtocol) -> dict:
    """
    Construct the 'properties' section for a Gen3 schema entity.

    This combines the entity's own properties and any link properties.

    Args:
        entity_name: The name of the entity.
        data: The data structure containing entities and links.

    Returns:
        A dictionary of all properties (including links) for the entity.

    Raises:
        ValueError: If the entity is not found.
    """
    links = get_entity_links(entity_name, data)
    props = get_properties(entity_name, data)
    props = strip_required_field(props)
    
    # Flatten property dicts into a single dict
    props_dict = {}
    for prop in props:
        if isinstance(prop, dict):
            prop = format_enum(prop)
            props_dict.update(prop)
    
    # Add link properties
    for link in links:
        link_prop = create_link_prop(link['parent'], link['multiplicity'])
        props_dict.update(link_prop)
    
    return props_dict


def get_category(entity_name: str, data: DataSourceProtocol) -> str:
    """
    Get the category value for a given entity.

    Args:
        entity_name: The name of the entity.
        data: The data structure containing entities.

    Returns:
        The category value (as a string).

    Raises:
        ValueError: If the entity is not found.
    """
    ent = get_entity_data(entity_name, data)
    category = ent.category
    
    # If it's an Enum, get its value; otherwise, return as is
    if hasattr(category, "value"):
        return category.value
    return category


def get_entity_value(entity_name: str, key: str, data: DataSourceProtocol) -> str | list | dict | None:
    """
    Return the value of a single key within an entity object.

    Args:
        entity_name: The name of the entity to retrieve.
        key: The key whose value is to be returned.
        data: The data structure containing entities.

    Returns:
        The value associated with the specified key in the entity object.

    Raises:
        ValueError: If the entity is not found.
        KeyError: If the key doesn't exist in the entity.
    """
    ent = get_entity_data(entity_name, data)
    entity_dict = ent.model_dump()
    
    if key not in entity_dict:
        raise KeyError(f"Key '{key}' not found in entity '{entity_name}'")
    
    return entity_dict[key]


def is_file_entity(entity_name: str, data: DataSourceProtocol) -> bool:
    """
    Determine if an entity is a file entity (category: data_file).

    Args:
        entity_name: The name of the entity.
        data: The data structure containing entities.

    Returns:
        True if the entity is a file entity, False otherwise.
    """
    try:
        category_value = get_entity_value(entity_name, 'category', data)
        return category_value == 'data_file'
    except (ValueError, KeyError):
        return False


def populate_template(entity_name: str, input_data: DataSourceProtocol, template: dict) -> dict:
    """
    Populate a Gen3 schema template dictionary with values from a Pydantic data model.

    This function takes an entity name, a Pydantic model instance containing entity data,
    and a Gen3 schema template dictionary. It fills a copy of the template with values
    from the input data, applying special logic for certain keys (e.g., 'name', 'category',
    'properties', 'links').

    Args:
        entity_name: The name of the entity to populate in the template.
        input_data: A Pydantic model instance containing the entity's data.
        template: A Gen3 schema template dictionary to be populated.

    Returns:
        A new Gen3 schema template dictionary populated with values from the input data.

    Raises:
        ValueError: If the entity is not found in input_data.
    """
    ent = get_entity_data(entity_name, input_data)
    ent_dict = ent.model_dump()
    output_schema = template.copy()
    
    # add entity name as title
    output_schema['title'] = ent.name
    
    # Check if entity is a file category
    file_entity = is_file_entity(entity_name, input_data)
    
    # Populate template with entity data
    for key, value in ent_dict.items():
        if key == 'name':
            output_schema['id'] = value
        elif key == 'category':
            output_schema[key] = get_category(entity_name, input_data)
        elif key == 'properties':
            output_schema[key] = construct_props(entity_name, input_data)
        elif key in output_schema:
            output_schema[key] = value
        else:
            logger.debug(f"Key '{key}' from entity '{entity_name}' not found in template")
    
    # add required props
    props = get_properties(entity_name, input_data)
    required_props = get_required_prop_names(props)
    if required_props:
        output_schema['required'] = required_props
    
    # Process and add links
    links = get_entity_links(entity_name, input_data)
    converted_links = convert_entity_links(links)
    
    # Add core metadata link for file entities
    if file_entity and links:
        converted_links = add_core_metadata_link(converted_links, links[0]['child'])
    
    # Create link group if multiple links exist
    if len(converted_links) > 1:
        output_schema['links'] = create_link_group(converted_links)
    else:
        output_schema['links'] = converted_links
    
    return output_schema
