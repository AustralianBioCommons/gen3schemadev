# Gen3SchemaDev 2.0 Planning

## Target Audience:
- Junior developer with minimal data modelling experience

## Key functions:
1. Schema Development in LinkML to gen3 jsonschema
2. Schema visualisation with ddvis
3. Synthetic Data Generation (maybe move this to a separate repo)
	1. Synthetic data is useful to see what the data structure and links will look like, as well as do a test upload.

## What the repo will be:
1. Python Toolset
	1. Users can use the classes and functions in the toolset in their own dev environment
2. Documentation
	1. Conceptual data modelling in gen3
	2. Linkml syntax for gen3
	3. Source code documentation
	4. Example usage   
3. Templates
	1. linkml templates
4. Examples
	1. Full schema examples

## Github Workflows:
- Build
- Test
- Publish pypi on release
- Update sphinx docs on release


---


# Business Analysis

## Use Cases
1. As a data modeller, I want to write the logic of my data model, and I want a gen3 jsonschema at the end, so that I can upload it straight to gen3.
1. As a data modeller, I want to have a UI type experience for defining my data model, so that I don't have to work with low level serialisation syntax.
1. As a new data modeller, I want to learn how to define entities, relationships, properties, etc, in a data model
1. As a developer, I want to interatively view my graph data model in a browser window.


## AI assisted use cases

### **UC1: Guided Learning for New Modelers**
*   **As a:** New Data Modeler
*   **I want to:** Access tutorials and guided workflows.
*   **So that I can:** Learn the core concepts of data modeling (such as defining entities, properties, and relationships) while using the tool.

**Acceptance Criteria:**
*   The system should offer documentation and tutorials for the tool.
*   The tool should provide templates or examples of common data modeling patterns that a new user can explore.

### **UC2: Automated Schema Generation**
*   **As a:** Data Modeler
*   **I want to:** Define a data model using a high-level interface or language.
*   **So that I can:** Automatically generate a compliant Gen3 data dictionary without needing to write or debug the low-level syntax myself.

**Acceptance Criteria:**
*   The system must provide an input method (UI or domain-specific language) that does not require low level editing.
*   There must be a function to trigger the generation of a Gen3 JSON Schema file.
*   The generated schema must be valid and ready for direct upload into a Gen3 environment.


### **UC3: Interactive Model Visualization**
*   **As a:** Developer
*   **I want to:** View an interactive, real-time graph visualization of the data model in a browser window.
*   **So that I can:** Immediately validate the structure, visualise relationships, and understand the impact of changes as I iterate on the model.

**Acceptance Criteria:**
*   The system must render the data model as a graph diagram in a web browser.
*   The visualization must update with a manual refresh to reflect any changes made to the model.
*   The user must be able to interact with the graph (e.g., pan, zoom, click on nodes for details).


### **UC4: Model Validation**
*   **As a:** Developer
*   **I want to:** Know when my gen3 data dictionary is valid for input into the Gen3 system
*   **So that I can:** Ensure the model is correct and can be uploaded to Gen3.

**Acceptance Criteria:**
*   The system provides a `validate model` function that checks the entire data model against the gen3 [metaschema](https://github.com/uc-cdis/dictionaryutils/blob/master/dictionaryutils/schemas/metaschema.yaml).
*   The system checks the data model against gen3 specific business rules.
*   Validation errors and warnings are returned to the user, with each item containing a clear, human-readable message explaining the issue and referencing the specific entity or property at fault.
*   The system prevents the generation of a JSON schema if there are critical errors present in the model.


### **UC5: Command-Line Project Initialization**

*   **As a:** Developer
*   **I want to:** Be able to initialise a modelling development directory
*   **So that I can:** Immediately start working in a standardised environment with structure and examples.

**Acceptance Criteria:**
*   The tool creates a structured directory as a starting point
*   The tool also populates templates and examples for users to get started with


***

## Are there things that already do this?
|Use Case|Existing Solutions|Pros|Cons|
|--------|------------------|-----|-----|
|UC1|||||
|UC2|[linkml](https://linkml.io/linkml/intro/tutorial01.html)||||
|UC3|[dictionary-visualiser](https://github.com/bioteam/dictionary-visualizer)|looks exactly like gen3|||
|UC4|look into gdcdictionary or dict utils for business logic||||
|UC5|||||
|UC6|||||

