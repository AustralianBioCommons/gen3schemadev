# gen3datasubmitter.py Documentation

## Overview
This module provides classes and functions for handling metadata submission to Gen3 Indexd. It includes utilities for reading and writing metadata files, pulling parameters from Gen3 Indexd using GUIDs, and updating metadata files with the necessary information.

## Classes

### `AddIndexdMetadata`
A class to handle adding metadata to Gen3 Indexd. This class provides methods to read and write metadata files, pull parameters from Gen3 Indexd using GUIDs, and match file names to their corresponding GUIDs.

#### Attributes
- **`index`**: An instance of the `Gen3Index` class for interacting with Gen3 Indexd.
- **`metadata_dir`**: The directory where metadata files are stored.
- **`indexd_guid_path`**: The path to the JSON file containing indexd GUIDs.

#### Methods
- **`__init__(self, auth, metadata_dir: str, indexd_guid_path: str)`**
  - Initializes the `AddIndexdMetadata` class with authentication, metadata directory, and indexd GUID path.

- **`pull_indexd_param(self, guid: str, file_name: str)`**
  - Pulls parameters from Gen3 Indexd using a GUID and returns them as a dictionary.

- **`read_metadata(self, file_path: str)`**
  - Reads a metadata file from the specified path and returns the parsed JSON object.

- **`write_metadata(self, file_path: str, metadata: dict)`**
  - Writes a metadata dictionary to the specified file path.

- **`pull_filename(self, json_obj: dict)`**
  - Extracts the file name from a JSON object.

- **`pull_gen3_guid(self, indexd_guid_path: str, file_name: str)`**
  - Pulls the object_id from a JSON file for a matching file name.

- **`update_metadata_with_indexd(self, file_path: str, output_dir: str, project_id: str, n_file_progress: int, n_file_total: int)`**
  - Updates metadata files with parameters pulled from Gen3 Indexd.

## Functions

### `extract_gen3_guids(log_path, project_id, output_dir, prefix: str = "PREFIX")`
Extracts filenames and object_ids from a gen3-client log file and writes them to an object manifest file.

#### Args
- **`log_path`**: The path to the gen3-client log file.
- **`project_id`**: The project identifier.
- **`output_dir`**: The directory to save the output manifest file.
- **`prefix`**: The prefix for object_ids. Defaults to "PREFIX".

#### Returns
- **`list`**: A list of dictionaries, each containing 'filename' and 'object_id' keys.

### `create_manifest_from_folder(folder_path, project_id=None, output_path=None, exclude_extension: list = None)`
Reads the files in the specified folder and creates a JSON manifest file.

#### Args
- **`folder_path`**: The path to the folder containing the files.
- **`project_id`**: The ID of the project.
- **`output_path`**: The path where the manifest file will be saved.
- **`exclude_extension`**: A list of file extensions to exclude from the manifest.

#### Returns
- **`str`**: The path to the created manifest file or an error message.

### `check_unlinked_objects(file_path)`
Checks for unlinked objects in a metadata file.

#### Args
- **`file_path`**: The path to the metadata file.

#### Returns
- **`list`**: A list of filenames that are unlinked.

### `update_metadata(base_dir, auth_file, indexd_guid_file, project_id: str = None)`
Updates metadata files for all file nodes in the given base directory by adding indexd GUIDs to their metadata.

#### Args
- **`base_dir`**: The path to the base directory.
- **`auth_file`**: The path to the authentication file.
- **`indexd_guid_file`**: The path to the indexd GUID file created from the gen3-client log files.
- **`project_id`**: The ID of the project.

#### Returns
- **`None`**

### `copy_remaining_metadata(base_dir)`
Copies metadata files for all non-file nodes in the given base directory to the indexd folder.

#### Args
- **`base_dir`**: The path to the directory containing all the non-file and non-indexd updated metadata JSON files.

#### Returns
- **`None`**

### `submit_metadata(base_dir: str, project_id: str, api_endpoint: str, credentials: str, exclude_nodes: list = ["project", "program", "acknowledgement", "publication"], dry_run: bool = False)`
Submits metadata JSON files to the Gen3 API endpoint.

#### Args
- **`base_dir`**: The path to the folder containing the metadata JSON files.
- **`project_id`**: The ID of the project.
- **`api_endpoint`**: Gen3 API endpoint.
- **`credentials`**: The path to the file containing the API credentials.
- **`exclude_nodes`**: A list of node names to exclude from the import. Defaults to ["project", "program", "acknowledgement", "publication"].
- **`dry_run`**: If True, perform a dry run without actual submission. Defaults to False.

#### Returns
- **`None`**

### `delete_metadata(import_order_file: str, project_id: str, api_endpoint: str, credentials: str, exclude_nodes: list = ["project", "program", "acknowledgement", "publication"])`
Deletes metadata JSON files from the Gen3 API endpoint.

#### Args
- **`import_order_file`**: The path to the import order file.
- **`project_id`**: The ID of the project.
- **`api_endpoint`**: Gen3 API endpoint.
- **`credentials`**: The path to the file containing the API credentials.
- **`exclude_nodes`**: A list of node names to exclude from the deletion. Defaults to ["project", "program", "acknowledgement", "publication"].

#### Returns
- **`None`**

## Example Usage

### Adding Indexd Metadata
```python
from gen3.auth import Gen3Auth

auth = Gen3Auth(refresh_file='path/to/auth.json')
metadata_handler = AddIndexdMetadata(
    auth=auth,
    metadata_dir='path/to/metadata',
    indexd_guid_path='path/to/indexd_guids.json'
)

metadata_handler.update_metadata_with_indexd(
    file_path='example_metadata.json',
    output_dir='output',
    project_id='project123',
    n_file_progress=1,
    n_file_total=10
)
```

### Extracting Gen3 GUIDs
```python
extracted_data = extract_gen3_guids(
    log_path='path/to/logs',
    project_id='project123',
    output_dir='output'
)
```

### Creating a Manifest from a Folder
```python
manifest_path = create_manifest_from_folder(
    folder_path='path/to/folder',
    project_id='project123',
    output_path='path/to/output',
    exclude_extension=['.tmp', '.log']
)
```

### Checking Unlinked Objects
```python
unlinked_objects = check_unlinked_objects(file_path='path/to/metadata.json')
print(unlinked_objects)
```

### Updating Metadata
```python
update_metadata(
    base_dir='path/to/base_dir',
    auth_file='path/to/auth.json',
    indexd_guid_file='path/to/indexd_guids.json',
    project_id='project123'
)
```

### Copying Remaining Metadata
```python
copy_remaining_metadata(base_dir='path/to/base_dir')
```

### Submitting Metadata
```python
submit_metadata(
    base_dir='path/to/base_dir',
    project_id='project123',
    api_endpoint='https://gen3.example.com',
    credentials='path/to/credentials.json',
    exclude_nodes=["project", "program"],
    dry_run=True
)
```

### Deleting Metadata
```python
delete_metadata(
    import_order_file='path/to/DataImportOrder.txt',
    project_id='project123',
    api_endpoint='https://gen3.example.com',
    credentials='path/to/credentials.json',
    exclude_nodes=["project", "program"]
)
```

This documentation provides an overview of the classes and functions available in the `gen3datasubmitter.py` module, along with example usage to help you get started.