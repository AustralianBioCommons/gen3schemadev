---
title: Links
has_children: false
parent: Schemas
nav_order: 2
authors: ["Marion Shadbolt", "Joshua Harris"]
---

# Defining Links in Gen3

The Gen3 data model follows a graph structure. At the very top sits the **Program** entity, the ultimate root of your data structure. Links are what connect all the different entities in this graph, establishing how they relate to one another.

A core principle to remember is that links are directional, always connecting a child entity up to its parent. For the data model to be a single, connected graph, **every entity must have at least one link (or link subgroup) that is marked as `required: true`**. This ensures no entity is ever left isolated.

## The Anatomy of a Link

Each link is defined by a set of properties that tell the system how two entities are connected. Here is a quick reference for what each property does.

| Key | Description | Example Values |
| :--- | :--- | :--- |
| **name** | The name for the link, as seen from the child entity. This is often the parent's name in plural form. | `subjects` |
| **backref** | The name for the link from the parent's perspective, pointing back to the child. | `demographics` |
| **label** | A simple descriptor for the type of relationship between the entities. | String: `describes` |
| **target_type** | The unique ID of the parent entity you are linking to. | `subject` |
| **multiplicity** | The numeric relationship between the child and parent, such as one-to-one or many-to-many. | `one_to_one`, `one_to_many`, `many_to_one`, `many_to_many`  |
| **required** | A true or false value indicating if every instance of the child must have this link to a parent. | `true`, `false` |

While `name` and `backref` provide useful field names, they don't define the connection's behavior. To understand the true nature of the relationship, such as how many children can connect to a parent, you must always check the `multiplicity` property.


## Example 1:
Let's look at a practical example. Imagine we are inside the `demographic` [entity](../examples/schema/yaml/demographic.yaml) and want to link it to a `subject` [entity](../examples/schema/yaml/subject.yaml).

```yaml
links:
  - name: subjects
    backref: demographics
    label: describes
    target_type: subject
    multiplicity: one_to_one
    required: true
```
In this scenario, we are establishing a strict pairing. The `multiplicity` of `one_to_one` ensures that for every demographic record, there is exactly one subject, and vice versa. Because `required` is set to `true`, a demographic record cannot exist without a corresponding subject. In plain English, this means: "A demographic profile describes one subject, and that subject has one demographic profile."



## Example 2:
Now, let's consider a more flexible connection. Here, we are inside a `lipidomics_file` [entity](../examples/schema/yaml/lipidomics_file.yaml) and want to link it to the `sample` [entity](../examples/schema/yaml/sample.yaml) from which it was derived.

```yaml
links:
  - name: samples
    backref: lipidomics_files
    label: data_from
    target_type: sample
    multiplicity: many_to_many
    required: false
```
The `multiplicity` of `many_to_many` allows for a single file to be associated with multiple samples, and it also allows a single sample to be associated with multiple lipidomics files. The link is optional because `required` is `false`. In other words: "A lipidomics file can come from multiple samples, and a sample can be linked to many lipidomics files."


# Advanced Linking with Subgroups

Sometimes, an entity needs to connect to one of several possible parents. You can define multiple, independent links, but a more powerful method is to use a subgroup. By grouping links, you can apply rules to the group as a whole using two flags: `exclusive` and `required`.

This allows for the following scenarios:

| exclusive | required | Result |
| :--- | :--- | :--- |
| `true` | `true` | You must link to exactly one entity from the group. |
| `false` | `true` | You must link to at least one entity from the group, and can link to more. |
| `true` | `false` | You can link to one entity from the group, or none at all. |
| `false` | `false` | Linking is completely optional; you can link to none, one, or multiple entities. |

**Important**: As a requirement in Gen3, any entity classified as a `data_file` must always contain a link to `core_metadata_collection`.

```yaml
links:
  - exclusive: false
    required: true
    subgroup:
      - name: samples
        backref: lipidomics_files
        label: data_from
        target_type: sample
        multiplicity: many_to_many
        required: false
      - name: core_metadata_collection
        backref: lipidomics_files
        label: describes
        target_type: core_metadata_collection
        multiplicity: one_to_one
        required: false
```
In this setup, the subgroup has `required: true` and `exclusive: false`. This means a `lipidomics_file` must be linked to at least one of the entities in the group, and it can be linked to more than one. It can be linked to a `sample`, a `core_metadata_collection`, or both. While the individual links inside the group are optional (`required: false`), the subgroup's top-level rule ensures the node is never left orphaned.
