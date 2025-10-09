# Gen3SchemaDev 2.0 Planning


## Business Analysis


### **UC1: Guided Learning for New Modelers**
*   **As a:** New Data Modeler
*   **I want to:** Access tutorials and guided workflows.
*   **So that I can:** Learn the core concepts of data modeling (such as defining nodes, properties, and relationships) while using the tool.

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
*   Validation errors and warnings are returned to the user, with each item containing a clear, human-readable message explaining the issue and referencing the specific node or property at fault.
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
|UC1|Want to write custom docs| Tailor and curate for our target audience| Info probably already exists out there||
|UC2|[linkml](https://linkml.io/linkml/intro/tutorial01.html)| good docs, and great adaptor for other formats| Have to learn new syntax||
|UC3|[dictionary-visualiser](https://github.com/bioteam/dictionary-visualizer)|looks exactly like gen3| reads from s3||
|UC4|uc-dis/data-simulator|gen3 specific|||
|UC5|Will write own script||||

