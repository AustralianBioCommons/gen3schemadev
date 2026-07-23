from typing import Any, Dict, List, Literal, Optional
from enum import Enum
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    AnyUrl,
)


# Presets shipped with gen3schemadev that a node may extend. These carry
# node-level settings that Gen3 microservices depend on (project's release
# flags, its uniqueKeys on `code`, the DUO consent_codes enumDef), which the
# input language cannot otherwise express.
EXTENDABLE_PRESETS = ('program', 'project', 'core_metadata_collection')


class Property(BaseModel):
    """Schema for gen3 property"""
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    name: str = Field(description="The name of the property.")
    type: Literal[
        'string', 'integer', 'number', 'boolean', 'datetime', 'enum', 'array'
    ] = Field(description="The data type of the property.")
    description: str = Field(description="A human-readable description of the property.")
    required: bool = Field(default=False, description="Whether this property is required for the node.")
    # Accepts either a list of EnumValue objects or a list of strings (for YAML input like in input_example.yml)
    enums: Optional[List[str]] = Field(
        default=None,
        description="A string list of possible values."
    )

    # Passthrough annotations. These are emitted verbatim alongside the
    # property so the input language can express the parts of JSON Schema the
    # formatters do not build themselves.
    default: Optional[Any] = Field(
        default=None,
        description="Default value applied when the property is absent.",
    )
    format: Optional[str] = Field(
        default=None,
        description="JSON Schema format annotation, e.g. 'date-time'.",
    )
    items: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Item schema for 'array' properties. Overrides the default {'type': 'string'}.",
    )
    enum_def: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        validation_alias=AliasChoices('enum_def', 'enumDef'),
        serialization_alias='enumDef',
        description="Ontology term definitions accompanying an enum, e.g. DUO consent codes.",
    )
    pattern: Optional[str] = Field(
        default=None,
        description="Regular expression the value must match.",
    )
    term: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Term reference block, e.g. {'$ref': '_terms.yaml#/datetime'}.",
    )

    @field_validator('enums')
    def check_enums_for_enum_type(cls, v, info):
        """
        Validates that 'enums' is provided if 'type' is 'enum',
        matching the conditional requirement in the schema.
        """
        if info.data.get('type') == 'enum' and v is None:
            raise ValueError("The 'enums' field is required when the property type is 'enum'")
        return v


# Inherit from str and Enum to create a string-based enumeration
class CategoryEnum(str, Enum):
    ADMINISTRATIVE = "administrative"
    ANALYSIS = "analysis"
    BIOSPECIMEN = "biospecimen"
    CLINICAL = "clinical"
    DATA_FILE = "data_file"
    METADATA_FILE = "metadata_file"
    NOTATION = "notation"
    INDEX_FILE = "index_file"
    CLINICAL_ASSESSMENT = "clinical_assessment"
    MEDICAL_HISTORY = "medical_history"
    DATA_OBSERVATIONS = "data_observations"
    EXPERIMENTAL_METHODS = "experimental_methods"
    SUBJECT_CHARACTERISTICS = "subject_characteristics"
    IMAGING = "imaging"
    STUDY_ADMINISTRATION = "study_administration"
    SATELLITE = "satellite"
    RADAR = "radar"
    STREAM_GAUGE = "stream_gauge"
    WEATHER_STATION = "weather_station"


class node(BaseModel):
    """A data node (node) in the model."""
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    name: str = Field(description="The unique name of the node.")
    description: Optional[str] = Field(default=None, description="A human-readable description of the node.")
    category: Optional[CategoryEnum] = Field(
        default=None,
        description="The category the node belongs to. Optional when the node extends a preset.",
    )
    properties: List[Property] = Field(default_factory=list, description="A list of properties for the node.")

    extends: Optional[Literal[EXTENDABLE_PRESETS]] = Field(
        default=None,
        description=(
            "Merge this node onto a packaged preset instead of building it from scratch. "
            "Anything declared here overrides the preset; everything else is inherited."
        ),
    )

    # Node-level Gen3 settings. Each of these names a key in the generated
    # schema; leaving one unset inherits the metaschema default rather than
    # writing null.
    submittable: Optional[bool] = Field(default=None, description="Whether data can be submitted to this node.")
    validators: Optional[List[str]] = Field(default=None, description="Additional validator functions to run.")
    system_properties: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices('system_properties', 'systemProperties'),
        serialization_alias='systemProperties',
        description="Non-user-facing properties managed by the Gen3 backend.",
    )
    unique_keys: Optional[List[List[str]]] = Field(
        default=None,
        validation_alias=AliasChoices('unique_keys', 'uniqueKeys'),
        serialization_alias='uniqueKeys',
        description="Property combinations the validator enforces as unique.",
    )
    required: Optional[List[str]] = Field(
        default=None,
        description=(
            "Explicit list of required property names. Takes precedence over per-property "
            "'required: true' flags when both are given."
        ),
    )
    namespace: Optional[str] = Field(default=None, description="Namespace override for this node.")
    program: Optional[str] = Field(default=None, description="Program scope, '*' by default.")
    project: Optional[str] = Field(default=None, description="Project scope, '*' by default.")

    @model_validator(mode='after')
    def check_category_present_without_extends(self):
        """
        A node built from scratch needs a category; one that extends a preset
        inherits the preset's category unless it overrides it.

        This is a model validator rather than a field validator because a field
        validator does not run when the field is omitted altogether, which is
        precisely the case being guarded against.
        """
        if self.category is None and self.extends is None:
            raise ValueError(
                "'category' is required unless the node sets 'extends' to inherit from a preset"
            )
        return self


class Link(BaseModel):
    """A relationship between nodes."""
    model_config = ConfigDict(extra='forbid')

    parent: str = Field(description="The parent node in the relationship.")
    multiplicity: Literal['one_to_many', 'many_to_one', 'one_to_one', 'many_to_many'] = Field(description="The cardinality of the relationship.")
    child: str = Field(description="The child node in the relationship.")


class DataModel(BaseModel):
    """
    Schema to validate the data model configuration file.
    """
    model_config = ConfigDict(extra='forbid')

    version: str = Field(pattern=r'^\d+\.\d+\.\d+$', description="The semantic version of the configuration file.")
    url: AnyUrl = Field(description="The URL to the data portal.")
    nodes: List[node] = Field(description="A list of data nodes (nodes) in the model.")
    links: List[Link] = Field(description="A list of relationships between nodes.")
    definitions: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Extra shared definitions merged into the generated _definitions.yaml, "
            "so custom enums and refs survive regeneration."
        ),
    )
