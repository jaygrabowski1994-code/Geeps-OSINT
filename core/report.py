"""
Report engine for Geeps OSINT Hub.

Every investigation module's output is captured automatically -- no
per-module code needed. core.ui's ok()/warn()/err()/info()/section()/
prompt() calls all mirror into whatever ReportSession is currently
active via record(). osint.py starts a session before running a
plugin and ends it after, then offers to save it.

Output formats:
  - HTML: a single self-contained, styled file. Open it in any browser;
    use the browser's own Print -> Save as PDF for a PDF copy. This
    avoids pulling in a native PDF-rendering dependency (e.g.
    WeasyPrint needs system Cairo/Pango libraries that are painful to
    install on Termux) just to produce what a browser already does for
    free.
  - JSON: the same data, structured, for scripting/archival.
"""

from __future__ import annotations

import html
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"

_lock = threading.Lock()
_active: Optional["ReportSession"] = None


@dataclass
class ReportSession:
    title: str
    started_at: datetime = field(default_factory=datetime.now)
    entries: List[Tuple[str, str]] = field(default_factory=list)  # (level, message)
    _entry_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, level: str, message: str) -> None:
        with self._entry_lock:
            self.entries.append((level, message))

    @property
    def target(self) -> str:
        """Best-effort label for filenames/headers: the first prompted value, if any."""
        for level, message in self.entries:
            if level == "target":
                return message.split(": ", 1)[-1]
        return "unspecified"

    def has_content(self) -> bool:
        return any(level != "section" for level, _ in self.entries)

    def save(self, formats: Tuple[str, ...] = ("html", "json")) -> List[Path]:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = self.started_at.strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in self.title)
        safe_target = "".join(c if c.isalnum() or c in "-_." else "_" for c in self.target)[:50]
        base = f"{safe_title}_{safe_target}_{stamp}"

        written: List[Path] = []
        if "html" in formats:
            path = REPORT_DIR / f"{base}.html"
            path.write_text(render_html(self), encoding="utf-8")
            written.append(path)
        if "json" in formats:
            path = REPORT_DIR / f"{base}.json"
            path.write_text(render_json(self), encoding="utf-8")
            written.append(path)
        return written


def start_session(title: str) -> ReportSession:
    """Begin recording a new session as the active one. Ends any prior session implicitly."""
    global _active
    with _lock:
        _active = ReportSession(title=title)
        return _active


def end_session() -> Optional[ReportSession]:
    """Stop recording and return the finished session (or None if none was active)."""
    global _active
    with _lock:
        session, _active = _active, None
        return session


def record(level: str, message: str) -> None:
    """Called by core.ui on every ok/warn/err/info/section/prompt -- no-op if no session is active."""
    session = _active  # snapshot; fine if it changes concurrently, we just skip or hit the right one
    if session is not None:
        session.add(level, message)


_LEVEL_STYLE = {
    "ok": ("\u2713", "#1a7f37"),
    "warn": ("\u26a0", "#9a6700"),
    "err": ("\u2717", "#cf222e"),
    "info": ("\u2022", "#0969da"),
    "target": ("\u25b8", "#57606a"),
}


def render_html(session: ReportSession) -> str:
    rows = []
    for level, message in session.entries:
        if level == "section":
            rows.append(
                f'<tr class="section"><td colspan="2">{html.escape(message)}</td></tr>'
            )
            continue
        symbol, color = _LEVEL_STYLE.get(level, ("\u2022", "#57606a"))
        rows.append(
            '<tr class="entry">'
            f'<td class="sym" style="color:{color}">{symbol}</td>'
            f'<td>{html.escape(message)}</td>'
            "</tr>"
        )

    generated = session.started_at.strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(session.title)} report</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 800px;
         margin: 2rem auto; padding: 0 1rem; color: #1f2328; background: #fff; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 0; }}
  .meta {{ color: #57606a; font-size: 0.9rem; margin-bottom: 1.5rem; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td {{ padding: 0.35rem 0.5rem; vertical-align: top; border-bottom: 1px solid #eaeef2; }}
  tr.section td {{ font-weight: 600; background: #f6f8fa; padding-top: 0.75rem;
                    border-bottom: 2px solid #d0d7de; }}
  td.sym {{ width: 1.5rem; font-weight: bold; }}
  footer {{ margin-top: 2rem; color: #8b949e; font-size: 0.8rem; }}
  @media print {{ body {{ margin: 0.5in; }} }}
</style>
</head>
<body>
  <h1>{html.escape(session.title)}</h1>
  <div class="meta">Target: {html.escape(session.target)} &middot; Generated {generated}</div>
  <table>
    {''.join(rows)}
  </table>
  <footer>Generated by Geeps OSINT Hub. To save as PDF, open this file in a
  browser and use Print &rarr; Save as PDF.</footer>
</body>
</html>
"""


def render_json(session: ReportSession) -> str:
    return json.dumps(
        {
            "title": session.title,
            "target": session.target,
            "generated": session.started_at.isoformat(),
            "entries": [{"level": level, "message": message} for level, message in session.entries],
        },
        indent=2,
    )
