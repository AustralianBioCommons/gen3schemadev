from typing import List, Literal, Optional
from enum import Enum 
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    AnyUrl,
)


class Property(BaseModel):
    """Schema for gen3 property"""
    name: str = Field(description="The name of the property.")
    type: Literal[
        'string', 'integer', 'number', 'boolean', 'datetime', 'enum'
    ] = Field(description="The data type of the property.")
    description: str = Field(description="A human-readable description of the property.")
    required: bool = Field(default=False, description="Whether this property is required for the node.")
    # Accepts either a list of EnumValue objects or a list of strings (for YAML input like in input_example.yml)
    enums: Optional[List[str]] = Field(
        default=None,
        description="A string list of possible values."
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

    class ConfigDict:
        extra = 'forbid'


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
    name: str = Field(description="The unique name of the node.")
    description: Optional[str] = Field(default=None, description="A human-readable description of the node.")
    category: CategoryEnum = Field(description="The category the node belongs to.")
    properties: List[Property] = Field(default_factory=list, description="A list of properties for the node.")
    
    class ConfigDict:
        extra = 'forbid'


class Link(BaseModel):
    """A relationship between nodes."""
    parent: str = Field(description="The parent node in the relationship.")
    multiplicity: Literal['one_to_many', 'many_to_one', 'one_to_one', 'many_to_many'] = Field(description="The cardinality of the relationship.")
    child: str = Field(description="The child node in the relationship.")
    
    class ConfigDict:
        extra = 'forbid'


class DataModel(BaseModel):
    """
    Schema to validate the data model configuration file.
    """
    version: str = Field(pattern=r'^\d+\.\d+\.\d+$', description="The semantic version of the configuration file.")
    url: AnyUrl = Field(description="The URL to the data portal.")
    nodes: List[node] = Field(description="A list of data nodes (nodes) in the model.")
    links: List[Link] = Field(description="A list of relationships between nodes.")

    class ConfigDict:
        extra = 'forbid'
