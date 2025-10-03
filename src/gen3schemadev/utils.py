import json
import os
import yaml
from jsonschema import validate
import logging

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
            bundle[file_name.replace('.yaml', '')] = load_yaml(file_path)
    if yamls_found == 0:
        raise Exception(f"No YAML files found in directory: {input_dir}")
    return bundle
