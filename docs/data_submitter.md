# Data Submission Script Documentation

## Overview

This script is designed to submit data and metadata to a Gen3 instance using the Gen3 SDK and command line tool. It supports various functionalities such as deleting existing metadata, uploading dummy data files, and updating metadata JSON files.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
  - [Arguments](#arguments)
  - [Examples](#examples)
- [Functions](#functions)
  - [parse_arguments](#parse_arguments)
  - [delete_metadata](#delete_metadata)
- [Main Function Workflow](#main-function-workflow)
  - [Deleting Metadata](#deleting-metadata)
  - [Uploading Dummy Data Files to S3](#uploading-dummy-data-files-to-s3)
  - [Creating Gen3 SDK Class Objects](#creating-gen3-sdk-class-objects)
  - [Creating Projects](#creating-projects)
  - [Adding Index Properties to Metadata JSONs](#adding-index-properties-to-metadata-jsons)
  - [Submitting Updated Data File Index Metadata](#submitting-updated-data-file-index-metadata)
- [Contributing](#contributing)
- [License](#license)

## Installation

Ensure you have the necessary dependencies installed. You can install them using pip:

```bash
pip install gen3
```

## Usage

### Arguments

The script accepts the following command-line arguments:

- `--folder`: The outer folder where simulated data lives (required).
- `--projects`: Space-delimited names of specific projects, which are sub-folders of the provided folder (default: `["AusDiab", "FIELD", "BioHEART-CT"]`).
- `--delete-all-metadata`: If specified, deletes all node metadata below the project level.
- `--profile`: The name of your Gen3-client profile, required for uploading data files to the portal.
- `--api-endpoint`: The URL of the data commons (e.g., `https://data.acdc.ozheart.org`).
- `--credentials`: The path to the `credentials.json` with authority to upload to the commons (default: `_local/credentials.json`).
- `--numparallel`: Number of cores to use for uploading in parallel (default: 2).
- `--add-subjects`: If specified, skips program and project creation and adds nodes from subjects onwards.
- `--metadata-only`: If specified, only updates the metadata JSON files and does not upload associated data files.

### Examples

#### Basic Usage

```bash
python datas_submittor.py --folder /path/to/data --api-endpoint https://data.acdc.ozheart.org --credentials /path/to/credentials.json
```

#### Deleting All Metadata

```bash
python datas_submittor.py --folder /path/to/data --delete-all-metadata --api-endpoint https://data.acdc.ozheart.org --credentials /path/to/credentials.json
```

#### Uploading Metadata Only

```bash
python datas_submittor.py --folder /path/to/data --metadata-only --api-endpoint https://data.acdc.ozheart.org --credentials /path/to/credentials.json
```

## Functions

### parse_arguments

Parses command-line arguments.

```python
def parse_arguments():
    parser = argparse.ArgumentParser()
    # Argument definitions...
    return parser.parse_args()
```

### delete_metadata

Deletes metadata for a given project.

```python
def delete_metadata(project_name, folder_path, api_endpoint, credentials_path):
    with open(os.path.join(folder_path, project, "DataImportOrder.txt"), "r") as f:
        import_order = [line.rstrip() for line in f]
        import_order.remove("project")
        import_order.remove("program")
    import_order.reverse()
    endpoint = api_endpoint
    auth = Gen3Auth(endpoint=endpoint, refresh_file=credentials_path)
    sub = Gen3Submission(endpoint=endpoint, auth_provider=auth)
    sub.delete_nodes("program1", project_name, import_order)
```

## Main Function Workflow

### Deleting Metadata

If the `--delete-all-metadata` flag is specified, the script will prompt the user for confirmation and then delete all existing metadata for the specified projects.

```python
if args.delete_all_metadata:
    proceed = input(f"Are you sure you want to delete all existing metadata for the projects: {args.projects}? y/n\n")
    if proceed.lower() == "y":
        for project in args.projects:
            delete_metadata(project, args.folder, args.api_endpoint, args.credentials)
        print("Deletion completed, now exiting.")
        sys.exit()
    else:
        print("ok, now exiting. Please remove --delete_all_metadata flag and rerun script.")
        sys.exit()
```

### Uploading Dummy Data Files to S3

For each project, if the `--metadata-only` flag is not specified, the script will upload dummy data files to S3 using the Gen3 client.

```python
if not args.metadata_only:
    if args.profile and os.path.exists(os.path.join(folder, project, "dummy_files")):
        upload_path = os.path.join(folder, project, "dummy_files")
        bash_command = f"gen3-client upload --upload-path={upload_path} --profile={args.profile} --numparallel={args.numparallel}"
        process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
```

### Creating Gen3 SDK Class Objects

The script creates instances of Gen3 SDK classes for authentication, submission, and indexing.

```python
auth = Gen3Auth(endpoint=args.api_endpoint, refresh_file=args.credentials)
sub = Gen3Submission(endpoint=args.api_endpoint, auth_provider=auth)
index = Gen3Index(endpoint=args.api_endpoint, auth_provider=auth)
```

### Creating Projects

If the `--add-subjects` flag is not specified, the script will create a new program and project in the Gen3 instance.

```python
if not args.add_subjects:
    sub.create_program({
        "dbgap_accession_number": "prg123",
        "name": "program1",
        "type": "program"
    })
    proj = json.load(open(os.path.join(folder, project, "edited_jsons", "project.json")))
    sub.create_project("program1", proj)
```

### Adding Index Properties to Metadata JSONs

The script reads the `DataImportOrder.txt` file and updates the metadata JSON files with index properties from the Gen3 instance.

```python
for line in open(os.path.join(folder, project, "DataImportOrder.txt"), "r"):
    line = line.strip()
    if args.add_subjects:
        skip_objects = ["program", "project", "acknowledgement", "publication"]
    else:
        skip_objects = ["program", "project", "acknowledgement", "publication"]
    if line not in skip_objects:
        print(f"uploading {line}")
        try:
            jsn = json.load(open(os.path.join(folder, project, "edited_jsons", f"{line}.json")))
            # if you are uploading metdata and dummy files, and the json ends with "file", then try find the file in gen3 S3 and get index properties
            if not args.metadata_only:
                if line.endswith("file"):
                    for file_md in jsn:
                        try:
                            # Getting index properties of the data file from the gen3 index class
                            indexed_file = index.get_with_params({"file_name": file_md['file_name']})
                            # writing index properties to the key values
                            file_md['object_id'] = indexed_file['did']
                            file_md['md5sum'] = indexed_file['hashes']['md5']
                            file_md['file_size'] = indexed_file['size']
                        except KeyError as e:
                            print(e)
                            print(f"{file_md['file_name']} data file not yet uploaded")
                        except requests.exceptions.HTTPError as e:
                            print(e)
                            content = e.response.content
                            print(f"{file_md['file_name']} data file not yet uploaded")
                            pass
                        except TypeError as e:
                            print(e)
                            print(f"{file_md['file_name']} data file not yet uploaded")
            
```

### Submitting Updated Data File Index Metadata

The script submits the updated metadata JSON files to the Gen3 instance.

```python
try:
    sub.submit_record("program1", project, jsn)
except requests.exceptions.HTTPError as e:
    content = e.response.content
    try:
        content = json.dumps(json.loads(content), indent=4, sort_keys=True)
    except:
        pass
    raise requests.exceptions.HTTPError(content, response=e.response)
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## AI disclosure
- This document was primarily made with gpt-4o on 2024-06-20
- Further iterations of the document will be made manually
- Document vetted by Joshua Harris 2024-06-20