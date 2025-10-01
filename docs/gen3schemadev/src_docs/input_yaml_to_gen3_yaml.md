# Usage: Converting Input YAML to Gen3 YAML

This guide demonstrates how to use the Gen3 Schema Dev tools to convert a custom input YAML schema into a Gen3-compatible YAML schema.

## Prerequisites

- Python environment with the `gen3schemadev` package installed (from your local `src/` directory).
- Input YAML file (e.g., `tests/input_example.yml`).
- Gen3 metaschema YAML file (e.g., `src/gen3schemadev/schema/gen3_metaschema.yml`).

## Example Code

```python
from gen3schemadev.schema.gen3_template import *
from gen3schemadev.utils import *
from gen3schemadev.schema.input_schema import DataModel
from gen3schemadev.converter import *

# Load the Gen3 metaschema template
metaschema_path = "../src/gen3schemadev/schema/gen3_metaschema.yml"
converter_template = generate_gen3_template(metaschema_path)

# Load and validate the input YAML data model
data = load_yaml('../tests/input_example.yml')
validated_model = DataModel.model_validate(data)

# Populate the Gen3 template with the validated model
out_template = populate_template('lipidomics_file', validated_model, converter_template)

# Write the output to a YAML file
write_yaml(out_template, 'output.yml')
```

## Step-by-Step Instructions

1. **Import Required Modules**  
   Import the necessary functions and classes from the `gen3schemadev` package.

2. **Load the Gen3 Metaschema Template**  
   Use `generate_gen3_template()` to load the Gen3 metaschema, which serves as the base for your output.

3. **Load and Validate Input YAML**  
   - Use `load_yaml()` to read your custom input YAML file.
   - Validate the loaded data using `DataModel.model_validate()` to ensure it matches the expected schema.

4. **Populate the Gen3 Template**  
   Use `populate_template()` to fill the Gen3 template with your validated data model.  
   - The first argument is the node name (e.g., `'lipidomics_file'`).

5. **Write the Output YAML**  
   Use `write_yaml()` to save the populated template to an output file (e.g., `output.yml`).

## Output

- The resulting file (`output.yml`) will be a Gen3-compatible YAML schema, ready for use in Gen3 data commons.

## Notes

- Adjust file paths as needed depending on your working directory.
- The node name (`'lipidomics_file'`) should match the node you want to generate in your schema.

---
