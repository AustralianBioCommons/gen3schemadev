---
title: Descriptors
has_children: false
parent: Schemas
nav_order: 1
---

# Descriptors
{: .no_toc .text-delta }

1. TOC
{:toc}

| Key                  | Description                                                                                      | allowed values                                                                                       |
|----------------------|--------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------|
| $schema              | The version of json schema                                                                       | "http://json-schema.org/draft-04/schema#"                                                            |
| id                   | Node id used for data query/submission                                                           | string                                                                                               |
| title                | Name for the schema                                                                              | string                                                                                               |
| type                 | The type of the schema                                                                           | 'object'                                                                                             |
| namespace            | the commons that uses this schema, usually a url                                                 | string                                                                                               |
| category             | categories that represent broad roles for the node, these are customisable for different data models. Useful in querying as you can select all nodes of a particular category | in [core dictionary](https://gen3.org/resources/operator/#3-creating-a-new-data-dictionary) they are: `administrative`, `index_file`, `biospecimen`, `clinical`, `notation`, `data_file`, `analysis` |
| program              | ? guess is that it can configure which program this schema could be a part of with * meaning all | '*'                                                                                                  |
| project              | ? guess is that it can configure which project this schema could be a part of with * meaning all | '*'                                                                                                  |
| description          | A description for the schema                                                                     | string                                                                                               |
| additionalProperties | Disallows a user from adding more properties than are specified in the schema when validating    | false                                                                                                |
| submittable          | Whether this schema is directly submittable to the gen3 portal | true/false                                                                                           |
| validators           | ?                                                                                                | ?                                                                                                    |
| systemProperties     | these properties are those that will be automatically filled by the system unless otherwise defined by the user. These basic properties define the node itself but still need to be placed into the model. | as a minimum <br> - id <br> - project_id <br> - state <br> - created_datetime <br> - updated_datetime|

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