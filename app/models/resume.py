from typing import Optional

from pydantic import BaseModel, Field


class ResumeProfile(BaseModel):

    name: Optional[str] = None

    email: Optional[str] = None

    phone: Optional[str] = None

    location: Optional[str] = None

    headline: Optional[str] = None

    professional_summary: Optional[str] = None

    skills: list[str] = Field(
        default_factory=list
    )

    experience: list[str] = Field(
        default_factory=list
    )

    education: list[str] = Field(
        default_factory=list
    )

    projects: list[str] = Field(
        default_factory=list
    )

    certifications: list[str] = Field(
        default_factory=list
    )

    achievements: list[str] = Field(
        default_factory=list
    )

    links: list[str] = Field(
        default_factory=list
    )