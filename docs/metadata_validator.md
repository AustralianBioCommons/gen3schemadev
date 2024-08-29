# gen3validate.py Documentation

## Overview
This module provides classes and functions for validating JSON data against JSON schemas, resolving schema references, and combining synthetic data into a single JSON file. It includes utilities for timing function execution and visualizing validation errors.

## Classes

### `SchemaResolver`
Handles the resolution of JSON schema references and the combination of resolved schemas. This class is essential for breaking down bundled schemas into individual components, resolving internal and external references, and reassembling them into a coherent, resolved schema.

#### Methods
- **`__init__(self, bundle_json_path: str, unresolved_dir: str, resolved_output_dir: str, definitions_fn: str, terms_fn: str)`**
  - Initializes the `SchemaResolver` with paths for the bundle JSON, unresolved directory, resolved output directory, definitions file, and terms file.

- **`split_bundle_json(self, write_dir: str, return_dict: bool = False)`**
  - Splits the bundle JSON file into individual JSON files and saves them in the specified directory. Optionally returns a dictionary of the individual JSON files.

- **`read_json(self, json_path: str)`**
  - Reads a JSON file from the given path and returns the parsed JSON object.

- **`write_json(self, json_path: str, schema: dict)`**
  - Writes a JSON schema to the specified path.

- **`resolve_references(self, schema, ref_path: str)`**
  - Recursively resolves references in a JSON node. This method is crucial for ensuring that all `$ref` pointers in the schema are replaced with the actual referenced content.

- **`redefine_ref_path(self, match_str: str, replace_str: str, schema: dict)`**
  - Recursively replaces `$ref` paths in a JSON schema. This is useful for updating reference paths to point to the correct files.

- **`resolve_refs(self, schema_path: str, reference_path: str)`**
  - Resolves references in a JSON schema file using definitions from another JSON file.

- **`move_resolved_schemas(self, source_dir: str, target_dir: str)`**
  - Moves resolved schemas to a new directory.

- **`resolve_schemas(self)`**
  - Splits the bundled JSON and writes individual JSON nodes, then resolves references in the definition file and other schemas.

- **`combine_resolved_schemas(self, resolved_dir, output_dir, output_filename='schema_dev_resolved.json')`**
  - Combines all resolved JSON schemas into a single bundled JSON file.

### `SchemaValidatorSynth`
Specifically designed for the validation of synthetic data created by UMCCR (University of Melbourne Centre for Cancer Research). This class validates a list of data objects against a JSON schema and provides detailed error reporting and visualization.

#### Methods
- **`__init__(self, schema_fn: str, data: list)`**
  - Initializes the `SchemaValidatorSynth` with a schema filename and a list of data objects.

- **`read_schema(self)`**
  - Reads the JSON schema from the specified file.

- **`validate_schema(self)`**
  - Validates the JSON schema against the data objects. Returns a dictionary containing the number of successful and failed validations, error messages, and log messages.

- **`print_errors(self)`**
  - Prints the error messages from the validation results.

- **`return_errors(self)`**
  - Returns the error messages from the validation results as a JSON string.

- **`print_summary(self)`**
  - Prints a summary of the validation results, including the total number of data objects, successful validations, and failed validations.

- **`plot_invalid_keys(self)`**
  - Plots the frequency of invalid keys from the validation results, providing a visual representation of the most common validation errors.

### `QuickValidateSynth`
Performs quick validation of JSON files in a directory against resolved schemas. This class is useful for rapidly checking the validity of multiple JSON files, especially in a development or testing environment.

#### Methods
- **`__init__(self, data_dir: str, project_name_list: list, resolved_schema_dir: str, exclude_nodes: list = None)`**
  - Initializes the `QuickValidateSynth` with the data directory, project names, resolved schema directory, and optional nodes to exclude.

- **`generate_json_paths(self, project_name: str) -> list`**
  - Generates a list of JSON paths based on the data directory and project name.

- **`read_single_json(self, json_path: str) -> list`**
  - Reads a single JSON file from the given path and returns it as a list of data objects.

- **`extract_node_names(self, json_paths: list) -> list`**
  - Extracts node names from the given list of JSON file paths using regex.

- **`extract_node_name(self, json_path: str) -> str`**
  - Extracts the filename without extension from a given file path.

- **`get_schema_fn(self, node_name: str) -> str`**
  - Constructs the schema filename for a given node name.

- **`quick_validate(self)`**
  - Performs quick validation of JSON files against resolved schemas and stores errors.

### `SyntheticDataCombiner`
Combines synthetic data from multiple JSON files into a single JSON file. This class is particularly useful for merging data from different sources or experiments into a unified dataset.

#### Methods
- **`__init__(self, input_dir, exclude_files=None)`**
  - Initializes the `SyntheticDataCombiner` with the input directory and optional files to exclude.

- **`json_files_to_dataframes(self)`**
  - Reads JSON files from a directory, converts them to pandas DataFrames, and stores the DataFrames in a list.

- **`bind_dataframes_by_column(self, dataframes_list, remove_duplicates=False)`**
  - Binds a list of pandas DataFrames by columns.

- **`dataframe_to_json(self, df, output_file)`**
  - Converts a pandas DataFrame to a JSON file with each row as an object in an array.

### `SchemaValidatorDataFrame`
Validates a DataFrame against a JSON schema and reports validation results. This class is useful for validating tabular data that has been converted to JSON format.

#### Methods
- **`__init__(self, data: list, schema_fn: str)`**
  - Initializes the `SchemaValidatorDataFrame` with data and a schema filename.

- **`read_schema(self)`**
  - Reads the JSON schema from the specified file.

- **`validate_schema(self)`**
  - Validates the JSON schema against the data objects and returns validation results and metrics.

- **`print_errors(self)`**
  - Prints the error messages from the validation results.

- **`return_errors(self)`**
  - Returns the error messages from the validation results as a JSON string.

- **`print_summary(self)`**
  - Prints a summary of the validation results, including the total number of data objects, successful validations, and failed validations.

- **`plot_invalid_keys(self)`**
  - Plots the frequency of invalid keys from the validation results, providing a visual representation of the most common validation errors.

### `ValidationReporter`
Reports validation results from a CSV file against a schema. This class reads data from a CSV file, validates it against a given schema, and transforms the validation results into a specific format for reporting.

#### Methods
- **`__init__(self, csv_path, schema_path, n_rows=None)`**
  - Initializes the `ValidationReporter` with the CSV path, schema path, and optional number of rows to read.

- **`csv_to_json(self)`**
  - Reads data from the CSV file and converts it to JSON format.

- **`transform_validate_df(self)`**
  - Transforms the validation DataFrame into a specific format for reporting.

- **`write_df(self, output_dir, project_id)`**
  - Writes the validation DataFrame to a CSV file in the specified output directory.

## Decorators

### `timeit`
A decorator to measure the execution time of functions. This is useful for profiling and optimizing performance.

#### Usage
```python
@timeit
def some_function():
    # function implementation
```

## Example Usage

### Resolving Schemas
```python
resolver = SchemaResolver(
    bundle_json_path='path/to/bundle.json',
    unresolved_dir='path/to/unresolved',
    resolved_output_dir='path/to/resolved',
    definitions_fn='_definitions.json',
    terms_fn='_terms.json'
)
resolver.resolve_schemas()
```

### Validating Synthetic Data
```python
data = [...]  # List of synthetic data objects
validator = SchemaValidatorSynth(schema_fn='path/to/schema.json', data=data)
validator.print_summary()
validator.plot_invalid_keys()
```

### Quick Validation
```python
quick = QuickValidateSynth(
    data_dir='path/to/data',
    project_name_list=['Project1', 'Project2'],
    resolved_schema_dir='path/to/resolved_schemas'
)
quick.quick_validate()
```

### Combining Synthetic Data
```python
combiner = SyntheticDataCombiner(input_dir='path/to/input')
dataframes = combiner.json_files_to_dataframes()
combined_df = combiner.bind_dataframes_by_column(dataframes, remove_duplicates=True)
combiner.dataframe_to_json(combined_df, 'path/to/output.json')
```

### Reporting Validation Results
```python
reporter = ValidationReporter(csv_path='path/to/data.csv', schema_path='path/to/schema.json')
reporter.write_df(output_dir='path/to/output', project_id='ProjectID')
```

This documentation provides an overview of the classes and methods available in the `gen3validate.py` module, along with example usage to help you get started.