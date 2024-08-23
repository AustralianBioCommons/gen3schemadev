import json
from jsonschema import ValidationError, Draft4Validator, exceptions
import jsonschema
import os
import shutil
import matplotlib.pyplot as plt
import pandas as pd

class SchemaResolver:
    def __init__(self, base_path: str, bundle_json_path: str):
        """
        Initializes the SchemaValidator with a base path and bundle JSON path.

        Args:
        - base_path (str): The base directory path where JSON schemas are located.
        - bundle_json_path (str): The path to the bundle JSON file.
        """
        self.base_path = base_path
        self.bundle_json_path = bundle_json_path

    def split_bundle_json(self, write_dir: str, return_dict: bool = False):
        """
        Split the bundle JSON file into individual JSON files and save them in the specified directory.

        Args:
            write_dir (str): The directory path where the individual JSON files will be saved.
            return_dict (bool, optional): Whether to return the dictionary of individual JSON files. Defaults to False.

        Returns:
            dict or None: If return_dict is True, returns a dictionary containing the individual JSON files.
                Otherwise, returns None.
        """
        # opening bundle json
        with open(self.bundle_json_path, 'r') as f:
            bundle_json = json.load(f)
        bundle_json_keys = list(bundle_json.keys())
        
        # saving individual jsons
        out_jsons = {}
        for bundle_key in bundle_json_keys:
            print(f'writing {bundle_key} to json')
            key_name = bundle_key.replace('.yaml', '.json')
            out_jsons[key_name] = bundle_json[bundle_key]
        
        # writing individual jsons
        for keys in out_jsons.keys():
            out_json_path = os.path.join(write_dir, keys)
            with open(out_json_path, 'w') as f:
                json.dump(out_jsons[keys], f)
            print(f'{out_json_path} successfully saved')
        
        if return_dict:
            return out_jsons

    def read_json(self, json_fn: str):
        json_path = os.path.join(self.base_path, json_fn)
        with open(json_path, 'r') as f:
            schema = json.load(f)
        print(f'{json_path} successfully loaded')
        return schema

    def write_json(self, json_fn: str, schema: dict):
        json_path = os.path.join(self.base_path, json_fn)
        with open(json_path, 'w') as f:
            json.dump(schema, f, indent=4)
        print(f'{json_path} successfully saved')

    def resolve_references(self, schema, ref_fn: str):
        """
        Recursively resolves references in a JSON node.

        This function takes a JSON node as input and recursively resolves any references found in the node.
        If the node is a dictionary and contains a key '$ref', the function splits the value of '$ref' into
        two parts: the reference file path and the reference key. It then opens the reference file (if it exists)
        and loads its content. The function then traverses the reference key to find the corresponding content
        in the reference file. The resolved content is then merged with the current node, excluding the '$ref' key.

        If the node is a list, the function recursively resolves each item in the list.

        If the node is neither a dictionary nor a list, the function returns the node as is.

        Parameters:
        - schema (dict): The JSON node to resolve references in.

        Returns:
        - dict: The resolved JSON node with references resolved.
        """
        # loading reference file 
        if ref_fn:
            try:
                ref_file_path = os.path.join(self.base_path, ref_fn)
                with open(ref_file_path, 'r') as f:
                    ref_input_content = json.load(f)
                    print(f'Reference file: {ref_file_path} successfully loaded')
            except FileNotFoundError:
                print(f'Reference file: {ref_file_path} not found')
                ref_input_content = {}


        def resolve_node(node, manual_ref_content=ref_input_content):
            if isinstance(node, dict):
                if '$ref' in node:
                    ref_path = node['$ref']
                    ref_file, ref_key = ref_path.split('#')
                    ref_file = ref_file.strip()
                    ref_key = ref_key.strip('/')
                    # print(f'Resolving $ref: {ref_file}#{ref_key}')
                
                    # if a reference file is in the reference, load the pre-defined reference, if no file exists, then use the schema itself as reference
                    if ref_file:
                        ref_content = manual_ref_content
                    else:
                        ref_content = schema
                    
                    
                    for part in ref_key.split('/'):
                        ref_content = ref_content[part]

                    resolved_content = resolve_node(ref_content)
                    # Merge resolved content with the current node, excluding the $ref key
                    return {**resolved_content, **{k: resolve_node(v) for k, v in node.items() if k != '$ref'}}
                else:
                    return {k: resolve_node(v) for k, v in node.items()}
            elif isinstance(node, list):
                return [resolve_node(item) for item in node]
            else:
                return node

        return resolve_node(schema)

    def redefine_ref_path(self, match_str: str, replace_str: str, schema: dict):
        """
        Recursively replaces $ref paths in a JSON schema.

        Args:
        - match_str (str): The string to match in the $ref path.
        - replace_str (str): The string to replace the match_str with.
        - schema (dict): The JSON schema to modify.

        Returns:
        - dict: The modified JSON schema with updated $ref paths.
        """
        def replace_refs(node):
            if isinstance(node, dict):
                if '$ref' in node and match_str in node['$ref']:
                    node['$ref'] = node['$ref'].replace(match_str, replace_str)
                return {k: replace_refs(v) for k, v in node.items()}
            elif isinstance(node, list):
                return [replace_refs(item) for item in node]
            else:
                return node

        return replace_refs(schema)

    def resolve_refs(self, schema_fn, reference_fn: str):
        """
        Resolves references in a JSON schema file using definitions from another JSON file.

        Args:
        - schema_fn (str): The name of the schema JSON file to resolve.
        - ref_fn (str): The name of the JSON file with the reference definitions.

        Returns:
        - dict: The resolved JSON schema.
        """
        # Read JSON files
        schema_obj = self.read_json(schema_fn)

        # Redefine $ref paths in schema_obj if necessary
        if '_definitions.json' in schema_fn:
            schema_obj = self.redefine_ref_path('_terms.yaml', '_terms.json', schema_obj)
            # print("$ref paths redefined: '_terms.yaml' to '_terms.json'")
        else:
            schema_obj = self.redefine_ref_path('_definitions.yaml', '_definitions_[resolved].json', schema_obj)
            # print("$ref paths redefined: '_definitions.yaml' to '_definitions_[resolved].json'")
            schema_obj = self.redefine_ref_path('.yaml', '.json', schema_obj)
            # print("$ref paths redefined: '.yaml' to '.json'")


        # Resolve references
        resolved_schema = self.resolve_references(schema_obj, ref_fn=reference_fn)
        
        # Write resolved schema
        resolved_schema_file = schema_fn.replace('.json', '_[resolved].json')
        self.write_json(resolved_schema_file, resolved_schema)

        if resolved_schema is not None:
            return print(f'=== {schema_fn} successfully resolved ===')
        else:
            return print(f'=== {schema_fn} failed to resolve ===')

    def move_resolved_schemas(self, target_dir: str):
        """
        Moves resolved schemas to a new directory.

        Args:
        - target_dir (str): The target directory where the resolved schemas should be moved.
        """
        os.makedirs(target_dir, exist_ok=True)
        ref_files = [f for f in os.listdir(self.base_path) if '[resolved].json' in f]
        for f in ref_files:
            shutil.move(os.path.join(self.base_path, f), os.path.join(target_dir, f))
            
    

class SchemaValidator:
    def __init__(self, data: list, schema_fn: str):
        self.data = data
        self.schema_fn = schema_fn
        self.schema = self.read_schema()
        self.results = self.validate_schema()
        self.errors = self.results['error_messages']
     
    def read_schema(self):
        with open(self.schema_fn, 'r') as f:
            schema = json.load(f)
        print(f'{self.schema_fn} successfully loaded')
        return schema
    
    def validate_schema(self):
        """
        Validates a JSON schema against a data dictionary.

        Args:
        - schema_fn (str): The relative path of the [resolved] JSON schema file.
        - data (dict): The data dictionary to validate against the schema.

        Returns:
        - dict: A results object containing the number of successful and failed validations, and error messages for failed objects.
        """
        # Create a validator with the resolver
        validator = Draft4Validator(self.schema)
        
        # Initialize counters and error storage
        success_count = 0
        fail_count = 0
        error_messages = {}

        # Function to validate per object
        def validate_object(obj, idx):
            try:
                validator.validate(obj)
                print("=== SUCCESS ===")
                return True
            except jsonschema.exceptions.ValidationError as e:
                error_messages[idx] = {
                    "Invalid key": list(e.path),
                    "Schema path": list(e.schema_path),
                    "Validator": e.validator,
                    "Validator value": e.validator_value,
                    "Validation error": e.message
                }
                print(f"Invalid key: {list(e.path)}")
                print(f"Schema path: {list(e.schema_path)}")
                print(f"Validator: {e.validator}")
                print(f"Validator value: {e.validator_value}")
                print(f"Validation error: {e.message}")
                print('=== FAIL ===')
                return False
        
        try:
            total = len(self.data)
            for idx, item in enumerate(self.data, start=1):
                print(f"=== Validating item {idx} of {total} ===")
                if validate_object(item, idx):
                    success_count += 1
                else:
                    fail_count += 1
        except Exception as e:
            print(f"An error occurred during validation: {e}")

        return {
            "total_count": total,
            "success_count": success_count,
            "fail_count": fail_count,
            "error_messages": error_messages
        }

    def print_errors(self):
        """
        Print the error messages from the validation results.

        This function takes no parameters.

        Returns:
            None
        """
        return print(json.dumps(self.results['error_messages'], indent=4))
    
    def return_errors(self):
        """
        Print the error messages from the validation results.

        This function takes no parameters.

        Returns:
            None
        """
        return json.dumps(self.results['error_messages'], indent=4)
    
    def print_summary(self):
        """
        Print the summary of the validation results.

        This function prints the total number of data objects, the number of successful validations, and the number of failed validations.

        Parameters:
            self (object): The instance of the class.

        Returns:
            None
        """
        validation_results = self.results
        print("\n=== VALIDATION RESULTS ===\nTotal number of data objects:", validation_results["total_count"])
        print("Number of successful validations:", validation_results["success_count"])
        print("Number of failed validations:", validation_results["fail_count"])


    def plot_invalid_keys(self):
        """
        Plot the frequency of invalid keys from the validation results.

        This function extracts the "Invalid key" values from the validation results and creates a DataFrame.
        It then counts the occurrences of each invalid key and plots a bar graph to visualize the frequency.

        Parameters:
            self (object): The instance of the class.

        Returns:
            None

        Raises:
            None
        """
        invalid_keys = []
        for idx, error in self.errors.items():
            invalid_keys.extend(error.get("Invalid key", []))
        
        # Creating a DataFrame for the invalid keys
        df = pd.DataFrame(invalid_keys, columns=["Invalid Key"])
        
        # Counting occurrences of each invalid key
        key_counts = df["Invalid Key"].value_counts()
        
        # Plotting the bar graph
        plt.figure(figsize=(10, 6))
        key_counts.plot(kind='bar')
        plt.title('Frequency of Invalid Keys')
        plt.xlabel('Invalid Key')
        plt.ylabel('Frequency')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
        
        
class ValidationReporter:
    # this will provide functions and methods to report validation results
    print("hello world")