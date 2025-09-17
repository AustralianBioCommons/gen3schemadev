# Tools for Gen3 Data Dictionary Development
This repository facilitates Gen3 data modeling using Google Sheets. It includes tools to convert Google Sheets into YAML files and then into a bundled JSON format. Additionally, it offers tools for schema validation and local data model visualization.


## Setup

### 1. Set up environment
```bash
git clone --recurse-submodules "https://github.com/AustralianBioCommons/gen3schemadev.git"
cd gen3schemadev
pip install poetry
poetry install
source $(poetry env info --path)/bin/activate
```
### 2. Install Docker
To install Docker Desktop, download it from the [Docker website](https://www.docker.com/products/docker-desktop) and follow the installation instructions for your operating system. After installation, verify by running `docker --version` in the terminal.

### 3. Spin up containers
```bash
cd umccr-dictionary
make down
make pull
make up
make ps
cd ..
```

## Usage

By default the script will use the Google Sheet template. The template can be accessed [here](https://docs.google.com/spreadsheets/d/1zjDBDvXgb0ydswFBwy47r2c8V1TFnpUj1jcG0xsY7ZI/edit?usp=sharing). Feel free to duplicate this spreadsheet and input your own google sheet id along with the tab ids for objects, links, properties, and enums as arguments for the script.

```bash
# to run with template google sheet
poetry run bash scripts/generate_schema.sh 

# to run with custom google_sheet
poetry run bash scripts/generate_schema.sh \\
  --google-id "1zjDBDvXgb0ydswFBwy47r2c8V1TFnpUj1jcG0xsY7ZI" \\
  --objects-gid "0" \\
  --links-gid "270346573" \\
  --properties-gid "613332252" \\
  --enums-gid "1807456496"
```

For more detailed step by step instructions can run using the [Schema Development Framework Notebook](jupyter/schema_dev_framework.ipynb).

## Outputs

Example outputs can be found in the [example_outputs folder](example_outputs/).

The script writes outputs to the `output` directory:
- The gen3 bundled json file will be in `output/schema/json/schema_dev.json`
- The gen3 yaml files will be in `output/schema/yaml/`
- The google sheets that were downloaded will be in `output/schema/input_google_sheets1`