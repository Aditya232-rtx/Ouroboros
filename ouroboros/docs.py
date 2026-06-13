"""
ouroboros/docs.py — PDF security report generation.

Uses ReportLab to build a professional security report PDF.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger("ouroboros.docs")


class DocumentationGenerator:
    """Generate PDF security reports from scan results."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    async def generate(self, repo_path: str, fixes: Dict[str, Any]) -> str:
        """
        Build a PDF security report.

        Returns the absolute path to the generated PDF.
        """
        output_path = str(
            Path(repo_path).parent / "ouroboros-security-report.pdf"
        )
        self._build_pdf(output_path, fixes)
        logger.info("PDF report saved → %s", output_path)
        return output_path

    # ------------------------------------------------------------------

    def _build_pdf(self, output_path: str, fixes: Dict) -> None:
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Title
        story.append(
            Paragraph("Ouroboros Security Report", styles["Title"])
        )
        story.append(Spacer(1, 12))
        story.append(
            Paragraph(
                f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 24))

        # Summary table
        patches = fixes.get("patches", [])
        risk_reduction = fixes.get("risk_reduction", 0)
        verified = fixes.get("verified", False)

        table_data = [
            ["Metric", "Value"],
            ["Patches Generated", str(len(patches))],
            ["Risk Reduction", f"{risk_reduction}%"],
            ["All Patches Verified", "Yes" if verified else "No"],
        ]
        table = Table(table_data, colWidths=[220, 220])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f0f4ff")],
                    ),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("PADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 24))

        # Patch details
        story.append(Paragraph("Patches Applied", styles["Heading2"]))
        for i, p in enumerate(patches, 1):
            sev = p.get("severity", "?")
            fp = p.get("file_path", "unknown")
            vid = p.get("vuln_id", "?")
            story.append(
                Paragraph(f"{i}. [{sev}] {fp} — {vid}", styles["Normal"])
            )
            story.append(Spacer(1, 4))

        doc.build(story)
