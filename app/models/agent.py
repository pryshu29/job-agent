from typing import Literal, Optional

from pydantic import BaseModel, Field


class ProfileUpdate(BaseModel):

    field: str = Field(
        description=(
            "The candidate profile field that should be "
            "created or updated."
        )
    )

    value: str = Field(
        description=(
            "The value that should be stored for this "
            "candidate profile field."
        )
    )


class AgentDecision(BaseModel):

    intent: Literal[
        "profile_update",
        "resume",
        "job_search",
        "job_analysis",
        "career_recommendation",
        "application",
        "interview",
        "opportunity",
        "general_career",
        "out_of_scope",
    ]

    profile_updates: list[ProfileUpdate] = Field(
        default_factory=list
    )

    response: str = Field()

    next_question: Optional[str] = Field(
        default=None
    )

    needs_clarification: bool = Field(
        default=False
    )