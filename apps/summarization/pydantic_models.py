"""Pydantic models for summarization responses."""

from typing import Optional

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


"""Pydantic models for summarization responses."""


class Stats(BaseModel):
    """Statistics for the project summary header."""

    participants: int = Field(description="Number of participants")
    contributions: int = Field(description="Total number of contributions")
    modules: int = Field(description="Number of modules in the project")


class ModuleSummary(BaseModel):
    """Response model for module summarization."""

    module_name: str = Field(description="Name of the module")
    purpose: str = Field(description="Goal/purpose of the module")
    main_sentiments: list[str] = Field(
        default_factory=list,
        description="Main sentiments or key points from user contributions",
    )
    phase_status: str = Field(
        description="Phase status: 'past', 'active', or 'upcoming'"
    )
    link: str = Field(description="Link to the module")
    first_content: Optional[str] = Field(
        None, description="First content/early signs (for active modules)"
    )


class ProjectSummaryResponse(BaseModel):
    """Response model for complete project summarization."""

    # Header
    title: str = Field(default="Zusammenfassung der Beteiligung")

    # Stats box
    stats: Stats = Field(description="Participation statistics")

    general_summary: str = Field(description="General summary of the entire project")
    general_goals: list[str] = Field(description="Overall goals of the project")
    # Timeline sections
    past_summary: str = Field(description="Summary of what has happened so far")
    past_modules: list[ModuleSummary] = Field(
        default_factory=list,
        description="Modules that are completed (phase_status='past')",
    )

    current_summary: str = Field(description="Summary of what is currently happening")
    current_modules: list[ModuleSummary] = Field(
        default_factory=list,
        description="Modules that are active (phase_status='active')",
    )

    upcoming_summary: str = Field(description="Summary of what will happen")
    upcoming_modules: list[ModuleSummary] = Field(
        default_factory=list,
        description="Modules that are upcoming (phase_status='upcoming')"
    )

class DocumentInputItem(BaseModel):
    """Single document input item with handle and URL."""
    
    handle: str = Field(description="Unique identifier/handle for the document")
    url: str = Field(description="URL of the document")


class DocumentSummaryItem(BaseModel):
    """Response model for a single document summary with handle."""
    
    handle: str = Field(description="Unique identifier/handle for the document")
    summary: str = Field(description="Summary of the document content")


class DocumentSummaryResponse(BaseModel):
    """Response model for multiple document summaries."""
    
    documents: list[DocumentSummaryItem] = Field(
        default_factory=list,
        description="List of document summaries, each with handle and summary",
    )