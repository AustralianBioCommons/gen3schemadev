# Generates gen3 jsonschema template for a single entity using the gen3 metaschema
from gen3schemadev.utils import *


def generate_gen3_template(metaschema: str) -> dict:
    """
    Generates a Gen3 JSON schema template for a single entity using the provided metaschema YAML file.

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
        metaschema_data = load_yaml(metaschema)
        out_template = {}
        properties = metaschema_data.get('properties', {})
        out_template['$schema'] = metaschema_data.get('$schema')
        for k, v in properties.items():
            if 'default' in v:
                out_template[k] = v['default']
            else:
                out_template[k] = None
        return out_template
    except Exception as e:
        print(f"An error occurred while generating the Gen3 template: {e}")
        raise