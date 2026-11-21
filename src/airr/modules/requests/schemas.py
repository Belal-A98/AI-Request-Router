"""Request intake contract (shared by API and signed webhook)."""
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Intake(BaseModel):
    model_config = ConfigDict(extra='forbid')
    external_id: str = Field(min_length=1, max_length=120)
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=10000)

    @field_validator('external_id', 'subject', 'message')
    @classmethod
    def trimmed(cls, value):
        cleaned = value.strip()
        if not cleaned:
            raise ValueError('May not be blank')
        return cleaned
