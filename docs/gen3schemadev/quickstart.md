# Quickstart

## Pre-requisites
- `python v3.9.5` or higher (`3.12.10` recommended; CI tests 3.9 through 3.12)
- `poetry v2.1.3` or higher
- `docker compose` (optional for dictionary visualisation)

*For detailed setup instructions [click here](../../docs/setup.md)*

## 1. Installation
- Follow the instructions [here](../../docs/setup.md)

## 2. Create the input_yaml template
- Learn how to create one [here](first_dictionary.md).
- You can also create a template starting file with the command below.
```bash
gen3schemadev init
# alternatively you can define the template file name
gen3schemadev init -o input_example.yaml
```

## 3. Generate Gen3 Schemas
- Will convert the input_yaml to a folder of gen3 schemas.
```bash
gen3schemadev generate -i input_example.yaml -o gen3_data_dictionary/
```

### 3.1 Running generate a second time
- `generate` never overwrites existing files by default. The first run above works because the
  folder is empty; run it again and it will stop and list what it would have replaced.
- This is deliberate. Those files may contain edits that your `input_yaml` knows nothing about, and
  the tool cannot tell whether you meant to keep them.
- Which flag you want depends on how your repository works:
```bash
# The input_yaml is the source of truth - regenerate from it every time
gen3schemadev generate -i input_example.yaml -o gen3_data_dictionary/ --input-driven

# Regenerate a single node, leaving every other file untouched
gen3schemadev generate -i input_example.yaml -o gen3_data_dictionary/ --only subject

# Overwrite everything - this discards any hand edits in the folder
gen3schemadev generate -i input_example.yaml -o gen3_data_dictionary/ --force
```
- *If you are not sure which of these you want, read [Running a Gen3 Dictionary Repository](dictionary_repo.md). It is short, and it saves a lot of confusion later.*

### 3.2 Further Gen3 Yaml Configuration (optional)
- This step is for advanced users that want to edit gen3 Json Schemas manually.
- This step provides advanced features and is how gen3 schemas are usually modified.
- You can learn more about how to modify gen3 schemas [here](../gen3_data_modelling/dictionary_structure.md).
- If you go down this path, the gen3 schemas become your source of truth rather than the
  `input_yaml`. Delete the `input_yaml` once you are done with it so it cannot mislead the next
  person — see [Bootstrap, then fork](dictionary_repo.md#bootstrap-then-fork).

### 3.3 Adding properties to program, project or core_metadata_collection
- These three nodes carry settings that other gen3 microservices rely on, so declaring one as an
  ordinary node rebuilds it from generic defaults and drops those settings.
- Use `extends` to add properties while inheriting everything else:
```yaml
nodes:
  - name: project
    extends: project
    properties:
      - name: institute_name
        description: "Institution leading the study."
        type: string
```

### 3.4 Checking a dictionary still matches its input
- `--check` regenerates in memory, compares against the folder, writes nothing, and exits non-zero
  if they disagree. This is the command to run in CI.
```bash
gen3schemadev generate -i input_example.yaml -o gen3_data_dictionary/ --check
```


## 4. Validate schema
- After you are happy with the folder of gen3 schemas, you can validate them using the `gen3schemadev validate` command.
- This will do two things, first it will do a validation against the [gen3 metaschema](../../src/gen3schemadev/schema/schema_templates/gen3_metaschema.yml) and secondly it will do business rule validation based on the logic in the [`rule_validator.py` module](../../src/gen3schemadev/validators/rule_validator.py) 
```bash
gen3schemadev validate -y gen3_data_dictionary
```

## 5. Bundle Schemas
- The next step is to bundle the gen3 schemas into a single `Gen3 Bundled Schema` (see definitions [here](../gen3_data_modelling/dictionary_structure.md)).
- This single bundled json file is what is used to deploy the model into gen3 via the `sheepdog` microservice. 
- We can also use this `Gen3 Bundled Schema` to visualise the data dictionary (described in the next step).
```bash
 gen3schemadev bundle -i gen3_data_dictionary -f gen3_data_dictionary/gen3_bundled_schema.json
```


## Visualise the `Gen3 Data Dictionary`
- Important: You must have `docker compose` installed on your system. To install, follow the instructions [here](https://docs.docker.com/compose/install/).
- To view what the `Gen3 Bundled Schema` looks like, we can use the `gen3schemadev visualize` command.
```bash
gen3schemadev visualise -i gen3_data_dictionary/gen3_bundled_schema.json
```


