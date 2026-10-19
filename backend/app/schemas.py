from typing import Literal

from pydantic import BaseModel, Field

from app import taxonomy

RoleType = Literal[tuple(taxonomy.ROLE_TYPES)]
RoleTypeOrNonStem = Literal[tuple(taxonomy.ROLE_TYPES) + (taxonomy.NON_STEM,)]
IndustryOrOther = Literal[tuple(taxonomy.INDUSTRIES) + (taxonomy.OTHER,)]


class TagResult(BaseModel):
    role_type: RoleTypeOrNonStem
    work_arrangement: Literal[tuple(taxonomy.WORK_ARRANGEMENTS)]


class CompanyTagResult(BaseModel):
    industry: IndustryOrOther
    confidence: Literal["high", "low"]


class Location(BaseModel):
    city: str | None = None
    state: str | None = None


class Education(BaseModel):
    school: str
    degree: str | None = None
    major: str | None = None
    grad_date: str | None = None
    gpa: float | None = None


class Skills(BaseModel):
    programming_languages: list[str] = []
    frameworks_libraries: list[str] = []
    software_tools: list[str] = []
    hardware_fabrication: list[str] = []
    lab_techniques: list[str] = []
    domain_knowledge: list[str] = []


class Experience(BaseModel):
    title: str
    org: str
    start: str | None = None
    end: str | None = None
    highlights: list[str] = []


class Project(BaseModel):
    name: str
    tech: list[str] = []
    summary: str


class Profile(BaseModel):
    """Prompt 1's output. Lives in the browser; the server never stores it."""

    is_stem: bool
    name: str | None = None
    location: Location = Location()
    education: list[Education] = []
    class_standing: Literal["freshman", "sophomore", "junior", "senior", "masters", "phd", "unknown"]
    skills: Skills = Skills()
    experience: list[Experience] = []
    projects: list[Project] = []
    coursework: list[str] = []
    certifications: list[str] = []
    suggested_role_types: list[RoleType] = Field(default=[], max_length=3)
    parse_warnings: list[str] = []
