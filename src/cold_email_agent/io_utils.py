from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from cold_email_agent.models import Lead, LeadOutput

REQUIRED_LEAD_COLUMNS = {"name", "company", "website", "role"}


def load_leads(path: str | Path) -> list[Lead]:
    path = Path(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_LEAD_COLUMNS - set(reader.fieldnames or [])
        #check for required columns
        if missing:
            missing_fields = ", ".join(sorted(missing))
            raise ValueError(f"Lead CSV is missing required columns: {missing_fields}")
        leads = []
        for row in reader:
            if not any((row.get(column) or "").strip() for column in REQUIRED_LEAD_COLUMNS):
                continue
            leads.append(
                Lead(
                    name=(row.get("name") or "").strip(),
                    company=(row.get("company") or "").strip(),
                    website=(row.get("website") or "").strip(),
                    role=(row.get("role") or "").strip(),
                    #return "" if no url
                    linkedin_url=(row.get("linkedin_url") or "").strip(),
                )
            )
    return leads


def ensure_run_directory(base_dir: str | Path | None = None) -> Path:
    if base_dir:
        run_dir = Path(base_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir
    parent = Path("runs")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = parent / f"run-{timestamp}"
    #create runs first if not exist
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_output_csv(path: str | Path, rows: Iterable[LeadOutput]) -> None:
    path = Path(path)
    rows = list(rows)
    if not rows:
        raise ValueError("No rows to write.")
    with path.open("w", encoding="utf-8", newline="") as handle:
        #use the first reponse as a sample to get all keys
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


class JsonlLogger:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def log(self, event_type: str, **payload: object) -> None:
        record = {
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            "event_type": event_type,
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
