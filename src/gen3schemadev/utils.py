import json
import os
import yaml
from jsonschema import validate
import logging
from gen3_validator.resolve_schema import ResolveSchema
import tempfile


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
        dir_path = os.path.dirname(file_path)
        if dir_path:
            create_dir_if_not_exists(file_path)
        with open(file_path, 'w') as f:
            yaml.safe_dump(data, f, sort_keys=False, indent=2)
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
        dir_path = os.path.dirname(file_path)
        if dir_path:
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


def resolve_schema(schema_dir: str = None, schema_path: str = None) -> dict:
    """
    Load and resolve a Gen3 JSON schema from either a directory of YAML files or a bundled JSON file.

    If `schema_dir` is provided, all YAML files in the directory are bundled into a temporary JSON file,
    which is then resolved. If `schema_path` is provided, it is used directly.

    Returns:
        list: A list of resolved schema dictionaries.

    Raises:
        Exception: If neither `schema_dir` nor `schema_path` is provided, or if resolution fails.
    """
    temp_file_path = None
    if schema_dir:
        bundled_schema = bundle_yamls(schema_dir)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", dir=".", delete=False) as tf:
            json.dump(bundled_schema, tf)
            temp_file_path = tf.name
            schema_path = temp_file_path

    try:
        resolver = ResolveSchema(schema_path)
        resolver.resolve_schema()
        resolved = resolver.schema_resolved
        output = {}
        
        for k, v in resolved.items():
            schema_name = v.get('id', '')
            output[f"{schema_name}.yaml"] = v

        if isinstance(output, dict):
            return output
        else:
            raise Exception(f"Resolved schema not dictionary of schemas, failed to resolve schema: {resolved}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

