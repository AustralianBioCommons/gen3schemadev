---
title: Links
has_children: false
parent: Schemas
nav_order: 2
---

# Links
{: .no_toc .text-delta }

1. TOC
{:toc}

Links are what join the nodes of your data model together. The links go **from** the child **to** the parent with the `Program` always being the ultimate root of the data model. Links are also described with a `backref`, `label` and `multiplicity` that should match up to one of the specified relationships in the `_definitions.yaml` file. All nodes must have at least one required link or link subgroup to ensure it will be joined to the rest of the data model.


| Key          | Description                              | example values      |
|--------------|------------------------------------------|---------------------|
| name         | The name of the link from this schema to its parent, usually the parent's name in plural form   |                 |
| backref      | The back reference from the parent back to the child, usually the name of the schema pluralised |                 |
| label        | A descriptor for the type of relationship. (Not sure if this is a controlled vocabulary or free text) | `describes`, `member_of`, `derived_from`, `data_from`  |
| target_type  | the node id of the parent                                                                       |                                                              |
| multiplicity | describes the numeric relationship from the child to the parent, these should be defined in the `_definitions.yaml` | `one_to_one`, `one_to_many`, `many_to_many`, `to_one_project`, `to_many_project` |
| required     | Whether each instance of this schema needs to have this link                                     | `true`, `false`  |

A simple example links code snippet from the gdc dictionary `case.yaml`:

```yaml
links:
  - name: experiments 
    backref: cases
    label: member_of
    target_type: experiment
    multiplicity: many_to_one
    required: true
```

The above `links` snippet is specifying that a `case` is a `member_of` an `experiment`, that is, the `experiment` is the parent of the `case`. The `multiplicity` indicates it is a `many_to_one` relationship, that is, many cases can be a part of a single experiment. The `required` property indicates this relationship is required, that is, every case that is submitted must be linked to a single experiment.

## Multiple links

If a child can link to multiple parents, that is, be a child of either `parentA` AND/OR `parentB` , simply list an additional link, example from gdc dictionary `clinical_test.yaml`. Bear in mind that there has to be at least one link that has `required: true` to ensure that nodes are always connected to the rest of the graph.

```yaml
links:
  - name: cases 
    backref: clinical_tests
    label: performed_for 
    target_type: case
    multiplicity: many_to_one
    required: true
  - name: diagnoses
    backref: clinical_tests
    label: relates_to
    target_type: diagnosis
    multiplicity: many_to_many
    required: false
```

The `links` snippet above indicates that the `clinical_test` node must be linked to a `case` node (`required: true`), and that a single case may be linked to multiple `clinical_tests` (`multiplicity: many_to_one`). In addition, a `clinical_test` node may be optionally linked (`required: false`) to one or more `diagnosis` nodes. Multiple `diagnoses` may be linked to multiple `clinical_tests` (`multiplicity: many_to_many`).

## Link subgroups

If a single node instance needs to link to multiple parents, and the linking is related in some way, a link `subgroup` can be specified. The nature of how nodes are linked with a subgroup is by using a two boolean fields, `exclusive` and `required`, within the `links` block of the schema.

This allows for the following scenarios:

| exclusive | required | result                                                                            |
|-----------|----------|-----------------------------------------------------------------------------------|
| `true`    | `true`   | You must link to only one of the subgroup nodes                                   |
| `false`   | `true`   | You can pick one or more of the subgroup nodes, but you need to pick at least one |
| `true`    | `false`  | You can pick one or not, but not more than one subgroup node                      |
| `false`   | `false`  | You can pick none, one, or more of the subgroup nodes if you want to              |

Example from gdc dictionary `submitted_aligned_reads.yaml`

```yaml
links:
  - exclusive: false
    required: true
    subgroup:
    - name: read_groups
      backref: submitted_aligned_reads_files
      label: data_from
      target_type: read_group
      multiplicity: one_to_many
      required: false
    - name: core_metadata_collections
      backref: submitted_aligned_reads_files
      label: data_from
      target_type: core_metadata_collection
      multiplicity: many_to_many
      required: false
```

In this example, the `submitted_aligned_reads` node needs to be linked to at least one of `read_groups` OR `core_metadata_collections` (or both). The subgroup is necessary because if they were specified as two individual non-required links, you could end up with the a node that isn't connected to the rest of the graph.
