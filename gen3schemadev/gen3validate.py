import json
from jsonschema import ValidationError, Draft4Validator, exceptions
import os
import shutil
import matplotlib.pyplot as plt
import pandas as pd
import jsonschema
import numpy as np
import time
from datetime import datetime
from functools import wraps


def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        print(f"Starting '{func.__name__}' at {datetime.fromtimestamp(start_time)}")
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        print(f"'{func.__name__}' took {elapsed_time:.2f} seconds")
        if hasattr(args[0], 'timing_info'):
            args[0].timing_info[func.__name__] = elapsed_time
        return result
    return wrapper

class SchemaResolver:
    def __init__(self, bundle_json_path: str, unresolved_dir: str, resolved_output_dir: str, definitions_fn: str, terms_fn: str):
        """
        Initializes the SchemaValidator with a bundle JSON path and other required paths.

        Args:
        - bundle_json_path (str): The path to the bundle JSON file.
        - unresolved_dir (str): Bundled json will be split into this folder
        - resolved_output_dir (str): Directory where the resolved schemas will be moved.
        - definitions_fn (str): The filename of the definitions JSON file.
        - terms_fn (str): The filename of the terms JSON file.
        """
        self.bundle_json_path = bundle_json_path
        self.unresolved_dir = unresolved_dir
        self.resolved_output_dir = resolved_output_dir
        self.definitions_fn = definitions_fn
        self.terms_fn = terms_fn

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
        
        # Check if the write directory exists
        if os.path.exists(write_dir):
            # If it exists, delete the directory and its contents
            shutil.rmtree(write_dir)
            print(f'{write_dir} already exists. Deleting the directory and its contents.')

        # Create the write directory
        os.makedirs(write_dir)
        print(f'{write_dir} created successfully.')
        
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

    def read_json(self, json_path: str):
        try:
            with open(json_path, 'r') as f:
                schema = json.load(f)
            return schema
        except FileNotFoundError:
            print(f"Error: The file {json_path} was not found.")
        except json.JSONDecodeError:
            print(f"Error: The file {json_path} is not a valid JSON file.")
        except Exception as e:
            print(f"An unexpected error occurred while reading {json_path}: {e}")
        return None
    
    def write_json(self, json_path: str, schema: dict):
        with open(json_path, 'w') as f:
            json.dump(schema, f, indent=4)
        print(f'{json_path} successfully saved')

    def resolve_references(self, schema, ref_path: str):
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
        if ref_path:
            try:
                with open(ref_path, 'r') as f:
                    ref_input_content = json.load(f)
                    print(f'Reference file: {ref_path} successfully loaded')
            except FileNotFoundError:
                print(f'Reference file: {ref_path} not found')
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

    def resolve_refs(self, schema_path: str, reference_path: str):
        """
        Resolves references in a JSON schema file using definitions from another JSON file.

        Args:
        - schema_path (str): The path of the schema JSON file to resolve.
        - reference_path (str): The path of the JSON file with the reference definitions.

        Returns:
        - dict: The resolved JSON schema.
        """
        # Read JSON files
        schema_obj = self.read_json(schema_path)

        # Redefine $ref paths in schema_obj if necessary
        if '_definitions.json' in schema_path:
            schema_obj = self.redefine_ref_path('_terms.yaml', '_terms.json', schema_obj)
            # print("$ref paths redefined: '_terms.yaml' to '_terms.json'")
        else:
            schema_obj = self.redefine_ref_path('_definitions.yaml', '_definitions_[resolved].json', schema_obj)
            # print("$ref paths redefined: '_definitions.yaml' to '_definitions_[resolved].json'")
            schema_obj = self.redefine_ref_path('.yaml', '.json', schema_obj)
            # print("$ref paths redefined: '.yaml' to '.json'")


        # Resolve references
        resolved_schema = self.resolve_references(schema_obj, ref_path=reference_path)
        
        # Write resolved schema
        resolved_schema_file = schema_path.replace('.json', '_[resolved].json')
        self.write_json(resolved_schema_file, resolved_schema)

        if resolved_schema is not None:
            return print(f'=== {schema_path} successfully resolved ===')
        else:
            return print(f'=== {schema_path} failed to resolve ===')

    def move_resolved_schemas(self, source_dir: str, target_dir: str):
        """
        Moves resolved schemas to a new directory.

        Args:
        - source_dir (str): The directory where the resolved schemas are currently located.
        - target_dir (str): The target directory where the resolved schemas should be moved.
        """
        os.makedirs(target_dir, exist_ok=True)
        ref_files = [f for f in os.listdir(source_dir) if '[resolved].json' in f]
        for f in ref_files:
            shutil.move(os.path.join(source_dir, f), os.path.join(target_dir, f))

    def resolve_schemas(self):
        """
        Split the bundled JSON and write as individual json nodes. It then resolves references in the definition file first,
        then uses this resolved definition file to resolve all the other schemas.

        Returns:
            None
        """
        try:
            if os.path.exists(self.unresolved_dir):
                print(f"Schema directory {self.unresolved_dir} exists. Removing it.")
                shutil.rmtree(self.unresolved_dir, ignore_errors=True)
            else:
                print(f"Schema directory {self.unresolved_dir} does not exist. Creating it.")
            os.makedirs(self.unresolved_dir, exist_ok=True)
            print(f"Schema directory {self.unresolved_dir} created.")

            print("Splitting bundle JSON into individual JSON files.")
            self.split_bundle_json(write_dir=self.unresolved_dir)
            definitions_path = os.path.join(self.unresolved_dir, self.definitions_fn)
            terms_path = os.path.join(self.unresolved_dir, self.terms_fn)
            print(f"Resolving references in '{definitions_path}' using '{terms_path}'.")
            self.resolve_refs(definitions_path, reference_path=terms_path)

            json_files = [fn for fn in os.listdir(self.unresolved_dir) if not fn.startswith('_')]
            ref_file = definitions_path.replace('.json', '_[resolved].json')
            print(f"Found JSON files to resolve: {json_files}")
            for fn in json_files:
                full_path = os.path.join(self.unresolved_dir, fn)
                print(f"Resolving references in {full_path} using {ref_file}.")
                self.resolve_refs(full_path, ref_file)

            os.makedirs(self.resolved_output_dir, exist_ok=True)
            print(f"Resolved output directory: {self.resolved_output_dir}")
            self.move_resolved_schemas(self.unresolved_dir, self.resolved_output_dir)
            print("Resolved schemas moved successfully.")
        except Exception as e:
            print(f"An error occurred: {e}")
    
    def combine_resolved_schemas(self, resolved_dir, output_dir, output_filename='schema_dev_resolved.json'):
        """
        Combine all resolved JSON schemas into a single bundled JSON file.

        Parameters:
            resolved_dir (str): Directory where the resolved schemas are stored.
            output_file (str): Path to the output bundled JSON file.
            output_filename (str): Name of the output bundled JSON file. Defaults to 'schema_dev_resolved.json'.

        Returns:
            None
        """
        bundled_schema = {}
        
        # Iterate over all JSON files in the resolved directory
        for filename in os.listdir(resolved_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(resolved_dir, filename)
                with open(file_path, 'r') as f:
                    schema = json.load(f)
                    # Merge the schema into the bundled_schema object
                    for key, value in schema.items():
                        if key in bundled_schema:
                            if isinstance(bundled_schema[key], dict) and isinstance(value, dict):
                                for sub_key, sub_value in value.items():
                                    if sub_key not in bundled_schema[key]:
                                        bundled_schema[key][sub_key] = sub_value
                            elif isinstance(bundled_schema[key], list) and isinstance(value, list):
                                bundled_schema[key].extend(value)
                            else:
                                # If there are multiple different values for the same key, pick the first key-value pair
                                continue
                        else:
                            bundled_schema[key] = value
        
        # Write the bundled schema to the output file in the output directory
        output_file_path = os.path.join(output_dir, output_filename)
        with open(output_file_path, 'w') as f:
            json.dump(bundled_schema, f, indent=4)
        print(f'Bundled schema successfully saved to {output_file_path}')


class SchemaValidatorSynth:
    """
    Initializes the SchemaValidatorSynth with a list of data objects and a schema filename.

    Args:
    - schema_fn (str): The filename of the JSON schema to validate against.
    - data (list): The list of data objects to validate.
    """
    def __init__(self, schema_fn: str, data: list):
        self.schema_fn = schema_fn
        self.data = data
        self.schema = self.read_schema()
        self.results = self.validate_schema()
        self.errors = self.results['error_messages']
     
    
    def read_schema(self):
        try:
            with open(self.schema_fn, 'r') as f:
                schema = json.load(f)
            # print(f'{self.schema_fn} successfully loaded')
            return schema
        except FileNotFoundError:
            print(f"Error: The file {self.schema_fn} was not found.")
        except json.JSONDecodeError:
            print(f"Error: The file {self.schema_fn} is not a valid JSON file.")
        except Exception as e:
            print(f"An unexpected error occurred while reading {self.schema_fn}: {e}")
        return None
    
    def validate_schema(self):
        """
        Validates a JSON schema against a data dictionary.

        Returns:
        - dict: A results object containing the number of successful and failed validations, error messages for failed objects, and log messages.
        """
        # Create a validator with the resolver
        validator = jsonschema.Draft4Validator(self.schema)
        
        # Initialize counters and error storage
        success_count = 0
        fail_count = 0
        error_messages = {}
        log_messages = []

        # Function to validate per object
        def validate_object(obj, idx):
            try:
                validator.validate(obj)
                log_messages.append("=== SUCCESS ===")
                return True
            except jsonschema.exceptions.ValidationError as e:
                error_messages[idx] = {
                    "Invalid key": list(e.path),
                    "Schema path": list(e.schema_path),
                    "Validator": e.validator,
                    "Validator value": e.validator_value,
                    "Validation error": e.message
                }
                log_messages.append(f"Invalid key: {list(e.path)}")
                log_messages.append(f"Schema path: {list(e.schema_path)}")
                log_messages.append(f"Validator: {e.validator}")
                log_messages.append(f"Validator value: {e.validator_value}")
                log_messages.append(f"Validation error: {e.message}")
                log_messages.append('=== FAIL ===')
                return False
        
        try:
            total = len(self.data)
            for idx, item in enumerate(self.data, start=1):
                log_messages.append(f"=== Validating item {idx} of {total} ===")
                if validate_object(item, idx):
                    success_count += 1
                else:
                    fail_count += 1
            return {
                "total_count": total,
                "success_count": success_count,
                "fail_count": fail_count,
                "error_messages": error_messages,
                "log_messages": log_messages
            }
        except Exception as e:
            log_messages.append(f"An error occurred during validation: {e}")
            return {
                "total_count": 0,
                "success_count": 0,
                "fail_count": 0,
                "error_messages": error_messages,
                "log_messages": log_messages
            }
        


    def print_errors(self):
        """
        Print the error messages from the validation results.

        This function takes no parameters.

        Returns:
            None
        """
        print(json.dumps(self.results['error_messages'], indent=4))
    
    def return_errors(self):
        """
        Print the error messages from the validation results.

        This function takes no parameters.

        Returns:
            str: A JSON string of the error messages.
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
        
class QuickValidateSynth:
    def __init__(self, data_dir: str, project_name_list: list, resolved_schema_dir: str, exclude_nodes: list = None):
        self.data_dir = data_dir
        self.project_name_list = project_name_list
        self.resolved_schema_dir = resolved_schema_dir
        self.exclude_nodes = exclude_nodes if exclude_nodes is not None else []
        self.json_paths = []
        self.nodes = []
        self.errors = {}

    def generate_json_paths(self, project_name: str) -> list:
        """
        Generates a list of JSON paths based on the inputs: data_dir, project_name, and node.

        Returns:
        - list: A list of JSON file paths.
        """
        try:
            import os
            json_paths = [
                os.path.join(self.data_dir, project_name, file)
                for file in os.listdir(os.path.join(self.data_dir, project_name))
                if file.endswith('.json')
            ]
            filtered_json_paths = [path for path in json_paths if not any(exclude_node in path for exclude_node in self.exclude_nodes)]            # print(f'Generated JSON paths: {filtered_json_paths}')
            return filtered_json_paths
        except Exception as e:
            print(f"An error occurred while generating JSON paths: {e}")
            return []

    def read_single_json(self, json_path: str) -> list:
        """
        Reads a single JSON file from the given absolute path and returns it as a list of data objects.

        Args:
        - json_path (str): The absolute path to the JSON file.

        Returns:
        - list: A list of data objects contained in the JSON file.
        """
        try:
            with open(json_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"An error occurred while reading JSON file {json_path}: {e}")
            return []

    def extract_node_names(self, json_paths: list) -> list:
        """
        Extracts node names from the given list of JSON file paths using regex.

        Args:
        - json_paths (list): A list of JSON file paths.

        Returns:
        - list: A list of node names extracted from the JSON file paths.
        """
        import re

        node_names = []
        for path in json_paths:
            try:
                pattern = re.compile(r'{}/(.*)\.json'.format(re.escape(self.data_dir)))
                match = pattern.search(path)
                if match:
                    node_names.append(match.group(1))
                else:
                    print(f"No node name found in {path}")
            except Exception as e:
                print(f"An error occurred while processing {path}: {e}")
        return node_names
    
    def extract_node_name(self, json_path: str) -> str:
        """
        Extract the filename without extension from a given file path.

        Args:
            file_path (str): The file path to process.

        Returns:
            str: The filename without the extension.
        """
        # Split the path by '/'
        parts = json_path.split('/')
        # Take the last part and remove the '.json' extension
        fn_rm_ext = parts[-1].replace('.json', '')
        return fn_rm_ext

    def get_schema_fn(self, node_name: str) -> str:
        return f'{self.resolved_schema_dir}/{node_name}_[resolved].json'
    
    def quick_validate(self):
        for project in self.project_name_list:
            json_paths = self.generate_json_paths(project)
            for jsn in json_paths:
                node = self.extract_node_name(jsn)
                schema_fn = self.get_schema_fn(node)
                data = self.read_single_json(jsn)
                validator = SchemaValidatorSynth(schema_fn, data)
                errors = validator.return_errors()
                errors_dict = json.loads(errors)
                self.errors[(project, node)] = errors_dict
                
                if not errors_dict:
                    print(f'=== {project}/{node} is valid ===')
                else:
                    print(f'=== {project}/{node} contains errors ===')
    
class SyntheticDataCombiner:
    def __init__(self, input_dir, exclude_files=None):
        """
        Initialize the SyntheticDataCombiner with the input directory and optional exclude files.

        Args:
            input_dir (str): The directory containing the JSON files to read.
            exclude_files (list, optional): List of filenames to exclude. Defaults to ['project.json', 'program.json'].
        """
        self.input_dir = input_dir
        self.exclude_files = exclude_files if exclude_files is not None else ['project.json', 'program.json']
        self.df_list = self.json_files_to_dataframes()
        self.combined_df = self.bind_dataframes_by_column(self.df_list)

    def json_files_to_dataframes(self):
        """
        Read JSON files from a directory, convert them to pandas DataFrames, and store the DataFrames in a list.

        Returns:
            list: A list of pandas DataFrames.
        """
        dataframes = []
        files = [file for file in os.listdir(self.input_dir) if file.endswith('.json') and file not in self.exclude_files]

        def read_json_file(file_path):
            with open(file_path, 'r') as f:
                try:
                    data = json.load(f)
                    if not isinstance(data, list):
                        raise ValueError(f"Expected a list of objects in the JSON file {file_path}")
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Error reading JSON from file {file_path}: {e}")
                    return None
            return data

        for file in files:
            data = read_json_file(os.path.join(self.input_dir, file))
            if data is not None:
                df = pd.json_normalize(data)
                dataframes.append(df)

        return dataframes

    def bind_dataframes_by_column(self, dataframes_list, remove_duplicates=False):
        """
        Bind a list of pandas DataFrames by columns.

        Args:
            dataframes_list (list): A list of pandas DataFrames.
            remove_duplicates (bool, optional): Whether to remove duplicate columns. Defaults to False.

        Returns:
            pd.DataFrame: A single DataFrame with all input DataFrames bound by columns.
        """
        combined_df = pd.concat(dataframes_list, axis=1)
        
        if remove_duplicates:
            combined_df = combined_df.loc[:, ~combined_df.columns.duplicated()]
        
        return combined_df

    def dataframe_to_json(self, output_file):
        """
        Convert the combined DataFrame to a JSON file with each row as an object in an array.

        Args:
            output_file (str): The path to the output JSON file.

        Returns:
            None
        """
        try:
            # Extract basename and basedir
            base_name = os.path.basename(output_file)
            base_dir = os.path.dirname(output_file)
            
            # Create basedir if it does not exist
            if not os.path.exists(base_dir):
                os.makedirs(base_dir)
            
            data = self.combined_df.to_dict(orient='records')
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"DataFrame successfully written to {output_file}")
        except Exception as e:
            print(f"Error writing DataFrame to JSON: {e}")


class SchemaValidatorDataFrame:
    def __init__(self, data: list, schema_fn: str):
        self.data = data
        self.schema_fn = schema_fn
        self.schema = self.read_schema()
        self.results, self.metrics = self.validate_schema()
        self.errors = self.results[self.results['Validation Result'] == 'FAIL']
     
    @timeit
    def read_schema(self):
        with open(self.schema_fn, 'r') as f:
            schema = json.load(f)
        print(f'{self.schema_fn} successfully loaded')
        return schema
    @timeit
    def validate_schema(self):
        """
        Validates a JSON schema against a data dictionary.

        Args:
        - schema_fn (str): The relative path of the [resolved] JSON schema file.
        - data (dict): The data dictionary to validate against the schema.

        Returns:
        - list: A list containing two DataFrames, one for validation results and one for metrics.
        """
        # Create a validator with the resolver
        validator = Draft4Validator(self.schema)
        
        # Initialize counters and error storage
        success_count = 0
        fail_count = 0
        validation_results = []
        log_messages = []

        # Function to validate per object
        @timeit
        def validate_object(obj, idx):
            errors = list(validator.iter_errors(obj))
            if not errors:
                validation_results.append({
                    "Index": idx,
                    "Validation Result": "SUCCESS",
                    "Invalid key": None,
                    "Schema path": None,
                    "Validator": None,
                    "Validator value": None,
                    "Validation error": None
                })
                log_messages.append("=== SUCCESS ===")
                return True
            else:
                for error in errors:
                    validation_results.append({
                        "Index": idx,
                        "Validation Result": "FAIL",
                        "Invalid key": list(error.path),
                        "Schema path": list(error.schema_path),
                        "Validator": error.validator,
                        "Validator value": error.validator_value,
                        "Validation error": error.message
                    })
                    log_messages.append(f"Invalid key: {list(error.path)}")
                    log_messages.append(f"Schema path: {list(error.schema_path)}")
                    log_messages.append(f"Validator: {error.validator}")
                    log_messages.append(f"Validator value: {error.validator_value}")
                    log_messages.append(f"Validation error: {error.message}")
                    log_messages.append('=== FAIL ===')
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
            log_messages.append(f"An error occurred during validation: {e}")

        results_df = pd.DataFrame(validation_results)
        metrics_df = pd.DataFrame([{
            "total_count": total,
            "success_count": success_count,
            "fail_count": fail_count,
            "validation_results": validation_results,
            "log_messages": log_messages
        }])

        return [results_df, metrics_df]

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
    """
    A class to report validation results from a CSV file against a schema.

    This class reads data from a CSV file, validates it against a given schema,
    and transforms the validation results into a specific format for reporting.

    Attributes:
        csv_path (str): The path to the CSV file.
        schema_path (str): The path to the schema file.
        nrows (int): The number of rows to read from the CSV file.
        dataframe (pd.DataFrame): The DataFrame to be converted to JSON format.
        data (list): The data read from the CSV file or DataFrame in JSON format.
        validator (SchemaValidatorDataFrame): The validator instance.
        validate_df (pd.DataFrame): The DataFrame containing validation errors. This is the full unfiltered DataFrame.
        output (pd.DataFrame): The transformed DataFrame for reporting.
    """
    def __init__(self, schema_path, csv_path=None, dataframe=None, n_rows=None):
        if dataframe is None and csv_path is None:
            raise ValueError("Either 'csv_path' or 'dataframe' must be provided.")
        
        self.csv_path = csv_path
        self.schema_path = schema_path
        self.nrows = n_rows
        if dataframe is not None:
            self.dataframe = self.read_n_rows(dataframe, self.nrows)
            self.data = self.dataframe_to_json()
        else:
            self.data = self.csv_to_json()
        self.validator = SchemaValidatorDataFrame(self.data, self.schema_path)
        self.validate_df = self.validator.errors  # access
        self.output = self.transform_validate_df()
    
    def read_n_rows(self, df, n):
        filt_df = df.head(n)
        return filt_df
    
    @timeit
    def csv_to_json(self):
        df = pd.read_csv(self.csv_path, nrows=self.nrows if self.nrows else None)
        json_data = df.to_dict(orient="records")
        return json_data
    
    @timeit
    def dataframe_to_json(self):
        json_data = self.dataframe.to_dict(orient="records")
        return json_data
    
    @timeit
    def transform_validate_df(self):
        required_columns = ['Index', 'Validation Result', 'Invalid key', 'Schema path', 'Validator', 'Validator value', 'Validation error']
        
        # Check if all required columns exist in the dataframe
        if not all(column in self.validate_df.columns for column in required_columns):
            raise ValueError(f"The dataframe is missing one or more required columns: {required_columns}")
        
                # Check if 'Invalid key' exists in the dataframe
        if 'Invalid key' not in self.validate_df.columns:
            raise ValueError("Invalid key not found: Make sure a bundled resolved schema has been created")
        
        def get_text_before_is_not(input_string):
            # Find the index of the substring " is not " or " does not "
            index_is_not = input_string.find(" is not ")
            index_does_not = input_string.find(" does not ")
            
            # Determine the correct index to use
            index = index_is_not if index_is_not != -1 else index_does_not
            
            # If the substring is found, return the part before it
            if index != -1:
                return input_string[:index]
            
            # If the substring is not found, return the original string
            return input_string
        
        try:
            # Filtering the validation results df
            filtered_df = self.validate_df[self.validate_df['Invalid key'].apply(lambda x: len(x) != 0)] 
            filtered_df = filtered_df.copy()
            filtered_df['key_error_filter'] = filtered_df['Invalid key'].astype(str) + " " + filtered_df['Validation error'].astype(str)
            filtered_df['input_value'] = filtered_df['Validation error'].apply(lambda x: get_text_before_is_not(x))
            filtered_df = filtered_df.rename(columns={'Index': 'Row'})
            columns_to_drop = ['Validation Result', 'Schema path', 'Validator', 'key_error_filter']
            filtered_df = filtered_df.drop(columns=columns_to_drop)
            filtered_df['unresolvable'] = np.nan
        except KeyError as e:
            raise KeyError(f"KeyError encountered: {e} does not exist | make sure a bundled resolved schema is used, to create run the resolve_schemas() method then combine_resolved_schemas() method all from the gen3schemadev.gen3validate.SchemaResolver class")

        # Convert 'Invalid key' to string for sorting
        filtered_df['Invalid key'] = filtered_df['Invalid key'].astype(str)
        filtered_df = filtered_df.sort_values(by=['Invalid key', 'Row'], na_position='last')
        # Reorder the columns as specified
        filtered_df = filtered_df[['Row', 'Invalid key', 'input_value', 'Validator value', 'Validation error', 'unresolvable']]
        # Rename the columns to match the specified names
        filtered_df.columns = ['row', 'invalid_key', 'input_value', 'validator_value', 'validation_error', 'unresolvable']
        # incrementing row by 1 for better readability
        filtered_df['row'] = filtered_df['row'] + 1

        return filtered_df
    
    
    @timeit
    def write_df(self, output_dir, project_id):
        # Check if the output directory exists, if not, create it
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"{output_dir} created successfully.")
        
        # Construct the full path using output_dir, current date, project_id, and schema_validation_df.csv
        current_date = pd.Timestamp.now().strftime('%Y-%m-%d')
        file_name = f"{current_date}_{project_id}_schema_validation_df.csv"
        full_path = os.path.join(output_dir, file_name)
        
        # Write the DataFrame to the constructed path
        self.output.to_csv(full_path, index=False)
        print(f"DataFrame successfully written to {full_path}")