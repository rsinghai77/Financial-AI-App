"""Report Export MCP Server — MCP-006.

Generates CSV and PDF reports from portfolio and performance data.
"""

import csv
import io
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from mcp.server import FastMCP

logger = logging.getLogger(__name__)
mcp = FastMCP("export-mcp")

EXPORT_DIR = Path("./exports")


def _ensure_export_dir() -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    return EXPORT_DIR


@mcp.tool()
def export_portfolio_csv(
    portfolio_data: dict[str, Any],
    output_path: Optional[str] = None,
) -> dict[str, Any]:
    """Export portfolio holdings to CSV.

    Args:
        portfolio_data: Portfolio dict from get_portfolio tool.
        output_path: Optional custom file path. Defaults to ./exports/portfolio_YYYYMMDD.csv.

    Returns:
        Dict with file_path and row_count.
    """
    export_dir = _ensure_export_dir()
    if output_path is None:
        output_path = str(export_dir / f"portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

    rows = []
    for account in portfolio_data.get("accounts", []):
        for holding in account.get("holdings", []):
            rows.append({
                "Account": account.get("name", ""),
                "Account Type": account.get("account_type", ""),
                "Ticker": holding.get("ticker", ""),
                "Asset Class": holding.get("asset_class", ""),
                "Quantity": holding.get("quantity", 0),
                "Cost Basis/Share": holding.get("cost_basis_per_share", 0),
                "Total Cost Basis": holding.get("total_cost_basis", 0),
                "Purchase Date": holding.get("purchase_date", ""),
                "Holding Period Days": holding.get("holding_period_days", 0),
                "Long Term": holding.get("is_long_term", False),
                "Notes": holding.get("notes", ""),
            })

    if not rows:
        return {"file_path": "", "row_count": 0, "error": "No holdings to export"}

    try:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return {"file_path": output_path, "row_count": len(rows)}
    except OSError as exc:
        return {"file_path": "", "row_count": 0, "error": str(exc)}


@mcp.tool()
def generate_performance_report(
    portfolio_data: dict[str, Any],
    performance_data: dict[str, Any],
    period: str = "ytd",
    output_path: Optional[str] = None,
) -> dict[str, Any]:
    """Generate a simple text-based performance report (PDF if reportlab available).

    Args:
        portfolio_data: Portfolio dict from get_portfolio tool.
        performance_data: Performance dict from get_performance tool.
        period: Report period label.
        output_path: Optional custom file path.

    Returns:
        Dict with file_path and pages.
    """
    export_dir = _ensure_export_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table

        if output_path is None:
            output_path = str(export_dir / f"performance_report_{timestamp}.pdf")

        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("FinApp — Portfolio Performance Report", styles["Title"]))
        story.append(Paragraph(f"Period: {period.upper()}  |  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
        story.append(Spacer(1, 12))

        # Disclaimer
        disclaimer = (
            "⚠️ This report is for informational purposes only and does not constitute "
            "financial advice. Always consult a licensed financial advisor before making "
            "investment decisions."
        )
        story.append(Paragraph(disclaimer, styles["Italic"]))
        story.append(Spacer(1, 12))

        # Summary table
        summary_data = [
            ["Metric", "Value"],
            ["Total Cost Basis", f"${portfolio_data.get('total_cost_basis', 0):,.2f}"],
            ["Period", period.upper()],
            ["Report Date", datetime.now().strftime("%Y-%m-%d")],
        ]
        table = Table(summary_data, colWidths=[200, 200])
        story.append(table)
        story.append(Spacer(1, 12))

        # Holdings
        story.append(Paragraph("Holdings Summary", styles["Heading2"]))
        holding_rows = [["Account", "Ticker", "Quantity", "Cost Basis/Share", "Total Cost"]]
        for account in portfolio_data.get("accounts", []):
            for h in account.get("holdings", []):
                holding_rows.append([
                    account.get("name", ""),
                    h.get("ticker", ""),
                    f"{h.get('quantity', 0):.4f}",
                    f"${h.get('cost_basis_per_share', 0):.2f}",
                    f"${h.get('total_cost_basis', 0):,.2f}",
                ])
        if len(holding_rows) > 1:
            h_table = Table(holding_rows, colWidths=[100, 60, 70, 100, 100])
            story.append(h_table)

        doc.build(story)
        return {"file_path": output_path, "pages": 1}

    except ImportError:
        # Fallback to plain text report
        if output_path is None:
            output_path = str(export_dir / f"performance_report_{timestamp}.txt")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("FinApp — Portfolio Performance Report\n")
            f.write("=" * 50 + "\n")
            f.write(f"Period: {period.upper()}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            f.write("DISCLAIMER: This report is for informational purposes only.\n\n")
            f.write(f"Total Cost Basis: ${portfolio_data.get('total_cost_basis', 0):,.2f}\n\n")
            f.write("Holdings:\n")
            for account in portfolio_data.get("accounts", []):
                for h in account.get("holdings", []):
                    f.write(
                        f"  {h.get('ticker', '')} | {h.get('quantity', 0):.4f} shares "
                        f"@ ${h.get('cost_basis_per_share', 0):.2f} = "
                        f"${h.get('total_cost_basis', 0):,.2f}\n"
                    )
        return {"file_path": output_path, "pages": 1}
    except Exception as exc:
        return {"file_path": "", "pages": 0, "error": str(exc)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
