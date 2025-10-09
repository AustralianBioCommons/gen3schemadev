---
title: Descriptors
has_children: false
parent: Schemas
nav_order: 1
authors: ["Marion Shadbolt", "Joshua Harris"]
---

# Descriptors

The descriptors are the top level fields of a schema that describe the schema itself. Some of these fields are specific to [JsonSchema](https://json-schema.org/overview/what-is-jsonschema), whilst others are gen3 specific. The Descriptors or field names are summarised in the table below.

- Feel free to see an example of what these descriptors look like in a gen3 schema yaml called [lipidomics_file](../../tests/gen3_schema/examples/yaml/lipidomics_file.yaml).
- You can also get a feel for what the descriptors do based on this [example schema](explainer_schema.yaml)

*Note: `required user input` indicates that the field should be defined by the user, if this value is `no` the field must still exist, but you can use the default value which is generic enough for most cases.*

| field name             | description                                                                                 | required user input | specificity | default value (json format)                                                     | data type                                                                                                                     | yaml example                       |
|------------------------|---------------------------------------------------------------------------------------------|---------------------|-------------|-------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|-------------------------------------|
| `$schema`              | Declares the version of the JSON Schema standard used                                       | no                  | jsonschema  | http://json-schema.org/draft-04/schema#                             | String                                                                                                                       | http://json-schema.org/draft-04/schema# |
| `id`                   | Unique identifier for the entity                                                            | yes                 | jsonschema  | n/a                                                               | String                                                                                                                       | lipidomics_file                     |
| `title`                | Name of the entity                                                                          | yes                 | jsonschema  | n/a                                                               | String                                                                                                                       | Lipidomics File                     |
| `category`             | Classification of entity                                                                    | yes                 | gen3        | n/a                                                               | Enum ['administrative', 'index_file', 'biospecimen', 'clinical', 'notation', 'data_file', 'analysis', 'experimental_methods'] | data_file                           |
| `description`          | Description of the schema                                                                   | yes                 | jsonschema  | n/a                                                               | String                                                                                                                       | Data file containing lipidomics data |
| `links`                | Array of objects that describe links to other entities                                      | yes                 | gen3        | n/a                                                               | Array                                                                                                                        | ![](img/links.png)                  |
| `required`             | Array listing the property names that must be present in a valid json object                | yes                 | jsonschema  | ['type', 'submitter_id', 'core_metadata_collection']               | Array                                                                                                                        | ![](img/required.png)               |
| `type`                 | Data type for the entity                                                                    | no                  | jsonschema  | object                                                            | String                                                                                                                       | object                              |
| `namespace`            | Namespace                                                                                   | no                  | gen3        | n/a                                                               | String                                                                                                                       | http://commons.heartdata.baker.edu.au/ |
| `program`              | Program the schema belongs to                                                               | no                  | gen3        | *                                                                 | String                                                                                                                       | *                                   |
| `project`              | Project the schema belongs to                                                               | no                  | gen3        | *                                                                 | String                                                                                                                       | *                                   |
| `additionalProperties` | A boolean that controls whether properties not explicitly defined in properties are allowed | no                  | jsonschema  | False                                                             | Bool                                                                                                                         | False                               |
| `submittable`          | Can you submit data to this entity?                                                         | no                  | gen3        | True                                                              | Bool                                                                                                                         | True                                |
| `validators`           | Custom field to hold validation logic                                                       | no                  | gen3        | None                                                              | String                                                                                                                       | None                                |
| `systemProperties`     | A list of gen3 specific properties                                                          | no                  | gen3        | ['id', 'project_id', 'state', 'created_datetime', 'updated_datetime'] | Array                                                                                                                        | ![](img/sysprops.png)               |
| `uniqueKeys`           | Properties in the entity that will be used for unique identification                        | no                  | gen3        | [['id'], ['project_id', 'submitter_id']]                          | Array                                                                                                                        | ![](img/unique.png)                 |


## Unique Keys

A set of `uniqueKeys` must be specified. This provides a way of uniquely identifying any node. 

note:
{: .label .label-yellow }

Am yet to come accross an example other than the one below. Not sure about the exact function of this field.

Example from `study.yaml`

```yaml
uniqueKeys:
  - [id]
  - [project_id, submitter_id]
```