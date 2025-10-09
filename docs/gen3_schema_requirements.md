# Gen3 Schema Requirements

This document outlines the business requirements for a Gen3 data dictionary.

Note: A single jsonschema represents a single entity in the data model. Multiple jsonschemas, representing multiple nodes are bundled into a list of jsonschemas and saved to a single json file. This json file is called a gen3 bundled jsonschema, and is uploaded to to sheepdog to deploy the data model.

## Examples

## Summary of Gen3 Schema Keys
- *Note:* Yaml examples of this table can be found [here](../tests/gen3_schema/examples/yaml/lipidomics_file.yaml).

| schema key           | description                                                                                 | required user input | specificity | default value                                                     | data type                                                                                                                     |
| -------------------- | ------------------------------------------------------------------------------------------- | ------------------- | ----------- | ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| id                   | Unique identifier for the entity                                                            | yes                 | jsonschema  | n/a                                                               | String                                                                                                                        |
| title                | Name of the entity                                                                          | yes                 | jsonschema  | n/a                                                               | String                                                                                                                        |
| category             | Classification of entity                                                                    | yes                 | gen3        | n/a                                                               | Enum `['administrative', 'index_file', 'biospecimen', 'clinical', 'notation', 'data_file', 'analysis', 'experimental_methods']`|
| description          | Description of the schema                                                                   | yes                 | jsonschema  | n/a                                                               | String                                                                                                                        |
| links                | Array of objects that describe links to other nodes                                      | yes                 | gen3        | n/a                                                               | Array                                                                                                                         |
| required             | Array listing the property names that must be present in a valid json object                | yes                 | jsonschema  | `['type', 'submitter_id', 'core_metadata_collection']`            | Array                                                                                                                         |
| type                 | Data type for the entity                                                                    | no                  | jsonschema  | object                                                            | String                                                                                                                        |
| namespace            | Namespace                                                                                   | no                  | gen3        | n/a                                                               | String                                                                                                                        |
| program              | program the schema belongs to                                                               | no                  | gen3        | *                                                                 | String                                                                                                                        |
| project              | project the schema belongs to                                                               | no                  | gen3        | *                                                                 | String                                                                                                                        |
| additionalProperties | A boolean that controls whether properties not explicitly defined in properties are allowed | no                  | jsonschema  | False                                                             | Bool                                                                                                                          |
| submittable          | can you submit data to this entity?                                                         | no                  | gen3        | True                                                              | Bool                                                                                                                          |
| validators           | Custom field to hold validation logic                                                       | no                  | gen3        | None                                                              | String                                                                                                                        |
| systemProperties     | A list of gen3 specific properties                                                          | no                  | gen3        | `['id', 'project_id', 'state', 'created_datetime', 'updated_datetime']` | Array                                                                                                                         |
| uniqueKeys           | Properties in the entity that will be used for unique identification                        | no                  | gen3        | `[['id'], ['project_id', 'submitter_id']]`                          | Array                                                                                                                         |


# Links
- All entites must have at least one link

Links are defined in the following format:

```yaml
links:
- name: <name>
    backref: <entity_name>
    label: <label>
    target_type: <target_type>
    multiplicity: <multiplicity>
    required: <required>
```


# Properties

## Ubiquitous Properties


## Link Array Properties