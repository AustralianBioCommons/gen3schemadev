import os
import logging
import yaml
import datetime

# Ensure logs directory exists
LOG_DIR = os.path.join(os.getcwd(), "logs")
if not os.path.isdir(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging for this module
LOG_FILE = os.path.join(LOG_DIR, f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}_gen3schematools.log")
logging.basicConfig(
    level=logging.INFO,
    filename=LOG_FILE,
    filemode="a",
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class DictDataTypeUpdater:
    def __init__(self, yaml_file_path: str):
        self.yaml_file_path = yaml_file_path
        self.data_dict = self.read_yaml()

    def read_yaml(self):
        """
        Reads a YAML file from the specified path and returns its contents as a dictionary.

        :return: Dictionary containing the YAML file data.
        :rtype: dict
        """
        logger.info(f"Reading YAML file: {self.yaml_file_path}")
        try:
            with open(self.yaml_file_path, "r") as file:
                data = yaml.safe_load(file)
            return data
        except Exception as e:
            logger.error(f"Failed to read YAML file '{self.yaml_file_path}': {e}")
            raise

    def write_yaml(self, yaml_content):
        """
        Writes the provided content back to the YAML file.
        """
        logger.info(f"Writing YAML file: {self.yaml_file_path}")
        try:
            with open(self.yaml_file_path, "w") as file:
                yaml.dump(yaml_content, file)
        except Exception as e:
            logger.error(f"Failed to write YAML file '{self.yaml_file_path}': {e}")
            raise

    def add_data_type_in_dict(self, data_dict, target_key, add_value):
        """Recursively add a value under matching keys in a nested dict.

        This method traverses the input dictionary and for each occurrence
        of target_key, ensures its value is a list and appends add_value.

        Args:
            data_dict (dict): The nested dictionary to search and modify.
            target_key (str): The key to match for adding the value.
            add_value: The value to append under the matching key.

        Returns:
            dict: The updated dictionary with added values.

        Raises:
            TypeError: If data_dict is not a dict or target_key is not a str.
            KeyError: If accessing a key in data_dict fails.
            RuntimeError: On unexpected errors during processing.
        """
        if not isinstance(data_dict, dict):
            msg = f"add_data_type_in_dict expects data_dict to be dict, got {type(data_dict).__name__}"
            logger.error(msg)
            raise TypeError(msg)
        if not isinstance(target_key, str):
            msg = f"add_data_type_in_dict expects target_key to be str, got {type(target_key).__name__}"
            logger.error(msg)
            raise TypeError(msg)

        for current_key in list(data_dict.keys()):
            try:
                current_value = data_dict[current_key]
            except KeyError as e:
                logger.error(f"Failed to access key '{current_key}': {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error accessing '{current_key}': {e}")
                raise

            logger.debug(f"Checking key: {current_key}")
            try:
                if isinstance(current_value, dict):
                    # Recurse into nested dictionary
                    self.add_data_type_in_dict(current_value, target_key, add_value)
                elif current_key == target_key:
                    # Convert to list if necessary, then append
                    if not isinstance(current_value, list):
                        data_dict[current_key] = [current_value]
                    data_dict[current_key].append(add_value)
                    logger.info(f"Updated key '{current_key}' to value: {data_dict[current_key]}")
            except Exception as e:
                logger.error(f"Error processing key '{current_key}': {e}")
                raise RuntimeError(f"Error processing key '{current_key}': {e}")

        return data_dict

    def update_data_type_in_dict(self, data_dict, target_key,
                                 target_value, replacement_value):
        """Recursively update matching key-value pairs in a nested dict.

        This method traverses the input dictionary and for each occurrence
        of target_key whose current value equals target_value, replaces
        it with replacement_value.

        Args:
            data_dict (dict): The nested dictionary to search and modify.
            target_key (str): The key to match for updating its value.
            target_value: The existing value to be replaced.
            replacement_value: The new value to set under the key.

        Returns:
            dict: The updated dictionary with replaced values.

        Raises:
            TypeError: If data_dict is not a dict or target_key is not a str.
            RuntimeError: On unexpected errors during processing.
        """
        if not isinstance(data_dict, dict):
            msg = f"update_data_type_in_dict expects data_dict to be dict, got {type(data_dict).__name__}"
            logger.error(msg)
            raise TypeError(msg)
        if not isinstance(target_key, str):
            msg = f"update_data_type_in_dict expects target_key to be str, got {type(target_key).__name__}"
            logger.error(msg)
            raise TypeError(msg)

        for current_key, current_value in list(data_dict.items()):
            logger.debug(f"Checking key: {current_key}")
            try:
                if isinstance(current_value, dict):
                    # Recurse into nested dictionary
                    self.update_data_type_in_dict(
                        current_value, target_key, target_value, replacement_value
                    )
                elif current_key == target_key and current_value == target_value:
                    data_dict[current_key] = replacement_value
                    logger.info(f"Updated key '{current_key}' to value: {replacement_value}")
            except Exception as e:
                logger.error(f"Error processing key '{current_key}': {e}")
                raise RuntimeError(f"Error processing key '{current_key}': {e}")

        return data_dict