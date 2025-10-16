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