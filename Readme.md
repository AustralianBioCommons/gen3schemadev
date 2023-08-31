# Automated processes for Gen3 Data Dictionary, data simulation and submission automation

This repository contains all tools used and/or developed by Australian BioCommons to help automate routine tasks with gen3.

## `gen3schemadev` is an object relational mapper library for gen3 schemas.

The library can be used in order to convert a spreadsheet format into a complete set of the yaml files required to build a Gen3 Data Dictionary.

An implementation of the library for generating the CAD dictionary is demonstrated by `sheet2yaml.py`.

## Current Workflow for editing CAD Project Dictionary

### Local deployment (compose-services) hard-coded google sheet
1. Make schema edits to the `Harmonised Variables - v1 google sheet`
2. All schema objects in the google sheet need to have a template schema in the `schema` folder (to be phased out when all info can be generated)
3. Run `schema2yaml.py` which automatically reads the google sheets and parses the required information, writing the parsed schemas to the folder `schema_out` 
4. Copy `schema_out/*.yaml` to `path/to/umccr-dictionary/dictionary/cad/gdcdictionary/schema`, compile, test, validate. If test or validate fails, go back to 1 above.
5. Simulate data with the new schema, `make simulate dd=cad`, adjust the number of samples and name of project as required.
   1. Replace random simulated values with plausible ones using `plausible-data-gen` script
6. Switch the old gen3 dictionary with the new one
   1. upload the compiled json schema to the configured s3 bucket@`DICTIONARY_URL`
   2. ?? delete psql volume (?) (only in development phase so doesn't matter if data is lost)
   3. disable indexing services (kibana, guppy, tube)
   4. restart services, re-configure auth
   5. upload the simulated data against the new dictionary
   6. re-enable and restart indexing services and re-run etl index (`guppy_setup.sh`)

### sheet2yaml-CLI.py

`sheet2yaml-CLI.py` is a similar script where inputs are specified as command line arguments rather than hard-coded into the script. 

To use this script, one needs to provide identifiers for the google sheet as well as to each tab of the google sheet that needs to be read.

Each google sheet must follow the expected format as specified in the [template sheet](https://docs.google.com/spreadsheets/d/1qEL6bx_Pmif-h6GL_U-k6eotwIhIxCxYIjLecGk2TV8/edit#gid=0).

run `python sheet2yaml-CLI.py -h` to see required arguments.

# Plausible Data Generator

A fairly simple python script that takes as input a path to a set of json files and a csv file describing plausible values and replaces the random numbers generated out of gen3 software with ones from a defined distribution or range.

## Usage

Clone this repo 

Example usage:

```shell
cd gen3schemadev
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 plausible_data_gen.py --path <PATH_TO_SIM_DATA> [--values <PATH_TO_CSV> | --gurl <PATH_TO_GOOGLE_SHEET>] --generate-files --file-types aligned_reads
```

The code snippet above would generate plausible data 

The program will write the modified json files to a directory called `edited_jsons`.

If the `--dummy_sequencing_files` and/or `--dummy_lipid_files` flags are specified, files will be placed into a directory called `dummy_files`

## Format of CSV

The CSV needs to have the following columns (see the [plausible values tab](https://docs.google.com/spreadsheets/d/1AX9HLzIV6wtkVylLkwOr3kdKDaZf4ukeYACTJ7lYngk/edit#gid=1400179124) for an example.)

| Column      | Definition                                                                                                       | Allowed values                          |
|-------------|------------------------------------------------------------------------------------------------------------------|-----------------------------------------|
| object      | The name of the schema node, i.e. <object>.json                                                                  |                                         |
| property    | The name of the property within that schema/object                                                               |                                         |
| data_type   | The type of data that needs to be generated. (enums and strings not currently supported)                         | range; mean; number; median; integer    |
| schema_type | The type of data in the schema (enums and strings not currently supported)                                       | datetime; integer; number; string; enum |
| mean        | Required if 'data_type' is 'mean', generates a random number from normal distribution centred on this number     | number                                  |
| sd          | Required if 'data_type' is 'mean', generates a random number from normal distribution with this as sd            | number                                  |
| median      | Required if 'data_type' is 'median', generates a random number from normal distribution centred on this number   | number                                  |
| first_quart | Required if 'data_type' is 'median', generates a random number from normal distribution using IQR to estimate sd | number                                  |
| third_quart | Required if 'data_type' is 'median', generates a random number from normal distribution using IQR to estimate sd | number                                  |
| proportion  | [NOT CURRENTLY USED] TODO: use this to select an appropriate proportion from enums                               | 0<x<1                                   |
| range_start | Required if 'data_type' is 'range', generates a random number between this number and 'range_end'                | number                                  |
| range_end   | Required if 'data_type' is 'range', generates a random number between 'range_end' and this number                | number                                  |
| source      | Reference where the information was found                                                                        | free text                               |
| enum        | [NOT CURRENTLY USED]                                                                                             |                                         |
