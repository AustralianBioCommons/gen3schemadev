#!/bin/bash

# Function to display usage
usage() {
    echo "Usage: $0 -s <schema_path> [-v]"
    echo "  -s <schema_path>  Path to the schema file"
    echo "  -v                Visualize the data dictionary"
    exit 1
}

# Parse arguments
VISUALIZE=false
while getopts ":s:v" opt; do
    case ${opt} in
        s )
            SCHEMA_PATH=$OPTARG
            ;;
        v )
            VISUALIZE=true
            ;;
        \? )
            usage
            ;;
    esac
done

# Check if schema path is provided
if [ -z "$SCHEMA_PATH" ]; then
    usage
fi

# Create directory and copy schema
mkdir -p ./umccr-dictionary/dictionary/schema_dev/gdcdictionary/schemas
cp "$SCHEMA_PATH" ./umccr-dictionary/dictionary/schema_dev/gdcdictionary/schemas/schema_dev.json
ls -lsha ./umccr-dictionary/dictionary/schema_dev/gdcdictionary/schemas/

# Running Validation
cd ./umccr-dictionary && make validate program=schema_dev

# Visualizing data dictionary if -v is given
if [ "$VISUALIZE" = true ]; then
    open http://localhost:8080/#schema/schema_dev.json
fi