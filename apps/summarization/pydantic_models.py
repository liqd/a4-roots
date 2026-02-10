"""Pydantic models for summarization responses."""

from pydantic import BaseModel
from pydantic import Field


class SummaryItem(BaseModel):
    """Response model for summarization."""

    title: str = Field(description="Title of the summary")
    summary: str = Field(description="The summary of the text or document")
    key_points: list[str] = Field(
        default_factory=list,
        description="Important points or keywords extracted from the text or document",
    )


class ModuleItem(BaseModel):
    """Response model for module summarization."""

    module_name: str = Field(description="Name of the module")
    summary: str = Field(description="Summary of the module")
    key_points: list[str] = Field(
        default_factory=list, description="Key points of the module"
    )
    phase_status: str = Field(
        description="Phase status: 'past' (in the past), 'active' (currently running), 'upcoming' (in the future)"
    )
    link: str = Field(description="Link to the module")


class SummaryResponse(BaseModel):
    """Response model for summarization."""

    summary_items: list[SummaryItem] = Field(
        default_factory=list,
        description=(
            "List of summary items. Each item contains: "
            "title, summary, key_points (list of important points)"
        ),
    )
    module_items: list[ModuleItem] = Field(
        default_factory=list,
        description=(
            "List of module items. Each item contains: "
            "module_name, summary, key_points (list of important points), "
            "phase_status (past/active/upcoming), link (URL to the module)"
        ),
    )
