# Developing a Gen3 Data Dictionary

![overview.png](docs/img/overview.png)

This repository aims to provide the documentation, learning materials, and software tools to facilitate the creation of a data model in Gen3.

***Pre-Reading**: Please become familiar with some [core data modelling concepts](docs/core_concepts/pre_reading.md) before starting.*


## Using Gen3SchemaDev as a data modelling tool
- [Quickstart](docs/gen3schemadev/quickstart.md)
- [Guide to creating your first dictionary](docs/gen3schemadev/first_dictionary.md)
- [Running a Gen3 dictionary repository](docs/gen3schemadev/dictionary_repo.md)
- [Troubleshooting](docs/gen3schemadev/troubleshooting.md)

### `generate` does not overwrite your files

`gen3schemadev generate` never overwrites existing files by default. Generating into an empty folder works as it always has; generating into a folder that already contains files stops and lists exactly what it would have replaced, along with the ways forward.

This matters because a dictionary repository can be run in more than one way. Some treat the `input_yaml` as the source of truth and regenerate from it. Others generate once and then edit the Gen3 schemas directly, at which point the generated files *are* the dictionary. The tool cannot tell which you are doing, and guessing wrong destroys work.

- `--input-driven` — the `input_yaml` is the source of truth; regenerate everything, and fail if the folder holds a file the input cannot produce
- `--only <node>` — regenerate named nodes, leaving every other file untouched
- `--check` — report whether the folder still matches the input, write nothing, exit non-zero on drift. This is the CI gate
- `--force` — overwrite everything, discarding any hand edits

Nodes may also `extend` the packaged `program`, `project` and `core_metadata_collection` presets, adding properties while inheriting the node-level settings other Gen3 microservices depend on. See [Running a Gen3 dictionary repository](docs/gen3schemadev/dictionary_repo.md).

### Null description placeholders

`gen3schemadev validate` warns about `description: null` placeholders anywhere in the dictionary (commonly in `_definitions.yaml`'s enum definitions). The Gen3 metaschema requires descriptions to be strings; null placeholders cause "No Description" in the data-dictionary viewer and metaschema validation failures that surface on resolved node schemas, far from the offending definition. Remove the null `description` keys to resolve the warning.


## Deep dive into Gen3 Data Modelling
*Special Thanks to Marion Shadbolt for providing the [source material](https://github.com/AustralianBioCommons/umccr-dictionary/tree/main/docs/schemas)*
1. [Gen3 Dictionary Overview](docs/gen3_data_modelling/dictionary_structure.md)
1. [Gen3 Schema Explained](docs/gen3_data_modelling/schemas.md)
   1. [Descriptors](docs/gen3_data_modelling/descriptors.md)
   2. [Links](docs/gen3_data_modelling/links.md)
   3. [Properties](docs/gen3_data_modelling/properties.md)
2. [Example of a Gen3 Schema yaml](docs/gen3_data_modelling/explainer_schema.yaml)
3. [Handy tips](docs/gen3_data_modelling/handy_tips.md)
4. [FAIR Concepts for Data Modelling](docs/core_concepts/fair.md)

## For Developers

### Installation and testing
```bash
# To install
pip install poetry
poetry install
source $(poetry env info --path)/bin/activate
gen3schemadev --version

# To run tests
poetry run pytest
```

### Contributing
Gen3SchemaDev is an open source project, and we highly encourage any contributions and PRs. Specifically we need the community to help with the following:
1. Keeping the [gen3 metaschema](src/gen3schemadev/schema/schema_templates/gen3_metaschema.yml) up to date 
2. Adding business rule logic to the [rule validator](src/gen3schemadev/validators/rule_validator.py) module. 
   1. For example, a node with the category `data_file` should have a collection of required data file properties such as md5sum, filesize, etc.

For PRs, please follow the [contributing guidelines](CONTRIBUTING.md).

## License
[Apache 2.0](LICENSE)

