from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from cold_email_agent.countries import normalize_country
from cold_email_agent.models import CampaignConfig


def load_campaign_config(path: str | Path) -> CampaignConfig:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        if path.suffix.lower() == ".json":
            raw = json.load(handle)
        else:
            raw = yaml.safe_load(handle)
    return CampaignConfig(
        sender_name=_get_required(raw, "sender_name"),
        sender_company=_get_required(raw, "sender_company"),
        sender_role=_get_required(raw, "sender_role"),
        sender_email=_get_required(raw, "sender_email"),
        product_name=_get_required(raw, "product_name"),
        product_pitch=_get_required(raw, "product_pitch"),
        campaign_goal=_get_required(raw, "campaign_goal"),
        tone=_get_required(raw, "tone"),
        length_preference=_get_required(raw, "length_preference"),
        call_to_action=_get_required(raw, "call_to_action"),
        value_props=_get_list(raw, "value_props"),
        constraints=_get_list(raw, "constraints"),
        research_model=raw.get("research_model", "gemini-2.5-flash-lite"),
        writing_model=raw.get("writing_model", "gemini-2.5-flash-lite"),
        review_model=raw.get("review_model", "gemini-2.5-flash-lite"),
        reasoning_effort=raw.get("reasoning_effort", "medium"),
        search_country=normalize_country(str(raw.get("search_country", "") or "")),
    )


def _get_required(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not value:
        raise ValueError(f"Campaign config is missing required field: {key}")
    return str(value)


def _get_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key, [])
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]
