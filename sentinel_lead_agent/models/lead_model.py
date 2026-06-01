from pydantic import BaseModel

class Lead(BaseModel):
    company_name: str
    website: str
    score: int
