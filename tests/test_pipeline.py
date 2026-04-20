from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from cold_email_agent.config import load_campaign_config
from cold_email_agent.io_utils import JsonlLogger, load_leads, write_output_csv
from cold_email_agent.models import CampaignConfig, EmailDraft, Lead, ResearchResult, ReviewResult, Signal
from cold_email_agent.pipeline import ColdEmailPipeline


class FakeProcessor:
    def research_lead(self, lead: Lead, campaign: CampaignConfig) -> ResearchResult:
        if lead.company == "Broken Co":
            raise RuntimeError("search failed")
        return ResearchResult(
            status="researched",
            summary="The company is hiring GTM roles and launched a new product line.",
            personalization_angle="Connect the launch to pipeline quality and fast response.",
            signals=[
                Signal(
                    label="New launch",
                    detail="They recently launched a self-serve product tier.",
                    why_it_matters="The team may be scaling outbound or lead qualification.",
                    source_url="https://example.com/news",
                    confidence="high",
                )
            ],
            warnings=[],
        )

    def draft_email(self, lead: Lead, campaign: CampaignConfig, research: ResearchResult) -> EmailDraft:
        return EmailDraft(
            subject=f"Idea for {lead.company}",
            body=f"Hi {lead.name},\n\nSaw the launch and thought this might help.\n\nBest,\n{campaign.sender_name}",
            rationale="Uses the launch as the hook.",
        )

    def review_email(
        self,
        lead: Lead,
        campaign: CampaignConfig,
        research: ResearchResult,
        draft: EmailDraft,
    ) -> ReviewResult:
        return ReviewResult(
            status="approved",
            score=86,
            final_subject=draft.subject,
            final_body=draft.body,
            notes=["Grounded in research."],
            personalization_checks=["Opening line references a concrete signal."],
        )


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.campaign = CampaignConfig(
            sender_name="Ava Seller",
            sender_company="Northstar AI",
            sender_role="AE",
            sender_email="ava@example.com",
            product_name="Northstar AI",
            product_pitch="we help reps personalize outbound with company research",
            campaign_goal="book more qualified meetings",
            tone="warm and concise",
            length_preference="short",
            call_to_action="Open to a 15-minute chat next week?",
        )

    def test_pipeline_handles_success_and_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "run.log.jsonl"
            logger = JsonlLogger(log_path)
            pipeline = ColdEmailPipeline(FakeProcessor(), logger)
            results = pipeline.run(
                [
                    Lead("Jane", "Good Co", "https://good.example", "VP Sales"),
                    Lead("John", "Broken Co", "https://broken.example", "CEO"),
                ],
                self.campaign,
            )

            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].review_status, "approved")
            self.assertEqual(results[1].review_status, "fallback")
            self.assertIn("search failed", results[1].error)
            self.assertTrue(log_path.exists())

    def test_csv_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "leads.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["name", "company", "website", "role", "linkedin_url"])
                writer.writeheader()
                writer.writerow(
                    {
                        "name": "Jane",
                        "company": "Acme",
                        "website": "https://acme.test",
                        "role": "VP Sales",
                        "linkedin_url": "",
                    }
                )

            leads = load_leads(csv_path)
            self.assertEqual(leads[0].company, "Acme")

            output_path = Path(temp_dir) / "emails.csv"
            pipeline = ColdEmailPipeline(FakeProcessor(), JsonlLogger(Path(temp_dir) / "log.jsonl"))
            write_output_csv(output_path, pipeline.run(leads, self.campaign))
            self.assertTrue(output_path.exists())

    def test_search_country_accepts_name_and_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "campaign.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "sender_name: Ava",
                        "sender_company: Northstar",
                        "sender_role: AE",
                        "sender_email: ava@example.com",
                        "product_name: Northstar",
                        "product_pitch: Helpful outbound research",
                        "campaign_goal: Book meetings",
                        "tone: concise",
                        "length_preference: short",
                        "call_to_action: Open to a quick chat?",
                        "search_country: Singapore",
                    ]
                ),
                encoding="utf-8",
            )
            config = load_campaign_config(config_path)
            self.assertEqual(config.search_country, "SG")

            config_path.write_text(config_path.read_text(encoding="utf-8").replace("Singapore", "GB"), encoding="utf-8")
            config = load_campaign_config(config_path)
            self.assertEqual(config.search_country, "GB")

    def test_search_country_rejects_invalid_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "campaign.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "sender_name: Ava",
                        "sender_company: Northstar",
                        "sender_role: AE",
                        "sender_email: ava@example.com",
                        "product_name: Northstar",
                        "product_pitch: Helpful outbound research",
                        "campaign_goal: Book meetings",
                        "tone: concise",
                        "length_preference: short",
                        "call_to_action: Open to a quick chat?",
                        "search_country: NotACountry",
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_campaign_config(config_path)


if __name__ == "__main__":
    unittest.main()
