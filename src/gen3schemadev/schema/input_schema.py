from typing import List, Literal, Optional
import yaml
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    AnyUrl,
    ValidationError
)

class EnumValue(BaseModel):
    """Single enum value"""
    name: str = Field(description="The name of the enum value.")

class Property(BaseModel):
    """Schema for gen3 property"""
    name: str = Field(description="The name of the property.")
    type: Literal['string', 'integer', 'number', 'boolean', 'datetime', 'enum'] = Field(
        description="The data type of the property."
    )
    description: str = Field(
        description="A human-readable description of the property."
    )
    required: bool = Field(
        default=False,
        description="Whether this property is required for the entity."
    )
    enums: Optional[List[EnumValue]] = Field(
        default=None,
        description="A list of possible values if the type is 'enum'."
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

class Entity(BaseModel):
    """A data entity (node) in the model."""
    name: str = Field(description="The unique name of the entity.")
    description: str = Field(description="A human-readable description of the entity.")
    category: str = Field(description="The category the entity belongs to.")
    properties: List[Property] = Field(
        default_factory=list,
        description="A list of properties for the entity."
    )

class Link(BaseModel):
    """A relationship between entities."""
    parent: str = Field(description="The parent entity in the relationship.")
    multiplicity: Literal['one_to_many', 'many_to_one', 'one_to_one', 'many_to_many'] = Field(
        description="The cardinality of the relationship."
    )
    child: str = Field(description="The child entity in the relationship.")

class DataModel(BaseModel):
    """
    Schema to validate the data model configuration file.
    """
    version: str = Field(
        pattern=r'^\d+\.\d+\.\d+$',
        description="The semantic version of the configuration file."
    )
    url: AnyUrl = Field(description="The URL to the data portal.")
    entities: List[Entity] = Field(
        description="A list of data entities (nodes) in the model."
    )
    links: List[Link] = Field(
        description="A list of relationships between entities."
    )

    class Config:
        # Disallows any properties not defined in the model, matching 'additionalProperties: false'
        extra = 'forbid'