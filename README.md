# Cold Email Agent

This project builds a CLI agent that takes a leads CSV and a campaign config, researches each lead, drafts a personalized cold email, reviews its own draft, and writes the results to disk.

The Gemini integration lives in `src/cold_email_agent/gemini_client.py`.

## What it does

For each lead, the pipeline runs three stages:

1. `research`: uses the Gemini API with Google Search grounding to gather email-usable signals
2. `draft`: turns the lead, campaign, and research into a subject line and body
3. `review`: checks factual grounding, personalization quality, tone, and CTA clarity before returning a final draft

If any stage fails for a lead, the tool falls back to a conservative draft that only uses the CSV fields and marks the row accordingly instead of crashing the batch.

## Input format

### Leads CSV

Required columns:

- `name`
- `company`
- `website`
- `role`

Optional columns:

- `linkedin_url`

### Campaign config

YAML or JSON is supported. The sample file in `sample_data/campaign.yaml` shows the expected schema.

Required fields:

- `sender_name`
- `sender_company`
- `sender_role`
- `sender_email`
- `product_name`
- `product_pitch`
- `campaign_goal`
- `tone`
- `length_preference`
- `call_to_action`

Optional fields:

- `value_props`
- `constraints`
- `research_model`
- `writing_model`
- `review_model`
- `reasoning_effort`
- `search_country`

Default model values:

- `gemini-2.5-flash-lite` for research, drafting, and review
- no search location bias unless `search_country` is set

## Output format

Each run writes a timestamped folder under `runs/` unless `--outdir` is provided.

- `emails.csv`: one row per lead with `subject`, `body`, `personalization_angle`, `signal_summary`, `signals_json`, `review_notes`, statuses, and any error text
- `run.log.jsonl`: append-only structured event log for stage-by-stage debugging

## Install

```bash
python -m venv email_agent
source email_agent/bin/activate
pip install -r requirements.txt
```

Set your API key:

```bash
export GEMINI_API_KEY=your_key_here
```

## Run

```bash
PYTHONPATH=src python -m cold_email_agent.cli \
  --leads sample_data/leads_test.csv \
  --config sample_data/campaign.yaml
```

Or after install:

```bash
cold-email-agent --leads sample_data/leads.csv --config sample_data/campaign.yaml
```

## Notes on design choices

- The tool is file-based only and intentionally avoids any sending workflow.
- CSV is used for both input and output so the results are easy to review in spreadsheets.
- `signals_json` stores structured evidence for each lead so a human reviewer can quickly inspect what drove the draft.
- The research step asks the model to prefer recent, company-specific sources and to state uncertainty instead of guessing.
- The default model is `gemini-2.5-flash-lite`, which Google currently documents as its smallest and most cost-effective Gemini 2.5 model with Google Search grounding support.
- `search_country` is optional. If you set it, you can use either a 2-letter code like `US`, `SG`, or `GB`, or a full name like `United States`, `Singapore`, or `United Kingdom`. Invalid values raise a config error early. If you leave it blank, research runs without a location bias.

## Test

```bash
PYTHONPATH=src python -m unittest discover -s tests
```
