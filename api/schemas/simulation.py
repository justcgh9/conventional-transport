from pydantic import BaseModel


class ScenarioRequestSchema(BaseModel):
    scenario: str
