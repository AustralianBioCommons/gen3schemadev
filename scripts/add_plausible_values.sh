#!/bin/bash

# This script generates plausible data using umccr-data-simulator JSONs, reads a Google Sheets URL with plausible values, and copies the generated data to an output directory.

# Function to display usage information
usage() {
    echo "Usage: $0 -i <input_json_path> -g <google_sheets_url> -s <study_id> -o <output_dir>"
    echo "  -i <input_json_path>     Path to the input JSON directory to be used for data generation."
    echo "  -g <google_sheets_url>   URL of the Google Sheets document to be used for data generation."
    echo "  -s <study_id>            Study ID to be used for the data generation (e.g., AusDiab)."
    echo "  -o <output_dir>          Path to the output directory where the generated data will be copied."
    exit 1
}

# Parse command-line arguments
while getopts ":i:g:s:o:" opt; do
    case ${opt} in
        i )
            INPUT_PATH=$OPTARG
            ;;
        g )
            GURL=$OPTARG
            ;;
        s )
            STUDY_ID=$OPTARG
            ;;
        o )
            OUTPUT_DIR=$OPTARG
            ;;
        \? )
            usage
            ;;
    esac
done

# Check if all arguments are provided
if [ -z "$INPUT_PATH" ] || [ -z "$GURL" ] || [ -z "$STUDY_ID" ] || [ -z "$OUTPUT_DIR" ]; then
    usage
fi

# Combine INPUT_PATH and STUDY_ID to form the final path
INPUT_FINAL_PATH="${INPUT_PATH}/${STUDY_ID}/"

# Check if JSON files are present in the input final path
if [ ! -d "$INPUT_FINAL_PATH" ] || [ -z "$(ls -A $INPUT_FINAL_PATH/*.json 2>/dev/null)" ]; then
    echo "No JSON files found in the input final path: $INPUT_FINAL_PATH"
    exit 1
fi


# Run plausible data generation
echo "Running plausible data generation..."
echo "current dir = $(pwd)"
echo "input final path = $INPUT_FINAL_PATH"

if [ -f "gen3schemadev/plausible_data_gen.py" ]; then
    cd gen3schemadev && python3 plausible_data_gen.py --path ../$INPUT_FINAL_PATH --gurl $GURL
elif [ -f "plausible_data_gen.py" ]; then
    python3 plausible_data_gen.py --path $INPUT_FINAL_PATH --gurl $GURL
else
    echo "plausible_data_gen.py not found in expected locations."
    exit 1
fi


# Check if the plausible data generation was successful
if [ $? -ne 0 ]; then
    echo "Plausible data generation failed."
    exit 1
fi

# Create the output directory if it doesn't exist
mkdir -p ${OUTPUT_DIR}/${STUDY_ID}

# Copy the generated data to the output directory
echo "Copying generated data to the output directory ${OUTPUT_DIR}/${STUDY_ID}/"
cp -r ./edited_jsons/${STUDY_ID}/* ${OUTPUT_DIR}/${STUDY_ID}/

# Copy DataImportOrder.txt to the output directory
if [ -f "../${INPUT_FINAL_PATH}/DataImportOrder.txt" ]; then
    echo "Copying DataImportOrder.txt to the output directory ${OUTPUT_DIR}/${STUDY_ID}/"
    cp ../${INPUT_FINAL_PATH}/DataImportOrder.txt ${OUTPUT_DIR}/${STUDY_ID}/
else
    echo "DataImportOrder.txt not found in the input final path: ${INPUT_FINAL_PATH}"
fi

# Remove the temporary edited_jsons directory
rm -r ./edited_jsons

if [ $? -eq 0 ]; then
    echo "=== SUCCESS ==="
else
    echo "=== WARNING: Check for Errors ==="
fi
