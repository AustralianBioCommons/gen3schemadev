import os
import sys
from gen3.auth import Gen3Auth
from gen3.index import Gen3Index
from gen3.submission import Gen3Submission
import json
from datetime import datetime
import uuid
import shutil


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



################################################
# Functions
################################################

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
        

def submit_metadata(base_dir: str, project_id: str, api_endpoint: str, credentials: str, exclude_nodes: list = ["project", "program", "acknowledgement", "publication"], 
                    dry_run: bool = False, max_submission_size_kb: int = 400, retries = 5, disable_input: bool = False,
                    specific_node: str = None, ab_path: bool = False, import_order_file: str = None):
    """
    Submits metadata json files to the gen3 api endpoint. Submission depends on a DataImportOrder.txt file, which defines the order of the nodes to be imported.

    Args:
        base_dir (str): The path to the folder containing the metadata .json files. Should not contain project_id or indexd folder
        project_id (str): The ID of the project.
        api_endpoint (str): Gen3 API endpoint.
        credentials (str): The path to the file containing the API credentials.
        exclude_nodes (list): A list of node names to exclude from the import. Default is ["project", "program", "acknowledgement", "publication"].
        dry_run (bool): If True, perform a dry run without actual submission. Default is False.
        max_submission_size_kb (int): The maximum size of each submission in kilobytes. Default is 400 KB.
        disable_input (bool): If True, disable user input confirmation. Default is False.
        specific_node (str): If not None, only submit the specified node.
        ab_path (bool): If True, use the absolute path to the base_dir.
        import_order_file (str): The absolute path to the import order file, if not defined the program will look for os.path.join(folder_path, project_name, "indexd", "DataImportOrder.txt")

    Returns:
        None
    """
    
    def get_import_order(project_name, folder_path):
        path = import_order_file or os.path.join(folder_path, project_name, "indexd", "DataImportOrder.txt")
        try:
            with open(path, "r") as f:
                import_order = [line.rstrip() for line in f]
                import_order = [node for node in import_order if node not in exclude_nodes]
            return import_order
        except FileNotFoundError:
            print(f"Error: DataImportOrder.txt not found in {path}")
            return []

    def read_json(json_fn, ab_path: bool = False):
        try:
            if ab_path:
                json_path = os.path.join(base_dir, json_fn)
            else:
                json_path = os.path.join(base_dir, project_id, 'indexd', json_fn)
            with open(json_path, 'r') as f:
                schema = json.load(f)
            print(f'{json_path} successfully loaded')
            return schema
        except FileNotFoundError:
            print(f"Error: JSON file {json_path} not found.")
            return None
        except json.JSONDecodeError:
            print(f"Error: JSON file {json_path} is not valid.")
            return None

    if specific_node is None:
        ordered_import_nodes = get_import_order(project_id, base_dir)
        final_ordered_import_nodes = [node for node in ordered_import_nodes if node not in exclude_nodes]

    # creating auth and submission objects
    auth = Gen3Auth(refresh_file=credentials)
    sub = Gen3Submission(endpoint=api_endpoint, auth_provider=auth)
    
    
    if not dry_run and not disable_input:
        confirm = input("Do you want to submit the metadata? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("Submission cancelled by user.")
            return
    

    def split_json_objects(json_list, max_size_kb=max_submission_size_kb, print_results=False):
        def get_size_in_kb(obj):
            return sys.getsizeof(json.dumps(obj)) / 1024

        def split_list(json_list):
            if get_size_in_kb(json_list) <= max_size_kb:
                return [json_list]
            
            mid = len(json_list) // 2
            left_list = json_list[:mid]
            right_list = json_list[mid:]
            
            return split_list(left_list) + split_list(right_list)

        split_lists = split_list(json_list)
        
        if print_results:
            for i, lst in enumerate(split_lists):
                print(f"List {i+1} size: {get_size_in_kb(lst):.2f} KB, contains {len(lst)} objects")
    
        return split_lists
    
    
    def process_node(node, sub, project_id, dry_run, max_retries=3):
        if dry_run:
            print(f"DRY RUN\t| {project_id}\t| {node} would be submitted")
            return

        print(f"\n\nIMPORTING\t| {project_id}\t| {node}")
        json_data = read_json(f"{node}.json", ab_path=ab_path)

        if json_data is None:
            print(f"SKIPPING\t| {project_id}\t| {node} due to errors in reading JSON")
            return
        
        json_split = split_json_objects(json_data, max_size_kb=max_submission_size_kb, print_results=True)
        n_json_data = len(json_split)
        
        for index, jsn in enumerate(json_split):
            retries = 0
            while retries < max_retries:
                try:
                    print(f"SUBMITTING\t| {project_id}\t| {node}\t| {index + 1}/{n_json_data} data splits")
                    sub.submit_record("program1", project_id, jsn)
                    print(f"SUCCESS\t| Imported: {project_id}\t| {node}")
                    break
                except Exception as e:
                    retries += 1
                    print(f"ERROR\t| {project_id}\t| {node}: {e} | Retry {retries}/{max_retries}")
                    if retries == max_retries:
                        print(f"FAILED\t| {project_id}\t| {node} after {max_retries} retries")

    
    if specific_node:
        process_node(specific_node, sub, project_id, dry_run, retries)
        return print(f"Done. {project_id} | {specific_node} metadata submitted")
    
    for node in final_ordered_import_nodes:
        process_node(node, sub, project_id, dry_run, retries)

         
def delete_metadata(import_order_file: str, project_id: str, api_endpoint: str, credentials: str, exclude_nodes: list = ["project", "program", "acknowledgement", "publication"], prompt_for_confirmation: bool = True):
    """
    Deletes metadata json files from the gen3 api endpoint. Deletion depends on a DataImportOrder.txt file, which defines the order of the nodes to be deleted.

    Args:
        import_order_file (str): The path to the import order file
        project_id (str): The ID of the project.
        api_endpoint (str): Gen3 API endpoint.
        credentials (str): The path to the file containing the API credentials.
        exclude_nodes (list): A list of node names to exclude from the deletion. Default is ["project", "program", "acknowledgement", "publication"].

    Returns:
        None
    """
    
    def get_import_order(import_order_file):
        try:
            with open(import_order_file, "r") as f:
                import_order = [line.rstrip() for line in f]
                import_order = [node for node in import_order if node not in exclude_nodes]
            return import_order
        except FileNotFoundError:
            print(f"Error: DataImportOrder.txt not found in {import_order_file}")
            return []

    ordered_import_nodes = get_import_order(import_order_file)
    auth = Gen3Auth(refresh_file=credentials)
    sub = Gen3Submission(endpoint=api_endpoint, auth_provider=auth)
    
    final_ordered_import_nodes = [node for node in ordered_import_nodes if node not in exclude_nodes]
    final_ordered_import_nodes.reverse()  # Reverse the order for deletion
    
    if prompt_for_confirmation:
        confirm = input("Do you want to delete the metadata? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("Deletion cancelled by user.")
            return
    
    for node in final_ordered_import_nodes:
        print(f"\n\n=== Deleting: {project_id} | {node} ===")
        try:
            sub.delete_nodes("program1", project_id, [node])
            print(f"=== Successfully Deleted: {node} ===")
        except Exception as e:
            print(f"=== Error deleting {node}: {e} ===")