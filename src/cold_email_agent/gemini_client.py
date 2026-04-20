from __future__ import annotations

import json
import os
from typing import Any

from cold_email_agent.models import CampaignConfig, EmailDraft, Lead, ResearchResult, ReviewResult, Signal
from cold_email_agent.prompts import (
    draft_system_prompt,
    draft_user_prompt,
    research_collection_prompt,
    research_system_prompt,
    research_structuring_prompt,
    research_user_prompt,
    review_system_prompt,
    review_user_prompt,
)


class GeminiLeadProcessor:
    def __init__(self, api_key: str | None = None):
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError(
                "The google-genai package is required. Install dependencies with `pip install -r requirements.txt`."
            ) from exc

        resolved_api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not resolved_api_key:
            raise RuntimeError(
                "No Gemini API key found. Pass --api-key or set GEMINI_API_KEY before running the CLI."
            )

        self.genai = genai
        self.types = types
        self.client = genai.Client(api_key=resolved_api_key)

    def research_lead(self, lead: Lead, campaign: CampaignConfig) -> ResearchResult:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["status", "summary", "personalization_angle", "signals", "warnings"],
            "properties": {
                "status": {"type": "string"},
                "summary": {"type": "string"},
                "personalization_angle": {"type": "string"},
                "warnings": {"type": "array", "items": {"type": "string"}},
                "signals": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["label", "detail", "why_it_matters", "source_url", "confidence"],
                        "properties": {
                            "label": {"type": "string"},
                            "detail": {"type": "string"},
                            "why_it_matters": {"type": "string"},
                            "source_url": {"type": "string"},
                            "confidence": {"type": "string"},
                        },
                    },
                },
            },
        }

        raw_research = self._grounded_research_text(
            model=campaign.research_model,
            system_prompt=research_system_prompt(),
            user_prompt=research_collection_prompt(lead, campaign),
            thinking_budget=self._thinking_budget(campaign.reasoning_effort),
        )
        payload = self._structured_response(
            model=campaign.research_model,
            schema=schema,
            system_prompt=research_system_prompt(),
            user_prompt=research_structuring_prompt(raw_research),
            thinking_budget=self._thinking_budget(campaign.reasoning_effort),
        )
        print(
                f"[debug] example signal for {lead.display_name}: "
                f"{payload['signals']}"
            )
        return ResearchResult(
            status=payload["status"],
            summary=payload["summary"],
            personalization_angle=payload["personalization_angle"],
            signals=[self._coerce_signal(signal) for signal in payload["signals"]],
            warnings=payload["warnings"],
        )

    def draft_email(self, lead: Lead, campaign: CampaignConfig, research: ResearchResult) -> EmailDraft:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["subject", "body", "rationale"],
            "properties": {
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "rationale": {"type": "string"},
            },
        }
        payload = self._structured_response(
            model=campaign.writing_model,
            schema=schema,
            system_prompt=draft_system_prompt(),
            user_prompt=draft_user_prompt(lead, campaign, research),
            thinking_budget=self._thinking_budget(campaign.reasoning_effort),
        )
        return EmailDraft(**payload)

    def review_email(
        self,
        lead: Lead,
        campaign: CampaignConfig,
        research: ResearchResult,
        draft: EmailDraft,
    ) -> ReviewResult:
        schema = {
            "type": "object",
            #return no other keys
            "additionalProperties": False,
            "required": [
                "status",
                "score",
                "final_subject",
                "final_body",
                "notes",
                "personalization_checks",
            ],
            "properties": {
                "status": {"type": "string"},
                "score": {"type": "integer"},
                "final_subject": {"type": "string"},
                "final_body": {"type": "string"},
                "notes": {"type": "array", "items": {"type": "string"}},
                "personalization_checks": {"type": "array", "items": {"type": "string"}},
            },
        }
        payload = self._structured_response(
            model=campaign.review_model,
            schema=schema,
            system_prompt=review_system_prompt(),
            user_prompt=review_user_prompt(lead, campaign, research, draft.subject, draft.body),
            thinking_budget=self._thinking_budget(campaign.reasoning_effort),
        )
        return ReviewResult(**payload)

    def _structured_response(
        self,
        *,
        model: str,
        schema: dict[str, Any],
        system_prompt: str,
        user_prompt: str,
        thinking_budget: int,
    ) -> dict[str, Any]:
        config = self.types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_json_schema=schema,
            thinking_config=self.types.ThinkingConfig(thinking_budget=thinking_budget),
        )
        response = self.client.models.generate_content(
            model=model,
            contents=user_prompt,
            config=config,
        )
        return json.loads(response.text)

    def _grounded_research_text(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        thinking_budget: int,
    ) -> str:
        grounding_tool = self.types.Tool(google_search=self.types.GoogleSearch())
        config = self.types.GenerateContentConfig(
            system_instruction=system_prompt,
            thinking_config=self.types.ThinkingConfig(thinking_budget=thinking_budget),
            tools=[grounding_tool],
        )
        response = self.client.models.generate_content(
            model=model,
            contents=user_prompt,
            config=config,
        )
        return response.text

    def _validate_keys(self, payload: dict[str, Any], schema: dict[str, Any]) -> None:
        required = set(schema.get("required", []))
        missing = sorted(required - set(payload))
        if missing:
            raise ValueError(f"Model response missing required keys: {', '.join(missing)}")

    def _coerce_signal(self, payload: Any) -> Signal:
        if isinstance(payload, str):
            return Signal(
                label="Research signal",
                detail=payload.strip(),
                why_it_matters=payload.strip(),
                source_url="",
                confidence="medium",
            )

        if not isinstance(payload, dict):
            return Signal(
                label="Research signal",
                detail=str(payload),
                why_it_matters=str(payload),
                source_url="",
                confidence="low",
            )

        detail = str(payload.get("detail") or payload.get("description") or payload.get("signal") or "")
        why_it_matters = str(
            payload.get("why_it_matters")
            or payload.get("why")
            or payload.get("relevance")
            or payload.get("why_it_matters_for_campaign")
            or detail
        )

        return Signal(
            label=str(payload.get("label") or payload.get("signal") or payload.get("title") or "Research signal"),
            detail=detail,
            why_it_matters=why_it_matters,
            source_url=str(payload.get("source_url") or payload.get("source") or payload.get("url") or ""),
            confidence=str(payload.get("confidence") or "medium"),
        )

    def _extract_json_object(self, text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError(f"Expected JSON object in model response, got: {text!r}")
        return cleaned[start : end + 1]

    def _thinking_budget(self, reasoning_effort: str) -> int:
        effort = reasoning_effort.lower()
        if effort in {"none", "minimal", "low"}:
            return 512
        if effort == "medium":
            return 2048
        if effort == "high":
            return 4096
        return 10240
