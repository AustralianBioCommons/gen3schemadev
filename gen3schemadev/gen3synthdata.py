import os
import shutil
import json
import yaml
import pandas as pd
import random
from datetime import datetime, timedelta, timezone


class gen3SynthFiles:
    """
    A class to handle synthetic file operations for Gen3 projects.

    Attributes:
        json_data_path (str): Path to the JSON data directory.
        project_id_list (list): List of project IDs to process.
        templates_path (str): Path to the templates directory.
        output_dir (str): Directory where output files will be stored.
        all_metadata_paths (list): List of all metadata file paths.
        metadata_file_list (list): List of metadata files.
        data_list (list): List of data objects parsed from JSON files.
        synthetic_file_index (dict): Index of synthetic files.
    """

    def __init__(self, json_data_path, project_id_list, templates_path, output_dir):
        """
        Initializes the gen3SynthFiles class with paths and project information.

        :param json_data_path: Path to the JSON data directory.
        :param project_id_list: List of project IDs to process.
        :param templates_path: Path to the templates directory.
        :param output_dir: Directory where output files will be stored.
        """
        self.json_data_path = json_data_path
        self.project_id_list = project_id_list
        self.templates_path = templates_path
        self.output_dir = output_dir
        self.all_metadata_paths = self.list_all_metadata_paths()
        self.metadata_file_list = self.list_metadata_files()
        self.data_list = []
        self.synthetic_file_index = {}

        # Purging output dir
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        self.synthetic_file_index = self.read_synthetic_file_index()

    def parse_json_data(self, project_id):
        """
        Parses JSON data files for a given project ID and populates the data list.

        :param project_id: The project ID for which to parse JSON data.
        """
        print("Parsing JSON data from:", self.json_data_path)  # Debugging print
        for filename in os.listdir(f"{self.json_data_path}/{project_id}"):
            if filename.endswith('file.json'):
                print("Processing file:", filename)  # Debugging print
                with open(os.path.join(self.json_data_path, project_id, filename), 'r') as f:
                    self.data_list.extend(json.load(f))
        print("Completed parsing JSON data.")  # Debugging print

    def read_json_file(self, file_path):
        """
        Reads a JSON file from the given file path and returns the data.

        :param file_path: Path to the JSON file.
        :return: Data contained in the JSON file.
        """
        print(f"Reading JSON file from: {file_path}")  # Debugging print
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            print("Completed reading JSON file.")  # Debugging print
            return data
        except FileNotFoundError:
            print(f"Error: The file {file_path} does not exist.")
        except json.JSONDecodeError as exc:
            print(f"Error parsing JSON file: {exc}")
        return None

    def write_json_file(self, data, file_path):
        """
        Writes the given data to a JSON file at the specified file path.

        :param data: Data to be written to the JSON file.
        :param file_path: Path where the JSON file will be written.
        """
        print(f"Writing JSON file to: {file_path}")  # Debugging print
        try:
            # Extract directory path from file_path
            dir_path = os.path.dirname(file_path)
            # Create directory if it does not exist
            os.makedirs(dir_path, exist_ok=True)

            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            print("Completed writing JSON file.")  # Debugging print
        except IOError as exc:
            print(f"Error writing JSON file: {exc}")

    def list_all_metadata_paths(self, print_list: bool = False):
        """
        Lists all metadata file paths for the projects.

        :param print_list: If True, prints the list of metadata paths.
        :return: List of all metadata file paths.
        """
        all_outputs = []

        for project_id in self.project_id_list:
            project_path = os.path.join(self.json_data_path, project_id)
            filenames = os.listdir(project_path)

            for filename in filenames:
                output = {project_id: filename}
                all_outputs.append(output)

        if print_list:
            for entry in self.metadata_file_list:
                print(entry)

        return all_outputs

    def list_metadata_files(self, print_list: bool = False):
        """
        Lists metadata files ending with 'file.json' for the projects.

        :param print_list: If True, prints the list of metadata files.
        :return: List of metadata files.
        """
        all_outputs = []

        for project_id in self.project_id_list:
            project_path = os.path.join(self.json_data_path, project_id)
            filenames = os.listdir(project_path)
            filtered_filenames = [
                filename for filename in filenames if filename.endswith('file.json')
            ]

            for filename in filtered_filenames:
                output = {project_id: filename}
                all_outputs.append(output)

        if print_list:
            for entry in self.metadata_file_list:
                print(entry)

        return all_outputs

    def read_synthetic_file_index(self):
        """
        Reads the synthetic file index from a YAML file.

        :return: Dictionary containing the synthetic file index.
        """
        index_file_path = os.path.join(self.templates_path, 'synthetic_file_index.yaml')
        print("Reading synthetic file index from:", index_file_path)  # Debugging print
        try:
            with open(index_file_path, 'r') as f:
                synthetic_file_index = yaml.safe_load(f)
            print("Completed reading synthetic file index.")  # Debugging print
        except FileNotFoundError:
            print(f"Error: The file {index_file_path} does not exist.")
        except yaml.YAMLError as exc:
            print(f"Error parsing YAML file: {exc}")
        return synthetic_file_index

    def find_dummy_file(self, data_format: str):
        """
        Finds a dummy file matching the given data format.

        :param data_format: The data format to match.
        :return: The filename of the matching dummy file.
        """
        matched_fn = None
        for synth_fn, synth_lookup in self.synthetic_file_index.items():
            if any(data_format in x for x in synth_lookup):
                return synth_fn
        if matched_fn is None:
            print(f'WARNING: "{data_format}" does not match any synthetic files')

    def copy_file(self, input_fn, rename_fn, project_id):
        """
        Copies a file from the templates directory to the output directory.

        :param input_fn: The input filename to copy.
        :param rename_fn: The new filename for the copied file.
        :param project_id: The project ID associated with the file.
        """
        src = os.path.join(self.templates_path, input_fn)
        dst = os.path.join(self.output_dir, project_id, rename_fn)

        if not os.path.exists(src):
            print(f"Error: The source file {src} does not exist.")
            return

        if not os.path.exists(os.path.join(self.output_dir, project_id)):
            os.makedirs(os.path.join(self.output_dir, project_id))

        print("Copying file from", src, "to", dst)  # Debugging print
        shutil.copy(src, dst)
        print("Completed copying file.")  # Debugging print

    def copy_dummy_files(self, preserve_dummy_names=False):
        """
        Copies dummy files for each project, optionally preserving dummy names.

        :param preserve_dummy_names: If True, preserves the original dummy file names.
        """
        for project_id in self.project_id_list:
            self.data_list = []
            self.parse_json_data(project_id)
            print(f"Total number of data objects: {len(self.data_list)}")

            for data_object in self.data_list:
                print(f"\nProcessing data object: {data_object}")  # Debugging print
                file_format = data_object['data_format']
                synth_file = self.find_dummy_file(file_format)

                if preserve_dummy_names:
                    file_name = synth_file
                else:
                    file_name = data_object['file_name']

                final_file_name = f'{file_name}.{file_format}'
                self.copy_file(synth_file, final_file_name, project_id)
                print(f"SUCCESS: Completed processing for file: {final_file_name}")  # Debugging print

    def copy_metadata_files(self):
        """
        Copies metadata files from the JSON data path to the output directory.
        """
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        for entry in self.all_metadata_paths:
            for project, filename in entry.items():
                print(f"Processing {project}: {filename}")  # Debugging print
                source_path = os.path.join(self.json_data_path, project, filename)
                dest_path = os.path.join(self.output_dir, project, filename)
                if not os.path.exists(source_path):
                    print(f"Error: The source file {source_path} does not exist.")
                    continue
                if not os.path.exists(os.path.dirname(dest_path)):
                    os.makedirs(os.path.dirname(dest_path))
                shutil.copy(source_path, dest_path)
                print(f"Copied {source_path} to {dest_path}")  # Debugging print

    def update_fn_metadata(self):
        """
        Updates the file name metadata in JSON files based on the synthetic file index.
        """
        for entry in self.metadata_file_list:
            for project, filename in entry.items():
                print(f"Processing {project}: {filename}")  # Debugging print
                metadata = self.read_json_file(os.path.join(self.json_data_path, project, filename))

                for data_object in metadata:
                    file_format = data_object['data_format']
                    synth_filename = self.find_dummy_file(file_format)
                    print(f"synth_filename: {synth_filename}")
                    synth_filename = synth_filename.split('.')[0]
                    print(f"updated synth_filename: {synth_filename}")
                    data_object['file_name'] = synth_filename

                self.write_json_file(metadata, os.path.join(self.output_dir, project, filename))
                

def gen_random_date_time_tz(num_dates: int, start_date="2008-01-01", end_date="2023-03-16"):
    """
    Generates a list of random ISO 8601 datetime strings between start_date and end_date, including timezone.

    Parameters:
    - start_date (str): The start date in ISO 8601 format (YYYY-MM-DD).
    - end_date (str): The end date in ISO 8601 format (YYYY-MM-DD).
    - num_dates (int): Number of random dates to generate.

    Returns:
    - list: A list of random ISO 8601 datetime strings between start_date and end_date, including timezone.
    """
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    
    random_dates = []
    for _ in range(num_dates):
        random_date = start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))
        # Randomly choose to add a timezone or UTC ('Z')
        if random.choice([True, False]):
            # Random timezone offset between -12:00 and +14:00 hours
            tz_offset_hours = random.randint(-12, 14)
            tz_offset_minutes = random.choice([0, 15, 30, 45]) * int(tz_offset_hours/abs(tz_offset_hours)) if tz_offset_hours != 0 else 0
            tz_info = timezone(timedelta(hours=tz_offset_hours, minutes=tz_offset_minutes))
            random_date = random_date.replace(tzinfo=tz_info)
        else:
            random_date = random_date.replace(tzinfo=timezone.utc)
        random_dates.append(random_date.isoformat())

    return random_dates


def gen_random_enums(enums: list, n: int):
    """
    Generates a list of n random enum values from the given list of enums.

    Parameters:
    - enums (list): A list of enum values to randomly select from.
    - n (int): The number of random enum values to generate.

    Returns:
    - list: A list of n random enum values from the given list of enums.
    """
    return [random.choice(enums) for _ in range(n)]


def update_json_key_values(base_path: str, json_filename: str, key: str, 
                           replacement: list = None, write_inplace: bool = True, 
                           enums: list = None, insert_date_time: bool = False):
    """
    Updates the date values for a specified key in a JSON file with randomly generated dates.

    Parameters:
    - base_path (str): The base directory path where the JSON file is located.
    - json_filename (str): The name of the JSON file to be updated.
    - key (str): The key in the JSON file whose values are to be updated with dates.
    - replacement (list): List of values

    This function reads the specified JSON file, updates the date values for the given key with
    randomly generated dates, and writes the updated data to a new file in an 'output' directory
    within the same base path.
    """

    # Construct the full path to the JSON file
    # print(f'base path = {base_path}')
    full_path = os.path.join(base_path, json_filename)

    # Reading the JSON file
    with open(full_path, 'r') as f:
        data = json.load(f)
        
    # Count number of entries in json data
    num_entries = len(data)
    date_list = gen_random_date_time_tz(num_entries)
    
    if insert_date_time:
        for i, entry in enumerate(data):
            data[i][key] = random.choice(date_list)
    elif enums is not None:
        for i, entry in enumerate(data):
            data[i][key] = random.choice(enums)
    else:
        # Updating the value of the specified key
        if len(data) == len(replacement):
            print('editing ' + str(key)) # Ensure there's a date for each entry
            for i, entry in enumerate(data):
                data[i][key] = replacement[i]
        elif len(data) < len(replacement):
            print('editing ' + str(key))
            for i, entry in enumerate(data):
                replacement_sub = replacement[0:len(data)]
                data[i][key] = replacement_sub[i]
        else:
            return print('not enough values in replacement list')


    # Constructing the path for the output file
    if write_inplace:
        output_dir = base_path
    elif write_inplace == False:
        output_dir = f"{base_path}/output"
        # print(f'writing in {output_dir}')
    else:
        raise ValueError("write_inplace must be True or False")
    
    os.makedirs(output_dir, exist_ok=True)  # Ensuring the output directory exists
    output_file = os.path.join(output_dir, os.path.basename(json_filename))

    # Writing the updated data to a new file in the 'output' directory
    print(f'writing edited json to {output_file}')
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=4)


def copy_data_import_order(programs, source_dir, dest_dir):
    for program in programs:
        src = os.path.join(source_dir, program, "DataImportOrder.txt")
        dest = os.path.join(dest_dir, program)
        print(f"Copying from {src} to {dest}")
        shutil.copy(src, dest)
        print(f"Successfully copied {src} to {dest}")


def copy_directory(src, dest):
    if os.path.exists(dest):
        confirm = input(f"Directory {dest} already exists. Do you want to overwrite all the files? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled by the user.")
            return
        shutil.rmtree(dest, ignore_errors=True)
        print(f"Directory {dest} was deleted")
    os.makedirs(dest, exist_ok=True)
    shutil.copytree(src, dest, dirs_exist_ok=True)
    print(f"Directory copied from {src} to {dest}")

class SchemaEnums:
    def __init__(self, enum_file_path, prop_file_path):
        """
        Initializes a SchemaEnums object.

        Parameters
        ----------
        enum_file_path : str
            The path to the enum CSV file.
        prop_file_path : str
            The path to the properties CSV file.
        """
        self.enum_file_path = enum_file_path
        self.prop_file_path = prop_file_path
        self.enum_csv = self.open_file(enum_file_path)
        self.prop_csv = self.open_file(prop_file_path)

    def open_file(self, file_path):
        """Opens a CSV file and returns it as a pandas DataFrame."""
        with open(file_path, 'r') as f:
            file = pd.read_csv(file_path, parse_dates=True)
            return file

    def pull_enums(self, key, node):
        """
        Retrieves the enum values for a given key (property) and node (data node / object from model) from the properties CSV.
        
        Example:
        For key = 'bp_lowering_meds' and node = 'blood_pressure',
        the function retrieves the enum reference code e.g. enum_bp_lowering_meds from the properties CSV,
        then uses this enum reference code to retrieve the enum values from the enum CSV.
        """
        if '.json' in node:
            node = node.split('.json')[0]
        try:
            enum_ref = self.prop_csv.loc[(self.prop_csv['VARIABLE_NAME'] == key) & (self.prop_csv['OBJECT'] == node), 'TYPE'].values
            if not enum_ref:
                raise ValueError(f"Key '{key}' with node '{node}' not found in properties CSV")
            enums = self.enum_csv.loc[self.enum_csv['type_name'] == enum_ref[0], 'enum'].tolist()
            return enums
        except Exception as e:
            print(f"Error pulling enums for key '{key}' with node '{node}': {e}")
            raise