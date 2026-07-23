# Declaring Links in the `input_yaml`

This page is a reference for how links are written in an `input_yaml` and what Gen3SchemaDev builds
from them.

It is the counterpart to [Defining Links in Gen3](../gen3_data_modelling/links.md), which describes
links as they appear in a finished `Gen3 Schema`. Read that one if you are hand-editing the
generated node yamls; read this one if your source of truth is an `input_yaml`.

For a step-by-step introduction rather than a reference, see
[Creating your first gen3 data dictionary](first_dictionary.md#4-links).

***

## The basic form

Links are declared as a flat list at the bottom of the `input_yaml`, not inside the nodes. Each
entry reads as *"one `parent` is linked to `multiplicity` `child`"*:

```yaml
links:
  - parent: sample
    multiplicity: one_to_many
    child: lipidomics_file
```

Gen3SchemaDev derives the rest of the `Gen3 Schema` link from that triple:

| Generated key | Where it comes from |
| :--- | :--- |
| `name` | the parent's name, pluralised |
| `backref` | the child's name, pluralised |
| `label` | always `part_of` |
| `target_type` | the parent |
| `multiplicity` | inverted, so it reads from the child's point of view |
| `required` | `true`, unless you say otherwise — see below |

- *Note: `multiplicity` is declared parent-to-child but recorded child-to-parent, so `one_to_many` in your `input_yaml` becomes `many_to_one` in the generated schema. That is not an error.*

***

## Making a link optional

Add `required` to say whether an instance of the child *must* be attached to a parent of that type.
It defaults to `true`, so leaving it out gives the same result as before this option existed.

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

***

## A node with several parents

When a node is the child of more than one link, Gen3SchemaDev collects them into a single subgroup
for you. You do not write the subgroup; you write one entry per parent, and each keeps its own
`required` value:

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

***

## How the two levels of `required` interact

A generated subgroup has two different `required` flags, and they answer different questions:

| Where | Question it answers | Settable from the `input_yaml`? |
| :--- | :--- | :--- |
| On an individual link | Must *this particular* parent be supplied? | Yes — `required` on the link |
| On the subgroup | Must *at least one* parent from the group be supplied? | No — always `true` |

So a node whose links are all `required: false` is still never left orphaned: the subgroup rule
means at least one parent must be present, while leaving the submitter free to choose which. That
combination is the usual shape for a file node that can hang off any one of several parents.

- *Note: the subgroup's own `exclusive` and `required` flags cannot currently be set from the `input_yaml` — they are always `false` and `true`. If you need `exclusive: true`, the generated schema must be edited by hand, and you are then maintaining that file rather than the input.*

***

## Links involving `program`, `project` and `core_metadata_collection`

These three nodes come from Gen3SchemaDev's own packaged templates, complete with their links. A
link you declare whose `child` is one of them is **discarded**, and setting `required` on it has no
effect.

The link from a `data_file` node *to* `core_metadata_collection` is the opposite case: it is added
for you, always with `required: false`, whether or not that node declares any links of its own.

***

## What the `input_yaml` cannot express

Worth knowing before you reach for it, so you do not spend time looking for an option that is not
there:

- **`label`** — always `part_of` for generated links
- **`name` and `backref`** — always the node name plus `s`, which can read awkwardly for names that
  do not pluralise that way
- **subgroup `exclusive` and `required`** — always `false` and `true`
- **more than one subgroup on a node** — all of a node's links go into one group

If your model genuinely needs any of these, the generated schema has to be maintained by hand. See
[Running a Gen3 dictionary repository](dictionary_repo.md) for what that means in practice, and how
to keep the repository honest about which files are generated and which are not.
