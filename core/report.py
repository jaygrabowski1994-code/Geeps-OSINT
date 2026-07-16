
"""
Simple reporting engine for Geeps OSINT Hub.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORT_DIR.mkdir(exist_ok=True)

@dataclass
class Report:
    title: str
    target: str
    entries: list[dict[str, Any]] = field(default_factory=list)

    def add(self, label: str, value: Any) -> None:
        self.entries.append({"label": label, "value": value})

    def save(self) -> tuple[Path, Path]:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in self.target)

        txt = REPORT_DIR / f"{self.title}_{safe}_{stamp}.txt"
        js = REPORT_DIR / f"{self.title}_{safe}_{stamp}.json"

        with txt.open("w", encoding="utf-8") as f:
            f.write(f"{self.title}\n")
            f.write(f"Target: {self.target}\n")
            f.write("=" * 50 + "\n\n")
            for item in self.entries:
                f.write(f"{item['label']}: {item['value']}\n")

        with js.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "title": self.title,
                    "target": self.target,
                    "generated": stamp,
                    "entries": self.entries,
                },
                f,
                indent=2,
            )

        return txt, js
