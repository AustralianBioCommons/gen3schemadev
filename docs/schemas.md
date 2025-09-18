---
title: Schemas
has_children: true
nav_order: 1
---

# Gen3 Schemas

Schemas in Gen3 are written and edited in individual `yaml` files per schema before being compiled into a single json file that is used as the data dictionary for a given gen3 instance.

Schemas are generally structured into three parts:
1. [Descriptors](https://australianbiocommons.github.io/umccr-dictionary/schemas/descriptors.html) - fields that describe the schema itself
1. [Links](https://australianbiocommons.github.io/umccr-dictionary/schemas/links.html) - how this schema links to other schema in the data model
1. [Properties](https://australianbiocommons.github.io/umccr-dictionary/schemas/properties.html) - the fields or attributes of the schema

The aim of this part of the documentation is to help explain the overal structure and individual components of the yaml files to make it easier to understand how to edit them to create a customised dictionary for your purposes.

Navigate to any of the above sections to learn more!

An ['explainer' yaml file](https://github.com/AustralianBioCommons/umccr-dictionary/blob/main/docs/schemas/explainer_schema.yaml) with explanatory comments is also available in the github repo for these docs.

## References

Materials in this documentation was drawn from the resources below as well as from the Slack Gen3 community on CDIS slack.

* [Gen3 Data Dictionary documentation](https://gen3.org/resources/user/dictionary/)
* [Gen3 Data Dictionary repo](https://github.com/uc-cdis/datadictionary)
* [Gen3 Data Modelling webinar slides](https://gen3.org/community/webinars/Webinar_20190509.pdf)
