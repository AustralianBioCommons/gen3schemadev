#!/bin/bash

# Function to display usage
usage() {
    cat <<EOF
Usage: $0 [options]

Options:
  -g GOOGLE_ID        Google Sheet ID (default: 1zjDBDvXgb0ydswFBwy47r2c8V1TFnpUj1jcG0xsY7ZI)
  -o OBJECTS_GID      GID for objects tab (default: 0)
  -l LINKS_GID        GID for links tab (default: 270346573)
  -p PROPERTIES_GID   GID for properties tab (default: 613332252)
  -e ENUMS_GID        GID for enums tab (default: 1807456496)
  -v                  Visualise the data dictionary in your browser after generation
  -h                  Show this help message and exit

Examples:
  # Run with default template Google Sheet
  $0

  # Run with custom Google Sheet and tab GIDs
  $0 -g "your_google_sheet_id" -o 0 -l 123456 -p 654321 -e 789012

  # Run and visualise the data dictionary
  $0 -v

Description:
  This script pulls a Gen3 data model schema from a Google Sheet, compiles it, validates it,
  and copies the resulting files to output directories. You can specify your own Google Sheet
  and tab GIDs, or use the defaults provided. Use -v to open the data dictionary visualisation
  in your browser after generation.

EOF
    exit 1
}

# Function to print error and exit
error_exit() {
    echo "ERROR: $1" >&2
    exit 1
}

# Default values
google_id='1zjDBDvXgb0ydswFBwy47r2c8V1TFnpUj1jcG0xsY7ZI'
objects_gid=0
links_gid=270346573
properties_gid=613332252
enums_gid=1807456496
visualise=0

# Parse arguments
while getopts ":g:o:l:p:e:vh" opt; do
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
    v) visualise=1
    ;;
    h) usage
    ;;
    *) usage
    ;;
  esac
done

# Get the directory where this script is located (not where it's run from)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ $? -ne 0 ]; then
    error_exit "Failed to determine script directory. Please check your environment."
fi
echo "Moving dir to $SCRIPT_DIR/.."
cd "$SCRIPT_DIR/.." || error_exit "Failed to change directory to $SCRIPT_DIR/.."

# Step 1: Pulling data schema from Google Sheets
echo "Pulling data schema from Google Sheets..."
rm -rf schema_out
python3 sheet2yaml-CLI.py \
    --google-id "$google_id" \
    --objects-gid "$objects_gid" \
    --links-gid "$links_gid" \
    --properties-gid "$properties_gid" \
    --enums-gid "$enums_gid" \
    --download \
    --output-dir 'output/schema/input_google_sheets'
if [ $? -ne 0 ]; then
    error_exit "Failed to pull data schema from Google Sheets. Please check your Google Sheet ID, GIDs, and network connection."
fi
echo "Data schema pulled successfully."

# Step 2: Moving schema_out to umccr-dictionary
echo "Moving schema_out to umccr-dictionary..."
mkdir -p umccr-dictionary/dictionary/schema_dev/gdcdictionary/schemas || error_exit "Failed to create target directory for schema files."
if ! cp schema_out/* umccr-dictionary/dictionary/schema_dev/gdcdictionary/schemas/ 2>/dev/null; then
    error_exit "Failed to copy schema files from schema_out to umccr-dictionary. Please ensure schema_out contains files and the target directory exists."
fi
ls -lsha umccr-dictionary/dictionary/schema_dev/gdcdictionary/schemas/
if [ $? -ne 0 ]; then
    error_exit "Failed to list schema files in umccr-dictionary. Please check permissions and directory structure."
fi
echo "Schema files moved successfully."

# Step 3: Compiling and bundling into JSON
echo "Compiling and bundling into JSON..."
cd umccr-dictionary || error_exit "Failed to change directory to umccr-dictionary. Please ensure the directory exists."
if ! make compile program=schema_dev; then
    error_exit "Compilation and bundling failed. Please check the output above for details and ensure all dependencies are installed."
fi
echo "Compilation and bundling completed."

# Step 4: Running Validation
echo "Running validation..."
if ! make validate program=schema_dev; then
    error_exit "Validation failed. Please check the output above for details."
fi
echo "Validation completed."

# Step 5: Copying files
cd .. || error_exit "Failed to return to project root directory."
echo "Step 5: Copying compiled schema and YAML files to output directories..."
mkdir -p output/schema/json || error_exit "Failed to create output/schema/json directory."
mkdir -p output/schema/yaml || error_exit "Failed to create output/schema/yaml directory."
echo "Copying JSON schema to output/schema/json/schema_dev.json..."
if ! cp umccr-dictionary/schema/schema_dev.json output/schema/json/schema_dev.json; then
    error_exit "Failed to copy schema_dev.json to output/schema/json/. Please ensure compilation was successful and the file exists."
fi
echo "Copying YAML schema files to output/schema/yaml/..."
if ! cp umccr-dictionary/dictionary/schema_dev/gdcdictionary/schemas/*.yaml output/schema/yaml/ 2>/dev/null; then
    error_exit "Failed to copy YAML schema files. Please ensure the source directory contains .yaml files."
fi
echo "All schema files have been successfully copied to the output/schema directory."

# Step 6: Visualizing data dictionary (optional)
if [ "$visualise" -eq 1 ]; then
  echo "Visualizing data dictionary..."
  if command -v open >/dev/null 2>&1; then
    open http://localhost:8080/#schema/schema_dev.json
    if [ $? -eq 0 ]; then
      echo "Data dictionary visualization opened in your default browser."
    else
      echo "WARNING: Tried to open browser but failed. Please open http://localhost:8080/#schema/schema_dev.json manually."
    fi
  else
    echo "WARNING: 'open' command not found. Please open http://localhost:8080/#schema/schema_dev.json manually in your browser."
  fi
fi
