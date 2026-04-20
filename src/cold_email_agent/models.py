from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Lead:
    name: str
    company: str
    website: str
    role: str
    linkedin_url: str = ""

    @property
    def display_name(self) -> str:
        return f"{self.name} @ {self.company}"


@dataclass
class CampaignConfig:
    sender_name: str
    sender_company: str
    sender_role: str
    sender_email: str
    product_name: str
    product_pitch: str
    campaign_goal: str
    tone: str
    length_preference: str
    call_to_action: str
    value_props: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    research_model: str = "gemini-2.5-flash-lite"
    writing_model: str = "gemini-2.5-flash-lite"
    review_model: str = "gemini-2.5-flash-lite"
    reasoning_effort: str = "medium"
    search_country: str = ""


@dataclass
class Signal:
    label: str
    detail: str
    why_it_matters: str
    source_url: str = ""
    confidence: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchResult:
    status: str
    summary: str
    personalization_angle: str
    signals: list[Signal] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["signals"] = [signal.to_dict() for signal in self.signals]
        return payload


@dataclass
class EmailDraft:
    subject: str
    body: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewResult:
    status: str
    score: int
    final_subject: str
    final_body: str
    notes: list[str] = field(default_factory=list)
    personalization_checks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LeadOutput:
    name: str
    company: str
    website: str
    role: str
    linkedin_url: str
    research_status: str
    review_status: str
    subject: str
    body: str
    personalization_angle: str
    signal_summary: str
    signals_json: str
    review_notes: str
    warnings: str
    error: str = ""
