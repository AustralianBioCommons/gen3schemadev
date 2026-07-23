---
title: Links
has_children: false
parent: Schemas
nav_order: 2
authors: ["Marion Shadbolt", "Joshua Harris"]
---

# Defining Links in Gen3

The Gen3 data model follows a graph structure. At the very top sits the **Program** node, the ultimate root of your data structure. Links are what connect all the different nodes in this graph, establishing how they relate to one another.

A core principle to remember is that links are directional, always connecting a child node up to its parent. For the data model to be a single, connected graph, **every node must have at least one link (or link subgroup) that is marked as `required: true`**. This ensures no node is ever left isolated.

## The Anatomy of a Link

Each link is defined by a set of properties that tell the system how two nodes are connected. Here is a quick reference for what each property does.

| Key | Description | Example Values |
| :--- | :--- | :--- |
| **name** | The name for the link, as seen from the child node. This is often the parent's name in plural form. | `subjects` |
| **backref** | The name for the link from the parent's perspective, pointing back to the child. | `demographics` |
| **label** | A simple descriptor for the type of relationship between the nodes. | String: `describes` |
| **target_type** | The unique ID of the parent node you are linking to. | `subject` |
| **multiplicity** | The numeric relationship between the child and parent, such as one-to-one or many-to-many. | `one_to_one`, `one_to_many`, `many_to_one`, `many_to_many`  |
| **required** | A true or false value indicating if every instance of the child must have this link to a parent. | `true`, `false` |



## Example 1:
Let's look at a practical example. Imagine we are inside the `demographic` [node](../../tests/gen3_schema/examples/yaml/demographic.yaml) and want to link it to a `subject` [node](../../tests/gen3_schema/examples/yaml/subject.yaml).

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
Now, let's consider a more flexible connection. Here, we are inside a `lipidomics_file` [node](../../tests/gen3_schema/examples/yaml/lipidomics_file.yaml) and want to link it to the `sample` [node](../../tests/gen3_schema/examples/yaml/sample.yaml) from which it was derived.

```yaml
links:
  - name: samples
    backref: lipidomics_files
    label: data_from
    target_type: sample
    multiplicity: one_to_many
    required: false
```
The `multiplicity` of `one_to_many` allows for a single lipidomics file to be associated with multiple samples. The link is optional because `required` is `false`. In other words: "A lipidomics file can come from multiple samples, or multiple samples are linked with a single lipidomics file."


# Advanced Linking with Subgroups

Sometimes, an node needs to connect to one of several possible parents. You can define multiple, independent links, but a more powerful method is to use a subgroup. By grouping links, you can apply rules to the group as a whole using two flags: `exclusive` and `required`.

This allows for the following scenarios:

| exclusive | required | Result |
| :--- | :--- | :--- |
| `true` | `true` | You must link to exactly one node from the group. |
| `false` | `true` | You must link to at least one node from the group, and can link to more. |
| `true` | `false` | You can link to one node from the group, or none at all. |
| `false` | `false` | Linking is completely optional; you can link to none, one, or multiple nodes. |

**Important**: As a requirement in Gen3, any node classified as a `data_file` must always contain a link to `core_metadata_collection`.

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
In this setup, the subgroup has `required: true` and `exclusive: false`. This means a `lipidomics_file` must be linked to at least one of the nodes in the group, and it can be linked to more than one. It can be linked to a `sample`, a `core_metadata_collection`, or both. While the individual links inside the group are optional (`required: false`), the subgroup's top-level rule ensures the node is never left orphaned.


***


# Declaring Links in the `input_yaml`

Everything above describes a `Gen3 Schema` as it is written out. If you are working from an `input_yaml`, you do not write those blocks yourself — you declare links as a flat list at the bottom of the file and Gen3SchemaDev builds them.

Each entry reads as *"one `parent` is linked to `multiplicity` `child`"*:

```yaml
links:
  - parent: sample
    multiplicity: one_to_many
    child: lipidomics_file
```

Gen3SchemaDev derives the rest: `name` from the parent, `backref` from the child, `label: part_of`, and the multiplicity inverted so that it reads from the child's point of view.

## Making a link optional

Add `required` to say whether an instance of the child *must* be attached to a parent of that type. It defaults to `true`, so leaving it out gives the same result as before this option existed.

```yaml
links:
  # Every lipidomics file must belong to a sample.
  - parent: sample
    multiplicity: one_to_many
    child: lipidomics_file

  # A file may record the site it came from, but does not have to.
  - parent: site
    multiplicity: one_to_many
    child: lipidomics_file
    required: false
```

- *Note: `required` is set per link, not per node. Where a node has several parents, each link is answered independently — the second and third links can disagree with the first.*

## A node with several parents

When a node is the child of more than one link, Gen3SchemaDev collects them into a single subgroup for you. You do not write the subgroup; you write one entry per parent, and each keeps its own `required` value:

```yaml
links:
  - parent: sample
    multiplicity: one_to_many
    child: lipidomics_file
    required: true
  - parent: lipidomics_assay
    multiplicity: one_to_many
    child: lipidomics_file
    required: true
  - parent: site
    multiplicity: one_to_many
    child: lipidomics_file
    required: false
```

This generates a subgroup of three links carrying `true`, `true` and `false` respectively.

## How the two levels of `required` interact

A generated subgroup has two different `required` flags, and they answer different questions:

| Where | Question it answers | Settable from the `input_yaml`? |
| :--- | :--- | :--- |
| On an individual link | Must *this particular* parent be supplied? | Yes — `required` on the link |
| On the subgroup | Must *at least one* parent from the group be supplied? | No — always `true` |

So a node whose links are all `required: false` is still never left orphaned: the subgroup rule means at least one parent must be present, while leaving the submitter free to choose which. That combination is the usual shape for a file node that can hang off any one of several parents.

- *Note: the subgroup's own `exclusive` and `required` flags cannot currently be set from the `input_yaml` — they are always `false` and `true`. If you need `exclusive: true`, the schema must be edited by hand.*

## Links involving `program`, `project` and `core_metadata_collection`

These three nodes come from Gen3SchemaDev's own packaged templates, complete with their links. A link you declare whose `child` is one of them is **discarded**, and setting `required` on it has no effect.

The link from a `data_file` node *to* `core_metadata_collection` is the opposite case: it is added for you, always with `required: false`, whether or not that node declares any links of its own.
