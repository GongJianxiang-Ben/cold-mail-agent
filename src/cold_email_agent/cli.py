from __future__ import annotations

import argparse
from pathlib import Path

from cold_email_agent.config import load_campaign_config
from cold_email_agent.io_utils import JsonlLogger, ensure_run_directory, load_leads, write_output_csv
from cold_email_agent.gemini_client import GeminiLeadProcessor
from cold_email_agent.pipeline import ColdEmailPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate personalized cold emails from a leads CSV.")
    parser.add_argument("--leads", required=True, help="Path to the leads CSV.")
    parser.add_argument("--config", required=True, help="Path to the campaign config YAML or JSON.")
    parser.add_argument(
        "--outdir",
        default=None,
        help="Optional output directory. Defaults to runs/run-<timestamp>/",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Optional Gemini API key. Falls back to GEMINI_API_KEY.",
    )
    parser.add_argument(
        "--debug-signal",
        action="store_true",
        help="Print the first researched signal for each lead for debugging.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    leads = load_leads(args.leads)
    if not leads:
        raise SystemExit("The leads CSV did not contain any usable rows.")
    campaign = load_campaign_config(args.config)
    run_dir = ensure_run_directory(args.outdir)
    logger = JsonlLogger(run_dir / "run.log.jsonl")
    processor = GeminiLeadProcessor(api_key=args.api_key)
    pipeline = ColdEmailPipeline(processor, logger, debug_signal=args.debug_signal)
    outputs = pipeline.run(leads, campaign)
    write_output_csv(run_dir / "emails.csv", outputs)
    print(f"Wrote {len(outputs)} email rows to {Path(run_dir / 'emails.csv')}")
    print(f"Run log: {Path(run_dir / 'run.log.jsonl')}")


if __name__ == "__main__":
    main()
