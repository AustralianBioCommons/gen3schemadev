import os
import logging
import yaml
import datetime
import json
from collections import defaultdict, deque

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
        """
        Recursively add a value to all occurrences of a given key in a nested dictionary.

        Example:
            yaml_fn = "gen3schemadev/schema_out/demographic.yaml"
            updater = DictDataTypeUpdater(yaml_fn)
            # Add None to all "enum" keys in the dictionary
            updater.add_data_type_in_dict(updater.data_dict, "enum", "null")

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
        """
        Recursively update the value of a given key in a nested dictionary if it matches a target value.

        Example:
            yaml_fn = "gen3schemadev/schema_out/demographic.yaml"
            updater = DictDataTypeUpdater(yaml_fn)
            # Update all "type": "number" to "type": ["number", "null"]
            updater.update_data_type_in_dict(updater.data_dict, "type", "number", ["number", "null"])

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

def update_definition_to_yaml(yaml_file_path, new_definition):
    """
    Updates a new definition then resaves back to a YAML file.

    Parameters:
        yaml_file_path (str): Path to the YAML file.
        new_definition (dict): Dictionary containing the new definition to add.

    Returns:
        None
    """
    logger.info(f"Starting update_definition_to_yaml for file: {yaml_file_path}")
    try:
        logger.debug(f"Reading YAML file: {yaml_file_path}")
        with open(yaml_file_path, 'r') as file:
            yaml_content = yaml.safe_load(file) or {}
        logger.debug(f"Current YAML content loaded: {yaml_content}")
    except Exception as e:
        logger.error(f"Failed to read YAML file '{yaml_file_path}': {e}")
        raise

    logger.info(f"Adding new definition to YAML content: {new_definition}")
    yaml_content.update(new_definition)

    try:
        logger.debug(f"Writing updated content back to YAML file: {yaml_file_path}")
        with open(yaml_file_path, 'w') as file:
            yaml.safe_dump(yaml_content, file)
    except Exception as e:
        logger.error(f"Failed to write YAML file '{yaml_file_path}': {e}")
        raise

    logger.info(f"Successfully added new definition to {yaml_file_path}")




class ResolveSchema:
    def __init__(self, schema_path: str):
        """
        Initialize the ResolveSchema class.

        Parameters:
        - schema_path (str): The path to the JSON schema file.
        """
        self.schema_path = schema_path
        self.schema = self.read_json(self.schema_path)
        self.nodes = self.get_nodes()
        self.node_pairs = self.get_all_node_pairs()
        self.node_order = self.get_node_order(edges=self.node_pairs)
        self.schema_list = self.split_json()
        self.schema_def = self.return_schema("_definitions.yaml")
        self.schema_term = self.return_schema("_terms.yaml")
        self.schema_def_resolved = self.resolve_references(
            self.schema_def, self.schema_term
        )
        self.schema_list_resolved = self.resolve_all_references()
        self.schema_resolved = self.schema_list_to_json(self.schema_list_resolved)

    def read_json(self, path: str) -> dict:
        """
        Read a JSON file and return its contents as a dictionary.

        Parameters:
        - path (str): The path to the JSON file.

        Returns:
        - dict: The contents of the JSON file.
        """
        with open(path) as f:
            return json.load(f)

    def get_nodes(self) -> list:
        """
        Retrieve all node names from the schema.

        Returns:
        - list: A list of node names.
        """
        nodes = list(self.schema.keys())
        return nodes

    def get_node_link(self, node_name: str) -> tuple:
        """
        Retrieve the links and ID for a given node.

        Parameters:
        - node_name (str): The name of the node.

        Returns:
        - tuple: A tuple containing the node ID and its links.
        """
        links = self.schema[node_name]["links"]
        node_id = self.schema[node_name]["id"]
        if "subgroup" in links[0]:
            return node_id, links[0]["subgroup"]
        else:
            return node_id, links

    def get_node_category(self, node_name: str) -> tuple:
        """
        Retrieve the category and ID for a given node, excluding certain nodes.

        Parameters:
        - node_name (str): The name of the node.

        Returns:
        - tuple: A tuple containing the node ID and its category, or None if the node is excluded.
        """
        category = self.schema[node_name]["category"]
        node_id = self.schema[node_name]["id"]
        return node_id, category

    def get_node_properties(self, node_name: str) -> tuple:
        """
        Retrieve the properties for a given node.

        Parameters:
        - node_name (str): The name of the node.

        Returns:
        - tuple: A tuple containing the node ID and its properties.
        """
        properties = {
            k: v for k, v in self.schema[node_name]["properties"].items()
            if k != "$ref"
        }
        property_keys = list(properties.keys())
        node_id = self.schema[node_name]["id"]
        return node_id, property_keys

    def generate_node_lookup(self) -> dict:
        node_lookup = {}
        excluded_nodes = [
            "_definitions.yaml",
            "_terms.yaml",
            "_settings.yaml",
            "program.yaml",
        ]

        for node in self.nodes:
            if node in excluded_nodes:
                continue

            category = self.get_node_category(node)
            if category:
                category = category[1]

            props = self.get_node_properties(node)
            node_lookup[node] = {"category": category, "properties": props}
        return node_lookup

    def find_upstream_downstream(self, node_name: str) -> list:
        """
        Takes a node name and returns the upstream and downstream nodes.

        Parameters:
        - node_name (str): The name of the node.

        Returns:
        - list: A list of tuples representing upstream and downstream nodes.
        """
        node_id, links = self.get_node_link(node_name)

        # Ensure links is a list
        if isinstance(links, dict):
            links = [links]

        results = []

        for link in links:
            target_type = link.get("target_type")

            if not node_id or not target_type:
                print("Missing essential keys in link:", link)
                results.append((None, None))
                continue

            results.append((target_type, node_id))

        return results

    def get_all_node_pairs(
        self,
        excluded_nodes=[
            "_definitions.yaml",
            "_terms.yaml",
            "_settings.yaml",
            "program.yaml",
        ],
    ) -> list:
        """
        Retrieve all node pairs, excluding specified nodes.

        Parameters:
        - excluded_nodes (list): A list of node names to exclude.

        Returns:
        - list: A list of node pairs.
        """
        node_pairs = []
        for node in self.nodes:
            if node not in excluded_nodes:
                node_pairs.extend(self.find_upstream_downstream(node))
            else:
                continue
        return node_pairs

    def get_node_order(self, edges: list) -> list:
        """
        Determine the order of nodes based on their dependencies.

        Parameters:
        - edges (list): A list of tuples representing node dependencies.

        Returns:
        - list: A list of nodes in topological order.
        """
        # Build graph representation
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        for upstream, downstream in edges:
            graph[upstream].append(downstream)
            in_degree[downstream] += 1
            if upstream not in in_degree:
                in_degree[upstream] = 0

        # Perform Topological Sorting (Kahn's Algorithm)
        sorted_order = []
        zero_in_degree = deque([node for node in in_degree if in_degree[node] == 0])

        while zero_in_degree:
            node = zero_in_degree.popleft()
            sorted_order.append(node)

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    zero_in_degree.append(neighbor)

        # Ensure core_metadata_collection is last
        sorted_order.remove("core_metadata_collection")
        sorted_order.append("core_metadata_collection")

        return sorted_order

    def split_json(self) -> list:
        """
        Split the schema into a list of individual node schemas.

        Returns:
        - list: A list of node schemas.
        """
        schema_list = []
        for node in self.nodes:
            schema_list.append(self.schema[node])
        return schema_list

    def return_schema(self, target_id: str) -> dict:
        """
        Retrieves the first dictionary from a list where the 'id' key matches the target_id.

        Parameters:
        - target_id (str): The value of the 'id' key to match.

        Returns:
        - dict: The dictionary that matches the target_id, or None if not found.
        """
        if target_id.endswith(".yaml"):
            target_id = target_id[:-5]

        result = next(
            (item for item in self.schema_list if item.get("id") == target_id), None
        )
        if result is None:
            print(f"{target_id} not found")
        return result

    def resolve_references(self, schema: dict, reference: dict) -> dict:
        """
        Takes a gen3 jsonschema draft 4 as a dictionary and recursively
        resolves any references using a reference schema which has no
        references.

        Parameters:
        - schema (dict): The JSON node to resolve references in.
        - reference (dict): The schema containing the references.

        Returns:
        - dict: The resolved JSON node with references resolved.
        """
        ref_input_content = reference

        def resolve_node(node, manual_ref_content=ref_input_content):
            if isinstance(node, dict):
                if "$ref" in node:
                    ref_path = node["$ref"]
                    ref_file, ref_key = ref_path.split("#")
                    ref_file = ref_file.strip()
                    ref_key = ref_key.strip("/")

                    # if a reference file is in the reference, load the pre-defined reference, if no file exists, then use the schema itself as reference
                    if ref_file:
                        ref_content = manual_ref_content
                    else:
                        ref_content = schema

                    for part in ref_key.split("/"):
                        ref_content = ref_content[part]

                    resolved_content = resolve_node(ref_content)
                    # Merge resolved content with the current node, excluding the $ref key
                    return {
                        **resolved_content,
                        **{k: resolve_node(v) for k, v in node.items() if k != "$ref"},
                    }
                else:
                    return {k: resolve_node(v) for k, v in node.items()}
            elif isinstance(node, list):
                return [resolve_node(item) for item in node]
            else:
                return node

        return resolve_node(schema)

    def schema_list_to_json(self, schema_list: list) -> dict:
        """
        Converts a list of JSON schemas to a dictionary where each key is the schema id
        with '.yaml' appended, and the value is the schema content.

        Parameters:
        - schema_list (list): A list of JSON schemas.

        Returns:
        - dict: A dictionary with schema ids as keys and schema contents as values.
        """
        schema_dict = {}
        for schema in schema_list:
            schema_id = schema.get("id")
            if schema_id:
                schema_dict[f"{schema_id}.yaml"] = schema
        return schema_dict

    def resolve_all_references(self) -> list:
        """
        Resolves references in all other schema dictionaries using the resolved definitions schema.

        Returns:
        - list: A list of resolved schema dictionaries.
        """

        print("=== Resolving Schema References ===")

        resolved_schema_list = []
        for node in self.nodes:
            if node == "_definitions.yaml" or node == "_terms.yaml":
                continue

            try:
                resolved_schema = self.resolve_references(
                    self.schema[node], self.schema_def_resolved
                )
                resolved_schema_list.append(resolved_schema)
                print(f"Resolved {node}")
            except KeyError as e:
                print(f"Error resolving {node}: Missing key {e}")
            except Exception as e:
                print(f"Error resolving {node}: {e}")

        return resolved_schema_list

    def return_resolved_schema(self, target_id: str) -> dict:
        """
        Retrieves the first dictionary from a list where the 'id' key matches the target_id.

        Parameters:
        - target_id (str): The value of the 'id' key to match.

        Returns:
        - dict: The dictionary that matches the target_id, or None if not found.
        """
        if target_id.endswith(".yaml"):
            target_id = target_id[:-5]

        result = next(
            (item for item in self.schema_list_resolved if item.get("id") == target_id),
            None,
        )
        if result is None:
            print(f"{target_id} not found")
        return result
