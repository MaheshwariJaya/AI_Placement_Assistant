"""
Document Exporter Engine for Automated Placement Reports.
Generates multi-page PDF documents (via PyMuPDF) with institutional branding,
multi-sheet OpenXML Excel workbooks (.xlsx via stdlib zipfile + XML), and CSV tables.
"""
import csv
import io
import os
from pathlib import Path
from typing import Any, List, Tuple
import xml.etree.ElementTree as ET
import zipfile

import pymupdf

from app.config import get_settings
from app.schemas.report import ReportDataPayload

settings = get_settings()


# ---------------------------------------------------------------------------
# PDF Generation with PyMuPDF
# ---------------------------------------------------------------------------

def generate_report_pdf(payload: ReportDataPayload) -> bytes:
    """Render a comprehensive, professional, multi-page PDF placement report."""
    doc = pymupdf.open()
    page_w, page_h = 595, 842  # Standard A4
    margin = 36
    y = margin

    def new_page():
        nonlocal y
        p = doc.new_page(width=page_w, height=page_h)
        y = margin
        return p

    page = new_page()

    def write_line(
        text: str,
        size: float = 9.5,
        bold: bool = False,
        color=(0.12, 0.16, 0.24),
        gap: float = 14,
        indent: float = 0,
    ):
        nonlocal page, y
        fontname = "hebo" if bold else "helv"
        words = str(text or "").split(" ")
        lines: List[str] = []
        cur = ""
        max_chars = int((page_w - 2 * margin - indent) / (size * 0.52))
        max_chars = max(max_chars, 40)

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
            if y > page_h - margin - 35:
                page = new_page()
            page.insert_text((margin + indent, y), ln, fontsize=size, fontname=fontname, color=color)
            y += gap

    # 1. Top Decorative Brand Bar
    page.draw_rect(pymupdf.Rect(margin, y, page_w - margin, y + 4), color=(0.24, 0.22, 0.72), fill=(0.24, 0.22, 0.72))
    y += 16

    # 2. Institutional Header & Title
    write_line(payload.institution_name.upper(), size=14, bold=True, color=(0.15, 0.18, 0.26), gap=18)
    inst_sub = f"{payload.institution_city} · Institutional Code: {payload.institution_code}"
    write_line(inst_sub, size=8.5, color=(0.4, 0.45, 0.52), gap=14)

    write_line(payload.title, size=13, bold=True, color=(0.24, 0.22, 0.72), gap=16)
    gen_sub = (
        f"Generated: {payload.generated_at.strftime('%Y-%m-%d %H:%M UTC')} | "
        f"By: {payload.generated_by_name} ({payload.generated_by_role}) | "
        f"Report Type: {payload.report_type_label}"
    )
    write_line(gen_sub, size=8, color=(0.35, 0.4, 0.48), gap=14)

    # 3. Applied Filters Pill Box
    filt = payload.filters_applied
    filt_parts = []
    if filt.academic_year:
        filt_parts.append(f"Academic Year: {filt.academic_year}")
    if filt.graduation_batch:
        filt_parts.append(f"Graduation Batch: {filt.graduation_batch}")
    if filt.department_id:
        filt_parts.append(f"Department ID: {filt.department_id}")
    if filt.company_id:
        filt_parts.append(f"Company ID: {filt.company_id}")
    if filt.drive_id:
        filt_parts.append(f"Drive ID: {filt.drive_id}")
    if filt.application_status:
        filt_parts.append(f"Status: {filt.application_status.replace('_', ' ').title()}")
    if filt.start_date:
        filt_parts.append(f"From: {filt.start_date.strftime('%Y-%m-%d')}")
    if filt.end_date:
        filt_parts.append(f"To: {filt.end_date.strftime('%Y-%m-%d')}")

    filt_text = "Filters Applied: " + (", ".join(filt_parts) if filt_parts else "Full Institution Cohort")
    write_line(filt_text, size=8, bold=True, color=(0.3, 0.35, 0.45), gap=16)

    # 4. Executive Summary KPI Grid (Table format)
    write_line("1. EXECUTIVE PLACEMENT SUMMARY", size=11, bold=True, color=(0.18, 0.22, 0.3), gap=16)
    kpis = payload.summary_kpis
    kpi_rows = [
        ("Total Eligible Students", str(kpis.total_eligible_students), "Total Placed (Accepted)", f"{kpis.total_placed_students} ({kpis.placement_rate_pct}%)"),
        ("Students in Pipeline", str(kpis.students_in_pipeline), "Students Not Yet Placed", str(kpis.students_not_yet_placed)),
        ("Participating Companies", str(kpis.total_companies), "Active Placement Drives", str(kpis.total_active_drives)),
        ("Offers Released", str(kpis.total_offers_released), "Offers Accepted", f"{kpis.total_accepted_offers} ({kpis.offer_acceptance_rate_pct}%)"),
        ("Average Package", f"{kpis.average_package_lpa} LPA" if kpis.average_package_lpa else "N/A", "Highest Package", f"{kpis.highest_package_lpa} LPA" if kpis.highest_package_lpa else "N/A"),
    ]

    col_w1 = 145
    col_w2 = 115
    row_h = 16
    for c1_label, c1_val, c2_label, c2_val in kpi_rows:
        if y > page_h - margin - 30:
            page = new_page()
        # Draw soft background cell
        page.draw_rect(pymupdf.Rect(margin, y - 2, margin + col_w1 + col_w2, y + row_h - 2), color=(0.92, 0.94, 0.96), fill=(0.97, 0.98, 0.99))
        page.draw_rect(pymupdf.Rect(margin + col_w1 + col_w2 + 10, y - 2, margin + 2 * (col_w1 + col_w2) + 10, y + row_h - 2), color=(0.92, 0.94, 0.96), fill=(0.97, 0.98, 0.99))

        page.insert_text((margin + 4, y + 10), c1_label, fontsize=8, fontname="helv", color=(0.35, 0.4, 0.48))
        page.insert_text((margin + col_w1, y + 10), c1_val, fontsize=8.5, fontname="hebo", color=(0.15, 0.18, 0.24))

        page.insert_text((margin + col_w1 + col_w2 + 14, y + 10), c2_label, fontsize=8, fontname="helv", color=(0.35, 0.4, 0.48))
        page.insert_text((margin + 2 * col_w1 + col_w2 + 10, y + 10), c2_val, fontsize=8.5, fontname="hebo", color=(0.15, 0.18, 0.24))
        y += row_h + 3
    y += 10

    # 5. Primary Report Data Table
    table_sec_title = f"2. {payload.report_type_label.upper()} DATA RECORDS ({len(payload.table_rows)} items)"
    write_line(table_sec_title, size=11, bold=True, color=(0.18, 0.22, 0.3), gap=16)

    headers = payload.table_headers or []
    rows = payload.table_rows or []

    if headers and rows:
        num_cols = len(headers)
        avail_w = page_w - 2 * margin
        base_w = avail_w / num_cols

        # Adjust specific columns if wide
        col_widths = [base_w] * num_cols

        def draw_table_header():
            nonlocal y
            page.draw_rect(pymupdf.Rect(margin, y - 2, margin + avail_w, y + 16), color=(0.24, 0.22, 0.72), fill=(0.24, 0.22, 0.72))
            cx = margin
            for idx, h in enumerate(headers):
                w = col_widths[idx]
                page.insert_text((cx + 3, y + 10), str(h)[:18], fontsize=7.5, fontname="hebo", color=(1.0, 1.0, 1.0))
                cx += w
            y += 20

        draw_table_header()

        for r_idx, row in enumerate(rows):
            if y > page_h - margin - 25:
                page = new_page()
                draw_table_header()

            # Zebra stripe
            row_fill = (0.97, 0.98, 0.99) if r_idx % 2 == 1 else (1.0, 1.0, 1.0)
            page.draw_rect(pymupdf.Rect(margin, y - 2, margin + avail_w, y + 13), color=(0.92, 0.93, 0.95), fill=row_fill)

            cx = margin
            vals = list(row.values()) if isinstance(row, dict) else list(row)
            for idx in range(num_cols):
                w = col_widths[idx]
                val_str = str(vals[idx] if idx < len(vals) else "")
                max_c = max(int(w / 4.8), 8)
                page.insert_text((cx + 3, y + 8), val_str[:max_c], fontsize=7, fontname="helv", color=(0.15, 0.18, 0.24))
                cx += w
            y += 15
        y += 10
    else:
        write_line("- No record matches the selected filters.", size=8.5, color=(0.4, 0.45, 0.5), gap=14)

    # 6. Recruitment Funnel (if room or on next page)
    if payload.recruitment_funnel:
        if y > page_h - margin - 80:
            page = new_page()
        write_line("3. RECRUITMENT FUNNEL STAGES", size=10, bold=True, color=(0.18, 0.22, 0.3), gap=14)
        for fn in payload.recruitment_funnel:
            write_line(f"- {fn.label}: {fn.count} ({fn.percentage}%)", size=8, color=(0.25, 0.3, 0.38), gap=12, indent=8)
        y += 6

    # 7. Policy and Disclaimers
    if y > page_h - margin - 60:
        page = new_page()
    write_line("4. INSTITUTIONAL PLACEMENT POLICY & NOTES", size=10, bold=True, color=(0.18, 0.22, 0.3), gap=14)
    for note in payload.notes_and_disclaimers:
        write_line(f"• {note}", size=7.5, color=(0.4, 0.45, 0.5), gap=11, indent=6)

    # 8. Second Pass: Insert Page Numbers & Footers
    total_pages = len(doc)
    for p_idx, p in enumerate(doc):
        footer_text = f"Page {p_idx + 1} of {total_pages} | {payload.institution_name} | Placement Intelligence System"
        p.insert_text((margin, page_h - margin + 14), footer_text, fontsize=7.5, fontname="helv", color=(0.45, 0.5, 0.58))
        p.draw_line(pymupdf.Point(margin, page_h - margin + 4), pymupdf.Point(page_w - margin, page_h - margin + 4), color=(0.85, 0.88, 0.92))

    data = doc.tobytes()
    doc.close()
    return data


# ---------------------------------------------------------------------------
# Multi-Sheet OpenXML Excel (.xlsx) Exporter
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


def generate_report_excel(payload: ReportDataPayload) -> bytes:
    """Create a multi-sheet OpenXML Excel (.xlsx) workbook for placement report."""
    kpis = payload.summary_kpis

    # Sheet 1: Executive Summary
    summary_rows: List[List[Any]] = [
        [payload.institution_name],
        [payload.title],
        ["Generated At (UTC)", payload.generated_at.isoformat()],
        ["Generated By", f"{payload.generated_by_name} ({payload.generated_by_role})"],
        ["Institution Code / City", f"{payload.institution_code} - {payload.institution_city}"],
        ["Policy Summary", payload.policy_summary],
        [],
        ["Core Placement Metric", "Value"],
        ["Total Registered Students", kpis.total_registered_students],
        ["Total Eligible Students", kpis.total_eligible_students],
        ["Total Placed Students (Unique Accepted)", kpis.total_placed_students],
        ["Placement Rate (%)", kpis.placement_rate_pct],
        ["Students in Active Pipeline", kpis.students_in_pipeline],
        ["Students Not Yet Placed", kpis.students_not_yet_placed],
        ["Total Participating Companies", kpis.total_companies],
        ["Total Active Placement Drives", kpis.total_active_drives],
        ["Total Published Jobs", kpis.total_published_jobs],
        ["Total Offers Released", kpis.total_offers_released],
        ["Total Accepted Offers", kpis.total_accepted_offers],
        ["Total Declined Offers", kpis.total_declined_offers],
        ["Pending Offers", kpis.pending_offers],
        ["Offer Acceptance Rate (%)", kpis.offer_acceptance_rate_pct],
        ["Average Package (LPA)", kpis.average_package_lpa if kpis.average_package_lpa is not None else "N/A"],
        ["Median Package (LPA)", kpis.median_package_lpa if kpis.median_package_lpa is not None else "N/A"],
        ["Highest Package (LPA)", kpis.highest_package_lpa if kpis.highest_package_lpa is not None else "N/A"],
    ]

    # Sheet 2: Main Report Table
    data_rows: List[List[Any]] = []
    if payload.table_headers:
        data_rows.append(payload.table_headers)
        for r in payload.table_rows:
            if isinstance(r, dict):
                data_rows.append(list(r.values()))
            else:
                data_rows.append(list(r))
    else:
        data_rows.append(["No records matching selected criteria."])

    # Sheet 3: Department Breakdown
    dept_rows: List[List[Any]] = [
        [
            "Department Code",
            "Department Name",
            "Eligible Students",
            "Placed Students",
            "Placement Rate (%)",
            "Offers Accepted",
            "Average Package (LPA)",
            "Highest Package (LPA)",
            "Top Recruiting Companies",
        ]
    ]
    for d in payload.department_stats:
        dept_rows.append([
            d.department_code,
            d.department_name,
            d.eligible_students,
            d.placed_students,
            d.placement_rate_pct,
            d.offers_accepted,
            d.average_package_lpa if d.average_package_lpa is not None else "N/A",
            d.highest_package_lpa if d.highest_package_lpa is not None else "N/A",
            ", ".join(d.top_recruiting_companies) if d.top_recruiting_companies else "None yet",
        ])

    # Sheet 4: Recruitment Funnel
    funnel_rows: List[List[Any]] = [
        ["Funnel Stage", "Stage Label", "Candidates Count", "Conversion Share (%)"]
    ]
    for fn in payload.recruitment_funnel:
        funnel_rows.append([fn.stage, fn.label, fn.count, fn.percentage])

    sheets: List[Tuple[str, List[List[Any]]]] = [
        ("Summary", summary_rows),
        ("Report_Data", data_rows),
        ("Departments", dept_rows),
        ("Recruitment_Funnel", funnel_rows),
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
        for idx, (sheet_name, r_list) in enumerate(sheets, start=1):
            wb_sheets.append(f'<sheet name="{sheet_name}" sheetId="{idx}" r:id="rId{idx}"/>')
            wb_rels.append(
                f'<Relationship Id="rId{idx}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                f'Target="worksheets/sheet{idx}.xml"/>'
            )
            zf.writestr(f"xl/worksheets/sheet{idx}.xml", _build_worksheet_xml(r_list))

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


# ---------------------------------------------------------------------------
# CSV Exporter
# ---------------------------------------------------------------------------

def generate_report_csv(payload: ReportDataPayload) -> bytes:
    """Create a UTF-8 with BOM CSV document for the report tabular records."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")

    # Header comments
    writer.writerow([f"# {payload.institution_name} - {payload.title}"])
    writer.writerow([f"# Generated: {payload.generated_at.isoformat()} by {payload.generated_by_name}"])
    writer.writerow([])

    if payload.table_headers:
        writer.writerow(payload.table_headers)
        for r in payload.table_rows:
            if isinstance(r, dict):
                writer.writerow(list(r.values()))
            else:
                writer.writerow(list(r))
    else:
        writer.writerow(["No data"])

    return ("\ufeff" + buf.getvalue()).encode("utf-8")


# ---------------------------------------------------------------------------
# File Storage Persistence Helper
# ---------------------------------------------------------------------------

def save_report_file(institution_id: int, file_name: str, file_bytes: bytes) -> Tuple[str, int]:
    """Persist generated report file to secure institutional directory."""
    base_dir = Path(settings.REPORT_STORAGE_DIR) / str(institution_id)
    base_dir.mkdir(parents=True, exist_ok=True)
    full_path = base_dir / file_name

    with open(full_path, "wb") as f:
        f.write(file_bytes)

    relative_path = str(full_path.as_posix())
    file_size = len(file_bytes)
    return relative_path, file_size

