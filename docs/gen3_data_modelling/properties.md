---
title: Properties
has_children: false
parent: Schemas
nav_order: 3
authors: ["Marion Shadbolt", "Joshua Harris"]
---

# Properties

Properties define the rules about the different 'fields' of the node, i.e. what kind of metadata will be stored against each node.

Each node should have:
 - property name
 - `description` - detailed description of the field
 - `type` - any of the existing [json schema](https://cswr.github.io/JsonSchema/spec/basic_types/) types.

For example:
```yaml
properties:
  year_birth:
    description: Year of birth at baseline (YYYY)
    type: integer
  month_birth:
    description: Month of birth at baseline (MM)
    type: integer
```

## Required & Preferred Properties

Any properties in the schema that are required are specified in a `required` block. Every schema should have the `submitter_id`, `type` and any parental links listed as required attributes. Any submission of a particular node type that does not contain values for the required nodes will not pass validation.

Example from [`demographic.yaml`](../../tests/gen3_schema/examples/yaml/demographic.yaml):

```yaml
required:
- type
- submitter_id
- subjects
```

A block of `preferred` attributes may also be specified. This would indicate an important field but submission of nodes without this field will still pass validation.

Example from [`demographic.yaml`](../../tests/gen3_schema/examples/yaml/demographic.yaml):

```yaml
preferred:
- year_birth
```


## Shared Property Definitions

In addition to the properties that you define as unique to a particular node, it is also useful to refer to properties that may be shared across many nodes. These properties can be saved within the [`_definitions.yaml`](../../tests/gen3_schema/examples/yaml/_definitions.yaml) and referred to as needed.

Some examples from the gdc dictionary are:

### Ubiquitous properties 

This `_definitions.yaml#/ubiquitous_properties` contains many of the required system properties such as `submitter_id` and `state`

### Link properties

In each schema, there needs to be a property that stores the link to its parent(s). 

These are referred to by the property that describes the link and reflect the multiplicity of the link. The default link properties that are included in the [`_definitions.yaml`](../../tests/gen3_schema/examples/yaml/_definitions.yaml) are:

- `to_one`
- `to_many`
- `to_one_project`
- `to_many_project`

These refer to the foreign key properties
- `foreign_key_project`
- `foreign_key`

As an example from the [`demographic.yaml`](../../tests/gen3_schema/examples/yaml/demographic.yaml), the `links` section of the file looks like:

```yaml
links:
- name: subjects
  backref: demographics
  label: describes
  target_type: subject
  multiplicity: one_to_one
  required: true
```

which means in the `properties` section, you need to refer to this link by including a property like:

```yaml
properties:
  subjects:
    $ref: _definitions.yaml#/to_one
```

## Property Types

Most property types are straight forward. Some of the types are explained in further detail below.

### Numeric properties

Properties with a numeric type, that is `integer` or `number` can be restricted with minimum and maximum values.

```yaml
age_at_diagnosis:
    description: Age at the time of diagnosis expressed in number of days since birth.
      If the age is greater than 32872 days (89 years), see 'age_at_diagnosis_gt89'.
    type: integer
    maximum: 32872
    minimum: 0
```

### String properties

A general string property will allow any free text unless a pattern or enumeration is specified.

#### Patterns

Regex patterns can be used to restrict a string property to a certain format.

Example from  [`_definitions.yaml`](../../tests/gen3_schema/examples/yaml/_definitions.yaml):

```yaml
UUID:
    term:
        $ref: "_terms.yaml#/UUID"
    type: string
    pattern: "^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$"
```

#### Enumerations

Enumerations for a property restrict the values to a set of allowed values. If a value is specified outside of this set, the metadata will fail validation.

Example from [`medical_history.yaml`](../../tests/gen3_schema/examples/yaml/medical_history.yaml):

```yaml
  hypertension_measurement_type:
    description: Whether the hypertension was measured at recruitment/patients on
      hypertension treatment or self-reported medical diagnosis
    enum:
    - self-reported
    - measured
```

#### Term definitions

Properties can be linked to external definitions, such as ontologies or the NCIT by the use of term definitions. A single property may be defined by multiple term definitions, for example, one pointing to a NCIT reference, and one pointing to an Ontology reference.

The format for specifying a term definition is:

```yaml
property_name:
  description: >
    Descriptive text.
  termDef:
    term: Term name from source
    source: name of source
    cde_id: source id from CDE browser
    cde_version: version of cde
    term_url: "https://direct-link-to-term"
```

It is common practice to put the term definitions into a file called [`_terms.yaml`](../../tests/gen3_schema/examples/yaml/_terms.yaml) and refer to them from a base schema.

In the [`_terms.yaml`](../../tests/gen3_schema/examples/yaml/_terms.yaml), this would look like this:

```yaml
bmi:
  description: >
    A calculated numerical quantity that represents an individual's weight to height ratio.
  termDef:
    term: Body Mass Index Value
    source: caDSR
    cde_id: 2006410
    cde_version: 3.0
    term_url: "https://cdebrowser.nci.nih.gov/cdebrowserClient/cdeBrowser.html#/search?publicId=2006410&version=3.0"
```

Whereas in the yaml that uses this term definition it would look something like this:

```yaml
properties:
  bmi:
    term:
      $ref: "_terms.yaml#/bmi"
    type: number
```


#### Enum definitions

As well as defining a term from an external ontology or vocabulary, you can also define each enumerated value.

In the example below from the [`medical_history.yaml`](../../tests/gen3_schema/examples/yaml/medical_history.yaml), we can see that property itself is defined in both SNOMED as well as the Human Phenotype Ontology by using two `termDef` entries. 

Each enum is also linked to an NCI Thesaurus entry using the `enumDef` syntax.

```yaml
  diabetes_type:
    description: diabetes diagnosed by fasting blood glucose >=7 mmol/l or tx AHA
      or 2 hour blood glucose >=11.1 mmol/l.
    termDef:
    - term: Diabetes mellitus
      source: hpo
      term_id: HP:0000819
      term_version: '2021-10-10'
    enum:
    - IGT
    - KDM
    - IFG
    - NDM
    - NGT
    enumDef:
    - enumeration: IGT
      source: hpo
      term_id: HP:0040270
    - enumeration: NDM
      source: SNOMED
      term_id: '870528001'
    - enumeration: NGT
      source: SNOMED
      term_id: '166926006'
```
