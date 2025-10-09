---
title: Dictionary Structure
has_children: false
nav_order: 1
authors: ["Marion Shadbolt", "Joshua Harris"]
---
# Dictionary Structure
The gen3 data dictionary is a graph based data model, where the nodes represent nodes and the edges represent relationships between the nodes. Each node is defined by a `schema` which is represented in [yaml format](explainer_schema.yaml). Therefore, an entire data dictionary can be defined by a [folder containing multiple yaml files](../../tests/gen3_schema/examples/yaml/).

To load the data dictionary into the gen3 system, the yaml files must be converted into json format, and then bundled into a list of jsonschemas which are saved to a single json file ([example](../../tests/gen3_schema/examples/json/schema_dev.json)). This json file is called a `Gen3 Bundled Schema`, and is uploaded to `sheepdog` to deploy the data model.

**Summary definitions**
- [`Gen3 Schema`](../../tests/gen3_schema/examples/yaml/lipidomics_file.yaml): A single yaml or json file that defines a single node in the data model. [Learn More](schemas.md)
- [`Gen3 Data Dictionary`](../../tests/gen3_schema/examples/yaml/): A folder containing multiple yaml files for each node in the data model.
- [`Gen3 Bundled Schema`](../../tests/gen3_schema/examples/json/schema_dev.json): A json file containing a list of jsonschemas for each node in the data model.

## Required nodes

All dictionaries must have the following schemas as part of the dictionary structure:
- `Program`
- `Project`
- `Core Metadata Collection`

While properties may be edited within these, the `dbgap` associated fields on the projects cannot be removed.

In addition, all data files need to be linked to the `core_metadata_collection`.

## Visual Example
- The files that created this example can be found [here](../../examples/schema/).

![](../../examples/schema/image.png)

## Official Documentation
- Official documentation for the Gen3 Data Dictionary can be found [here](https://docs.gen3.org/gen3-resources/operator-guide/create-data-dictionary/).

## What's next?
Now lets take a look at a [Gen3 Schema](schemas.md).