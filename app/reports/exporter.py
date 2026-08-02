"""Privacy-conscious local report exporters."""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path

from app.core.session import TestSession


class ReportExporter:
    """Export session metadata without embedding biometric source imagery."""

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def json_report(self, session: TestSession) -> Path:
        path = self.output_dir / f"facepilot-{session.id}.json"
        path.write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")
        return path

    def csv_report(self, session: TestSession) -> Path:
        path = self.output_dir / f"facepilot-{session.id}-signals.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["name", "score", "detail", "timestamp"])
            writer.writeheader()
            for signal in session.signals:
                writer.writerow(
                    {
                        "name": signal.name,
                        "score": signal.score,
                        "detail": signal.detail,
                        "timestamp": signal.timestamp,
                    }
                )
        return path

    def html_report(self, session: TestSession) -> Path:
        payload = session.to_dict()
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(signal.name)}</td>"
            f"<td>{signal.score:.1%}</td>"
            f"<td>{html.escape(signal.detail)}</td>"
            "</tr>"
            for signal in session.signals
        ) or '<tr><td colspan="3">No detector signals recorded.</td></tr>'
        document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FacePilot report {html.escape(session.id)}</title>
<style>
body{{font-family:Arial,sans-serif;max-width:960px;margin:40px auto;padding:0 20px;color:#15231d}}
h1{{color:#087748}} .badge{{display:inline-block;padding:6px 10px;background:#e8f7ef;border-radius:999px}}
table{{width:100%;border-collapse:collapse;margin-top:24px}}th,td{{border:1px solid #cad8d1;padding:10px;text-align:left}}
.notice{{margin-top:28px;padding:14px;background:#f1f6f3;border-left:4px solid #087748}}
</style>
</head>
<body>
<h1>FacePilot Authorized Test Report</h1>
<p><strong>Session:</strong> {html.escape(session.id)}</p>
<p><strong>Input:</strong> {html.escape(session.input_name)}</p>
<p><strong>Status:</strong> {html.escape(session.status.value)}</p>
<p><strong>Assessment:</strong> <span class="badge">{html.escape(str(payload['classification']))}</span></p>
<p><strong>Aggregate anomaly score:</strong> {float(payload['risk_score']):.1%}</p>
<table><thead><tr><th>Signal</th><th>Score</th><th>Detail</th></tr></thead><tbody>{rows}</tbody></table>
<div class="notice">Generated locally for systems owned by, or explicitly authorized for testing by, the operator. This report is not a biometric identity decision.</div>
</body></html>"""
        path = self.output_dir / f"facepilot-{session.id}.html"
        path.write_text(document, encoding="utf-8")
        return path
