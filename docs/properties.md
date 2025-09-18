---
title: Properties
has_children: false
parent: Schemas
nav_order: 3
---

# Properties
{: .no_toc .text-delta }

1. TOC
{:toc}

Properties define the rules about the different 'fields' of the node, i.e. what kind of metadata will be stored against each node.

Each node should have:
 - property name
 - `description` - detailed description of the field
 - `type` - any of the existing [json schema](https://cswr.github.io/JsonSchema/spec/basic_types/) types

## Required & Preferred Properties

Any properties in the schema that are required are specified in a `required` block. Every schema should have the `submitter_id`, `type` and any parental links listed as required attributes. Any submission of a particular node type that does not contain values for the required nodes will not pass validation.

Example from `study.yaml`:

```
required:
  - submitter_id
  - type
  - study_description
  - projects
```

A block of `preferred` attributes may also be specified. This would indicate an important field but submission of nodes without this field will still pass validation.

Example from `demographic.yaml`

```yaml
preferred:
  - year_of_death
```


## Shared Property Definitions

In addition to the properties that you define as unique to a particular node, it is also useful to refer to properties that may be shared across many nodes. These properties can be saved within the `_definitions.yaml` and referred to as needed.

Some examples from the gdc dictionary are:

### Ubiquitous properties 

This `_definitions.yaml#/ubiquitous_properties` contains many of the required system properties such as `submitter_id` and `state`

### Link properties

In each schema, there needs to be a property that stores the link to its parent(s). 

These are referred to by the property that describes the link and reflect the multiplicity of the link. The default link properties that are included in the `_definitions.yaml` are:

- `to_one`
- `to_many`
- `to_one_project`
- `to_many_project`

These refer to the foreign key properties
- `foreign_key_project`
- `foreign_key`

As an example from the `case.yaml`, the `links` section of the file looks like:

```yaml
links:
  - name: experiments 
    backref: cases
    label: member_of
    target_type: experiment
    multiplicity: many_to_one
    required: true
```

which means in the `properties` section, you need to refer to this link by including a property like:

```yaml
properties:
...
  experiments: 
    $ref: "_definitions.yaml#/to_one"
```

## Property Types

Most property types are straight forward. Some of the types are explained in further detail below.

### Numeric properties

Properties with a numeric type, that is `integer` or `number` can be restricted with minimum and maximum values.

Example from `diagnosis.yaml`

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

Example from  `_definitions.yaml`:

```yaml
UUID:
    term:
        $ref: "_terms.yaml#/UUID"
    type: string
    pattern: "^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$"
```

#### Enumerations

Enumerations for a property restrict the values to a set of allowed values. If a value is specified outside of this set, the metadata will fail validation.

Example from `family.yaml`:

```yaml
consanguinity:
    description: >-
      Indicate if consanguinity is present or suspected within a family
    enum:
      - None suspected
      - Present
      - Suspected
      - Unknown
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

It is common practice to put the term definitions into a file called `_terms.yaml` and refer to them from a base schema.

In the `_terms.yaml`, this would look like this:

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

In the example below from the `medical_history.yaml`, we can see that property itself is defined in both the NCI Thesaurus as well as the Human Phenotype Ontology by using two `termDef` entries. 

Each enum is also linked to an NCI Thesaurus entry using the `enumDef` syntax.

```yaml
coronary_artery_disease:
    description: >
      Reported Coronary Artery disease in the participant (HARMONIZED)
    enum:
      - "Positive"
      - "Negative"
      - "Reported Unknown"
      - "Not Reported"
      - "Not Applicable"
    termDef:
       - term: coronary_artery_disease
         source: NCI Thesaurus
         term_id: C26732
         term_version: 19.03d (Release date:2019-03-25)
    termDef:
       - term: coronary_artery_disease
         source: hp
         term_id: HP:0001677
         term_version: "2019-04-15"
    enumDef:
       - enumeration: Positive
         source: NCI Thesaurus
         term_id: C38758
         version_date: 19.03d (Release date:2019-03-25)
       - enumeration: Negative
         source: NCI Thesaurus
         term_id: C38757
         version_date: 19.03d (Release date:2019-03-25)
       - enumeration: Reported Unknown
         source: NCI Thesaurus
         term_id: C17998
         version_date: 19.03d (Release date:2019-03-25)
       - enumeration: Not Reported
         source: NCI Thesaurus
         term_id: C43234
         version_date: 19.03d (Release date:2019-03-25)
       - enumeration: Not Applicable
         source: NCI Thesaurus
         term_id: C48660
         version_date: 19.03d (Release date:2019-03-25)
```
