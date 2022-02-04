#This folder contains all scripts used to automate the development and data deployment process for gen3

##build_for_ecr.sh
this script will build both amd64 and arm64 versions using the dockerfile present and upload them to biocommons aws ECR. make sure you authenticated your local docker using login-docker.sh before running this script.
```shell
build_for_ecr.sh data_portal:2022.01
```

##login-docker.sh
This script will login the local docker instance to AWS ECR. your local aws client needs to be setup and have access rights to ECR for this script to work.
```shell
login-docker.sh
```

##publish_schema.sh
This script will take a schema from schemadev, compile the yaml into a json, create simulated data, deploy it to the local docker instance
after testing locally, the script will be uploaded to the cloud folder. After the script has completed gen3 needs to be reset on the server.

```shell
publish_schema.sh
```

#simulate_data.sh
This script will simulate data for a schema using plausible data gen. 

```shell
simulate_data.sh
```