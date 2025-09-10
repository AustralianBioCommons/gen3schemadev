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
echo "Moving dir to $SCRIPT_DIR/.."
cd "$SCRIPT_DIR/.."


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

# Step 5: Copying files
cd ..
echo "Step 5: Copying compiled schema and YAML files to output directories..."
mkdir -p output/schema/json
mkdir -p output/schema/yaml
echo "Copying JSON schema to output/schema/json/schema_dev.json..."
cp umccr-dictionary/schema/schema_dev.json output/schema/json/schema_dev.json
echo "Copying YAML schema files to output/schema/yaml/..."
cp umccr-dictionary/dictionary/schema_dev/gdcdictionary/schemas/*.yaml output/schema/yaml/
echo "All schema files have been successfully copied to the output/schema directory."

# Step 6: Visualizing data dictionary (optional)
if [ "$visualise" -eq 1 ]; then
  echo "Visualizing data dictionary..."
  open http://localhost:8080/#schema/schema_dev.json
  echo "Data dictionary visualization opened."
fi
