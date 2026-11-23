"""
Comprehensive integration, statistical, export, and security tests for TASK 05:
Placement Intelligence, Skill Demand & Statistical Forecasting.
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
from app.core.errors import AuthorizationException
from app.core.security import hash_password
from app.models.company import Company, RecruiterProfile
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
    DriveMode,
    DriveStatus,
    JobApplication,
    PlacementDrive,
    PlacementDriveJob,
    TpoScreeningStatus,
)
from app.models.resume import Resume
from app.models.student import StudentProfile, StudentSkill
from app.models.user import User, UserRole
from app.routes.tpo_intelligence import (
    export_tpo_intelligence_excel,
    export_tpo_intelligence_pdf,
    get_tpo_intelligence_dashboard,
)


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
        chunks.append(chunk if isinstance(chunk, (bytes, bytearray)) else chunk.encode("utf-8"))
    return b"".join(chunks)


async def _seed_intelligence_fixtures(session: AsyncSession):
    tag = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    pw_hash = hash_password("IntelPass123!")

    inst_a = Institution(name=f"Intel Alpha {tag}", code=f"IA{tag}".upper(), city="Jaipur", is_active=True)
    inst_b = Institution(name=f"Intel Beta {tag}", code=f"IB{tag}".upper(), city="Pune", is_active=True)
    session.add_all([inst_a, inst_b])
    await session.flush()

    dept_cs = Department(institution_id=inst_a.id, name="Computer Science", code=f"CS{tag[:4]}".upper(), is_active=True)
    dept_it = Department(institution_id=inst_a.id, name="Information Tech", code=f"IT{tag[:4]}".upper(), is_active=True)
    dept_b = Department(institution_id=inst_b.id, name="Other Dept", code=f"OD{tag[:4]}".upper(), is_active=True)
    session.add_all([dept_cs, dept_it, dept_b])
    await session.flush()

    tpo_a = User(
        email=f"tpoa_{tag}@ia.edu",
        hashed_password=pw_hash,
        full_name="TPO Alpha",
        role=UserRole.TPO,
        institution_id=inst_a.id,
        is_active=True,
        is_verified=True,
    )
    tpo_b = User(
        email=f"tpob_{tag}@ib.edu",
        hashed_password=pw_hash,
        full_name="TPO Beta",
        role=UserRole.TPO,
        institution_id=inst_b.id,
        is_active=True,
        is_verified=True,
    )
    recruiter_user = User(
        email=f"rec_{tag}@corp.com",
        hashed_password=pw_hash,
        full_name="Recruiter One",
        role=UserRole.RECRUITER,
        is_active=True,
        is_verified=True,
    )
    session.add_all([tpo_a, tpo_b, recruiter_user])
    await session.flush()

    comp1 = Company(name=f"Apex Cloud & Data {tag}", industry="Software")
    comp2 = Company(name=f"Vertex Systems {tag}", industry="Platform")
    session.add_all([comp1, comp2])
    await session.flush()

    rec_profile = RecruiterProfile(user_id=recruiter_user.id, company_id=comp1.id, designation="Lead TA")
    session.add(rec_profile)

    # Create 8 active students across 2024, 2025, 2026 in inst_a
    student_specs = [
        ("cs24_1", dept_cs.id, 2024, 8.6, ["Python", "SQL"]),
        ("cs24_2", dept_cs.id, 2024, 8.1, ["Python"]),
        ("cs25_1", dept_cs.id, 2025, 9.1, ["Python", "Kubernetes", "React"]),
        ("cs25_2", dept_cs.id, 2025, 8.4, ["SQL"]),
        ("it25_1", dept_it.id, 2025, 8.2, ["Docker", "SQL"]),
        ("cs26_1", dept_cs.id, 2026, 9.3, ["Python", "Kubernetes", "Docker"]),
        ("cs26_2", dept_cs.id, 2026, 8.0, ["Python"]),
        ("it26_1", dept_it.id, 2026, 8.5, ["React"]),
    ]

    profiles = {}
    resumes = {}
    first_student_user = None
    for key, dept_id, grad_yr, cgpa, sks in student_specs:
        u = User(
            email=f"{key}_{tag}@ia.edu",
            hashed_password=pw_hash,
            full_name=f"Student {key}",
            role=UserRole.STUDENT,
            institution_id=inst_a.id,
            department_id=dept_id,
            is_active=True,
            is_verified=True,
        )
        session.add(u)
        await session.flush()
        if first_student_user is None:
            first_student_user = u
        sp = StudentProfile(
            user_id=u.id,
            roll_number=f"{key}_{tag}".upper(),
            graduation_year=grad_yr,
            cgpa=cgpa,
            active_backlogs=0,
            total_backlogs=0,
            is_placement_ready=True,
        )
        session.add(sp)
        await session.flush()
        for sk in sks:
            session.add(StudentSkill(student_id=sp.id, skill_name=sk, category="technical", is_verified=True))
        res = Resume(
            student_id=sp.id,
            file_name=f"{key}.pdf",
            file_path=f"/tmp/{key}_{tag}.pdf",
            file_type="pdf",
            file_size_bytes=1024,
            file_hash=uuid.uuid4().hex * 2,
            parsing_status="approved",
            is_active=True,
        )
        session.add(res)
        await session.flush()
        profiles[key] = sp
        resumes[key] = res

    # Drives across 3 historical academic years
    drive_2024 = PlacementDrive(
        institution_id=inst_a.id,
        created_by_user_id=tpo_a.id,
        name=f"Campus Drive 2024 {tag}",
        academic_year="2023-2024",
        target_graduation_year=2024,
        registration_start_date=now - timedelta(days=760),
        registration_end_date=now - timedelta(days=730),
        drive_mode=DriveMode.ON_CAMPUS,
        status=DriveStatus.COMPLETED,
        is_active=True,
    )
    drive_2025 = PlacementDrive(
        institution_id=inst_a.id,
        created_by_user_id=tpo_a.id,
        name=f"Campus Drive 2025 {tag}",
        academic_year="2024-2025",
        target_graduation_year=2025,
        registration_start_date=now - timedelta(days=400),
        registration_end_date=now - timedelta(days=370),
        drive_mode=DriveMode.ON_CAMPUS,
        status=DriveStatus.COMPLETED,
        is_active=True,
    )
    drive_2026 = PlacementDrive(
        institution_id=inst_a.id,
        created_by_user_id=tpo_a.id,
        name=f"Campus Drive 2026 {tag}",
        academic_year="2025-2026",
        target_graduation_year=2026,
        registration_start_date=now - timedelta(days=20),
        registration_end_date=now + timedelta(days=20),
        drive_mode=DriveMode.ON_CAMPUS,
        status=DriveStatus.ONGOING,
        is_active=True,
    )
    session.add_all([drive_2024, drive_2025, drive_2026])
    await session.flush()

    # Jobs across years, companies, employment types & categories
    job_2024 = Job(
        company_id=comp1.id,
        institution_id=inst_a.id,
        created_by_user_id=recruiter_user.id,
        title="Backend Software Engineer",
        description="Distributed services.",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.HYBRID,
        location="Bengaluru",
        ctc_lpa=10.0,
        min_cgpa=6.5,
        target_graduation_year=2024,
        max_active_backlogs=0,
        max_total_backlogs=0,
        application_deadline=now - timedelta(days=730),
        status=JobStatus.CLOSED,
        created_at=now - timedelta(days=750),
    )
    job_2025_a = Job(
        company_id=comp1.id,
        institution_id=inst_a.id,
        created_by_user_id=recruiter_user.id,
        title="Data & ML Engineer",
        description="ML pipelines and data warehouses.",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.HYBRID,
        location="Hyderabad",
        ctc_lpa=12.0,
        min_cgpa=7.0,
        target_graduation_year=2025,
        max_active_backlogs=0,
        max_total_backlogs=0,
        application_deadline=now - timedelta(days=370),
        status=JobStatus.CLOSED,
        created_at=now - timedelta(days=390),
    )
    job_2025_b = Job(
        company_id=comp2.id,
        institution_id=inst_a.id,
        created_by_user_id=recruiter_user.id,
        title="Cloud Platform Intern",
        description="Kubernetes platform engineering.",
        employment_type=EmploymentType.INTERNSHIP,
        work_mode=WorkMode.REMOTE,
        location="Remote",
        ctc_lpa=None,  # Intentionally missing CTC to verify data completeness transparency
        min_cgpa=6.5,
        target_graduation_year=2025,
        max_active_backlogs=0,
        max_total_backlogs=0,
        application_deadline=now - timedelta(days=370),
        status=JobStatus.CLOSED,
        created_at=now - timedelta(days=380),
    )
    job_2026 = Job(
        company_id=comp2.id,
        institution_id=inst_a.id,
        created_by_user_id=recruiter_user.id,
        title="Full Stack SDE",
        description="Modern React and FastAPI systems.",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.ON_SITE,
        location="Pune",
        ctc_lpa=22.0,
        min_cgpa=7.0,
        target_graduation_year=2026,
        max_active_backlogs=0,
        max_total_backlogs=0,
        application_deadline=now + timedelta(days=15),
        status=JobStatus.PUBLISHED,
        created_at=now - timedelta(days=15),
    )
    session.add_all([job_2024, job_2025_a, job_2025_b, job_2026])
    await session.flush()

    session.add_all([
        PlacementDriveJob(drive_id=drive_2024.id, job_id=job_2024.id, is_active=True),
        PlacementDriveJob(drive_id=drive_2025.id, job_id=job_2025_a.id, is_active=True),
        PlacementDriveJob(drive_id=drive_2025.id, job_id=job_2025_b.id, is_active=True),
        PlacementDriveJob(drive_id=drive_2026.id, job_id=job_2026.id, is_active=True),
        JobEligibleDepartment(job_id=job_2024.id, department_id=dept_cs.id),
        JobEligibleDepartment(job_id=job_2025_a.id, department_id=dept_cs.id),
        JobEligibleDepartment(job_id=job_2025_b.id, department_id=dept_it.id),
        JobEligibleDepartment(job_id=job_2026.id, department_id=dept_cs.id),
        JobEligibleDepartment(job_id=job_2026.id, department_id=dept_it.id),
        JobSkill(job_id=job_2024.id, skill_name="Python", is_mandatory=True, weight_factor=1.5),
        JobSkill(job_id=job_2024.id, skill_name="SQL", is_mandatory=True, weight_factor=1.2),
        JobSkill(job_id=job_2025_a.id, skill_name="Python", is_mandatory=True, weight_factor=1.5),
        JobSkill(job_id=job_2025_a.id, skill_name="Kubernetes", is_mandatory=False, weight_factor=1.0),
        JobSkill(job_id=job_2025_b.id, skill_name="Docker", is_mandatory=True, weight_factor=1.4),
        JobSkill(job_id=job_2025_b.id, skill_name="Terraform", is_mandatory=True, weight_factor=1.2),
        JobSkill(job_id=job_2026.id, skill_name="Python", is_mandatory=True, weight_factor=1.5),
        JobSkill(job_id=job_2026.id, skill_name="Kubernetes", is_mandatory=True, weight_factor=1.3),
        JobSkill(job_id=job_2026.id, skill_name="Rust", is_mandatory=False, weight_factor=1.0),
    ])
    await session.flush()

    def _app(job_obj, key, drive_obj, status_val, pkg=None):
        is_withdrawn = status_val == ApplicationStatus.WITHDRAWN
        return JobApplication(
            job_id=job_obj.id,
            student_id=profiles[key].id,
            resume_id=resumes[key].id,
            drive_id=drive_obj.id,
            tpo_screening_status=TpoScreeningStatus.SHORTLISTED,
            tpo_screened_by_user_id=tpo_a.id,
            tpo_screened_at=now - timedelta(days=5),
            current_status=status_val,
            compatibility_score_at_application=85.0,
            offer_package_lpa=pkg,
            withdrawn_at=(now - timedelta(days=2)) if is_withdrawn else None,
            withdrawal_reason="Accepted alternative focus" if is_withdrawn else None,
            created_at=now - timedelta(days=10),
        )

    apps = [
        # 2024: cs24_1 accepted (10 LPA); cs24_2 declined (14 LPA -> MUST NOT count as placed)
        _app(job_2024, "cs24_1", drive_2024, ApplicationStatus.OFFER_ACCEPTED, 10.0),
        _app(job_2024, "cs24_2", drive_2024, ApplicationStatus.OFFER_DECLINED, 14.0),
        # 2025: cs25_1 has TWO accepted offers (12 LPA & 18 LPA -> deduplicate to 1 placed student @ 18 LPA!)
        _app(job_2025_a, "cs25_1", drive_2025, ApplicationStatus.OFFER_ACCEPTED, 12.0),
        _app(job_2025_b, "cs25_1", drive_2025, ApplicationStatus.OFFER_ACCEPTED, 18.0),
        # 2025: cs25_2 rejected (unplaced); it25_1 accepted with NO package -> increments missing package warning
        _app(job_2025_a, "cs25_2", drive_2025, ApplicationStatus.REJECTED, None),
        _app(job_2025_b, "it25_1", drive_2025, ApplicationStatus.OFFER_ACCEPTED, None),
        # 2026: cs26_1 accepted (22 LPA); cs26_2 interview_scheduled (in pipeline); it26_1 offered (pending, in pipeline) & withdrawn
        _app(job_2026, "cs26_1", drive_2026, ApplicationStatus.OFFER_ACCEPTED, 22.0),
        _app(job_2026, "cs26_2", drive_2026, ApplicationStatus.INTERVIEW_SCHEDULED, None),
        _app(job_2026, "it26_1", drive_2026, ApplicationStatus.OFFERED, 16.0),
        _app(job_2025_b, "it26_1", drive_2025, ApplicationStatus.WITHDRAWN, None),
    ]
    session.add_all(apps)
    await session.flush()

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "dept_cs": dept_cs,
        "dept_it": dept_it,
        "tpo_a": tpo_a,
        "tpo_b": tpo_b,
        "student_user": first_student_user,
        "recruiter_user": recruiter_user,
        "comp1": comp1,
        "comp2": comp2,
    }


def test_overview_dedup_declined_exclusion_and_packages():
    """Verify placed-student deduplication, strict exclusion of declined/withdrawn offers, and package math."""

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_intelligence_fixtures(session)
                    resp = await get_tpo_intelligence_dashboard(
                        refresh=True,
                        current_user=fx["tpo_a"],
                        db=session,
                    )

                    ov = resp.overview
                    assert ov.total_registered_students == 8
                    assert ov.total_eligible_students == 8
                    # cs24_1, cs25_1 (2 offers -> 1 student), it25_1, cs26_1 => 4 placed students
                    assert ov.total_placed_students == 4
                    assert ov.total_accepted_offers == 5
                    assert ov.total_declined_offers == 1
                    assert ov.pending_offers == 1
                    assert ov.total_offers_released == 7
                    # cs26_2 (interview_scheduled) + it26_1 (offered, not placed) => 2 in pipeline
                    assert ov.students_in_pipeline == 2
                    assert ov.students_not_yet_placed == 4
                    assert ov.placement_rate_pct == 50.0
                    # Placed packages: [10.0 (cs24_1), 18.0 (cs25_1 max), 22.0 (cs26_1)] => mean=16.67, median=18.0, max=22.0
                    assert ov.average_package_lpa == 16.67
                    assert ov.median_package_lpa == 18.0
                    assert ov.highest_package_lpa == 22.0
                    assert ov.offers_missing_package_count == 1
                    assert resp.data_completeness.offers_missing_package == 1
                    assert len(resp.data_completeness.warnings) >= 1
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_department_analytics_historical_trends_funnel_and_skills():
    """Verify department metrics, YoY historical trends, salary buckets, funnel, and skill intelligence."""

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_intelligence_fixtures(session)
                    resp = await get_tpo_intelligence_dashboard(
                        refresh=True,
                        current_user=fx["tpo_a"],
                        db=session,
                    )

                    dept_by_id = {d.department_id: d for d in resp.department_analytics}
                    cs = dept_by_id[fx["dept_cs"].id]
                    it = dept_by_id[fx["dept_it"].id]

                    assert cs.eligible_students == 6
                    assert cs.placed_students == 3  # cs24_1, cs25_1, cs26_1
                    assert cs.offers_accepted == 4
                    assert cs.placement_rate_pct == 50.0
                    assert it.eligible_students == 2
                    assert it.placed_students == 1  # it25_1
                    assert it.in_pipeline_students == 1  # it26_1

                    # Historical years 2024, 2025, 2026 sorted chronologically
                    years = [h.graduation_year for h in resp.historical_trends]
                    assert years == [2024, 2025, 2026]
                    assert resp.historical_trends[0].placement_rate_pct == 50.0  # 1/2
                    assert round(resp.historical_trends[1].placement_rate_pct, 1) == 66.7  # 2/3
                    assert round(resp.historical_trends[2].placement_rate_pct, 1) == 33.3  # 1/3
                    assert resp.historical_trends[1].yoy_placement_growth_pct_pts == 16.7

                    # Salary distribution covers all 3 deduplicated placed students with priced offers (10, 18, 22)
                    total_bucket_offers = sum(b.accepted_offer_count for b in resp.salary_distribution)
                    assert total_bucket_offers == 3

                    # Funnel stages monotonic non-increasing from Total Applications (10) -> Offer Accepted (5)
                    funnel_counts = [f.application_count for f in resp.recruitment_funnel]
                    assert funnel_counts[0] == 10
                    assert funnel_counts[-1] == 5  # 5 accepted offers

                    # Skill demand intelligence includes Python & Terraform gap
                    skill_names = [s.skill_name for s in resp.skill_intelligence.most_requested_skills]
                    assert "Python" in skill_names
                    gap_by_code = {g.department_code: g for g in resp.skill_intelligence.department_skill_gaps}
                    assert "Terraform" in gap_by_code[fx["dept_it"].code].missing_or_low_supply_skills
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_all_six_filters_and_statistical_forecasting():
    """Verify all 6 filters and statistical regression forecasts with CIs, R^2, sample size, and limitations."""

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_intelligence_fixtures(session)

                    full = await get_tpo_intelligence_dashboard(
                        refresh=True,
                        current_user=fx["tpo_a"],
                        db=session,
                    )
                    fc = full.forecasting
                    assert fc.overall_sample_years == 3
                    assert fc.target_graduation_year == 2027
                    assert "not guaranteed outcomes" in fc.disclaimer.lower() or "guarantee" in fc.disclaimer.lower()
                    for est in (
                        fc.placement_forecast,
                        fc.company_participation_forecast,
                        fc.offer_volume_forecast,
                    ):
                        assert est.sample_size == 3
                        assert est.ci_lower_95 <= est.projected_value <= est.ci_upper_95
                        assert len(est.limitations) >= 1
                        assert est.r_squared is not None

                    # Filter 1 & 2: academic_year & graduation_year
                    y25 = await get_tpo_intelligence_dashboard(
                        academic_year="2024-2025",
                        graduation_year=2025,
                        refresh=True,
                        current_user=fx["tpo_a"],
                        db=session,
                    )
                    assert y25.overview.total_eligible_students == 3
                    assert y25.overview.total_placed_students == 2
                    # Historical trends & forecasting intentionally preserve cross-year horizon when slicing batch overview
                    assert y25.forecasting.overall_sample_years == 3

                    # Filter 3: department_id
                    cs_only = await get_tpo_intelligence_dashboard(
                        department_id=fx["dept_cs"].id,
                        refresh=True,
                        current_user=fx["tpo_a"],
                        db=session,
                    )
                    assert cs_only.overview.total_eligible_students == 6
                    assert cs_only.overview.total_placed_students == 3

                    # Filter 4: company_id
                    comp2_only = await get_tpo_intelligence_dashboard(
                        company_id=fx["comp2"].id,
                        refresh=True,
                        current_user=fx["tpo_a"],
                        db=session,
                    )
                    assert comp2_only.overview.total_participating_companies == 1
                    assert comp2_only.overview.total_accepted_offers == 3  # cs25_1 on job_2025_b, it25_1, cs26_1

                    # Filter 5: job_category ("Data & AI" matches job_2025_a "Data & ML Engineer")
                    cat_res = await get_tpo_intelligence_dashboard(
                        job_category="Data & AI",
                        refresh=True,
                        current_user=fx["tpo_a"],
                        db=session,
                    )
                    assert cat_res.overview.total_published_jobs == 1
                    assert cat_res.overview.total_accepted_offers == 1
                    # Filter 6: employment_type ("internship" matches job_2025_b -> single year -> exploratory company/offer forecast)
                    intern_res = await get_tpo_intelligence_dashboard(
                        employment_type="internship",
                        refresh=True,
                        current_user=fx["tpo_a"],
                        db=session,
                    )
                    assert intern_res.overview.total_published_jobs == 1
                    assert intern_res.overview.total_accepted_offers == 2  # cs25_1 + it25_1 on job_2025_b
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_pdf_and_excel_report_exports():
    """Verify PDF binary structure via PyMuPDF and multi-sheet .xlsx XML workbook via zipfile."""

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_intelligence_fixtures(session)

                    pdf_resp = await export_tpo_intelligence_pdf(
                        refresh=True,
                        current_user=fx["tpo_a"],
                        db=session,
                    )
                    assert pdf_resp.media_type == "application/pdf"
                    pdf_bytes = await _consume_streaming_body(pdf_resp)
                    assert pdf_bytes.startswith(b"%PDF-")
                    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
                    assert doc.page_count >= 1
                    full_text = "\n".join(page.get_text() for page in doc)
                    doc.close()
                    assert "INSTITUTIONAL PLACEMENT INTELLIGENCE" in full_text
                    assert "4. STATISTICAL FORECASTS" in full_text

                    xlsx_resp = await export_tpo_intelligence_excel(
                        refresh=True,
                        current_user=fx["tpo_a"],
                        db=session,
                    )
                    assert "spreadsheetml" in xlsx_resp.media_type
                    xlsx_bytes = await _consume_streaming_body(xlsx_resp)
                    assert xlsx_bytes.startswith(b"PK")

                    with zipfile.ZipFile(io.BytesIO(xlsx_bytes), "r") as zf:
                        names = set(zf.namelist())
                        for sheet_idx in range(1, 6):
                            sheet_path = f"xl/worksheets/sheet{sheet_idx}.xml"
                            assert sheet_path in names
                            # Validate XML well-formedness (escapes '&' from 'Apex Cloud & Data')
                            ET.fromstring(zf.read(sheet_path))
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_tpo_rbac_and_cross_institution_isolation():
    """Verify student/recruiter roles are blocked and TPO staff cannot inspect another institution."""

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_intelligence_fixtures(session)

                    # Cross-institution TPO attempt must raise AuthorizationException
                    with pytest.raises(AuthorizationException):
                        await get_tpo_intelligence_dashboard(
                            institution_id=fx["inst_a"].id,
                            refresh=True,
                            current_user=fx["tpo_b"],
                            db=session,
                        )

                    # TPO Beta querying own empty institution sees 0 placed/eligible (no leakage from Alpha)
                    beta_own = await get_tpo_intelligence_dashboard(
                        refresh=True,
                        current_user=fx["tpo_b"],
                        db=session,
                    )
                    assert beta_own.overview.total_eligible_students == 0
                    assert beta_own.overview.total_placed_students == 0

                    # Non-TPO student & recruiter calls to resolve_tpo_institution_id / service blocked
                    from app.services.placement_analytics_service import resolve_tpo_institution_id

                    with pytest.raises(AuthorizationException):
                        resolve_tpo_institution_id(fx["student_user"], None)

                    with pytest.raises(AuthorizationException):
                        resolve_tpo_institution_id(fx["recruiter_user"], None)
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())
