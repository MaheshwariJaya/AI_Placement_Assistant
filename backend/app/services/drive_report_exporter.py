"""PDF and multi-sheet OpenXML Excel exporters for Drive-Specific Reports."""
import io
import zipfile
import xml.etree.ElementTree as ET
from typing import Any, List

import pymupdf

from app.schemas.drive_workspace import DriveReportResponse


def generate_drive_report_pdf(report: DriveReportResponse) -> bytes:
    """Render a clean PDF report covering drive overview, funnel, attendance & final outcomes."""
    doc = pymupdf.open()
    page_w, page_h = 595, 842
    margin = 40
    page = doc.new_page(width=page_w, height=page_h)
    y = margin

    def write_line(text: str, size: float = 10, bold: bool = False, color=(0.12, 0.16, 0.24), gap: float = 14):
        nonlocal page, y
        fontname = "hebo" if bold else "helv"
        words = str(text).split(" ")
        lines: List[str] = []
        cur = ""
        max_chars = 88 if size <= 10 else 68
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
            if y > page_h - margin - 20:
                page = doc.new_page(width=page_w, height=page_h)
                y = margin
            page.insert_text((margin, y), ln, fontsize=size, fontname=fontname, color=color)
            y += gap

    drv = report.drive
    dash = report.dashboard
    write_line(f"PLACEMENT DRIVE REPORT: {drv['name']}", size=13, bold=True, color=(0.24, 0.22, 0.72), gap=18)
    write_line(
        f"Academic Year: {drv['academic_year']} | Phase: {drv['lifecycle_phase']} | Mode: {drv['drive_mode']} | Venue: {drv.get('venue_location') or 'N/A'}",
        size=9,
        color=(0.35, 0.4, 0.48),
        gap=16,
    )

    write_line("1. PARTICIPATION & FUNNEL SUMMARY", size=11, bold=True, gap=16)
    write_line(
        f"Registered Students: {dash.total_registered_students} | Eligible: {dash.eligible_students} | Ineligible: {dash.ineligible_students}",
        gap=14,
    )
    write_line(
        f"Applications Received: {dash.applications_received} | Shortlisted: {dash.shortlisted_candidates} | Interviews Scheduled/Completed: {dash.interview_scheduled_count}/{dash.interview_completed_count}",
        gap=14,
    )
    write_line(
        f"Offers Released: {dash.offers_released} | Final Placements (Accepted): {dash.final_placements}",
        gap=16,
    )

    write_line("2. ROLE-WISE BREAKDOWN", size=11, bold=True, gap=16)
    for jb in report.dashboard.job_breakdown or []:
        write_line(
            f"- {jb.company_name} / {jb.title}: Apps {jb.applications_count}, Shortlisted {jb.shortlisted_count}, Offers {jb.offered_count}, Accepted {jb.accepted_count}",
            size=9,
            gap=13,
        )
    if not report.dashboard.job_breakdown:
        write_line("- No associated jobs recorded.", size=9, gap=13)
    y += 4

    write_line("3. ACTIVITY ATTENDANCE SUMMARY", size=11, bold=True, gap=16)
    for ac in report.attendance_summary:
        write_line(
            f"- {ac.title} ({ac.activity_type}) | Coord: {ac.coordinator_name} | Present: {ac.present_count}, Late: {ac.late_count}, Absent: {ac.absent_count}, Excused: {ac.excused_count} ({ac.attendance_rate_pct}%)",
            size=9,
            gap=13,
        )
    if not report.attendance_summary:
        write_line("- No scheduled drive activities recorded.", size=9, gap=13)
    y += 4

    write_line("4. FINAL PLACEMENT OUTCOMES (OFFER ACCEPTED)", size=11, bold=True, gap=16)
    for out in report.placed_outcomes:
        pkg = f"{out['package_lpa']} LPA" if out["package_lpa"] is not None else "N/A"
        write_line(
            f"- {out['roll_number']} ({out['student_name']}, {out['department']}) -> {out['company_name']} / {out['job_title']} ({pkg})",
            size=9,
            gap=13,
        )
    if not report.placed_outcomes:
        write_line("- No accepted placement offers recorded in this drive yet.", size=9, gap=13)

    data = doc.tobytes()
    doc.close()
    return data


def _col_letter(idx: int) -> str:
    res = ""
    n = idx + 1
    while n > 0:
        n, rem = divmod(n - 1, 26)
        res = chr(65 + rem) + res
    return res


def _build_sheet_xml(rows: List[List[Any]]) -> bytes:
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    root = ET.Element("worksheet", xmlns=ns)
    sheet_data = ET.SubElement(root, "sheetData")
    for r_idx, row_vals in enumerate(rows, start=1):
        row_el = ET.SubElement(sheet_data, "row", r=str(r_idx))
        for c_idx, val in enumerate(row_vals):
            ref = f"{_col_letter(c_idx)}{r_idx}"
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                cell = ET.SubElement(row_el, "c", r=ref, t="n")
                v_el = ET.SubElement(cell, "v")
                v_el.text = str(val)
            else:
                cell = ET.SubElement(row_el, "c", r=ref, t="inlineStr")
                is_el = ET.SubElement(cell, "is")
                t_el = ET.SubElement(is_el, "t")
                t_el.text = "" if val is None else str(val)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def generate_drive_report_excel(report: DriveReportResponse) -> bytes:
    """Build a multi-sheet .xlsx workbook covering Overview, Jobs, Attendance, and Placed Outcomes."""
    dash = report.dashboard
    drv = report.drive
    sheets = [
        (
            "Drive_Overview",
            [
                ["Field", "Value"],
                ["Drive Name", drv["name"]],
                ["Academic Year", drv["academic_year"]],
                ["Lifecycle Phase", drv["lifecycle_phase"]],
                ["Registered Students", dash.total_registered_students],
                ["Eligible Students", dash.eligible_students],
                ["Ineligible Students", dash.ineligible_students],
                ["Applications Received", dash.applications_received],
                ["Shortlisted Candidates", dash.shortlisted_candidates],
                ["Offers Released", dash.offers_released],
                ["Final Placements", dash.final_placements],
            ],
        ),
        (
            "Role_Breakdown",
            [["Job ID", "Company", "Role Title", "Applications", "Shortlisted", "Interviews", "Offers", "Accepted"]]
            + [
                [
                    jb.job_id,
                    jb.company_name,
                    jb.title,
                    jb.applications_count,
                    jb.shortlisted_count,
                    jb.interview_count,
                    jb.offered_count,
                    jb.accepted_count,
                ]
                for jb in dash.job_breakdown
            ],
        ),
        (
            "Activity_Attendance",
            [["Activity ID", "Title", "Type", "Coordinator", "Status", "Present", "Late", "Absent", "Excused", "Rate %"]]
            + [
                [
                    ac.activity_id,
                    ac.title,
                    ac.activity_type,
                    ac.coordinator_name,
                    ac.status,
                    ac.present_count,
                    ac.late_count,
                    ac.absent_count,
                    ac.excused_count,
                    ac.attendance_rate_pct,
                ]
                for ac in report.attendance_summary
            ],
        ),
        (
            "Placed_Outcomes",
            [["Student ID", "Roll Number", "Student Name", "Department", "Company", "Role", "Package (LPA)"]]
            + [
                [
                    out["student_id"],
                    out["roll_number"],
                    out["student_name"],
                    out["department"],
                    out["company_name"],
                    out["job_title"],
                    out["package_lpa"] if out["package_lpa"] is not None else "N/A",
                ]
                for out in report.placed_outcomes
            ],
        ),
    ]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        ct_parts = [
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        ]
        wb_sheets = []
        wb_rels = []
        for idx, (s_name, rows) in enumerate(sheets, start=1):
            zf.writestr(f"xl/worksheets/sheet{idx}.xml", _build_sheet_xml(rows))
            ct_parts.append(
                f'<Override PartName="/xl/worksheets/sheet{idx}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            )
            wb_sheets.append(f'<sheet name="{s_name}" sheetId="{idx}" r:id="rId{idx}"/>')
            wb_rels.append(
                f'<Relationship Id="rId{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{idx}.xml"/>'
            )

        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            + "".join(ct_parts)
            + "</Types>",
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        zf.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            "<sheets>"
            + "".join(wb_sheets)
            + "</sheets></workbook>",
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(wb_rels)
            + "</Relationships>",
        )
    return buf.getvalue()

