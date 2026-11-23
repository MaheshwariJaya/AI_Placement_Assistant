"""
Integration, accuracy, multi-format export, and security tests for TASK 07:
Automated Placement Report Generator.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import io
import uuid
import xml.etree.ElementTree as ET
import zipfile

import pymupdf
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import get_settings
from app.core.errors import AuthorizationException, EntityNotFoundException
from app.core.security import hash_password
from app.models.company import Company
from app.models.job import (
    EmploymentType,
    Job,
    JobEligibleDepartment,
    JobSkill,
    JobStatus,
    WorkMode,
)
from app.models.organization import Department, Institution
from app.models.placement import (
    ApplicationStatus,
    DriveLifecyclePhase,
    DriveMode,
    DriveStatus,
    JobApplication,
    PlacementDrive,
    PlacementDriveJob,
    PlacementDriveRegistration,
    TpoScreeningStatus,
)
from app.models.report import PlacementReport, ReportFormat, ReportStatus, ReportType
from app.models.resume import Resume
from app.models.student import StudentProfile, StudentSkill
from app.models.user import User, UserRole
from app.routes.reports import (
    delete_report_endpoint,
    download_report_file_endpoint,
    generate_and_save_report_endpoint,
    generate_report_async_endpoint,
    get_report_endpoint,
    get_report_options_endpoint,
    list_reports_history_endpoint,
    preview_report_endpoint,
)
from app.schemas.report import ReportFilterParams, ReportGenerateRequest
from app.services.report_file_exporter import (
    generate_report_csv,
    generate_report_excel,
    generate_report_pdf,
)
from app.services.report_generator_service import compile_report_data


def _new_test_engine():
    settings = get_settings()
    return create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        connect_args={"server_settings": {"search_path": f"{settings.DB_SCHEMA},public"}},
    )


async def _consume_streaming_body(resp) -> bytes:
    chunks = []
    async for chunk in resp.body_iterator:
        chunks.append(chunk)
    return b"".join(chunks)


async def _seed_report_fixtures(session: AsyncSession) -> dict:
    tag = uuid.uuid4().hex[:6]
    now = datetime.now(timezone.utc)

    # 1. Institutions
    inst_a = Institution(name=f"Apex Technical University {tag}", code=f"APEX_{tag}", city="Jaipur", is_active=True)
    inst_b = Institution(name=f"Zenith Institute {tag}", code=f"ZEN_{tag}", city="Udaipur", is_active=True)
    session.add_all([inst_a, inst_b])
    await session.flush()

    # 2. Departments
    dept_cs = Department(institution_id=inst_a.id, name="Computer Science", code=f"CS_{tag}", is_active=True)
    dept_ec = Department(institution_id=inst_a.id, name="Electronics & Comm", code=f"EC_{tag}", is_active=True)
    dept_b = Department(institution_id=inst_b.id, name="Information Tech", code=f"IT_{tag}", is_active=True)
    session.add_all([dept_cs, dept_ec, dept_b])
    await session.flush()

    # 3. Users: TPO A, TPO B, Admin, Students
    pwd = hash_password("ValidPass123!")
    tpo_a = User(
        institution_id=inst_a.id,
        department_id=dept_cs.id,
        email=f"tpo_a_{tag}@apex.edu",
        hashed_password=pwd,
        full_name="Dr. Anita Sharma",
        role=UserRole.TPO,
        is_active=True,
    )
    tpo_b = User(
        institution_id=inst_b.id,
        department_id=dept_b.id,
        email=f"tpo_b_{tag}@zenith.edu",
        hashed_password=pwd,
        full_name="Prof. Rajesh B",
        role=UserRole.TPO,
        is_active=True,
    )
    admin_user = User(
        institution_id=inst_a.id,
        department_id=dept_cs.id,
        email=f"admin_{tag}@apex.edu",
        hashed_password=pwd,
        full_name="Apex System Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    session.add_all([tpo_a, tpo_b, admin_user])
    await session.flush()

    # 4. Companies & Jobs
    comp_alpha = Company(name=f"AlphaCorp_{tag}", industry="Software Engineering", is_active=True, institution_id=inst_a.id)
    comp_beta = Company(name=f"BetaSystems_{tag}", industry="Cloud Systems", is_active=True, institution_id=inst_a.id)
    session.add_all([comp_alpha, comp_beta])
    await session.flush()

    job_alpha = Job(
        company_id=comp_alpha.id,
        institution_id=inst_a.id,
        created_by_user_id=tpo_a.id,
        title="Full Stack Developer",
        description="Core developer role",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.ON_SITE,
        status=JobStatus.PUBLISHED,
        location="Bengaluru",
        min_cgpa=7.0,
        ctc_lpa=12.0,
        application_deadline=now + timedelta(days=30),
        is_active=True,
    )
    job_beta = Job(
        company_id=comp_beta.id,
        institution_id=inst_a.id,
        created_by_user_id=tpo_a.id,
        title="DevOps Engineer",
        description="Infrastructure and SRE",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.ON_SITE,
        status=JobStatus.PUBLISHED,
        location="Pune",
        min_cgpa=6.5,
        ctc_lpa=16.0,
        application_deadline=now + timedelta(days=30),
        is_active=True,
    )
    session.add_all([job_alpha, job_beta])
    await session.flush()

    # 5. Placement Drive
    drive = PlacementDrive(
        institution_id=inst_a.id,
        created_by_user_id=tpo_a.id,
        name=f"Apex Spring Campus Drive 2026 {tag}",
        academic_year="2025-2026",
        target_graduation_year=2026,
        registration_start_date=now - timedelta(days=5),
        registration_end_date=now + timedelta(days=10),
        drive_mode=DriveMode.ON_CAMPUS,
        status=DriveStatus.ONGOING,
        lifecycle_phase=DriveLifecyclePhase.ONGOING,
        venue_location="Main Auditorium",
        target_graduation_batches=[2026],
        participating_company_ids=[comp_alpha.id, comp_beta.id],
        eligible_department_ids=[dept_cs.id, dept_ec.id],
    )
    session.add(drive)
    await session.flush()

    pdj_alpha = PlacementDriveJob(drive_id=drive.id, job_id=job_alpha.id, is_active=True)
    pdj_beta = PlacementDriveJob(drive_id=drive.id, job_id=job_beta.id, is_active=True)
    session.add_all([pdj_alpha, pdj_beta])
    await session.flush()

    # 6. Students:
    # stu1: CS 2026, CGPA 8.5, placed at AlphaCorp (12 LPA) and BetaSystems (18 LPA offer accepted)
    # stu2: CS 2026, CGPA 7.8, offered at AlphaCorp (12 LPA) but declined
    # stu3: EC 2026, CGPA 7.2, placed at AlphaCorp (12 LPA accepted)
    # stu4: CS 2026, CGPA 6.2, unplaced (no offers, in pipeline)
    # stu5: EC 2026, CGPA 6.0, unplaced (0 applications)
    # stu_other: Institution B student
    student_specs = [
        ("stu1", dept_cs, 2026, 8.5, 0),
        ("stu2", dept_cs, 2026, 7.8, 0),
        ("stu3", dept_ec, 2026, 7.2, 0),
        ("stu4", dept_cs, 2026, 6.2, 1),
        ("stu5", dept_ec, 2026, 6.0, 0),
    ]
    students = {}
    profiles = {}
    resumes = {}

    for key, d, yr, cgpa, backlogs in student_specs:
        u = User(
            institution_id=inst_a.id,
            department_id=d.id,
            email=f"{key}_{tag}@apex.edu",
            hashed_password=pwd,
            full_name=f"Student {key.upper()}",
            role=UserRole.STUDENT,
            is_active=True,
        )
        session.add(u)
        await session.flush()
        students[key] = u

        sp = StudentProfile(
            user_id=u.id,
            roll_number=f"26{key.upper()}_{tag}",
            graduation_year=yr,
            cgpa=cgpa,
            active_backlogs=backlogs,
            total_backlogs=backlogs,
            is_placement_ready=True,
        )
        session.add(sp)
        await session.flush()
        profiles[key] = sp

        res = Resume(
            student_id=sp.id,
            file_name=f"{key}_resume.pdf",
            file_path=f"uploads/{key}.pdf",
            file_type="pdf",
            file_size_bytes=1024,
            file_hash=f"{key:0<64}",
            parsing_status="approved",
            is_active=True,
        )
        session.add(res)
        await session.flush()
        resumes[key] = res

    # Register stu1, stu2, stu3 for drive
    for k in ("stu1", "stu2", "stu3", "stu4"):
        session.add(
            PlacementDriveRegistration(
                drive_id=drive.id,
                student_id=profiles[k].id,
                registered_by_user_id=students[k].id,
                registration_source="student_self",
                status="registered",
                eligibility_passed=True,
            )
        )
    await session.flush()

    # Applications:
    # app1: stu1 -> job_alpha -> OFFER_ACCEPTED (12 LPA)
    # app2: stu1 -> job_beta -> OFFER_ACCEPTED (18.5 LPA) -- stu1 has 2 accepted offers!
    # app3: stu2 -> job_alpha -> OFFER_DECLINED (12 LPA) -- declined must NOT count as placed!
    # app4: stu3 -> job_alpha -> OFFER_ACCEPTED (12 LPA)
    # app5: stu4 -> job_alpha -> SHORTLISTED (in pipeline)
    app1 = JobApplication(
        job_id=job_alpha.id,
        student_id=profiles["stu1"].id,
        resume_id=resumes["stu1"].id,
        drive_id=drive.id,
        tpo_screening_status=TpoScreeningStatus.SHORTLISTED,
        tpo_screened_by_user_id=tpo_a.id,
        tpo_screened_at=now - timedelta(days=5),
        compatibility_score_at_application=88.5,
        current_status=ApplicationStatus.OFFER_ACCEPTED,
        offer_package_lpa=12.0,
        created_at=now - timedelta(days=4),
    )
    app2 = JobApplication(
        job_id=job_beta.id,
        student_id=profiles["stu1"].id,
        resume_id=resumes["stu1"].id,
        drive_id=drive.id,
        tpo_screening_status=TpoScreeningStatus.SHORTLISTED,
        tpo_screened_by_user_id=tpo_a.id,
        tpo_screened_at=now - timedelta(days=5),
        compatibility_score_at_application=92.0,
        current_status=ApplicationStatus.OFFER_ACCEPTED,
        offer_package_lpa=18.5,
        created_at=now - timedelta(days=3),
    )
    app3 = JobApplication(
        job_id=job_alpha.id,
        student_id=profiles["stu2"].id,
        resume_id=resumes["stu2"].id,
        drive_id=drive.id,
        tpo_screening_status=TpoScreeningStatus.SHORTLISTED,
        tpo_screened_by_user_id=tpo_a.id,
        tpo_screened_at=now - timedelta(days=5),
        compatibility_score_at_application=76.0,
        current_status=ApplicationStatus.OFFER_DECLINED,
        offer_package_lpa=12.0,
        created_at=now - timedelta(days=2),
    )
    app4 = JobApplication(
        job_id=job_alpha.id,
        student_id=profiles["stu3"].id,
        resume_id=resumes["stu3"].id,
        drive_id=drive.id,
        tpo_screening_status=TpoScreeningStatus.SHORTLISTED,
        tpo_screened_by_user_id=tpo_a.id,
        tpo_screened_at=now - timedelta(days=5),
        compatibility_score_at_application=81.0,
        current_status=ApplicationStatus.OFFER_ACCEPTED,
        offer_package_lpa=12.0,
        created_at=now - timedelta(days=1),
    )
    app5 = JobApplication(
        job_id=job_alpha.id,
        student_id=profiles["stu4"].id,
        resume_id=resumes["stu4"].id,
        drive_id=drive.id,
        tpo_screening_status=TpoScreeningStatus.SHORTLISTED,
        tpo_screened_by_user_id=tpo_a.id,
        tpo_screened_at=now - timedelta(days=5),
        compatibility_score_at_application=84.0,
        current_status=ApplicationStatus.SHORTLISTED,
        created_at=now - timedelta(hours=12),
    )
    session.add_all([app1, app2, app3, app4, app5])
    await session.flush()

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "tpo_a": tpo_a,
        "tpo_b": tpo_b,
        "admin": admin_user,
        "dept_cs": dept_cs,
        "dept_ec": dept_ec,
        "comp_alpha": comp_alpha,
        "comp_beta": comp_beta,
        "job_alpha": job_alpha,
        "job_beta": job_beta,
        "drive": drive,
        "students": students,
        "profiles": profiles,
    }


def test_report_form_options_and_scoping():
    """Verify form options returns institution-scoped metadata, batches, depts, companies & report types."""

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_report_fixtures(session)

                    opts = await get_report_options_endpoint(current_user=fx["tpo_a"], session=session)
                    assert opts.institution_id == fx["inst_a"].id
                    assert 2026 in opts.graduation_batches
                    assert "2025-2026" in opts.academic_years
                    assert len(opts.report_types) == 10
                    assert len(opts.file_formats) == 3  # PDF, XLSX, CSV

                    dept_ids = {d.id for d in opts.departments}
                    assert fx["dept_cs"].id in dept_ids
                    assert fx["dept_ec"].id in dept_ids

                    comp_ids = {c.id for c in opts.companies}
                    assert fx["comp_alpha"].id in comp_ids
                    assert fx["comp_beta"].id in comp_ids
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_report_calculations_accuracy_and_policy():
    """
    Verify strict calculation accuracy:
    1. Placed students strictly count unique students with at least 1 OFFER_ACCEPTED.
    2. Multiple accepted offers (stu1 has 2 accepted offers) count as 1 placed student.
    3. Declined offer (stu2) does not count as placed student.
    4. Package uses highest accepted offer per student (stu1 uses 18.5 LPA, not 12.0 LPA).
    5. In pipeline and unplaced counts are accurate.
    """

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_report_fixtures(session)

                    req = ReportGenerateRequest(
                        report_type=ReportType.OVERALL_INSTITUTIONAL,
                        filters=ReportFilterParams(),
                    )
                    preview = await preview_report_endpoint(payload=req, current_user=fx["tpo_a"], session=session)

                    kpis = preview.summary_kpis
                    assert kpis.total_eligible_students == 5
                    # Placed students must be exactly 2: stu1 and stu3!
                    # stu1 holds 2 accepted offers; stu2 declined; stu4 in pipeline; stu5 no apps.
                    assert kpis.total_placed_students == 2
                    assert kpis.placement_rate_pct == 40.0  # 2/5 * 100%

                    # Placed students packages: stu1 has max(12, 18.5) = 18.5 LPA; stu3 has 12.0 LPA.
                    # Highest package = 18.5 LPA
                    # Average package = (18.5 + 12.0) / 2 = 15.25 LPA
                    assert kpis.highest_package_lpa == 18.5
                    assert kpis.average_package_lpa == 15.25
                    assert kpis.median_package_lpa == 18.5  # sorted([12.0, 18.5])[1] = 18.5

                    # Offers counts:
                    # Released: app1(accepted), app2(accepted), app3(declined), app4(accepted) = 4
                    # Accepted: app1, app2, app4 = 3
                    # Declined: app3 = 1
                    assert kpis.total_offers_released == 4
                    assert kpis.total_accepted_offers == 3
                    assert kpis.total_declined_offers == 1
                    assert kpis.offer_acceptance_rate_pct == 75.0  # 3/4 = 75%

                    # Pipeline vs unplaced counts:
                    # stu4 is shortlisted -> students_in_pipeline == 1
                    # stu2 (declined, no active pipeline) + stu5 (0 apps) -> students_not_yet_placed == 2
                    assert kpis.students_in_pipeline == 1
                    assert kpis.students_not_yet_placed == 2

                    # Department breakdowns:
                    # CS: 3 eligible (stu1, stu2, stu4), 1 placed (stu1) -> 33.33%
                    # EC: 2 eligible (stu3, stu5), 1 placed (stu3) -> 50.0%
                    cs_stat = next(d for d in preview.department_stats if d.department_id == fx["dept_cs"].id)
                    assert cs_stat.eligible_students == 3
                    assert cs_stat.placed_students == 1
                    assert cs_stat.placement_rate_pct == 33.33
                    assert cs_stat.average_package_lpa == 18.5

                    ec_stat = next(d for d in preview.department_stats if d.department_id == fx["dept_ec"].id)
                    assert ec_stat.eligible_students == 2
                    assert ec_stat.placed_students == 1
                    assert ec_stat.placement_rate_pct == 50.0
                    assert ec_stat.average_package_lpa == 12.0
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_all_ten_report_types_generation():
    """Verify preview data generation across all 10 standard report types."""

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_report_fixtures(session)

                    for r_type in ReportType:
                        req = ReportGenerateRequest(report_type=r_type)
                        data = await preview_report_endpoint(payload=req, current_user=fx["tpo_a"], session=session)
                        assert data.report_type == r_type
                        assert data.title
                        assert len(data.table_headers) > 0
                        assert isinstance(data.table_rows, list)
                        assert data.summary_kpis.total_eligible_students == 5

                        if r_type == ReportType.STUDENT_PLACEMENT_STATUS:
                            # 5 student rows
                            assert len(data.table_rows) == 5
                            statuses = {r["placement_status"] for r in data.table_rows}
                            assert "Placed" in statuses
                            assert "In Pipeline" in statuses
                            assert "Not Placed" in statuses

                        elif r_type == ReportType.UNPLACED_STUDENTS:
                            # 3 unplaced students (stu2, stu4, stu5)
                            assert len(data.table_rows) == 3
                            for r in data.table_rows:
                                assert "action_recommendation" in r

                        elif r_type == ReportType.COMPANY_WISE:
                            assert len(data.table_rows) >= 2
                            alpha_row = next(r for r in data.table_rows if fx["comp_alpha"].name in r["company_name"])
                            assert alpha_row["offers_released"] == 3
                            assert alpha_row["offers_accepted"] == 2

                        elif r_type == ReportType.PLACEMENT_DRIVE:
                            assert len(data.table_rows) >= 1
                            drv_row = data.table_rows[0]
                            assert drv_row["placed_students"] == 2

                        elif r_type == ReportType.OFFER_ACCEPTANCE:
                            # 4 offers released
                            assert len(data.table_rows) == 4

                        elif r_type == ReportType.SALARY_PACKAGE_ANALYSIS:
                            assert len(data.table_rows) == 6  # 6 tiers
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_pdf_excel_csv_export_and_formatting():
    """Verify document exports: PDF (PyMuPDF), Excel (.xlsx multi-sheet), and CSV."""

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_report_fixtures(session)

                    req = ReportGenerateRequest(
                        report_type=ReportType.STUDENT_PLACEMENT_STATUS,
                        file_format=ReportFormat.PDF,
                    )
                    data = await compile_report_data(
                        session=session,
                        current_user=fx["tpo_a"],
                        report_type=req.report_type,
                        filters=req.filters,
                    )

                    # 1. PDF
                    pdf_bytes = generate_report_pdf(data)
                    assert pdf_bytes.startswith(b"%PDF-")
                    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
                    assert len(doc) >= 1
                    first_page_text = doc[0].get_text()
                    assert fx["inst_a"].name.upper() in first_page_text
                    assert "Student-Wise Placement Status Report" in first_page_text
                    assert "Page 1 of" in first_page_text
                    doc.close()

                    # 2. Excel
                    xlsx_bytes = generate_report_excel(data)
                    assert xlsx_bytes.startswith(b"PK")
                    with zipfile.ZipFile(io.BytesIO(xlsx_bytes), "r") as zf:
                        sheet_files = [n for n in zf.namelist() if n.startswith("xl/worksheets/sheet")]
                        assert len(sheet_files) == 4
                        for sf in sheet_files:
                            xml_content = zf.read(sf)
                            ET.fromstring(xml_content)

                    # 3. CSV
                    csv_bytes = generate_report_csv(data)
                    assert csv_bytes.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
                    csv_str = csv_bytes.decode("utf-8-sig")
                    assert "Roll Number,Student Name" in csv_str
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_report_history_persistence_download_and_deletion():
    """Verify synchronous report generation saves to DB, allows secure download, and cleans up on delete."""

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_report_fixtures(session)

                    req = ReportGenerateRequest(
                        report_type=ReportType.COMPANY_WISE,
                        file_format=ReportFormat.PDF,
                        title="Corporate Recruitment Performance 2026",
                    )
                    saved = await generate_and_save_report_endpoint(
                        payload=req,
                        current_user=fx["tpo_a"],
                        session=session,
                    )
                    assert saved.id is not None
                    assert saved.status == ReportStatus.COMPLETED
                    assert saved.file_name.endswith(".pdf")
                    assert saved.file_size_bytes > 0
                    assert saved.download_url == f"/api/v1/reports/{saved.id}/download"

                    # List history
                    hist = await list_reports_history_endpoint(current_user=fx["tpo_a"], session=session)
                    assert len(hist) >= 1
                    assert any(r.id == saved.id for r in hist)

                    # Get single
                    single = await get_report_endpoint(report_id=saved.id, current_user=fx["tpo_a"], session=session)
                    assert single.id == saved.id

                    # Download file
                    dl_resp = await download_report_file_endpoint(report_id=saved.id, current_user=fx["tpo_a"], session=session)
                    assert dl_resp.status_code == 200

                    # Delete
                    del_res = await delete_report_endpoint(report_id=saved.id, current_user=fx["tpo_a"], session=session)
                    assert del_res["id"] == saved.id

                    with pytest.raises(EntityNotFoundException):
                        await get_report_endpoint(report_id=saved.id, current_user=fx["tpo_a"], session=session)
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_role_based_access_and_institution_isolation():
    """Verify students are blocked from reports and TPO from institution B cannot view institution A's reports."""

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_report_fixtures(session)

                    # 1. Create a report for Institution A
                    saved_a = await generate_and_save_report_endpoint(
                        payload=ReportGenerateRequest(report_type=ReportType.OVERALL_INSTITUTIONAL),
                        current_user=fx["tpo_a"],
                        session=session,
                    )

                    # 2. TPO B (Institution B) tries to read Institution A's report -> Forbidden!
                    with pytest.raises(AuthorizationException):
                        await get_report_endpoint(report_id=saved_a.id, current_user=fx["tpo_b"], session=session)

                    with pytest.raises(AuthorizationException):
                        await download_report_file_endpoint(report_id=saved_a.id, current_user=fx["tpo_b"], session=session)

                    with pytest.raises(AuthorizationException):
                        await delete_report_endpoint(report_id=saved_a.id, current_user=fx["tpo_b"], session=session)

                    # 3. Admin can read Institution A's report
                    admin_rep = await get_report_endpoint(report_id=saved_a.id, current_user=fx["admin"], session=session)
                    assert admin_rep.id == saved_a.id
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_report_async_background_generation():
    """Verify asynchronous background report generation."""
    from fastapi import BackgroundTasks

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_report_fixtures(session)

                    bg_tasks = BackgroundTasks()
                    req = ReportGenerateRequest(
                        report_type=ReportType.SALARY_PACKAGE_ANALYSIS,
                        file_format=ReportFormat.XLSX,
                        title="Background Salary Report",
                        async_generate=True,
                    )
                    queued = await generate_report_async_endpoint(
                        payload=req,
                        background_tasks=bg_tasks,
                        current_user=fx["tpo_a"],
                        session=session,
                    )
                    assert queued.status == ReportStatus.PROCESSING
                    assert len(bg_tasks.tasks) == 1

                    # Execute the queued task with test session
                    task = bg_tasks.tasks[0]
                    await task.func(*task.args, **{**task.kwargs, "session_override": session})

                    # Check updated record
                    updated = await session.get(PlacementReport, queued.id)
                    assert updated.status == ReportStatus.COMPLETED
                    assert updated.file_size_bytes > 0
                    assert updated.summary_snapshot["total_eligible_students"] == 5
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())
