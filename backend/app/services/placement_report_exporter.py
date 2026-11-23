"""
Report Export Engine for TPO Placement Intelligence & Forecasting.
Produces real binary PDF documents (via PyMuPDF) and multi-sheet OpenXML Excel (.xlsx)
workbooks (via Python stdlib zipfile + xml.etree.ElementTree) without external bloat.
"""
import io
from typing import Any, List
import xml.etree.ElementTree as ET
import zipfile

import pymupdf

from app.schemas.tpo_intelligence import TpoPlacementIntelligenceResponse


def _fmt_num(val: Any, suffix: str = "") -> str:
    if val is None:
        return "N/A"
    return f"{val}{suffix}"


def generate_intelligence_pdf(report: TpoPlacementIntelligenceResponse) -> bytes:
    """Render a clean multi-page PDF executive report using PyMuPDF."""
    doc = pymupdf.open()
    page_w, page_h = 595, 842  # A4 portrait
    margin = 40
    y = margin

    def new_page():
        nonlocal y
        p = doc.new_page(width=page_w, height=page_h)
        y = margin
        return p

    page = new_page()

    def write_line(text: str, size: int = 10, bold: bool = False, color=(0.12, 0.16, 0.22), gap: int = 15):
        nonlocal page, y
        if y > page_h - margin - 20:
            page = new_page()
        fontname = "helv" if not bold else "hebo"
        # Wrap long lines safely at ~88 chars
        words = (text or "").split(" ")
        lines: List[str] = []
        cur = ""
        max_chars = 86 if size <= 10 else 65
        for w in words:
            if len(cur) + len(w) + 1 <= max_chars:
                cur = f"{cur} {w}".strip()
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        for ln in lines or [""]:
            if y > page_h - margin - 18:
                page = new_page()
            page.insert_text((margin, y), ln, fontsize=size, fontname=fontname, color=color)
            y += gap

    # Header
    write_line("INSTITUTIONAL PLACEMENT INTELLIGENCE & FORECASTING REPORT", size=14, bold=True, color=(0.24, 0.22, 0.72), gap=20)
    write_line(
        f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')} | Institution ID: {report.filters_applied.institution_id}",
        size=9,
        color=(0.35, 0.4, 0.48),
        gap=14,
    )
    write_line(f"Policy: {report.policy_summary}", size=8, color=(0.35, 0.4, 0.48), gap=16)

    # Overview Section
    ov = report.overview
    write_line("1. PLACEMENT OVERVIEW", size=12, bold=True, gap=18)
    write_line(
        f"Eligible Students: {ov.total_eligible_students} (Registered: {ov.total_registered_students}) | "
        f"Placed (Accepted): {ov.total_placed_students} | Placement Rate: {ov.placement_rate_pct}%",
        gap=14,
    )
    write_line(
        f"In Recruitment Pipeline: {ov.students_in_pipeline} | Not Yet Placed: {ov.students_not_yet_placed} | "
        f"Active Drives: {ov.total_active_drives} | Companies: {ov.total_participating_companies}",
        gap=14,
    )
    write_line(
        f"Offers Released: {ov.total_offers_released} | Accepted: {ov.total_accepted_offers} | "
        f"Declined: {ov.total_declined_offers} | Pending: {ov.pending_offers}",
        gap=14,
    )
    write_line(
        f"Package Stats (LPA) - Avg: {_fmt_num(ov.average_package_lpa, ' LPA')} | "
        f"Median: {_fmt_num(ov.median_package_lpa, ' LPA')} | Highest: {_fmt_num(ov.highest_package_lpa, ' LPA')}",
        gap=18,
    )

    # Department Breakdown
    write_line("2. DEPARTMENT-WISE ANALYTICS", size=12, bold=True, gap=18)
    for d in report.department_analytics:
        write_line(
            f"- {d.department_code} ({d.department_name}): Eligible {d.eligible_students}, "
            f"Placed {d.placed_students} ({d.placement_rate_pct}%), "
            f"Avg {_fmt_num(d.average_package_lpa, ' LPA')}, High {_fmt_num(d.highest_package_lpa, ' LPA')}",
            size=9,
            gap=13,
        )
    y += 6

    # Historical Trends
    write_line("3. HISTORICAL BATCH & ACADEMIC YEAR TRENDS", size=12, bold=True, gap=18)
    for h in report.historical_trends:
        write_line(
            f"- {h.academic_year} (Batch {h.graduation_year}): Eligible {h.eligible_students}, Placed {h.placed_students} "
            f"({h.placement_rate_pct}%), Companies {h.participating_companies}, Offers Accepted {h.offers_accepted}/{h.offers_released}",
            size=9,
            gap=13,
        )
    y += 6

    # Statistical Forecasts
    fc = report.forecasting
    write_line(f"4. STATISTICAL FORECASTS ({fc.target_academic_year} / Batch {fc.target_graduation_year})", size=12, bold=True, gap=18)
    write_line(f"Disclaimer: {fc.disclaimer}", size=8, color=(0.55, 0.25, 0.1), gap=14)
    for est in (fc.placement_forecast, fc.company_participation_forecast, fc.offer_volume_forecast):
        write_line(
            f"- {est.metric_label}: Projected {est.projected_value} {est.unit} "
            f"[95% CI: {est.ci_lower_95} - {est.ci_upper_95}] | n={est.sample_size} yrs | Method: {est.methodology} ({est.confidence_level})",
            size=9,
            gap=14,
        )
    y += 6

    # Skill Demand
    write_line("5. SKILL DEMAND INTELLIGENCE", size=12, bold=True, gap=18)
    top_skills = ", ".join(f"{s.skill_name} ({s.job_postings_count} jobs)" for s in report.skill_intelligence.most_requested_skills[:8])
    win_skills = ", ".join(f"{s.skill_name} ({s.accepted_offer_count} accepted)" for s in report.skill_intelligence.winning_outcome_skills[:8])
    write_line(f"Most Requested Skills: {top_skills or 'Insufficient job skill data'}", size=9, gap=14)
    write_line(f"Winning Outcome Skills: {win_skills or 'Insufficient accepted offer data'}", size=9, gap=16)

    # Data Completeness Warnings
    if report.data_completeness.warnings:
        write_line("6. DATA COMPLETENESS & TRANSPARENCY NOTES", size=11, bold=True, gap=16)
        for w in report.data_completeness.warnings:
            write_line(f"* {w}", size=8, color=(0.45, 0.3, 0.1), gap=12)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ---------------------------------------------------------------------------
# Pure-Python OpenXML (.xlsx) Multi-Sheet Workbook Builder
# ---------------------------------------------------------------------------

def _col_letter(idx: int) -> str:
    res = ""
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        res = chr(65 + rem) + res
    return res


def _build_worksheet_xml(rows: List[List[Any]]) -> bytes:
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ET.register_namespace("", ns)
    root = ET.Element(f"{{{ns}}}worksheet")
    sheet_data = ET.SubElement(root, f"{{{ns}}}sheetData")

    for r_idx, row in enumerate(rows, start=1):
        row_el = ET.SubElement(sheet_data, f"{{{ns}}}row", {"r": str(r_idx)})
        for c_idx, val in enumerate(row, start=1):
            ref = f"{_col_letter(c_idx)}{r_idx}"
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                cell = ET.SubElement(row_el, f"{{{ns}}}c", {"r": ref})
                v_el = ET.SubElement(cell, f"{{{ns}}}v")
                v_el.text = str(val)
            else:
                cell = ET.SubElement(row_el, f"{{{ns}}}c", {"r": ref, "t": "inlineStr"})
                is_el = ET.SubElement(cell, f"{{{ns}}}is")
                t_el = ET.SubElement(is_el, f"{{{ns}}}t")
                t_el.text = "" if val is None else str(val)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def generate_intelligence_excel(report: TpoPlacementIntelligenceResponse) -> bytes:
    """Create a valid multi-sheet OpenXML Excel (.xlsx) workbook."""
    ov = report.overview
    fc = report.forecasting

    sheets: List[tuple[str, List[List[Any]]]] = [
        (
            "Overview",
            [
                ["AI-Powered Placement Intelligence & Forecasting Report"],
                ["Generated At (UTC)", report.generated_at.isoformat()],
                ["Institution ID", report.filters_applied.institution_id],
                ["Policy", report.policy_summary],
                [],
                ["Metric", "Value"],
                ["Total Registered Students", ov.total_registered_students],
                ["Total Eligible Students", ov.total_eligible_students],
                ["Total Placed Students (Accepted Only)", ov.total_placed_students],
                ["Students in Recruitment Pipeline", ov.students_in_pipeline],
                ["Students Not Yet Placed", ov.students_not_yet_placed],
                ["Total Active Placement Drives", ov.total_active_drives],
                ["Total Participating Companies", ov.total_participating_companies],
                ["Total Published Jobs", ov.total_published_jobs],
                ["Total Offers Released", ov.total_offers_released],
                ["Total Accepted Offers", ov.total_accepted_offers],
                ["Total Declined Offers", ov.total_declined_offers],
                ["Pending Offers", ov.pending_offers],
                ["Placement Rate (%)", ov.placement_rate_pct],
                ["Offer Acceptance Rate (%)", ov.offer_acceptance_rate_pct],
                ["Average Package (LPA)", ov.average_package_lpa if ov.average_package_lpa is not None else "N/A"],
                ["Median Package (LPA)", ov.median_package_lpa if ov.median_package_lpa is not None else "N/A"],
                ["Highest Package (LPA)", ov.highest_package_lpa if ov.highest_package_lpa is not None else "N/A"],
                ["Offers Missing Package Count", ov.offers_missing_package_count],
            ],
        ),
        (
            "Departments",
            [
                [
                    "Code",
                    "Department",
                    "Eligible",
                    "Placed",
                    "In Pipeline",
                    "Unplaced",
                    "Placement Rate (%)",
                    "Offers Accepted",
                    "Avg Package (LPA)",
                    "Highest Package (LPA)",
                    "Top Demanded Skills",
                    "Skill Gaps",
                ],
                *[
                    [
                        d.department_code,
                        d.department_name,
                        d.eligible_students,
                        d.placed_students,
                        d.in_pipeline_students,
                        d.unplaced_students,
                        d.placement_rate_pct,
                        d.offers_accepted,
                        d.average_package_lpa if d.average_package_lpa is not None else "N/A",
                        d.highest_package_lpa if d.highest_package_lpa is not None else "N/A",
                        ", ".join(d.top_demanded_skills),
                        ", ".join(d.skill_gaps),
                    ]
                    for d in report.department_analytics
                ],
            ],
        ),
        (
            "Historical_Trends",
            [
                [
                    "Academic Year",
                    "Graduation Batch",
                    "Eligible",
                    "Placed",
                    "Placement Rate (%)",
                    "YoY Growth (pct pts)",
                    "Companies",
                    "Offers Released",
                    "Offers Accepted",
                    "Offers Declined",
                    "Offer Conversion (%)",
                    "Avg LPA",
                    "Median LPA",
                    "Highest LPA",
                ],
                *[
                    [
                        h.academic_year,
                        h.graduation_year,
                        h.eligible_students,
                        h.placed_students,
                        h.placement_rate_pct,
                        h.yoy_placement_growth_pct_pts if h.yoy_placement_growth_pct_pts is not None else "N/A",
                        h.participating_companies,
                        h.offers_released,
                        h.offers_accepted,
                        h.offers_declined,
                        h.offer_conversion_rate_pct,
                        h.average_package_lpa if h.average_package_lpa is not None else "N/A",
                        h.median_package_lpa if h.median_package_lpa is not None else "N/A",
                        h.highest_package_lpa if h.highest_package_lpa is not None else "N/A",
                    ]
                    for h in report.historical_trends
                ],
            ],
        ),
        (
            "Forecasting",
            [
                ["Target Period", fc.target_academic_year, f"Batch {fc.target_graduation_year}"],
                ["Disclaimer", fc.disclaimer],
                [],
                ["Metric", "Unit", "Projected Value", "95% CI Lower", "95% CI Upper", "Sample Size", "R2", "Confidence", "Methodology", "Limitations"],
                *[
                    [
                        est.metric_label,
                        est.unit,
                        est.projected_value,
                        est.ci_lower_95,
                        est.ci_upper_95,
                        est.sample_size,
                        est.r_squared if est.r_squared is not None else "N/A",
                        est.confidence_level,
                        est.methodology,
                        " | ".join(est.limitations),
                    ]
                    for est in (
                        fc.placement_forecast,
                        fc.company_participation_forecast,
                        fc.offer_volume_forecast,
                    )
                ],
                [],
                ["Department", "Latest Rate (%)", "Projected Rate (%)", "95% CI Lower", "95% CI Upper", "Projected Placed Count", "Sample Size", "Trend", "Confidence"],
                *[
                    [
                        df.department_name,
                        df.latest_placement_rate_pct,
                        df.projected_placement_rate_pct,
                        df.ci_lower_95,
                        df.ci_upper_95,
                        df.projected_placed_students,
                        df.sample_size,
                        df.trend_direction,
                        df.confidence_level,
                    ]
                    for df in fc.department_forecasts
                ],
            ],
        ),
        (
            "Skill_Demand",
            [
                ["Skill", "Job Postings", "Mandatory Postings", "Accepted Offer Placements", "Outcome Share (%)"],
                *[
                    [
                        s.skill_name,
                        s.job_postings_count,
                        s.mandatory_count,
                        s.accepted_offer_count,
                        s.outcome_success_rate_pct,
                    ]
                    for s in report.skill_intelligence.most_requested_skills
                ],
            ],
        ),
    ]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        content_types = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
            '<Default Extension="xml" ContentType="application/xml"/>',
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        ]
        for idx in range(1, len(sheets) + 1):
            content_types.append(
                f'<Override PartName="/xl/worksheets/sheet{idx}.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            )
        content_types.append("</Types>")
        zf.writestr("[Content_Types].xml", "".join(content_types))

        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )

        wb_sheets = []
        wb_rels = []
        for idx, (sheet_name, rows) in enumerate(sheets, start=1):
            wb_sheets.append(f'<sheet name="{sheet_name}" sheetId="{idx}" r:id="rId{idx}"/>')
            wb_rels.append(
                f'<Relationship Id="rId{idx}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                f'Target="worksheets/sheet{idx}.xml"/>'
            )
            zf.writestr(f"xl/worksheets/sheet{idx}.xml", _build_worksheet_xml(rows))

        zf.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f"<sheets>{''.join(wb_sheets)}</sheets>"
            "</workbook>",
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f"{''.join(wb_rels)}"
            "</Relationships>",
        )

    return buf.getvalue()

