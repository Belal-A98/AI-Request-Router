"""Versioned reviewer decision input contracts."""
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Approval(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=1)
    category: str
    priority: str

    @field_validator('category')
    @classmethod
    def allowed_category(cls, value):
        if value not in {'sales', 'support', 'billing', 'other'}:
            raise ValueError('Unsupported category')
        return value

    @field_validator('priority')
    @classmethod
    def allowed_priority(cls, value):
        if value not in {'low', 'normal', 'high'}:
            raise ValueError('Unsupported priority')
        return value


class Rejection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=255)
