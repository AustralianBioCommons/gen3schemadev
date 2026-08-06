# Generates gen3 jsonschema template for a single node using the gen3 metaschema
from gen3schemadev.utils import *
import os
import yaml
import importlib.resources
import logging

logger = logging.getLogger(__name__)

def read_template_yaml(template_filename='template.yml'):
    """
    Reads a YAML template file from the schema_templates directory.

    Args:
        template_filename (str): The name of the YAML template file.

    Returns:
        dict: The loaded YAML data as a dictionary.
    """
    current_dir = os.path.dirname(__file__)
    template_path = os.path.join(current_dir, 'schema_templates', template_filename)
    with open(template_path, 'r') as file:
        data = yaml.safe_load(file)
    return data

def generate_gen3_template(metaschema: dict) -> dict:
    """
    Generates a Gen3 JSON schema template for a single node using the provided metaschema YAML file.

    Args:
        metaschema (str): Path to the metaschema YAML file.

    Returns:
        dict: A dictionary containing the default values for each property defined in the metaschema.

    Raises:
        FileNotFoundError: If the metaschema file does not exist.
        yaml.YAMLError: If there is an error parsing the YAML file.
        Exception: For any other unexpected errors.
    """
    try:
        metaschema_data = metaschema
        out_template = {}
        properties = metaschema_data.get('properties', {})
        out_template['$schema'] = metaschema_data.get('$schema')
        logger.info(f"Generating Gen3 template from metaschema with {len(properties)} properties.")
        for k, v in properties.items():
            if 'default' in v:
                out_template[k] = v['default']
                logger.debug(f"Set default for property '{k}': {v['default']}")
            else:
                out_template[k] = None
                logger.debug(f"No default for property '{k}', set to None.")
        logger.info("Gen3 template generation completed successfully.")
        return out_template
    except Exception as e:
        logger.error(f"An error occurred while generating the Gen3 template: {e}")
        raise


def generate_def_template():
    return read_template_yaml('_definitions.yaml')

def generate_setting_template():
    return read_template_yaml('_settings.yaml')

def generate_terms_template():
    return read_template_yaml('_terms.yaml')

def generate_project_template():
    return read_template_yaml('project.yaml')

def generate_core_metadata_template():
    return read_template_yaml('core_metadata_collection.yaml')

def get_metaschema():
    return read_template_yaml('gen3_metaschema.yml')

def generate_program_template():
    return read_template_yaml('program.yaml')

def shared_property_names(block_name: str) -> set:
    """
    Return the property names _definitions.yaml supplies through a shared block.

    Read from the packaged _definitions.yaml rather than hardcoded, so the set
    can never drift from the definitions actually generated. A hardcoded list
    is how the old "reserved system property" check ended up banning names that
    Gen3 itself uses on every node.

    The block's own $ref is followed, which is why this is not simply
    ``set(block)``: data_file_properties carries
    ``$ref: "#/ubiquitous_properties"``, so a naive read would miss 'type',
    'id' and 'submitter_id' and under-report on exactly the file nodes that
    need it most.

    Args:
        block_name: A key in _definitions.yaml, e.g. 'ubiquitous_properties'.

    Returns:
        The set of property names the block supplies, or an empty set if the
        block does not exist.
    """
    definitions = generate_def_template()

    def collect(name, seen):
        # A definition that referenced itself would otherwise hang generation.
        if name in seen:
            return set()
        seen.add(name)
        block = definitions.get(name)
        if not isinstance(block, dict):
            return set()
        names = set()
        for key, value in block.items():
            if key == '$ref':
                names |= collect(str(value).partition('#')[2].strip('/'), seen)
            else:
                names.add(key)
        return names

    return collect(block_name, set())


def get_input_example_text():
    """
    Returns the raw text of the packaged example input YAML.

    Returned as text rather than a parsed dict so `init` can write it out
    byte-for-byte identical to examples/input_example.yaml, preserving key
    order, comments and formatting that a load/dump round trip would lose.
    """
    current_dir = os.path.dirname(__file__)
    template_path = os.path.join(current_dir, 'schema_templates', 'input_example.yaml')
    with open(template_path, 'r') as file:
        return file.read()