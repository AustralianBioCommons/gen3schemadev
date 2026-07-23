# Troubleshooting Input YAML Validation Errors

## Running `gen3schemadev generate` gives Pydantic errors

After filling out the `input_yaml` file with your intended data model, running the `gen3schemadev generate` command triggers validation of your file's structure. The tool checks that your `input_yaml` follows the correct format and adheres to all required rules before proceeding with dictionary generation. If your `input_yaml` contains errors such as missing fields, incorrect data types, or invalid values the tool uses the Pydantic library to halt execution and display a detailed error message. This message indicates precisely what needs to be corrected in your `input_yaml` file.

## What the Pydantic error looks Like

When validation fails, Pydantic generates a detailed error output that shows exactly where problems occurred. Here's the complete error output generated from the example input file [input_example_fail.yml](../../tests/input_example_fail.yml):

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

The following sections examine each error from [input_example_fail.yml](../../tests/input_example_fail.yml) and show how to fix them.

### Error 1: Invalid Version Format

**Error Message:**
```
version
  String should match pattern '^\d+\.\d+\.\d+$' [type=string_pattern_mismatch, input_value='v0.1.0', input_type=str]
```

**Location Path:** `version` → This refers to the top-level `version` field.

**Problematic YAML (from [input_example_fail.yml](../../tests/input_example_fail.yml)):**
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

**Problematic YAML (from [input_example_fail.yml](../../tests/input_example_fail.yml)):**
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

**Problematic YAML (from [input_example_fail.yml](../../tests/input_example_fail.yml)):**
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

**Problematic YAML (from [input_example_fail.yml](../../tests/input_example_fail.yml)):**
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

Beyond the four validation errors shown, [input_example_fail.yml](../../tests/input_example_fail.yml) contains other problems that may not trigger validation errors but will cause issues:

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


# Errors from `generate` itself

The errors above come from validating your `input_yaml`. These come from `generate` deciding what it
is allowed to do to your output folder.

## "Refusing to overwrite N existing files"

**Error message:** `Refusing to overwrite 14 existing files in dictionary/`

**Cause:** `generate` never overwrites existing files by default, because they may contain edits your
`input_yaml` knows nothing about. This is not a failure — it is the tool declining to guess.

**Fix:** pick the option that matches how your repository works. The message lists all four:

- `--input-driven` — your `input_yaml` is the source of truth, so regenerating is normal and safe
- `--only <node>` — regenerate one node, leaving every other file untouched
- delete the `input_yaml` and edit the gen3 schemas directly from now on
- `--force` — overwrite everything, **discarding any hand edits** in those files

If you are unsure, [Running a Gen3 Dictionary Repository](dictionary_repo.md) walks through the
choice. Guessing here is how people lose an afternoon of hand edits.

## "N files are not produced by this input"

**Error message:** `1 file in dictionary/ is not produced by this input`

**Cause:** the folder contains a gen3 schema that your `input_yaml` does not describe — usually a
node that was removed from the input, or one written by hand. It cannot be regenerated, but `bundle`
still includes it, so it ships in the `Gen3 Bundled Schema` and is deployed.

**Fix:** if it is a deliberate hand-written node, nothing is wrong and this stays a warning. If you
expected your input to produce it, either add the node back to the input or delete the file. Under
`--input-driven` this is an error rather than a warning, because that flag asserts the input
describes the whole dictionary.

## "does not match the dictionary generated from ..."

**Error message:** printed by `generate --check`, listing files as Changed, Missing or Orphaned.

**Cause:** the committed dictionary and the `input_yaml` have drifted apart. Each category has a
different fix:

- **Changed** — the file was hand-edited, or the input changed and nobody regenerated
- **Missing** — the input describes a node that is not in the folder, so it will not be deployed
- **Orphaned** — a file the input cannot produce, which still ships in the bundle

**Fix:** regenerate for Changed and Missing. For Orphaned, decide whether the node belongs in the
input or should be deleted. `--check` writes nothing, so it is always safe to run first.

## "is not valid YAML at line N"

**Error message:** `input_dd.yaml is not valid YAML at line 1031, column 11` followed by
`mapping values are not allowed here`

**Cause:** a punctuation slip. Overwhelmingly the most common one is a missing colon after a node
name — `- name_of_node` where `- name: name_of_node` was meant.

**Fix:** check the reported line and the few lines above it. YAML reports where parsing became
impossible, which can be slightly below the line actually at fault. This error is worth taking
seriously in CI: one repository committed exactly this typo and nobody noticed for weeks, because
the previously generated files were still present and looked healthy.

## "does not describe a valid data model"

**Error message:** a list of locations such as `nodes.0.category` with an explanation under each.

**Cause:** the file is valid YAML but does not match the input schema — a misspelled field name, a
missing required field, or a value outside the allowed set.

**Fix:** read the location as a path into your file, so `nodes.0.category` is the category of the
first node. Note that unknown field names are now rejected rather than ignored, so a typo like
`descriptoin` fails here instead of silently producing a schema with that field missing.

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

