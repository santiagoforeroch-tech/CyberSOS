from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, TypeAdapter, model_validator

CATEGORIES = {"phishing", "fraude/estafa digital", "suplantación", "robo o acceso no autorizado a cuenta", "robo de información", "amenaza/acoso digital", "extorsión cibernética", "malware", "otro"}


class ReportCreate(BaseModel):
    category: str
    description: str = Field(min_length=20, max_length=5000)
    occurred_at: datetime | None = None
    occurred_at_is_approximate: bool = False
    channel: str | None = Field(default=None, max_length=80)
    related_information: dict = Field(default_factory=dict)
    reporter_name: str = Field(min_length=2, max_length=160)
    contact_type: str
    contact_value: str = Field(min_length=3, max_length=200)

    @model_validator(mode="after")
    def validate_values(self):
        if self.category not in CATEGORIES:
            raise ValueError("Selecciona una categoría válida")
        if self.contact_type not in {"email", "phone"}:
            raise ValueError("Selecciona correo o teléfono")
        if self.contact_type == "email":
            TypeAdapter(EmailStr).validate_python(self.contact_value)
        return self


class ReportSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_number: str
    source: str
    category: str
    reporter_name: str
    status: str
    priority: str
    created_at: datetime


class ReportUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None


class ObservationCreate(BaseModel):
    text: str = Field(min_length=2, max_length=3000)

