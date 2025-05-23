import os
import sys
from gen3.auth import Gen3Auth
from gen3.index import Gen3Index
from gen3.submission import Gen3Submission
import json
from datetime import datetime
import uuid
import shutil


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