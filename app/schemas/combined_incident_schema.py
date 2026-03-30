from pydantic import BaseModel
from .incident_schema import IncidentFormSchema
from .client_schema import ClientFormSchema


class CombinedIncidentSchema(BaseModel):
    """Combined incident + clients for single-pass AI extraction."""
    incident: IncidentFormSchema = IncidentFormSchema()
    clients: list[ClientFormSchema] = []
