from __future__ import annotations

import json
from dataclasses import asdict

from cold_email_agent.io_utils import JsonlLogger
from cold_email_agent.models import CampaignConfig, EmailDraft, Lead, LeadOutput, ResearchResult, ReviewResult, Signal


class ColdEmailPipeline:
    def __init__(self, processor, logger: JsonlLogger, debug_signal: bool = False):
        self.processor = processor
        self.logger = logger
        self.debug_signal = debug_signal

    def run(self, leads: list[Lead], campaign: CampaignConfig) -> list[LeadOutput]:
        self.logger.log(
            "run_started",
            lead_count=len(leads),
            research_model=campaign.research_model,
            writing_model=campaign.writing_model,
            review_model=campaign.review_model,
        )
        outputs = [self._process_lead(lead, campaign) for lead in leads]
        self.logger.log("run_completed", lead_count=len(leads))
        return outputs

    def _process_lead(self, lead: Lead, campaign: CampaignConfig) -> LeadOutput:
        self.logger.log("lead_started", lead=asdict(lead))
        try:
            research = self._research(lead, campaign)
            draft = self._draft(lead, campaign, research)
            review = self._review(lead, campaign, research, draft)
            output = self._build_output(lead, research, review, "")
            self.logger.log(
                "lead_completed",
                lead=lead.display_name,
                research_status=research.status,
                review_status=review.status,
                score=review.score,
            )
            return output
        except Exception as exc:  # noqa: BLE001
            self.logger.log("lead_failed", lead=lead.display_name, error=str(exc))
            fallback_research = fallback_research_result(lead)
            fallback_review = fallback_review_result(lead, campaign, fallback_research, str(exc))
            return self._build_output(lead, fallback_research, fallback_review, str(exc))

    def _research(self, lead: Lead, campaign: CampaignConfig) -> ResearchResult:
        self.logger.log("stage_started", lead=lead.display_name, stage="research")
        research = self.processor.research_lead(lead, campaign)
        if self.debug_signal and research.signals:
            self.logger.log(
                "debug_signal",
                lead=lead.display_name,
                example_signal=research.signals[0].to_dict(),
            )
        self.logger.log("stage_completed", lead=lead.display_name, stage="research", payload=research.to_dict())
        return research

    def _draft(self, lead: Lead, campaign: CampaignConfig, research: ResearchResult) -> EmailDraft:
        self.logger.log("stage_started", lead=lead.display_name, stage="draft")
        draft = self.processor.draft_email(lead, campaign, research)
        self.logger.log("stage_completed", lead=lead.display_name, stage="draft", payload=draft.to_dict())
        return draft

    def _review(
        self,
        lead: Lead,
        campaign: CampaignConfig,
        research: ResearchResult,
        draft: EmailDraft,
    ) -> ReviewResult:
        self.logger.log("stage_started", lead=lead.display_name, stage="review")
        review = self.processor.review_email(lead, campaign, research, draft)
        self.logger.log("stage_completed", lead=lead.display_name, stage="review", payload=review.to_dict())
        return review

    def _build_output(
        self,
        lead: Lead,
        research: ResearchResult,
        review: ReviewResult,
        error: str,
    ) -> LeadOutput:
        signal_summary = " | ".join(f"{signal.label}: {signal.detail}" for signal in research.signals)
        warnings = " | ".join(research.warnings)
        review_notes = " | ".join(review.notes + review.personalization_checks)
        return LeadOutput(
            name=lead.name,
            company=lead.company,
            website=lead.website,
            role=lead.role,
            linkedin_url=lead.linkedin_url,
            research_status=research.status,
            review_status=review.status,
            subject=review.final_subject,
            body=review.final_body,
            personalization_angle=research.personalization_angle,
            signal_summary=signal_summary,
            signals_json=json.dumps([signal.to_dict() for signal in research.signals], ensure_ascii=False),
            review_notes=review_notes,
            warnings=warnings,
            error=error,
        )


def fallback_research_result(lead: Lead) -> ResearchResult:
    return ResearchResult(
        status="fallback",
        summary="Research failed, so this draft is based only on the provided lead fields.",
        personalization_angle=f"Reference {lead.company} and the lead's role without adding unsupported claims.",
        signals=[
            Signal(
                label="Provided lead data",
                detail=f"{lead.name} is listed as {lead.role} at {lead.company}.",
                why_it_matters="This is the only verified information available for fallback drafting.",
                source_url=lead.website,
                confidence="high",
            )
        ],
        warnings=["Automated research failed; review this email carefully before sending."],
    )


def fallback_review_result(
    lead: Lead,
    campaign: CampaignConfig,
    research: ResearchResult,
    error: str,
) -> ReviewResult:
    subject = f"{campaign.product_name} for {lead.company}"
    body = (
        f"Hi {lead.name},\n\n"
        f"I noticed you're the {lead.role} at {lead.company}. "
        f"I'm reaching out because {campaign.product_pitch}\n\n"
        f"If helpful, I can share a few ideas on how this could support {campaign.campaign_goal.lower()}.\n\n"
        f"{campaign.call_to_action}\n\n"
        f"Best,\n{campaign.sender_name}"
    )
    notes = [f"Fallback draft used because the full pipeline failed: {error}"]
    notes.extend(research.warnings)
    return ReviewResult(
        status="fallback",
        score=40,
        final_subject=subject,
        final_body=body,
        notes=notes,
        personalization_checks=["Only provided lead data was used."],
    )
