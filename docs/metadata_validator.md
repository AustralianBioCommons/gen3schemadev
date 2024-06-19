# Metadata Validator

This guide explains how to use the [gen3schemadev](gen3schemadev/) library to validate specifically gen3 metadata against JSON schemas. The classes for the metadata validator are in the [gen3validate.py](gen3schemadev/gen3schemadev/gen3validate.py) script, where there are two main classes `SchemaResolver` and `SchemaValidator`

## How it works:

### `SchemaResolver`
1. A bundled json containing all the schemas for each node is loaded and separated back into individual .json files
1. All references ('$ref') in \_definitions.json (formally \_definitions.yaml) are resolved using both internal references and external references in \_terms.json
1. The fully resolved '\_definitions\_\[resolved\].json' is then used to fully resolve all other schemas

### `SchemaValidator`
1. A SchemaValidator class is created by parsing a list of data objects (multiple dicts in a list) and a resolved schema
1. The SchemaValidator class will then validate the data agains the schema
1. The SchemaValidator will save data validation stats, along with error messages for each data object
1. The SchemaValidator also has a function to plot the frequency of invalid keys so you can identify which ones need fixing


## Prerequisites

Ensure you have the necessary libraries installed:
```bash
pip install jsonschema pyyaml
```

## Step-by-Step Instructions

### 1. Refresh the `gen3schemadev` Library

First, refresh the `gen3schemadev` library to ensure you are using the latest version:
```python
import importlib
import gen3schemadev
importlib.reload(gen3schemadev)
import os
import shutil
```

### 2. Prepare the Output Directory

Create an output directory for unresolved schemas. If the directory already exists, it will be removed and recreated:
```python
output_dir = '../output/schema/json/unresolved'
if os.path.exists(output_dir):
    shutil.rmtree(output_dir, ignore_errors=True)
os.makedirs(output_dir, exist_ok=True)
```

### 3. Initialize the `SchemaResolver`

Initialize the `SchemaResolver` with the base path and the path to the bundled JSON file:
```python
resolver = gen3schemadev.gen3validate.SchemaResolver(
    base_path=output_dir, 
    bundle_json_path='../output/schema/json/schema_dev.json'
)
```

### 4. Split the Bundled JSON

Split the bundled JSON into individual JSON files:
```python
resolver.split_bundle_json(write_dir=output_dir)
```

### 5. Resolve the Definition File

Resolve the references in the `_definitions.json` file using `_terms.json`:
```python
resolver.resolve_refs('_definitions.json', reference_fn='_terms.json')
```

### 6. Resolve the other Schemas

Resolve references in other JSON schemas using the resolved definition file:
```python
jsonfn = [fn for fn in os.listdir(output_dir) if not fn.startswith('_')]
refFn = '_definitions_[resolved].json'
for fn in jsonfn:
    print(fn)
    resolver.resolve_refs(fn, refFn)
```

### 7. Move Resolved Schemas

Move the resolved schemas to a new directory:
```python
target_dir = os.path.join(output_dir, '../resolved')
os.makedirs(target_dir, exist_ok=True)
resolver.move_resolved_schemas(target_dir=target_dir)
```

### 8. Validate Example Data

Prepare example data to validate:
```python
data_to_validate = [
    {
        "baseline_age": 44.551604483338444,
        "bmi_baseline": 69.49984415734117,
        "education": "some high school",
    },
    {
        "baseline_age": 30.123456789012345,
        "bmi_baseline": 22.345678901234567,
        "education": "bachelor's degree",
    },
    {
        "baseline_age": 55.987654321098765,
        "bmi_baseline": 27.123456789012345,
        "education": "master's degree",
    },
    {
        "baseline_age": 40.567890123456789,
        "bmi_baseline": 31.234567890123456,
        "education": "high school graduate",
    },
]
```

### 9. Alternate data preperation

Alternatively you can use the read_json method in the resolver to load a data list
```python
data = resolver.read_json('../../../synthetic_data/raw_gen3schemadev/AusDiab/demographic.json')
```

### 10. Run Validation

Initialize the `SchemaValidator` and run the validation:
```python
validator = gen3schemadev.gen3validate.SchemaValidator(
    data=data, 
    schema_fn='../output/schema/json/resolved/demographic_[resolved].json'
)
```

### 11. Print Summary and Errors

Print the validation summary and error messages:
```python
validator.print_summary()
validator.print_errors()
```

### 12. Plot Invalid Keys

Plot a summary of invalid keys:
```python
validator.plot_invalid_keys()
```

By following these steps, you can validate your metadata against the appropriate JSON schemas, ensuring that all references are correctly resolved.