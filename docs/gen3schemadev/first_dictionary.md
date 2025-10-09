# Creating your first gen3 data dictionary

A data model is a blueprint that defines the structure and format for organising data. The two primary types are relational and graph models.

### Relational Model
In a relational model, data is organised into tables.
*   **Tables**, also called **entities**, represent concepts like `disease`, `patient`, `sample`, etc.
*   **Columns**, also called **attributes**, define the details of an entity, such as `patient_id`, `bp_systolic`, etc.
*   **Relationships** are rules that link different tables together. e.g `patient` has a relationship with `disease` through the `disease_id` column.

### Graph Model
A graph model, which is used by Gen3, organises data using nodes and links.
*   **Nodes** are used to represent entities.
*   **Links**, or edges, represent the relationships that connect nodes.
*   **Properties** are key-value pairs that store descriptive details about nodes and links.

### Terminology Comparison

| Concept | Relational Model Term | Graph Model Term |
| :--- | :--- | :--- |
| Represents an object | Entity (Table) | Node |
| Describes the object | Attribute (Column) | Property |
| Connects objects | Relationship | Link (Edge) |


**Importantly: Gen3 uses a graph model to represent the data model.**

--


Gen3SchemaDev provides a high level input_yaml file where you can define the major components of your data model. This input_yaml file abstracts away some of the complexity and formatting needed for creating gen3 schemas. 


# Nodes
An node represents a table of data in the data model. nodes encapsulate related information, for example, information about the patient, the sample, sequencing run, output files, etc. When data is submitted to the data model, each table of metadata will correspond to a specific node. 

The example below shows the nodes `program`, `project`, `subject`, `acknowledgement`, `publication`, and `core_metadata_collection`.


![node_example](node_example.png)

# Properties
Properties are found within nodes. Properties can be thought of as the columns in a table. Each properties will have the property name (column name), a description of what the property is, and a data type. 

## Data types
| Data Type  | Description                                      | Example Value         |
|------------|--------------------------------------------------|----------------------|
| string     | Textual data                                     | "sample123"          |
| integer    | Whole numbers                                    | 42                   |
| number     | Numeric values (integer or floating point)        | 3.14                 |
| boolean    | True or false values                             | true                 |
| object     | Key-value pairs (dictionary/map)                  | {"age": 30}          |
| array      | Ordered list of values                           | [1, 2, 3]            |
| null       | Null value (no value)                            | null                 |

*These are the standard [JSON Schema data types](https://json-schema.org/understanding-json-schema/reference/type.html) used to define the kind of data a property can hold.*
  

## Enums
In a `property`, a specific data type called an enumeration (`enum`) can be used to specify a set of allowed values, like a controlled vocabulary. `Enums` are an `array` data type, where each value in the array is an allowed value. 

For example, a property that specifies the experiment type could be defined as: `['RNAseq', 'ChIPseq', 'LC-WGS', 'WES', 'WGS']`.


# Links
Links are used to connect nodes together. Links are directional, always connecting a child node up to its parent. 

Importantly, links have a `multiplicity`, which can be one of: 
- `one_to_one`
- `one_to_many`
- `many_to_one`
- `many_to_many`

## Example:

The example below shows some properties from the `medical_history` node. Notice how the first column is the property name, the second column is the data type, the third whether the property is required or not, and the fourth is the description.

![prop_example](prop_example.png)

- Some properties, like `atrial_fibrillation`, can only accept a specific set of values. In this case, the only allowed values are `yes` or `no`. This is an example of a controlled vocabulary, which we define using an `enum`.

---

### Example 1
> Use case: "Each patient may have multiple blood samples taken, but information about mortality will always be one record per patient."

How would we define these links?

First, lets define the `nodes`:
- `patient`
- `blood_sample`
- `mortality`

Then, lets define the `links`:
- `patient` -> `one_to_many` -> `blood_sample`
- `blood_sample` -> `one_to_one` -> `mortality`

---

### Example 2
> Use case: "Multiple samples are loaded into a mass spectrometry machine each run, which produces a batch of mass spectrometry data files. However, all the data files from every mass spectrometry run are analysed with a single lipidomics workflow."

Lets define the `nodes`:
- `sample`
- `mass_spectrometry_run`
- `mass_spectrometry_data_file`
- `lipidomics_workflow`

Then, lets define the `links`:
- `sample` -> `many_to_one` -> `mass_spectrometry_run`
- `mass_spectrometry_run` -> `one_to_many` -> `mass_spectrometry_data_file`
- `mass_spectrometry_data_file` -> `many_to_one` -> `lipidomics_workflow`

---

# Lets make a Gen3 Data Dictionary!
- Follow this guide on how to use Gen3SchemaDev to create your first dictionary: [Creating your first dictionary](..//gen3schemadev/first_dictionary.md)