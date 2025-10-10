# Troubleshooting Input YAML Validation Errors

## Running `gen3schemadev generate` gives Pydantic errors

After filling out the `input_yaml` file with your intended data model, running the `gen3schemadev generate` command triggers validation of your file's structure. The tool checks that your `input_yaml` follows the correct format and adheres to all required rules before proceeding with dictionary generation. If your `input_yaml` contains errors such as missing fields, incorrect data types, or invalid values the tool uses the Pydantic library to halt execution and display a detailed error message. This message indicates precisely what needs to be corrected in your `input_yaml` file.

## What the Pydantic error looks Like

When validation fails, Pydantic generates a detailed error output that shows exactly where problems occurred. Here's the complete error output generated from the example input file [input_example_fail.yml](../../examples/input/input_example_fail.yml):

```
Traceback (most recent call last):
  File "/Users/harrijh/projects/gen3schemadev/.venv/bin/gen3schemadev", line 6, in <module>
    sys.exit(main())
             ^^^^^^
  File "/Users/harrijh/projects/gen3schemadev/src/gen3schemadev/cli.py", line 110, in main
    validated_model = DataModel.model_validate(data)
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/harrijh/projects/gen3schemadev/.venv/lib/python3.12/site-packages/pydantic/main.py", line 705, in model_validate
    return cls.__pydantic_validator__.validate_python(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
pydantic_core._pydantic_core.ValidationError: 4 validation errors for DataModel
version
  String should match pattern '^\d+\.\d+\.\d+$' [type=string_pattern_mismatch, input_value='v0.1.0', input_type=str]
    For further information visit https://errors.pydantic.dev/2.11/v/string_pattern_mismatch
url
  Input should be a valid URL, relative URL without a base [type=url_parsing, input_value='link-to-data-portal', input_type=str]
    For further information visit https://errors.pydantic.dev/2.11/v/url_parsing
nodes.0.category
  Input should be 'administrative', 'analysis', 'biospecimen', 'clinical', 'data', 'data_bundle', 'data_file', 'index_file', 'metadata_file', 'notation', 'qc_bundle' or 'TBD' [type=enum, input_value='random_file', input_type=str]
    For further information visit https://errors.pydantic.dev/2.11/v/enum
links.0.multiplicity
  Input should be 'one_to_many', 'many_to_one', 'one_to_one' or 'many_to_many' [type=literal_error, input_value='one_to_heaps', input_type=str]
    For further information visit https://errors.pydantic.dev/2.11/v/literal_error
```

The traceback at the top shows where in the code the validation occurred, while the section after `ValidationError: 4 validation errors for DataModel` lists each specific problem found.

### Understanding Error Location Paths

Pydantic uses **dot notation** to specify where in the YAML structure each error occurs. This notation works like a roadmap to navigate through nested data structures. Here's how to interpret it.

- **Dots (`.`)** separate levels in the hierarchy
- **Numbers** indicate array/list positions, starting from 0 (zero-indexed)

**Examples:**

- `version` → The top-level field called "version"
- `nodes.0.category` → Find the `nodes` field, grab the **first** entry (index 0), then get its `category` value
- `links.0.multiplicity` → Find the `links` field, grab the **first** entry (index 0), then get its `multiplicity` value

Think of the numbers as counting positions in a list, where the first item is 0, the second is 1, and so on. So `nodes.0` means "the first item in the nodes list", and `nodes.1` would mean "the second item in the nodes list".

Each error entry contains several key components that help identify and fix issues:[15]

- **Field location**: Shows which field contains the error using dot notation
- **Error description**: A human-readable explanation of what's wrong
- **Error type**: A computer-readable identifier (e.g., `string_pattern_mismatch`, `enum`)
- **Input value**: The actual value provided that caused the error
- **Documentation link**: A URL to detailed information about that error type

## Breaking Down the Four Validation Errors

The following sections examine each error from [input_example_fail.yml](../../examples/input/input_example_fail.yml) and show how to fix them.

### Error 1: Invalid Version Format

**Error Message:**
```
version
  String should match pattern '^\d+\.\d+\.\d+$' [type=string_pattern_mismatch, input_value='v0.1.0', input_type=str]
```

**Location Path:** `version` → This refers to the top-level `version` field.

**Problematic YAML (from [input_example_fail.yml](../../examples/input/input_example_fail.yml)):**
```yaml
version: v0.1.0
```

**Problem:** The version string includes a leading `v`, but the validation pattern expects only digits and dots (e.g., `0.1.0`).

**Solution:**
```yaml
version: 0.1.0
```

***

### Error 2: Invalid URL Format

**Error Message:**
```
url
  Input should be a valid URL, relative URL without a base [type=url_parsing, input_value='link-to-data-portal', input_type=str]
```

**Location Path:** `url` → This refers to the top-level `url` field.

**Problematic YAML (from [input_example_fail.yml](../../examples/input/input_example_fail.yml)):**
```yaml
url: link-to-data-portal
```

**Problem:** The value is plain text rather than a properly formatted URL.

**Solution:**
```yaml
url: https://link-to-data-portal.example.com
```

***

### Error 3: Invalid Category Enum Value

**Error Message:**
```
nodes.0.category
  Input should be 'administrative', 'analysis', 'biospecimen', 'clinical', 'data', 'data_bundle', 'data_file', 'index_file', 'metadata_file', 'notation', 'qc_bundle' or 'TBD' [type=enum, input_value='random_file', input_type=str]
```

**Location Path:** `nodes.0.category` → Find the `nodes` field, go to the **first entry** (index 0), then locate the `category` field within that entry.

**Problematic YAML (from [input_example_fail.yml](../../examples/input/input_example_fail.yml)):**
```yaml
nodes:
- name: project          # This is nodes[0] - the first item
  description: Gen3 Compulsory Node
  category: random_file  # This is the problematic field
```

**Problem:** The value `random_file` is not one of the allowed category values. The error message lists all valid options, showing that only specific predefined values are accepted.

**Solution:**
```yaml
nodes:
- name: project
  description: Gen3 Compulsory Node
  category: administrative  # Changed to a valid enum value
```

***

### Error 4: Invalid Multiplicity Value

**Error Message:**
```
links.0.multiplicity
  Input should be 'one_to_many', 'many_to_one', 'one_to_one' or 'many_to_many' [type=literal_error, input_value='one_to_heaps', input_type=str]
```

**Location Path:** `links.0.multiplicity` → Find the `links` field, go to the **first entry** (index 0), then locate the `multiplicity` field within that entry.

**Problematic YAML (from [input_example_fail.yml](../../examples/input/input_example_fail.yml)):**
```yaml
links:
- parent: project          # This is links[0] - the first item
  multiplicity: one_to_heaps  # This is the problematic field
  child: sample
```

**Problem:** The value `one_to_heaps` is not a valid multiplicity option. Only the four values listed in the error message are accepted.

**Solution:**
```yaml
links:
- parent: project
  multiplicity: one_to_many  # Changed to a valid literal value
  child: sample
```

***

## Additional Issues in the Example YAML

Beyond the four validation errors shown, [input_example_fail.yml](../../examples/input/input_example_fail.yml) contains other problems that may not trigger validation errors but will cause issues:

**Typo in property key:**
```yaml
- name: sample
  proprties:  # Should be "properties"
```

**Incorrect data type:**
```yaml
- name: sample_id
  type: strings  # Should be "string" (singular)
```

***


# Best Practices for Avoiding Validation Errors

- **Check spelling carefully**: Ensure field names match the schema exactly (e.g., `properties` not `proprties`)
- **Review allowed values**: When using enums or restricted fields, verify values against the schema documentation
- **Validate data types**: Confirm that strings, numbers, and other types match requirements
- **Use YAML linting tools**: Tools like YAML Lint or IDE extensions can catch syntax errors before validation
- **Read error messages thoroughly**: Pydantic provides specific guidance about expected values and formats, including lists of valid options
- **Understand dot notation**: Learn to trace error paths through nested structures using dots and array indices
- **Check documentation links**: The URLs in error messages link to detailed explanations of each error type

***

This systematic approach helps identify validation errors, understand their root causes, and apply the correct fixes efficiently.

