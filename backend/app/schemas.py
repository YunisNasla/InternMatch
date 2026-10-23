from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from app import taxonomy

RoleType = Literal[tuple(taxonomy.ROLE_TYPES)]
RoleTypeOrNonStem = Literal[tuple(taxonomy.ROLE_TYPES) + (taxonomy.NON_STEM,)]
Industry = Literal[tuple(taxonomy.INDUSTRIES)]
Term = Literal[taxonomy.SUPPORTED_TERMS]
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


ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class FilterState(BaseModel):
    """Search preferences. Defaults match PROMPTS.md; Pydantic enforces every allowed value."""

    # Every list goes into the refinement prompt, so each is capped at its number of options.
    industries: list[Industry] = Field(default=[], max_length=len(taxonomy.INDUSTRIES))  # empty means all
    role_types: list[RoleType] = Field(default=[], max_length=len(taxonomy.ROLE_TYPES))  # empty means all
    home_city: ShortText | None = None
    max_distance_miles: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    work_arrangements: list[Literal["in_person", "hybrid", "remote"]] = Field(
        default=["in_person", "hybrid", "remote"], min_length=1, max_length=3,
    )
    terms: list[Term] = Field(default=["Summer 2027"], min_length=1, max_length=len(taxonomy.SUPPORTED_TERMS))
    posted_within_days: Literal[7, 30] | None = None
    exclude_companies: list[ShortText] = Field(default=[], max_length=50)
    include_keywords: list[ShortText] = Field(default=[], max_length=50)
    exclude_keywords: list[ShortText] = Field(default=[], max_length=50)
    emphasis: ShortText | None = None
    sort_by: Literal["fit_score", "posted"] = "fit_score"


# The refine field table (PROMPTS.md Prompt 4): allowed actions, and whether page 2 shows the field.
# Allowed values come from FilterState above; the prompt's field list must match both.
LIST_ACTIONS = ("set", "add", "remove")
REFINE_FIELDS = {
    "industries": (LIST_ACTIONS, True),
    "role_types": (LIST_ACTIONS, True),
    "home_city": (("set",), True),
    "max_distance_miles": (("set",), True),
    "work_arrangements": (LIST_ACTIONS, True),
    "terms": (LIST_ACTIONS, True),
    "posted_within_days": (("set",), True),
    "exclude_companies": (LIST_ACTIONS, True),
    "include_keywords": (LIST_ACTIONS, False),
    "exclude_keywords": (LIST_ACTIONS, False),
    "emphasis": (("set",), False),
    "sort_by": (("set",), False),
}


class RefineChange(BaseModel):
    field: str
    action: Literal["set", "add", "remove"]
    value: Any = None


class RefineResult(BaseModel):
    intent: Literal["update_filters", "explain", "clarify"]
    changes: list[RefineChange] = []
    reply: str


class Requirement(BaseModel):
    requirement: str
    type: Literal["must", "nice", "inferred"]
    evidence: str
    status: Literal["met", "partial", "not_met"]


class Gate(BaseModel):
    gate: str
    status: Literal["pass", "fail", "needs_check"]
    note: str


def tier_for(score: int) -> str:
    return "strong" if score >= 85 else "good" if score >= 70 else "stretch" if score >= 50 else "long_shot"


class ScoreResult(BaseModel):
    """Prompts 2 + 3 output. The reasoning fields come first, so the score is written last."""

    requirements: list[Requirement]
    eligibility: list[Gate] = []
    fit_score: int = Field(ge=0, le=100)
    tier: Literal["strong", "good", "stretch", "long_shot"]
    confidence: Literal["high", "medium", "low"]
    top_matches: list[str] = []
    key_gaps: list[str] = []
    recruiter_note: str
    resume_tip: str

    @field_validator("top_matches", "key_gaps")
    @classmethod
    def at_most_three(cls, items: list[str]) -> list[str]:
        return items[:3]  # trimming is cheaper than a retry for one extra line

    @model_validator(mode="after")
    def tier_matches_score(self):
        self.tier = tier_for(self.fit_score)  # PROMPTS.md: trust fit_score when the two disagree
        return self
