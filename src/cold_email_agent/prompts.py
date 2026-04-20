from __future__ import annotations

import textwrap

from cold_email_agent.models import CampaignConfig, Lead, ResearchResult


def research_system_prompt() -> str:
    #remove all preceeding blank character
    return textwrap.dedent(
        """
        You research B2B sales leads for cold outbound.
        Gather only signals that could plausibly improve a personalized email.
        Prefer recent and company-first evidence such as the company site, product pages,
        press releases, blogs, job postings, and credible third-party coverage.
        If evidence is weak, say so instead of guessing.
        """
    ).strip()


def research_user_prompt(lead: Lead, campaign: CampaignConfig) -> str:
    geography_hint = (
        f"- Search geography hint: prioritize sources relevant to country code {campaign.search_country}\n"
        if campaign.search_country
        else ""
    )
    return textwrap.dedent(
        f"""
        Research this lead and company for a cold outbound campaign.

        Lead:
        - Name: {lead.name}
        - Company: {lead.company}
        - Website: {lead.website}
        - Role: {lead.role}
        - LinkedIn URL: {lead.linkedin_url or "Not provided"}

        Campaign context:
        - Product: {campaign.product_name}
        - Pitch: {campaign.product_pitch}
        - Goal: {campaign.campaign_goal}
        {geography_hint}

        Return exactly one JSON object with keys:
        status, summary, personalization_angle, signals, warnings.
        Do not wrap the JSON in markdown fences.
        Return 2-5 concrete, email-usable signals.
        Each signal should connect what you found to why it matters for this campaign.
        """
    ).strip()


def research_collection_prompt(lead: Lead, campaign: CampaignConfig) -> str:
    geography_hint = (
        f"- Search geography hint: prioritize sources relevant to country code {campaign.search_country}\n"
        if campaign.search_country
        else ""
    )
    return textwrap.dedent(
        f"""
        Research this lead and company for a cold outbound campaign.

        Lead:
        - Name: {lead.name}
        - Company: {lead.company}
        - Website: {lead.website}
        - Role: {lead.role}
        - LinkedIn URL: {lead.linkedin_url or "Not provided"}

        Campaign context:
        - Product: {campaign.product_name}
        - Pitch: {campaign.product_pitch}
        - Goal: {campaign.campaign_goal}
        {geography_hint}

        Find concrete, recent, company-relevant facts that could improve a personalized cold email.

        Output plain research notes only.
        Include:
        - 3-6 factual bullets
        - source URLs when available
        - uncertainty notes if evidence is weak

        Do not return JSON.
        """
    ).strip()


def research_structuring_prompt(raw_research: str) -> str:
    return textwrap.dedent(
        f"""
        Convert the research notes below into exactly one JSON object with keys:
        status, summary, personalization_angle, signals, warnings.

        Requirements:
        - `signals` must be an array of 2-5 objects
        - each signal object must contain:
          - `label`: 2-4 words
          - `detail`: one factual sentence
          - `why_it_matters`: one short sentence tied to the campaign
          - `source_url`: URL string if available, otherwise empty string
          - `confidence`: low, medium, or high
        - do not return plain strings inside `signals`
        - do not wrap the JSON in markdown fences
        - if evidence is weak, say so in `warnings`

        Research notes:
        {raw_research}
        """
    ).strip()


def draft_system_prompt() -> str:
    return textwrap.dedent(
        """
        You write thoughtful cold emails that sound human.
        Use the research directly, avoid hype, and keep claims grounded in the provided facts.
        Write for light human editing, not fully automated send-ready perfection.
        """
    ).strip()


def draft_user_prompt(lead: Lead, campaign: CampaignConfig, research: ResearchResult) -> str:
    value_props = "\n".join(f"- {item}" for item in campaign.value_props) or "- None provided"
    constraints = "\n".join(f"- {item}" for item in campaign.constraints) or "- None provided"
    signals = "\n".join(
        f"- {signal.label}: {signal.detail} Why it matters: {signal.why_it_matters}"
        for signal in research.signals
    ) or "- No verified signals found"
    return textwrap.dedent(
        f"""
        Write a personalized cold email.

        Prospect:
        - Name: {lead.name}
        - Role: {lead.role}
        - Company: {lead.company}

        Sender:
        - Name: {campaign.sender_name}
        - Company: {campaign.sender_company}
        - Role: {campaign.sender_role}
        - Email: {campaign.sender_email}

        Campaign:
        - Product: {campaign.product_name}
        - Product pitch: {campaign.product_pitch}
        - Goal: {campaign.campaign_goal}
        - Tone: {campaign.tone}
        - Length: {campaign.length_preference}
        - Call to action: {campaign.call_to_action}
        - Value props:
        {value_props}
        - Constraints:
        {constraints}

        Research summary:
        - Summary: {research.summary}
        - Personalization angle: {research.personalization_angle}
        - Signals:
        {signals}

        Requirements:
        - Make it clear the email was written specifically for this company.
        - Avoid generic compliments.
        - Do not invent customer results, metrics, or facts.
        - Keep paragraphs short and easy to skim.
        """
    ).strip()


def review_system_prompt() -> str:
    return textwrap.dedent(
        """
        You review cold emails for factual grounding, personalization quality, tone, and usefulness.
        Tighten weak lines, remove generic fluff, and ensure the final draft is safe for a human reviewer.
        """
    ).strip()


def review_user_prompt(
    lead: Lead,
    campaign: CampaignConfig,
    research: ResearchResult,
    subject: str,
    body: str,
) -> str:
    signals = "\n".join(
        f"- {signal.label}: {signal.detail} ({signal.why_it_matters})"
        for signal in research.signals
    ) or "- No strong signals available"
    return textwrap.dedent(
        f"""
        Review and improve this cold email.

        Lead:
        - Name: {lead.name}
        - Company: {lead.company}
        - Role: {lead.role}

        Campaign:
        - Tone: {campaign.tone}
        - Length preference: {campaign.length_preference}
        - Goal: {campaign.campaign_goal}
        - CTA: {campaign.call_to_action}

        Allowed facts:
        {signals}

        Draft subject:
        {subject}

        Draft body:
        {body}

        Review checklist:
        - Is every personalized claim supported by the allowed facts?
        - Does the opening line feel specific rather than templated?
        - Is the ask clear and low-friction?
        - Would a human reviewer feel comfortable sending this after light edits?
        """
    ).strip()
