# Core Principles to Data Modelling

## Table of Contents
Data modelling in Gen3SchemaDev focuses on the following core concepts:
- [Core Principles to Data Modelling](#core-principles-to-data-modelling)
  - [Table of Contents](#table-of-contents)
- [Entities](#entities)
- [Properties](#properties)
  - [Data types](#data-types)
  - [Enums](#enums)
- [Links](#links)
    - [Example 1](#example-1)
    - [Example 2](#example-2)
- [Now lets try to make a Gen3 Dictionary!](#now-lets-try-to-make-a-gen3-dictionary)

---



# Entities
An entity represents a table of data in the data model. Entities encapsulate related information, for example, information about the patient, the sample, sequencing run, output files, etc. When data is submitted to the data model, each table of metadata will correspond to a specific entity. 

The example below shows the entities `program`, `project`, `subject`, `acknowledgement`, `publication`, and `core_metadata_collection`.


![entity_example](entity_example.png)

# Properties
Properties are found within entities. Properties can be thought of as the columns in a table. Each properties will have the property name (column name), a description of what the property is, and a data type. 

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

The example below shows some properties from the `medical_history` entity. Notice how the first column is the property name, the second column is the data type, the third whether the property is required or not, and the fourth is the description.

![prop_example](prop_example.png)

- Some properties, for example `atrial_fibrillation`, have `yes` and `no` as the data type. This is an example of what an enumeration looks like, the two possible values are `yes` and `no`.
- Another interesting property is `timepoints`, which has the data type of `array` or `object`. In Gen3, this property serves as a way to store linkage information between entities. For example, the `timepoints` property can be used to link a `subject` with a value of ```{"submitter_id": "subject_3a3312b756"}```. In the subjects entity, the value of `submitter_id` would be `subject_3a3312b756`.

*Note: These link properties are automatically added in when using Gen3SchemaDev so that you can focus more on the unique properties of your data model. For more advanced information you can find [here](../gen3_data_modelling/links.md)**

## Enums
A specific data type called an enumeration (enum) can be used to specify a set of allowed values, like a controlled vocabulary. `Enums` are an `array` data type, where each value in the array is an allowed value. 

For example, a property that specifies the experiment type could be defined as: `['RNAseq', 'ChIPseq', 'LC-WGS', 'WES', 'WGS']`.


# Links
Links are used to connect entities together. Links are directional, always connecting a child entity up to its parent. 

Importantly, links have a `multiplicity`, which can be one of: 
- `one_to_one`
- `one_to_many`
- `many_to_one`
- `many_to_many`


---

### Example 1
> Use case: "Each patient may have multiple blood samples taken, but information about mortality will always be one record per patient."

How would we define these links?

First, lets define the `entities`:
- `patient`
- `blood_sample`
- `mortality`

Then, lets define the `links`:
- `patient` -> `one_to_many` -> `blood_sample`
- `blood_sample` -> `one_to_one` -> `mortality`

---

### Example 2
> Use case: "Multiple samples are loaded into a mass spectrometry machine each run, which produces a batch of mass spectrometry data files. However, all the data files from every mass spectrometry run are analysed with a single lipidomics workflow."

Lets define the `entities`:
- `sample`
- `mass_spectrometry_run`
- `mass_spectrometry_data_file`
- `lipidomics_workflow`

Then, lets define the `links`:
- `sample` -> `many_to_one` -> `mass_spectrometry_run`
- `mass_spectrometry_run` -> `one_to_many` -> `mass_spectrometry_data_file`
- `mass_spectrometry_data_file` -> `many_to_one` -> `lipidomics_workflow`

---

# Now lets try to make a Gen3 Dictionary!
- 