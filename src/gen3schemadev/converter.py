from dataclasses import dataclass, asdict
from typing import Optional, List, Union, Any
import logging

# Set up basic logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class Entity:
    name: str
    description: str
    category: str
    properties: list
    links: list

    def to_dict(self):
        return asdict(self)

@dataclass
class LinkObj:
    name: str
    backref: str
    label: Optional[str]
    target_type: str
    multiplicity: str
    required: bool

    def to_dict(self):
        return asdict(self)

@dataclass
class LinkGroup:
    exclusive: bool
    required: bool
    subgroup: List[dict]

    def to_dict(self):
        return asdict(self)

def get_entity_data(entity: str, data: Any) -> Entity:
    """
    Retrieve the Entity object for a given entity name from the data structure.

    Args:
        entity (str): The name of the entity to retrieve.
        data (Any): The data structure containing entities (should have a .entities attribute).

    Returns:
        Entity: The Entity object matching the given name.

    Raises:
        ValueError: If the entity is not found in data.entities.
        AttributeError: If the data structure is invalid.
        Exception: For any other unexpected errors.
    """
    try:
        for ent in data.entities:
            if ent.name == entity:
                return ent
        raise ValueError(f"Entity '{entity}' not found in data.entities")
    except AttributeError as e:
        raise AttributeError(f"Invalid data structure: {e}")
    except Exception as e:
        raise Exception(f"An error occurred while retrieving entity data: {e}")

def get_entity_links(entity: str, data: Any) -> list[dict]:
    """
    Retrieve all links where the given entity is the child.

    Args:
        entity (str): The name of the entity (child) to find links for.
        data (Any): The data structure containing links (should have a .links attribute).

    Returns:
        list[dict]: A list of link dictionaries where the entity is the child.
    """
    links = data.links
    entity_links = []
    for link in links:
        if link.child == entity:
            entity_links.append(link.model_dump())
    return entity_links

def create_core_metadata_link(child_name: str) -> dict:
    """
    Create a special link dictionary for core metadata collections.

    This is used for file entities that must be linked to a core_metadata_collection.

    Args:
        child_name (str): The name of the child entity.

    Returns:
        dict: A dictionary representing the core metadata link.
    """
    link_obj = LinkObj(
        name=f"core_metadata_collections",
        backref=f"{child_name}s",
        label=None,
        target_type="core_metadata_collection",
        multiplicity="one_to_one",
        required=True 
    )
    return link_obj.to_dict()

def convert_entity_links(links: dict, entity_file: bool = False) -> dict:
    """
    Convert a list of link dictionaries into the Gen3 schema 'links' format.

    If the entity is a file (entity_file=True), a core metadata link is also added.

    Args:
        links (dict): A list of link dictionaries for the entity.
        entity_file (bool): Whether the entity is a file (adds core metadata link if True).

    Returns:
        dict: The formatted 'links' section for the Gen3 schema.
    """
    link_list = []
    for link in links:
        link_obj = LinkObj(
            name=f"{link['parent']}s",
            backref=f"{link['child']}s",
            label=None,
            target_type=link['parent'],
            multiplicity=link['multiplicity'],
            required=True  # TODO: Remove hardcoding, should pull from input yaml
        )
        link_list.append(link_obj.to_dict())

    if entity_file:
        core_link = create_core_metadata_link(links[0]['child'])
        link_list.append(core_link)

    if len(link_list) > 1:
        group = LinkGroup(
            exclusive=False,
            required=True,
            subgroup=link_list
        )
        output = group.to_dict()
    else:
        output = link_list
    return output

def create_link_prop(target_entity: str, multiplicity: str) -> dict:
    """
    Create a property dictionary for a link to another entity.

    Args:
        target_entity (str): The name of the target entity.
        multiplicity (str): The multiplicity of the link (e.g., 'one_to_one', 'one_to_many').

    Returns:
        dict: A dictionary representing the link property for the schema.
    """
    link_prop = {}
    link_prop[f"{target_entity}s"] = {
        "$ref": f"_definitions.yaml#/{multiplicity}"
    }
    return link_prop

def get_properties(entity_name: str, data: Any) -> list[dict]:
    """
    Retrieve the list of property dictionaries for a given entity.

    Args:
        entity_name (str): The name of the entity.
        data (Any): The data structure containing entities.

    Returns:
        list[dict] or None: A list of property dictionaries, or None if no properties found.
    """
    output = []
    ent = get_entity_data(entity_name, data)
    props = ent.properties
    if props:
        for prop in props:
            pdict = {
                prop.name: {k: v for k, v in prop.model_dump().items() if k != "name"}
            }
            output.append(pdict)
    else:
        logger.warn(f'No properties found for entity {entity_name}')
        output = None
    return output

def construct_props(entity_name: str, data: Any) -> dict:
    """
    Construct the 'properties' section for a Gen3 schema entity.

    This combines the entity's own properties and any link properties.

    Args:
        entity_name (str): The name of the entity.
        data (Any): The data structure containing entities and links.

    Returns:
        dict: A dictionary of all properties (including links) for the entity.
    """
    links = get_entity_links(entity_name, data)
    props = get_properties(entity_name, data)
    if props is None:
        props = []
    # Flatten property dicts into a single dict
    props_dict = {}
    for prop in props:
        if isinstance(prop, dict):
            props_dict.update(prop)
    # Add link properties
    for link in links:
        link_prop = create_link_prop(link['parent'], link['multiplicity'])
        props_dict.update(link_prop)
    return props_dict

def get_category(entity_name: str, data: Any) -> str:
    """
    Get the category value for a given entity.

    Args:
        entity_name (str): The name of the entity.
        data (Any): The data structure containing entities.

    Returns:
        str: The category value (as a string).
    """
    ent = get_entity_data(entity_name, data)
    category = ent.category
    # If it's an Enum, get its value; otherwise, return as is
    if hasattr(category, "value"):
        return category.value
    return category

def get_entity_value(entity_name: str, key: str, data: Any):
    """
    Returns the value of a single key within an entity object.

    Args:
        entity_name (str): The name of the entity to retrieve.
        key (str): The key whose value is to be returned.
        data (Any): The data structure containing entities.

    Returns:
        The value associated with the specified key in the entity object.
    """
    ent = get_entity_data(entity_name, data)
    return ent.model_dump()[key]

def populate_template(entity_name: str, input_data, template) -> dict:
    """
    Populate a Gen3 schema template dictionary with values from a Pydantic data model.

    This function takes an entity name, a Pydantic model instance containing entity data,
    and a Gen3 schema template dictionary. It fills a copy of the template with values
    from the input data, applying special logic for certain keys (e.g., 'name', 'category',
    'properties', 'links'). If a key from the input data is not found in the template,
    it is added with a value of None and a warning is logged.

    Args:
        entity_name (str): The name of the entity to populate in the template.
        input_data: A Pydantic model instance containing the entity's data.
        template (dict): A Gen3 schema template dictionary to be populated.

    Returns:
        dict: A new Gen3 schema template dictionary populated with values from the input data.

    Side Effects:
        Logs a warning if a key from the input data is not found in the template.
    """

    ent = get_entity_data(entity_name, input_data)
    ent_dict = ent.model_dump()
    output_schema = template.copy()
    
    # Checking if entity is file category
    file_cat = False
    category_value = get_entity_value(entity_name, 'category', input_data)
    if category_value == 'data_file':
        file_cat = True
    
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
            logger.warning(f"Key '{key}' not found in template")
    
    # adding links
    links = get_entity_links(entity_name, input_data)
    output_schema['links'] = convert_entity_links(links, entity_file=file_cat)
    
    return output_schema