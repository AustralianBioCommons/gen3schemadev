from gen3.index import Gen3Index
import json
import os
from datetime import datetime
import uuid


class Gen3IndexdUpdateMetadata:
    
    def __init__(self, auth, metadata_dir: str, indexd_guid_path: str):
        self.index = Gen3Index(auth)
        self.metadata_dir = metadata_dir
        self.indexd_guid_path = indexd_guid_path
    
    def pull_indexd_param(self, guid: str):
        try:
            output = self.index.get(guid)
            if output:
                print(f"SUCCESS: pulled indexd parameters for: {guid}")
            return {
                'file_name': output['file_name'],
                'object_id': output['did'],
                'file_size': output['size'],
                'md5sum': output['hashes']['md5']
            }
        except Exception as e:
            print(f"ERROR: No metadata found for GUID: {guid} | Check S3 | {e}")
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
    
    def update_metadata(self, file_path: str, output_dir: str):
        print(f"\n\n\n=======================================================\n=======================================================")
        print(f"UPDATING METADATA: {file_path}")
        print(f"=======================================================\n=======================================================")
        metadata = self.read_metadata(file_path)
        for entry in metadata:
            filename = self.pull_filename(entry)
            guid = self.pull_gen3_guid(f"{self.indexd_guid_path}", filename)
            print(f"Filename: {filename} | GUID: {guid}")
            if guid:
                indexes = self.pull_indexd_param(guid)
                if indexes:
                    print(f"Appending metadata: {indexes}")
                    entry['file_name'] = indexes['file_name']
                    entry['object_id'] = indexes['object_id']
                    entry['file_size'] = indexes['file_size']
                    entry['md5sum'] = indexes['md5sum']
                else:
                    print(f"Skipping {filename} Could not pull indexd parameters.")
            else:
                print(f"Skipping {filename} Could not pull GUID.")

        # writing metadata
        if not os.path.exists(f"{self.metadata_dir}/{output_dir}"):
            os.makedirs(f"{self.metadata_dir}/{output_dir}", exist_ok=True)
        print(f"Writing metadata to: {self.metadata_dir}/{output_dir}/{file_path}")
        self.write_metadata(f"{output_dir}/{file_path}", metadata)
        

    def create_manifest_from_folder(self, project_id):
        """
        Reads the files in the specified folder and creates a JSON manifest file.

        Args:
            project_id (str): The ID of the project.
        """
        
        folder_path = f"{self.metadata_dir}/{project_id}"
        output_path = f"{self.metadata_dir}/../../../manifests"
        
        files = os.listdir(folder_path)
        # print(f"Found {files} files in the folder.")
        manifest = [
            {
                "file_name": file,
                "object_id": f"temp_{str(uuid.uuid4())}"
            }
            for file in files
        ]
        # print(f"Manifest: {manifest}")
        
        date_time = datetime.now().strftime("%Y%m%d")
        
        if not os.path.exists(output_path):
            os.makedirs(output_path, exist_ok=True)
        
        with open(f"{output_path}/{date_time}_{project_id}_manifest.json", 'w') as manifest_file:
            json.dump(manifest, manifest_file, indent=4)
        
        print(f"Manifest file created at: {output_path}")


# Functions
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
            "file_name": key.split(f"{project_id}/")[1],
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


def create_manifest_from_folder(folder_path, project_id, output_path):
    """
    Reads the files in the specified folder and creates a JSON manifest file.

    Args:
        folder_path (str): The path to the folder containing the files.
        project_id (str): The ID of the project.
        output_path (str): The path where the manifest file will be saved.
    """
    
    files = os.listdir(f"{folder_path}/{project_id}")
    # print(f"Found {files} files in the folder.")
    manifest = [
        {
            "file_name": file,
            "object_id": f"temp_{str(uuid.uuid4())}"
        }
        for file in files
    ]
    # print(f"Manifest: {manifest}")
    
    date_time = datetime.now().strftime("%Y%m%d")
    
    outpath_dir = os.path.dirname(output_path)
    if not os.path.exists(outpath_dir):
        os.makedirs(outpath_dir, exist_ok=True)
    
    with open(f"{output_path}/{date_time}_{project_id}_manifest.json", 'w') as manifest_file:
        json.dump(manifest, manifest_file, indent=4)
    
    return (f"Manifest file created at: {output_path}")


# def check_unlinked_objects(file_path):
#     # read json file
#     with open(file_path, 'r') as f:
#         data = json.load(f)
#         print(f"Metadata read from: {file_path}")
    
#     # for each object in the array, check if object_id key exists, if not, pull the value of filename, and append to unlinked_list
#     unlinked_list = []
#     n_objects = len(data)
#     unlinked_count = 0
#     for entry in data:
#         if 'object_id' not in entry:
#             filename = f"{entry['file_name']}.{entry['data_format']}"
#             unlinked_list.append(filename)
#             unlinked_count += 1
#     print(f"Unlinked objects: {unlinked_count}/{n_objects}")
#     return unlinked_list


#     def update_and_copy_metadata(base_dir, auth_file, indexd_guid_file):
#         import sys
#         import os
#         from gen3.auth import Gen3Auth
#         from gen3.index import Gen3Index
#         sys.path.append(os.path.abspath('gen3schemadev'))
#         # Refresh the gen3schemadev library
#         import importlib
#         import gen3schemadev
#         importlib.reload(gen3schemadev)
#         import shutil
#         import glob

#         # Check if base directory exists
#         if not os.path.exists(base_dir):
#             print(f"Error: Base directory {base_dir} does not exist.")
#             return

#         # Check if auth file exists
#         if not os.path.isfile(auth_file):
#             print(f"Error: Auth file {auth_file} does not exist.")
#             return

#         # Check if indexd guid file exists
#         if not os.path.isfile(indexd_guid_file):
#             print(f"Error: Indexd GUID file {indexd_guid_file} does not exist.")
#             return

#         # Creating indexd linked metadata files for all file nodes
#         data_import_nodes = os.listdir(f"{base_dir}/")
#         file_nodes = [node for node in data_import_nodes if node.endswith('_file.json')]
#         non_file_nodes = [node for node in data_import_nodes if not node.endswith('_file.json')]

#         print(f"Found {len(file_nodes)} file nodes and {len(non_file_nodes)} non-file nodes in {base_dir}")

#         # Adding indexd guids to file node metadata
#         auth = Gen3Auth(refresh_file=auth_file)
#         index_meta = gen3schemadev.gen3datasubmitter.Gen3IndexdUpdateMetadata(auth, f"{base_dir}", indexd_guid_file)
#         for fn in file_nodes:
#             print(f"Updating metadata for file node: {fn}")
#             index_meta.update_metadata(f"{fn}", "indexd")

#         # Ensure the indexd directory exists
#         indexd_dir = f"{base_dir}/indexd"
#         if not os.path.exists(indexd_dir):
#             os.makedirs(indexd_dir, exist_ok=True)
#             print(f"Created directory: {indexd_dir}")

#         # Copying non-file nodes to the indexd folder
#         for node in non_file_nodes:
#             print(f"Copying non-file node: {node} to {indexd_dir}")
#             shutil.copy(f"{base_dir}/{node}", f"{indexd_dir}/{node}")

#         data_import_order_file = f"{base_dir}/DataImportOrder.txt"
#         if os.path.isfile(data_import_order_file):
#             print(f"Copying DataImportOrder.txt to {indexd_dir}")
#             shutil.copy(data_import_order_file, f"{indexd_dir}/DataImportOrder.txt")
#         else:
#             print(f"Warning: DataImportOrder.txt does not exist in {base_dir}")

class MetadataManager:
    def __init__(self, base_dir, auth_file, indexd_guid_file):
        """
        Initializes a new instance of the MetadataManager class.

        Args:
            base_dir (str): The base directory path.
            auth_file (str): The path to the authentication file.
            indexd_guid_file (str): The path to the indexd GUID file.

        Initializes the following instance variables:
            - base_dir (str): The base directory path.
            - auth_file (str): The path to the authentication file.
            - indexd_guid_file (str): The path to the indexd GUID file.
            - auth (None): The authentication object.
            - index_meta (None): The index metadata object.
        """
        self.base_dir = base_dir
        self.auth_file = auth_file
        self.indexd_guid_file = indexd_guid_file
        self.auth = None
        self.index_meta = None

    def initialize_gen3_auth(self):
        from gen3.auth import Gen3Auth
        from gen3.index import Gen3Index
        import sys
        import os
        sys.path.append(os.path.abspath('gen3schemadev'))
        import importlib
        import gen3schemadev
        importlib.reload(gen3schemadev)

        # Check if base directory exists
        if not os.path.exists(self.base_dir):
            raise FileNotFoundError(f"Base directory {self.base_dir} does not exist.")

        # Check if auth file exists
        if not os.path.isfile(self.auth_file):
            raise FileNotFoundError(f"Auth file {self.auth_file} does not exist.")

        # Check if indexd guid file exists
        if not os.path.isfile(self.indexd_guid_file):
            raise FileNotFoundError(f"Indexd GUID file {self.indexd_guid_file} does not exist.")

        self.auth = Gen3Auth(refresh_file=self.auth_file)
        self.index_meta = gen3schemadev.gen3datasubmitter.Gen3IndexdUpdateMetadata(self.auth, self.base_dir, self.indexd_guid_file)

    def check_unlinked_objects(self, file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
            print(f"Metadata read from: {file_path}")

        unlinked_list = []
        n_objects = len(data)
        unlinked_count = 0
        for entry in data:
            if 'object_id' not in entry:
                filename = f"{entry['file_name']}.{entry['data_format']}"
                unlinked_list.append(filename)
                unlinked_count += 1
        print(f"Unlinked objects: {unlinked_count}/{n_objects}")
        return unlinked_list

    def update_and_copy_metadata(self):
        import shutil
        import os

        self.initialize_gen3_auth()

        data_import_nodes = os.listdir(f"{self.base_dir}/")
        file_nodes = [node for node in data_import_nodes if node.endswith('_file.json')]
        non_file_nodes = [node for node in data_import_nodes if not node.endswith('_file.json')]

        print(f"Found {len(file_nodes)} file nodes and {len(non_file_nodes)} non-file nodes in {self.base_dir}")

        for fn in file_nodes:
            print(f"Updating metadata for file node: {fn}")
            self.index_meta.update_metadata(f"{fn}", "indexd")

        indexd_dir = f"{self.base_dir}/indexd"
        if not os.path.exists(indexd_dir):
            os.makedirs(indexd_dir, exist_ok=True)
            print(f"Created directory: {indexd_dir}")

        for node in non_file_nodes:
            print(f"Copying non-file node: {node} to {indexd_dir}")
            shutil.copy(f"{self.base_dir}/{node}", f"{indexd_dir}/{node}")

        data_import_order_file = f"{self.base_dir}/DataImportOrder.txt"
        if os.path.isfile(data_import_order_file):
            print(f"Copying DataImportOrder.txt to {indexd_dir}")
            shutil.copy(data_import_order_file, f"{indexd_dir}/DataImportOrder.txt")
        else:
            print(f"Warning: DataImportOrder.txt does not exist in {self.base_dir}")
