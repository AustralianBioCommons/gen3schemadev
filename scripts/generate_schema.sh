#!/bin/bash

# Function to display usage
usage() {
    echo "Usage: $0 [-g google_id] [-o objects_gid] [-l links_gid] [-p properties_gid] [-e enums_gid]"
    exit 1
}

# Default values
google_id='1zjDBDvXgb0ydswFBwy47r2c8V1TFnpUj1jcG0xsY7ZI'
objects_gid=0
links_gid=270346573
properties_gid=613332252
enums_gid=1807456496

# Parse arguments
while getopts ":g:o:l:p:e:" opt; do
  case $opt in
    g) google_id="$OPTARG"
    ;;
    o) objects_gid="$OPTARG"
    ;;
    l) links_gid="$OPTARG"
    ;;
    p) properties_gid="$OPTARG"
    ;;
    e) enums_gid="$OPTARG"
    ;;
    *) usage
    ;;
  esac
done

# Step 1: Pulling data schema from Google Sheets
echo "Pulling data schema from Google Sheets..."
rm -rf schema_out
python3 sheet2yaml-CLI.py --google-id "$google_id" --objects-gid "$objects_gid" --links-gid "$links_gid" --properties-gid "$properties_gid" --enums-gid "$enums_gid"
echo "Data schema pulled successfully."

# Step 2: Moving schema_out to umccr-dictionary
echo "Moving schema_out to umccr-dictionary..."
mkdir -p umccr-dictionary/dictionary/schema_dev/gdcdictionary/schemas
cp schema_out/* umccr-dictionary/dictionary/schema_dev/gdcdictionary/schemas/
ls -lsha umccr-dictionary/dictionary/schema_dev/gdcdictionary/schemas/
echo "Schema files moved successfully."

# Step 3: Compiling and bundling into JSON
echo "Compiling and bundling into JSON..."
cd umccr-dictionary && make compile program=schema_dev
echo "Compilation and bundling completed."

# Step 4: Running Validation
echo "Running validation..."
make validate program=schema_dev
echo "Validation completed."

# Step 5: Visualizing data dictionary
echo "Visualizing data dictionary..."
open http://localhost:8080/#schema/schema_dev.json
echo "Data dictionary visualization opened."
