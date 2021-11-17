## CAD Template yamls

This folder contains template yamls that are used for a base from which to inject properties from the template spreadsheet.

For each 'object' or 'entity' in the spreadsheet, there should exist a template which contains all the information that is either static across schemas or has not yet been automated.

It also contains template `core_metadata_collection`, `_definitions`, `_terms` and `_settings` yamls directly copied from the anvil gdc dictionary for generic definitions.

Schemas for the CAD project are largely based on the Anvil & BioData Catalyst/gtex dictionary with project specific edits.


Proposed additional keywords
============================

The schemas defined here follow jsonschema as closely as possbile,
introducing new keywords as needed.

systemAlias
-----------

For implementation. Allows properties to be stored as different
keywords.  The property listed in the properties section is what the
user will refer to it, and the systemAlias value is what it will be
stored in the database as.

systemProperties
---------------

The property keys listed under systemProperties are properties that
the submitter is not allowed to update.

parentType
---------------

The type of object that the parent relationship points to.
