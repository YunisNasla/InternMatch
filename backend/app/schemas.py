from typing import Literal

from pydantic import BaseModel

from app import taxonomy

RoleTypeOrNonStem = Literal[tuple(taxonomy.ROLE_TYPES) + (taxonomy.NON_STEM,)]
IndustryOrOther = Literal[tuple(taxonomy.INDUSTRIES) + (taxonomy.OTHER,)]


class TagResult(BaseModel):
    role_type: RoleTypeOrNonStem
    work_arrangement: Literal[tuple(taxonomy.WORK_ARRANGEMENTS)]


class CompanyTagResult(BaseModel):
    industry: IndustryOrOther
    confidence: Literal["high", "low"]
