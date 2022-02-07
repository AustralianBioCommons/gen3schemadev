# This folder contains all scripts used to automate the development and data deployment process for gen3

## build_for_ecr.sh
this script will build both amd64 and arm64 versions using the dockerfile present and upload them to biocommons aws ECR. make sure you authenticated your local docker using login-docker.sh before running this script.
```shell
build_for_ecr.sh data_portal:2022.01
```

## login-docker.sh
This script will login the local docker instance to AWS ECR. your local aws client needs to be setup and have access rights to ECR for this script to work.
```shell
login-docker.sh
```

## new_dict_and_data.sh
This script automates the steps involved in
1. updating the cad data dictionary from the Harmonised Variables google sheet
2. simulating metadata and replacing with plausible values
3. generating dummy sequencing and lipidomics files
4. uploading the new dictionary to aws for local testing
5. Stops so you can check local deployment
6. uploading the new dictionary to the production aws s3
7. Stops so you can reset the instance with the new dictionary
8. uploads all metadata and data files to the production instance

### Prerequisites 
- Docker must be installed and running before starting the script
- The script assumes you have a virtual environment called `venv` in this git repo
The following need to be configured in the script 
- `UMCCR_SCHEMA_INSTALLATION` - the location where you have cloned the [`umccr-dictionary` repo](https://github.com/umccr/umccr-dictionary)
- `SCHEMADEV_INSTALLATION` - The location of this repo
- `COMPOSE_SERVICES_INSTALLATION` - The location of your clone of the [`compose-services` repo](https://github.com/uc-cdis/compose-services)
- `projects` - A space delimited list of the names of the projects you want to simulate and upload data for e.g. `"AusDiab FIELD""`
- `num_samples` - The number of objects you want to generate for each node in the data dictionary
- `profile` - The name of your pre-configured profile for the [gen3 command line tool](https://gen3.org/resources/user/gen3-client/#3-upload-data-files)

## publish_schema.sh
This script will take a schema from schemadev, compile the yaml into a json, create simulated data, deploy it to the local docker instance
after testing locally, the script will be uploaded to the cloud folder. After the script has completed gen3 needs to be reset on the server.

```shell
publish_schema.sh
```

## simulate_data.sh
This script will simulate data for a schema using plausible data gen. 

```shell
simulate_data.sh
```