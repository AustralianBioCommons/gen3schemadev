# Troubleshooting Input YAML Validation Errors

## What Is Data Validation and Why Does It Matter?

Think of data validation as a quality control checkpoint for information entering a system. Just as a form might require an email address to contain an "@" symbol, or a date to be in a specific format, validation ensures that data meets certain rules before it's processed.[10][11][12][13]

In this context, the Pydantic library acts as an automated checker that reads the YAML file and compares it against a predefined set of rules (called a schema). This schema acts as a blueprint, specifying what format, structure, and data types are expected. If the data doesn't match these rules—for example, if a URL is missing, or a category uses an invalid value—Pydantic stops the process and provides detailed feedback about what went wrong.[12][13][14][15]

This prevents errors from propagating through the system and helps maintain data quality and consistency. Rather than discovering problems later when the data is being used, validation catches issues immediately, making them easier to identify and fix.[11][16][12]

## What a Full Validation Error Looks Like

When validation fails, Pydantic generates a detailed error output that shows exactly where problems occurred. Here's the complete error output generated from the example input file [input_example_fail.yml](../../examples/input/input_example_fail.yml):[15]

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
entities.0.category
  Input should be 'administrative', 'analysis', 'biospecimen', 'clinical', 'data', 'data_bundle', 'data_file', 'index_file', 'metadata_file', 'notation', 'qc_bundle' or 'TBD' [type=enum, input_value='random_file', input_type=str]
    For further information visit https://errors.pydantic.dev/2.11/v/enum
links.0.multiplicity
  Input should be 'one_to_many', 'many_to_one', 'one_to_one' or 'many_to_many' [type=literal_error, input_value='one_to_heaps', input_type=str]
    For further information visit https://errors.pydantic.dev/2.11/v/literal_error
```

The traceback at the top shows where in the code the validation occurred, while the section after `ValidationError: 4 validation errors for DataModel` lists each specific problem found.[15]

### Understanding Error Location Paths

Pydantic uses **dot notation** to specify where in the YAML structure each error occurs. This notation works like a roadmap to navigate through nested data structures. Here's how to interpret it:[1][3]

- **Dots (`.`)** separate levels in the hierarchy[1]
- **Numbers** indicate array/list positions, starting from 0 (zero-indexed)[3]

**Examples:**

- `version` → The top-level field called "version"
- `entities.0.category` → Find the `entities` field, grab the **first** entry (index 0), then get its `category` value[3]
- `links.0.multiplicity` → Find the `links` field, grab the **first** entry (index 0), then get its `multiplicity` value[3]

Think of the numbers as counting positions in a list, where the first item is 0, the second is 1, and so on. So `entities.0` means "the first item in the entities list", and `entities.1` would mean "the second item in the entities list".[3]

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

**Location Path:** `version` → This refers to the top-level `version` field.[15]

**Problematic YAML (from [input_example_fail.yml](../../examples/input/input_example_fail.yml)):**
```yaml
version: v0.1.0
```

**Problem:** The version string includes a leading `v`, but the validation pattern expects only digits and dots (e.g., `0.1.0`).[15]

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

**Location Path:** `url` → This refers to the top-level `url` field.[15]

**Problematic YAML (from [input_example_fail.yml](../../examples/input/input_example_fail.yml)):**
```yaml
url: link-to-data-portal
```

**Problem:** The value is plain text rather than a properly formatted URL.[13]

**Solution:**
```yaml
url: https://link-to-data-portal.example.com
```

***

### Error 3: Invalid Category Enum Value

**Error Message:**
```
entities.0.category
  Input should be 'administrative', 'analysis', 'biospecimen', 'clinical', 'data', 'data_bundle', 'data_file', 'index_file', 'metadata_file', 'notation', 'qc_bundle' or 'TBD' [type=enum, input_value='random_file', input_type=str]
```

**Location Path:** `entities.0.category` → Find the `entities` field, go to the **first entry** (index 0), then locate the `category` field within that entry.[3]

**Problematic YAML (from [input_example_fail.yml](../../examples/input/input_example_fail.yml)):**
```yaml
entities:
- name: project          # This is entities[0] - the first item
  description: Gen3 Compulsory Node
  category: random_file  # This is the problematic field
```

**Problem:** The value `random_file` is not one of the allowed category values. The error message lists all valid options, showing that only specific predefined values are accepted.[14]

**Solution:**
```yaml
entities:
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

**Location Path:** `links.0.multiplicity` → Find the `links` field, go to the **first entry** (index 0), then locate the `multiplicity` field within that entry.[3]

**Problematic YAML (from [input_example_fail.yml](../../examples/input/input_example_fail.yml)):**
```yaml
links:
- parent: project          # This is links[0] - the first item
  multiplicity: one_to_heaps  # This is the problematic field
  child: sample
```

**Problem:** The value `one_to_heaps` is not a valid multiplicity option. Only the four values listed in the error message are accepted.[14]

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

## Best Practices for Avoiding Validation Errors

- **Check spelling carefully**: Ensure field names match the schema exactly (e.g., `properties` not `proprties`)[12]
- **Review allowed values**: When using enums or restricted fields, verify values against the schema documentation[14]
- **Validate data types**: Confirm that strings, numbers, and other types match requirements[16]
- **Use YAML linting tools**: Tools like YAML Lint or IDE extensions can catch syntax errors before validation[12]
- **Read error messages thoroughly**: Pydantic provides specific guidance about expected values and formats, including lists of valid options[14][15]
- **Understand dot notation**: Learn to trace error paths through nested structures using dots and array indices[1][3]
- **Check documentation links**: The URLs in error messages link to detailed explanations of each error type[15]

***

This systematic approach helps identify validation errors, understand their root causes, and apply the correct fixes efficiently.[12][14][15]

[1](https://stackoverflow.com/questions/39463936/python-accessing-yaml-values-using-dot-notation)
[2](https://community.home-assistant.io/t/dot-period-at-start-of-line-in-yaml-not-a-yaml-feature-so-what-does-it-do/822330)
[3](https://spacelift.io/blog/yaml)
[4](https://yaml.org/spec/1.2.2/)
[5](https://github.com/ansible/ansible/issues/71661)
[6](https://www.reddit.com/r/ansible/comments/1dcgk22/convert_yamldotnotation_to_python_dictsyntax/)
[7](https://mikefarah.gitbook.io/yq/v3.x/usage/path-expressions)
[8](https://github.com/roboll/helmfile/issues/936)
[9](https://www.commonwl.org/user_guide/topics/yaml-guide.html)
[10](https://www.tibco.com/glossary/what-is-data-validation)
[11](https://www.informatica.com/services-and-training/glossary-of-terms/data-validation-definition.html)
[12](https://www.rudderstack.com/learn/data-collection/validation-of-data-collection/)
[13](https://www.techtarget.com/searchdatamanagement/definition/data-validation)
[14](https://www.packetcoders.io/what-is-schema-validation/)
[15](https://betterstack.com/community/guides/scaling-python/pydantic-explained/)
[16](https://corporatefinanceinstitute.com/resources/data-science/data-validation/)