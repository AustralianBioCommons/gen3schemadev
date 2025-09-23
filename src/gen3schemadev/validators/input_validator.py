import logging
from gen3schemadev.schema.input_schema import DataModel
import yaml

logger = logging.getLogger(__name__)

def load_yaml(file_path):
    """
    Loads a YAML file and returns its contents as a Python object.

    Args:
        file_path (str): Path to the YAML file.

    Returns:
        dict: Parsed YAML content.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If the file is not valid YAML.
        Exception: For any other exceptions during file reading.
    """
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
            logger.info(f"Successfully loaded YAML file: {file_path}")
            return data
    except FileNotFoundError as e:
        logger.error(f"File not found: {file_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error in file {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading YAML file {file_path}: {e}")
        raise

def validate_input_yaml(file_path):
    """
    Validates the input YAML file against the Pydantic DataModel schema.

    Args:
        file_path (str): Path to the YAML file.

    Returns:
        DataModel: An instance of DataModel if validation is successful.

    Raises:
        ValidationError: If the data does not conform to the DataModel schema.
        Exception: For any other exceptions during validation.
    """
    try:
        data = load_yaml(file_path)
        validated = DataModel.model_validate(data)
        logger.info(f"Completed validation for file: {file_path}")
        return validated
    except Exception as e:
        logger.error(f"Failed to run validation for file {file_path}: {e}")
        raise
