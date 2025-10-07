import json
import os
import yaml
from jsonschema import validate
import logging
from gen3_validator.resolve_schema import ResolveSchema

# Set up basic logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def create_dir_if_not_exists(dir_path):
    base_path = os.path.dirname(dir_path)
    if not os.path.exists(base_path):
        os.makedirs(base_path)
        logger.info(f"Created directory: {base_path}")

def load_yaml(file_path):
    """
    Loads a YAML file and returns its contents.
    Logs success or error messages.
    """
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
            logger.info(f"Successfully loaded YAML file: {file_path}")
            return data
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error in file {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading YAML file {file_path}: {e}")
        raise

def write_yaml(data, file_path):
    """
    Writes a Python object to a YAML file.
    Logs success or error messages.
    """
    try:
        create_dir_if_not_exists(file_path)
        with open(file_path, 'w') as f:
            yaml.safe_dump(data, f, sort_keys=False)
            logger.info(f"Successfully wrote YAML file: {file_path}")
    except Exception as e:
        logger.error(f"Failed to write YAML file {file_path}: {e}")
        raise

def read_json(file_path):
    """
    Reads a JSON file and returns its contents.
    Logs success or error messages.
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            logger.info(f"Successfully loaded JSON file: {file_path}")
            return data
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error in file {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading JSON file {file_path}: {e}")
        raise

def write_json(data, file_path):
    """
    Writes a Python object to a JSON file.
    Logs success or error messages.
    """
    try:
        create_dir_if_not_exists(file_path)
        with open(file_path, 'w') as f:
            json.dump(data, f)
            logger.info(f"Successfully wrote JSON file: {file_path}")
    except Exception as e:
        logger.error(f"Failed to write JSON file {file_path}: {e}")
        raise

def bundle_yamls(input_dir: str) -> dict:
    """
    Bundles all YAML files in a directory into a single dictionary.
    """
    bundle = {}
    yamls_found = 0
    for file_name in os.listdir(input_dir):
        if file_name.endswith('.yaml') or file_name.endswith('.yml'):
            yamls_found += 1
            file_path = os.path.join(input_dir, file_name)
            bundle[file_name] = load_yaml(file_path)
    if yamls_found == 0:
        raise Exception(f"No YAML files found in directory: {input_dir}")
    return bundle


def resolve_schema(schema_path: str) -> list:
    """
    Resolves a Gen3 JSON schema file and returns the resolved schema as a list of schema dicts.
    """
    resolver = ResolveSchema(schema_path)
    resolver.resolve_schema()
    # The resolved schema may be a dict (bundled) or a list (already split)
    # If it's a dict, return its values as a list; if it's already a list, return as is
    if isinstance(resolver.schema_resolved, dict):
        return list(resolver.schema_resolved.values())
    return resolver.schema_resolved

def bundled_schema_to_list_dict(bundled_schema: list[dict]) -> list[dict]:
    """
    Validates a list of Gen3 schema dictionaries and returns the list if valid.

    :param bundled_schema: List of schema dictionaries.
    :type bundled_schema: list[dict]

    :returns: The validated list of schema dictionaries.
    :rtype: list[dict]

    :raises ValueError: If auxiliary files are found in the schema list.
    :raises Exception: If the input is not a list of dicts or another error occurs.
    """
    try:
        if not isinstance(bundled_schema, list) or not all(isinstance(v, dict) for v in bundled_schema):
            raise Exception("Input must be a list of dictionaries representing schemas.")

        ids = [v.get("id") for v in bundled_schema]
        aux_files = {"_definitions.yaml", "_settings.yaml", "_terms.yaml"}
        if any(aux_file in ids for aux_file in aux_files):
            raise ValueError(
                "Auxiliary files (_definitions.yaml, _settings.yaml, _terms.yaml) found in schema list. "
                "Make sure you have resolved the bundled jsonschema first using "
                "`gen3schemadev.utils.resolve_schema()`"
            )

        return bundled_schema
    except Exception as e:
        logger.exception("Failed to parse bundled schema list.")
        raise
