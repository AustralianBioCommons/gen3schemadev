# Quickstart

## Pre-requisites
- `python v3.12.10` or higher
- `poetry v2.1.3` or higher
- `docker compose` (optional for dictionary visualisation)

## 1. Installation
```bash
pip install gen3schemadev
```

## 2. Create the input_yaml template
- Learn how to create one [here](first_dictionary.md).
- You can also create a template starting file with the command below.
```bash
gen3schemadev template -o input_example.yml
```

## 3. Generate Gen3 Schemas
- Will convert the input_yaml to a folder of gen3 schemas.
```bash
gen3schemadev generate -i tests/input_example.yml -o gen3_data_dictionary/
```

### 3.1 Further Gen3 Yaml Configuration (optional)
- This step is for advanced users that want to edit gen3 Json Schemas manually.
- This step provides advanced features and is how gen3 schemas are usually modified.
- You can learn more about how to modify gen3 schemas [here](../gen3_data_modelling/dictionary_structure.md).


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


