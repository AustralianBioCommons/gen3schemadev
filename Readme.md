# Tools for Gen3 Data Dictionary Development
This repository facilitates Gen3 data modeling using Google Sheets. It includes tools to convert Google Sheets into YAML files and then into a bundled JSON format. Additionally, it offers tools for schema validation and local data model visualization.


## Setup

### 1. Set up environment
```bash
git clone --recurse-submodules "https://github.com/AustralianBioCommons/gen3schemadev.git"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
### 2. Install Docker
To install Docker Desktop, download it from the [Docker website](https://www.docker.com/products/docker-desktop) and follow the installation instructions for your operating system. After installation, verify by running `docker --version` in the terminal.

### 3. Spin up containers
```bash
cd umccr-dictionary
make pull
make up
make ps
cd ..
```

## Usage

You can run using the [Schema Development Framework Notebook](jupyter/schema_dev_framework.ipynb) or by following the usage below.

Alternatively you can run the script:
```bash
bash scripts/generate_schema.sh --help
bash scripts/generate_schema.sh
```


### 1. Pull Data Schema from Google Sheets

This step involves pulling the schema design from a Google Sheet template. The template can be accessed [here](https://docs.google.com/spreadsheets/d/1zjDBDvXgb0ydswFBwy47r2c8V1TFnpUj1jcG0xsY7ZI/edit?usp=sharing). Feel free to duplicate this spreadsheet and input your own google sheet id along with the tab ids for objects, links, properties, and enums.

```bash
[ -d "schema_out" ] && rm -rf "schema_out"
python3 sheet2yaml-CLI.py --google-id '1zjDBDvXgb0ydswFBwy47r2c8V1TFnpUj1jcG0xsY7ZI' --objects-gid 0 --links-gid 270346573 --properties-gid 613332252 --enums-gid 1807456496
```

### 2. Move Schema Output

Move the generated schema files to the `umccr-dictionary` directory:

```bash
mkdir -p umccr-dictionary/dictionary/schema_dev/gdcdictionary/schemas
cp schema_out/* umccr-dictionary/dictionary/schema_dev/gdcdictionary/schemas/
ls -lsha umccr-dictionary/dictionary/schema_dev/gdcdictionary/schemas/
```

### 3. Compile and Bundle into JSON

Compile and bundle the schema into a JSON format:

```bash
cd umccr-dictionary && make compile program=schema_dev
```

### 4. Run Validation

Validate the compiled schema:

```bash
cd umccr-dictionary && make validate program=schema_dev
```

### 5. Visualize Data Dictionary

Open the data dictionary visualization in your web browser:

```bash
open http://localhost:8080/#schema/schema_dev.json
```

### 6. View Outputs

After running the script, you can view the generated outputs in the `output` folder. This folder contains the schema files pulled from the Google Sheets. You can access this folder directly in your file system or use the following command to open it:
