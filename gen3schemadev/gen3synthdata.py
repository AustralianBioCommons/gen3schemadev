import os
import sys
import shutil
import json
import yaml
import pandas as pd
import random
import uuid
from datetime import datetime, timedelta, timezone
from gen3.auth import Gen3Auth
from gen3.index import Gen3Index
from gen3.submission import Gen3Submission


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
        try:
            if data_format is None or data_format == "null":
                print(f'WARNING: data_format is None or "null", cannot find dummy file')
                return None
            for synth_fn, synth_lookup in self.synthetic_file_index.items():
                if any(data_format in x for x in synth_lookup):
                    return synth_fn
            if matched_fn is None:
                print(f'WARNING: "{data_format}" does not match any synthetic files')
        except Exception as e:
            print(f"Exception occurred in find_dummy_file: {e}")
            return None

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
        Adds exception handling for file operations and key lookups.
        """
        for entry in self.metadata_file_list:
            for project, filename in entry.items():
                try:
                    print(f"Processing {project}: {filename}")  # Debugging print
                    metadata_path = os.path.join(self.json_data_path, project, filename)
                    metadata = self.read_json_file(metadata_path)
                except Exception as e:
                    print(f"Error reading JSON file {metadata_path}: {e}")
                    continue

                for data_object in metadata:
                    try:
                        file_format = data_object['data_format']
                        synth_filename = self.find_dummy_file(file_format)
                        print(f"synth_filename: {synth_filename}")
                        synth_filename = synth_filename.split('.')[0]
                        print(f"updated synth_filename: {synth_filename}")
                        data_object['file_name'] = synth_filename
                    except KeyError as ke:
                        print(f"KeyError in data_object: {ke}. Skipping this object.")
                        continue
                    except Exception as e:
                        print(f"Unexpected error processing data_object: {e}. Skipping this object.")
                        continue

                try:
                    output_path = os.path.join(self.output_dir, project, filename)
                    self.write_json_file(metadata, output_path)
                except Exception as e:
                    print(f"Error writing JSON file {output_path}: {e}")
                

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



class AddIndexdMetadata:
    """
    A class to handle adding metadata to Gen3 Indexd.

    This class provides methods to read and write metadata files, pull parameters from Gen3 Indexd using GUIDs, 
    and match file names to their corresponding GUIDs. It is designed to facilitate the integration of metadata 
    with Gen3 Indexd, ensuring that metadata files are properly updated with the necessary information.

    Attributes:
        index (Gen3Index): An instance of the Gen3Index class for interacting with Gen3 Indexd.
        metadata_dir (str): The directory where metadata files are stored.
        indexd_guid_path (str): The path to the JSON file containing indexd GUIDs.
    """
    def __init__(self, auth, metadata_dir: str, indexd_guid_path: str):
        self.index = Gen3Index(auth)
        self.metadata_dir = metadata_dir
        self.indexd_guid_path = indexd_guid_path
    
    def pull_indexd_param(self, guid: str, file_name: str):
        try:
            output = self.index.get(guid)
            if output:
                try:
                    output_jsn = {
                        'file_name': output['file_name'],
                        'object_id': output['did'],
                        'file_size': output['size'],
                        'md5sum': output['hashes']['md5']
                    }
                    print(f"{file_name}\t| SUCCESS | pulled indexd parameters for: {guid}")
                    return output_jsn
                except KeyError as e:
                    print(f"{file_name}\t| ERROR | Missing required key {e} in output for GUID: {guid}")
                    return None
        except Exception as e:
            # print(f"{file_name} | ERROR | No metadata found for GUID: {guid} | Check S3 | {e}")
            return None
    
    def read_metadata(self, file_path: str):
        with open(f"{self.metadata_dir}/{file_path}", "r") as f:
            metadata = json.load(f)
            print(f"Metadata read from: {file_path}")
        return metadata
    
    def write_metadata(self, file_path: str, metadata: dict):
        with open(f"{self.metadata_dir}/{file_path}", "w") as f:
            json.dump(metadata, f, indent=4, sort_keys=True)
        print(f"Metadata written to: {file_path}")
    
    def pull_filename(self, json_obj: dict):
        try:
            file_name = json_obj['file_name']
            data_format = json_obj['data_format']
            complete_fn = f"{file_name}.{data_format}"
            return complete_fn
        except KeyError as e:
            print(f"KeyError: {e} in entry {entry}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e} in entry {entry}")
            return None
    
    def pull_gen3_guid(self, indexd_guid_path: str, file_name: str):
        """
        Pulls the object_id from a JSON file for a matching file_name.

        Args:
            indexd_guid_path (str): The path to the JSON file.
            file_name (str): The file name to match.
            
        Returns:
            str: The object_id if found, else None.
        """
        try:
            with open(indexd_guid_path, "r") as f:
                data = json.load(f)
                for entry in data:
                    if entry.get("file_name") == file_name:
                        return entry.get("object_id")
            print(f"No matching file_name found for: {file_name}")
            return None
        except Exception as e:
            print(f"Error reading JSON file: {indexd_guid_path} | {e}")
            return None
    
    def update_metadata_with_indexd(self, file_path: str, output_dir: str, project_id: str, n_file_progress: int, n_file_total: int):
        print(f"\n\n\n=======================================================\n=======================================================")
        print(f"UPDATING METADATA: {file_path}")
        print(f"=======================================================\n=======================================================")
        metadata = self.read_metadata(file_path)
        num_objects = len(metadata)
        print(f"Number of objects in JSON array: {num_objects}")
        for index, entry in enumerate(metadata):
            print(f"\nFILE | {project_id} | {n_file_progress + 1}/{n_file_total} | {file_path}")
            print(f"{index+1}/{num_objects} | {entry['file_name']}")
            filename = self.pull_filename(entry)
            guid = self.pull_gen3_guid(f"{self.indexd_guid_path}", filename)
            print(f"{filename}\t| GUID | {guid}")
            if guid:
                indexes = self.pull_indexd_param(guid, filename)
                if indexes:
                    print(f"{filename}\t| UPDATING | Appending metadata: {indexes}")
                    entry['file_name'] = indexes['file_name']
                    entry['object_id'] = indexes['object_id']
                    entry['file_size'] = indexes['file_size']
                    entry['md5sum'] = indexes['md5sum']
                else:
                    print(f"{filename}\t| SKIPPING | Could not pull indexd parameters.")
            else:
                print(f"{filename}\t| SKIPPING | Could not pull GUID.")

        # writing metadata
        if not os.path.exists(f"{self.metadata_dir}/{output_dir}"):
            os.makedirs(f"{self.metadata_dir}/{output_dir}", exist_ok=True)
        print(f"Writing metadata to: {self.metadata_dir}/{output_dir}/{file_path}")
        self.write_metadata(f"{output_dir}/{file_path}", metadata)


def extract_gen3_guids(log_path, project_id, output_dir, prefix: str = "PREFIX"):
    """
    Extracts filenames and object_ids from a gen3-client log file and writes them to an object manifest file.

    Args:
        log_path (str): The path to the gen3-client log file.
        project_id (str): The project identifier.
        output_dir (str): The directory to save the output manifest file.

    Returns:
        list: A list of dictionaries, each containing 'filename' and 'object_id' keys.
    """
    log_file_path = f"{log_path}/{project_id}_succeeded_log.json"
    
    if not os.path.exists(log_path):
        print(f"{log_path} does not exist.")
        return []
    
    print(f"Extracting data from {log_file_path}")
    with open(log_file_path, 'r') as file:
        log_data = json.load(file)
    
    extracted_data = [
        {
            "date_time": datetime.now().isoformat(),
            "project_id": project_id,
            "file_name": os.path.basename(key),
            "object_id": f"{prefix}/{value.split(f'{prefix}/')[1]}"
        }
        for key, value in log_data.items()
    ]
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Create output filename
    date_time = datetime.now().strftime("%Y%m%d")
    output_fn = f"{output_dir}/{date_time}_{project_id}_succeeded_log.json"
    
    # Check if output file already exists
    if os.path.exists(output_fn):
        user_input = input(f"The output file {output_fn} already exists. Do you want to overwrite it? (yes/no): ").strip().lower()
        if user_input == 'yes':
            print(f"Overwriting {output_fn}")
        elif user_input == 'no':
            print("Operation aborted by the user.")
            return []
        else:
            print("Invalid input. Operation aborted.")
            return []
    
    # Write data to output file
    print(f"Writing data to {output_fn}")
    with open(output_fn, 'w') as file:
        json.dump(extracted_data, file, indent=4)
    print(f"Manifest file written to {output_fn}")

    return extracted_data


def create_manifest_from_folder(folder_path, project_id=None, output_path=None, exclude_extension: list = None):
    """
    Reads the files in the specified folder and creates a JSON manifest file. If project_id is not specified, the folder name is used.

    Args:
        folder_path (str): The path to the folder containing the files.
        project_id (str): The ID of the project.
        output_path (str): The path where the manifest file will be saved.
        exclude_extension (list): A list of file extensions to exclude from the manifest.
    
    Returns:
        str: The path to the created manifest file or an error message.
    """
    date_time = datetime.now().strftime("%Y%m%d")
    
    if not project_id:
        files = os.listdir(folder_path)
        manifest_path = f"{output_path}/{date_time}_manifest.json"
    else:
        files = os.listdir(os.path.join(folder_path, project_id))
        manifest_path = f"{output_path}/{date_time}_{project_id}_manifest.json"
    
    if exclude_extension:
        files = [file for file in files if not any(file.endswith(ext) for ext in exclude_extension)]
    
    manifest = [
        {
            "file_name": file,
            "object_id": f"temp_{str(uuid.uuid4())}"
        }
        for file in files
    ]
    
    outpath_dir = os.path.dirname(output_path)
    if not os.path.exists(outpath_dir):
        os.makedirs(outpath_dir, exist_ok=True)
    
    try:
        with open(manifest_path, 'w') as manifest_file:
            json.dump(manifest, manifest_file, indent=4)
    except IOError as e:
        print(f"Error writing to file {manifest_path}: {e}")
        return f"Error writing to file {manifest_path}: {e}"
    
    return f"Manifest file created at: {manifest_path}"


def check_unlinked_objects(file_path):
    # read json file
    with open(file_path, 'r') as f:
        data = json.load(f)
        print(f"Metadata read from: {file_path}")
    
    # for each object in the array, check if object_id key exists, if not, pull the value of filename, and append to unlinked_list
    unlinked_list = []
    n_objects = len(data)
    unlinked_count = 0
    for entry in data:
        if 'object_id' not in entry:
            filename = f"{entry['file_name']}.{entry['data_format']}"
            unlinked_list.append(filename)
            unlinked_count += 1
    if unlinked_count == 0:
        print(f"{file_path} all objects successfully Linked")
    else:
        print(f"{file_path} {unlinked_count}/{n_objects} objects unlinked")
    return unlinked_list




def update_metadata(base_dir, auth_file, indexd_guid_file, project_id: str = None):
    """
    Update metadata files for all file nodes in the given base directory by adding indexd guids to their metadata.
    
    Args:
        base_dir (str): The path to the base directory.
        auth_file (str): The path to the authentication file.
        indexd_guid_file (str): The path to the index_guids file created from the gen3-client log files, generated with the extract_gen_guids function.
    
    Returns:
        None
    
    Raises:
        None
    """

    # Check if base directory exists
    if not os.path.exists(base_dir):
        print(f"Error: Base directory {base_dir} does not exist.")
        return

    # Check if auth file exists
    if not os.path.isfile(auth_file):
        print(f"Error: Auth file {auth_file} does not exist.")
        return

    # Check if indexd guid file exists
    if not os.path.isfile(indexd_guid_file):
        print(f"Error: Indexd GUID file {indexd_guid_file} does not exist.")
        return

    # Creating indexd linked metadata files for all file nodes
    data_import_nodes = os.listdir(f"{base_dir}/")
    file_nodes = [node for node in data_import_nodes if node.endswith('_file.json')]
    total_file_nodes = len(file_nodes)
    print(f"Found {len(file_nodes)} file nodes in {base_dir}")
    
    # Adding indexd guids to file node metadata
    auth = Gen3Auth(refresh_file=auth_file)
    index_meta = AddIndexdMetadata(auth, f"{base_dir}", indexd_guid_file)
    for index, fn in enumerate(file_nodes):
        print(f"Updating metadata for file node: {fn}")
        index_meta.update_metadata_with_indexd(f"{fn}", "indexd", n_file_progress=index, n_file_total=total_file_nodes, project_id=project_id)
        
        
def copy_remaining_metadata(base_dir):
    """
    Copy metadata files for all non-file nodes in the given base directory to the indexd folder. All file node metadata would have been copied with update_metadata function.
    
    Args:
        base_dir (str): The path to the directory containing all the non-file and non-indexd updated metadata json files.
    
    Returns:
        None
    
    Raises:
        None
    """

    # Check if base directory exists
    if not os.path.exists(base_dir):
        print(f"Error: Base directory {base_dir} does not exist.")
        return

    # Creating indexd linked metadata files for all non-file nodes
    data_import_nodes = os.listdir(f"{base_dir}/")
    non_file_nodes = [node for node in data_import_nodes if not node.endswith('_file.json')]

    print(f"Found {len(non_file_nodes)} non-file nodes in {base_dir}")

    # Ensure the indexd directory exists
    indexd_dir = f"{base_dir}/indexd"
    if not os.path.exists(indexd_dir):
        os.makedirs(indexd_dir, exist_ok=True)
        print(f"Created directory: {indexd_dir}")

    # Copying non-file nodes to the indexd folder
    for node in non_file_nodes:
        src_path = f"{base_dir}/{node}"
        dst_path = f"{indexd_dir}/{node}"
        
        if os.path.isfile(src_path):
            print(f"Copying non-file node: {node} to {indexd_dir}")
            shutil.copy(src_path, dst_path)
        else:
            print(f"Skipping directory: {node}")

    data_import_order_file = f"{base_dir}/DataImportOrder.txt"
    if os.path.isfile(data_import_order_file):
        print(f"Copying DataImportOrder.txt to {indexd_dir}")
        shutil.copy(data_import_order_file, f"{indexd_dir}/DataImportOrder.txt")
    else:
        print(f"Warning: DataImportOrder.txt does not exist in {base_dir}")
        