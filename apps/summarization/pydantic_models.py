"""Pydantic models for summarization responses."""

from pydantic import BaseModel
from pydantic import Field


class SummaryItem(BaseModel):
    """Response model for summarization."""

    title: str = Field(description="Title of the summary")
    summary: str = Field(description="Die Zusammenfassung des Textes oder Bildes")
    key_points: list[str] = Field(
        default_factory=list,
        description="Wichtige Punkte oder Stichworte aus dem Text oder Bild",
    )


class ModuleItem(BaseModel):
    """Response model for module summarization."""

    module_name: str = Field(description="Name of the module")
    summary: str = Field(description="Summary of the module")
    key_points: list[str] = Field(
        default_factory=list, description="Key points of the module"
    )
    phase_status: str = Field(
        description="Status der Phase: 'past' (Vergangenheit), 'active' (läuft gerade), 'upcoming' (Zukunft)"
    )
    link: str = Field(description="Link to the module")


class SummaryResponse(BaseModel):
    """Response model for summarization."""

    summary_items: list[SummaryItem] = Field(
        default_factory=list,
        description="Liste von Zusammenfassungs-Items. Jedes Item enthält: title (Titel), summary (Zusammenfassung), key_points (Liste von wichtigen Punkten)",
    )
    module_items: list[ModuleItem] = Field(
        default_factory=list,
        description="Liste von Modul-Items. Jedes Item enthält: module_name (Modulname), summary (Zusammenfassung), key_points (Liste von wichtigen Punkten), phase_status (past/active/upcoming), link (Link zum Modul)",
    )
