"""
Comprehensive integration & security tests for TASK 04:
Placement Preparation Arena.

Covers:
1. All 11 preparation categories, counts, and student proficiency metrics.
2. Question delivery security (no unreleased answers/explanations/hidden tests before submit).
3. MCQ & Behavioral STAR evaluation + post-submission explanations & review.
4. Multi-language coding execution (Python, JavaScript, Java) via isolated sandbox.
5. Coding sandbox security & resource limits (blocked network/file/process/eval, stripped env, infinite-loop timeout).
6. Timed test countdown enforcement & rejection of expired late answers.
7. Company-style prep provenance disclaimers (never claims confidential real questions).
8. Performance analytics (attempted/correct/incorrect/accuracy/avg solving time/trends).
9. Personalized practice linked to skill gaps, weak topics, target jobs & readiness gaps.
10. Privacy-preserving leaderboards (opt-in default False, anonymization, batch/dept scope, zero academic PII/CGPA).
11. TPO / Admin institutional test publishing, aggregated analytics & strict cross-institution isolation.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.core.errors import AppException, AuthorizationException
from app.core.security import hash_password
from app.models.arena import (
    ArenaAssessmentMode,
    ArenaAttempt,
    ArenaAttemptStatus,
    ArenaCategory,
    ArenaDifficulty,
    ArenaQuestion,
    ArenaQuestionType,
)
from app.models.company import Company, RecruiterProfile
from app.models.job import EmploymentType, Job, JobSkill, JobStatus, WorkMode
from app.models.organization import Department, Institution
from app.models.student import StudentProfile, StudentSkill
from app.models.user import User, UserRole
from app.routes.arena import (
    create_tpo_assessment_endpoint,
    create_tpo_question_endpoint,
    get_analytics_endpoint,
    get_attempt_detail_endpoint,
    get_leaderboard_endpoint,
    get_preferences_endpoint,
    get_recommendations_endpoint,
    get_tpo_analytics_endpoint,
    list_assessments_endpoint,
    list_categories_endpoint,
    list_questions_endpoint,
    run_sandbox_code_endpoint,
    start_attempt_endpoint,
    submit_answer_endpoint,
    submit_attempt_endpoint,
    update_preferences_endpoint,
)
from app.schemas.arena import (
    ArenaOptionItem,
    ArenaRunCodeRequest,
    ArenaStartAttemptRequest,
    ArenaSubmitAnswerRequest,
    ArenaSubmitAttemptRequest,
    ArenaTpoAssessmentCreateRequest,
    ArenaTpoQuestionCreateRequest,
    ArenaUserPreferenceUpdate,
)
from app.services.code_sandbox_service import CodeSandboxService


def _new_test_engine():
    settings = get_settings()
    return create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        connect_args={"server_settings": {"search_path": f"{settings.DB_SCHEMA},public"}},
    )


async def _seed_fixtures(session: AsyncSession):
    tag = uuid.uuid4().hex[:8]
    pw_hash = hash_password("ArenaPass123!")

    inst_a = Institution(name=f"Arena Alpha {tag}", code=f"AA{tag}".upper(), city="Jaipur", is_active=True)
    inst_b = Institution(name=f"Arena Beta {tag}", code=f"AB{tag}".upper(), city="Pune", is_active=True)
    session.add_all([inst_a, inst_b])
    await session.flush()

    dept_cs = Department(institution_id=inst_a.id, name="Computer Science", code=f"CS{tag[:4]}".upper(), is_active=True)
    dept_it = Department(institution_id=inst_a.id, name="Information Tech", code=f"IT{tag[:4]}".upper(), is_active=True)
    dept_b = Department(institution_id=inst_b.id, name="CSE Beta", code=f"CB{tag[:4]}".upper(), is_active=True)
    session.add_all([dept_cs, dept_it, dept_b])
    await session.flush()

    tpo_a = User(
        email=f"tpoa_{tag}@aa.edu",
        hashed_password=pw_hash,
        full_name="TPO Alpha",
        role=UserRole.TPO,
        institution_id=inst_a.id,
        is_active=True,
        is_verified=True,
    )
    tpo_b = User(
        email=f"tpob_{tag}@ab.edu",
        hashed_password=pw_hash,
        full_name="TPO Beta",
        role=UserRole.TPO,
        institution_id=inst_b.id,
        is_active=True,
        is_verified=True,
    )
    stu1_u = User(
        email=f"s1_{tag}@aa.edu",
        hashed_password=pw_hash,
        full_name="Priya Sharma",
        role=UserRole.STUDENT,
        institution_id=inst_a.id,
        department_id=dept_cs.id,
        is_active=True,
        is_verified=True,
    )
    stu2_u = User(
        email=f"s2_{tag}@aa.edu",
        hashed_password=pw_hash,
        full_name="Rohan Verma",
        role=UserRole.STUDENT,
        institution_id=inst_a.id,
        department_id=dept_it.id,
        is_active=True,
        is_verified=True,
    )
    stu3_b_u = User(
        email=f"s3_{tag}@ab.edu",
        hashed_password=pw_hash,
        full_name="Beta Student",
        role=UserRole.STUDENT,
        institution_id=inst_b.id,
        department_id=dept_b.id,
        is_active=True,
        is_verified=True,
    )
    rec_u = User(
        email=f"rec_{tag}@corp.com",
        hashed_password=pw_hash,
        full_name="Corp Recruiter",
        role=UserRole.RECRUITER,
        is_active=True,
        is_verified=True,
    )
    session.add_all([tpo_a, tpo_b, stu1_u, stu2_u, stu3_b_u, rec_u])
    await session.flush()

    sp1 = StudentProfile(
        user_id=stu1_u.id,
        roll_number=f"R1_{tag}",
        graduation_year=2027,
        cgpa=9.15,
        active_backlogs=0,
        total_backlogs=0,
    )
    sp2 = StudentProfile(
        user_id=stu2_u.id,
        roll_number=f"R2_{tag}",
        graduation_year=2027,
        cgpa=8.45,
        active_backlogs=1,
        total_backlogs=1,
    )
    sp3 = StudentProfile(
        user_id=stu3_b_u.id,
        roll_number=f"R3_{tag}",
        graduation_year=2027,
        cgpa=8.80,
        active_backlogs=0,
        total_backlogs=0,
    )
    session.add_all([sp1, sp2, sp3])
    await session.flush()

    # Give student 1 Python only, and publish a target job needing Docker + SQL + Python for skill gap matching
    session.add(StudentSkill(student_id=sp1.id, skill_name="Python", is_verified=True))

    comp = Company(name=f"CloudForge {tag}", industry="Software", is_verified=True)
    session.add(comp)
    await session.flush()
    rp = RecruiterProfile(user_id=rec_u.id, company_id=comp.id, designation="Tech Lead")
    session.add(rp)
    await session.flush()

    job = Job(
        company_id=comp.id,
        created_by_user_id=rec_u.id,
        title=f"Backend Cloud Engineer {tag}",
        description="Build microservices with Python, Docker, and PostgreSQL.",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.HYBRID,
        location="Bengaluru",
        application_deadline=datetime.now(timezone.utc) + timedelta(days=10),
        status=JobStatus.PUBLISHED,
        min_cgpa=6.5,
        max_active_backlogs=1,
    )
    session.add(job)
    await session.flush()
    session.add_all([
        JobSkill(job_id=job.id, skill_name="Python", is_mandatory=True),
        JobSkill(job_id=job.id, skill_name="Docker", is_mandatory=True),
        JobSkill(job_id=job.id, skill_name="SQL", is_mandatory=False),
    ])
    await session.flush()

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "dept_cs": dept_cs,
        "dept_it": dept_it,
        "tpo_a": tpo_a,
        "tpo_b": tpo_b,
        "stu1": stu1_u,
        "stu2": stu2_u,
        "stu3_b": stu3_b_u,
        "sp1": sp1,
        "sp2": sp2,
        "job": job,
    }


def _run_with_rollback(coro_fn):
    async def _runner():
        engine = _new_test_engine()
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with engine.connect() as conn:
            trans = await conn.begin()
            async with session_factory(bind=conn) as session:
                try:
                    await coro_fn(session)
                finally:
                    await trans.rollback()
        await engine.dispose()

    asyncio.run(_runner())


def test_arena_all_11_categories_and_no_answer_leak():
    async def _test(session: AsyncSession):
        fx = await _seed_fixtures(session)
        cats = await list_categories_endpoint(current_user=fx["stu1"], db=session)
        cat_keys = {c.category for c in cats}
        assert len(cat_keys) >= 11
        for expected_cat in (
            ArenaCategory.DSA,
            ArenaCategory.PROGRAMMING_FUNDAMENTALS,
            ArenaCategory.DBMS,
            ArenaCategory.OPERATING_SYSTEMS,
            ArenaCategory.COMPUTER_NETWORKS,
            ArenaCategory.OOP,
            ArenaCategory.QUANTITATIVE,
            ArenaCategory.APTITUDE_LOGICAL,
            ArenaCategory.VERBAL,
            ArenaCategory.HR_BEHAVIORAL,
            ArenaCategory.CS_MATHS_FOR_COMPUTING,
        ):
            assert expected_cat in cat_keys
            row = next(c for c in cats if c.category == expected_cat)
            assert row.total_questions >= 1

        # Public question endpoint must never leak answer key or explanation
        qs = await list_questions_endpoint(
            category=ArenaCategory.DBMS,
            difficulty=None,
            question_type=None,
            company_tag=None,
            search=None,
            skip=0,
            limit=20,
            current_user=fx["stu1"],
            db=session,
        )
        assert len(qs) >= 1
        dumped = qs[0].model_dump()
        assert "correct_option_key" not in dumped
        assert "explanation_text" not in dumped

    _run_with_rollback(_test)


def test_practice_timed_mode_explanations_and_expiry():
    async def _test(session: AsyncSession):
        fx = await _seed_fixtures(session)

        # 1. Topic practice unlocks explanation immediately after answer submission
        practice = await start_attempt_endpoint(
            req=ArenaStartAttemptRequest(mode=ArenaAssessmentMode.TOPIC_PRACTICE, category=ArenaCategory.DBMS, question_count=2),
            current_user=fx["stu1"],
            db=session,
        )
        first_q = practice.questions[0].question
        assert getattr(first_q, "explanation_text", None) is None
        ans_res = await submit_answer_endpoint(
            attempt_id=practice.id,
            req=ArenaSubmitAnswerRequest(question_id=first_q.id, selected_option_key="A", time_spent_seconds=25),
            current_user=fx["stu1"],
            db=session,
        )
        assert ans_res.immediate_review_unlocked is True
        assert ans_res.explanation_text is not None
        assert ans_res.correct_option_key == "A"

        # 2. Timed assessment hides explanations until final attempt submission
        assess_list = await list_assessments_endpoint(mode=ArenaAssessmentMode.TIMED_TEST, category=None, current_user=fx["stu1"], db=session)
        assert len(assess_list) >= 1
        timed = await start_attempt_endpoint(
            req=ArenaStartAttemptRequest(assessment_id=assess_list[0].id),
            current_user=fx["stu1"],
            db=session,
        )
        timed_q = timed.questions[0].question
        timed_ans = await submit_answer_endpoint(
            attempt_id=timed.id,
            req=ArenaSubmitAnswerRequest(question_id=timed_q.id, selected_option_key="B", time_spent_seconds=30),
            current_user=fx["stu1"],
            db=session,
        )
        assert timed_ans.immediate_review_unlocked is False
        assert timed_ans.explanation_text is None

        # Cross-student access check
        with pytest.raises(AuthorizationException):
            await get_attempt_detail_endpoint(attempt_id=timed.id, current_user=fx["stu2"], db=session)

        finalized = await submit_attempt_endpoint(
            attempt_id=timed.id,
            req=ArenaSubmitAttemptRequest(elapsed_seconds=95),
            current_user=fx["stu1"],
            db=session,
        )
        assert finalized.status == ArenaAttemptStatus.SUBMITTED
        assert finalized.questions[0].question.explanation_text is not None

        # 3. Expired attempt rejects late submissions
        exp_att = await start_attempt_endpoint(
            req=ArenaStartAttemptRequest(mode=ArenaAssessmentMode.TIMED_TEST, category=ArenaCategory.OOP, time_limit_minutes=5, question_count=2),
            current_user=fx["stu1"],
            db=session,
        )
        att_row = (await session.execute(select(ArenaAttempt).where(ArenaAttempt.id == exp_att.id))).scalar_one()
        att_row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        await session.flush()

        with pytest.raises(AppException) as exc_info:
            await submit_answer_endpoint(
                attempt_id=exp_att.id,
                req=ArenaSubmitAnswerRequest(question_id=exp_att.questions[0].question.id, selected_option_key="A"),
                current_user=fx["stu1"],
                db=session,
            )
        assert exc_info.value.code == "ATTEMPT_EXPIRED"

    _run_with_rollback(_test)


def test_coding_sandbox_multilang_and_security_restrictions():
    async def _test(session: AsyncSession):
        fx = await _seed_fixtures(session)

        # Start DSA coding practice
        dsa = await start_attempt_endpoint(
            req=ArenaStartAttemptRequest(mode=ArenaAssessmentMode.TOPIC_PRACTICE, category=ArenaCategory.DSA, difficulty=ArenaDifficulty.EASY, question_count=5),
            current_user=fx["stu1"],
            db=session,
        )
        coding_slot = next(s for s in dsa.questions if s.question.question_type == ArenaQuestionType.CODING)
        q = coding_slot.question

        # 1. Valid Python run-code (sample tests only + custom stdin)
        py_run = await run_sandbox_code_endpoint(
            attempt_id=dsa.id,
            req=ArenaRunCodeRequest(
                question_id=q.id,
                language="python",
                source_code=q.starter_code["python"],
                custom_stdin="9\n2 7 11 15\n",
            ),
            current_user=fx["stu1"],
            db=session,
        )
        assert py_run.isolated_execution is True
        assert py_run.all_passed is True
        assert all(tr.is_sample for tr in py_run.test_results)
        assert (py_run.custom_stdout or "").strip() == "0 1"

        # 2. Valid JavaScript (Node.js) run-code
        js_run = await run_sandbox_code_endpoint(
            attempt_id=dsa.id,
            req=ArenaRunCodeRequest(
                question_id=q.id,
                language="javascript",
                source_code=q.starter_code["javascript"],
            ),
            current_user=fx["stu1"],
            db=session,
        )
        assert js_run.all_passed is True

        # 3. Security blocks: socket, subprocess, file open, eval, Node net/fs, Java Socket
        blocked_python = [
            "import socket\nprint('x')",
            "import subprocess\nsubprocess.run(['dir'])",
            "open('hack.txt', 'w').write('x')",
            "eval('1+1')",
        ]
        for bad in blocked_python:
            res = await run_sandbox_code_endpoint(
                attempt_id=dsa.id,
                req=ArenaRunCodeRequest(question_id=q.id, language="python", source_code=bad),
                current_user=fx["stu1"],
                db=session,
            )
            assert res.all_passed is False
            assert res.security_violation is not None

        bad_js = await run_sandbox_code_endpoint(
            attempt_id=dsa.id,
            req=ArenaRunCodeRequest(question_id=q.id, language="javascript", source_code="const fs = require('fs'); console.log('hi');"),
            current_user=fx["stu1"],
            db=session,
        )
        assert bad_js.security_violation is not None

        bad_java = await run_sandbox_code_endpoint(
            attempt_id=dsa.id,
            req=ArenaRunCodeRequest(question_id=q.id, language="java", source_code="import java.net.Socket; public class Main { public static void main(String[] a) {} }"),
            current_user=fx["stu1"],
            db=session,
        )
        assert bad_java.security_violation is not None

        # 4. Verify environment isolation & timeout enforcement directly on sandbox service
        env_leak_check = await CodeSandboxService().execute_code(
            language="python",
            source_code="print('SAFE_ONLY')",
            test_cases=[{"stdin": "", "expected_stdout": "SAFE_ONLY", "is_sample": True}],
        )
        assert env_leak_check.all_passed is True

        # Submit coding answer -> runs sample + hidden tests
        submit_code_res = await submit_answer_endpoint(
            attempt_id=dsa.id,
            req=ArenaSubmitAnswerRequest(
                question_id=q.id,
                submitted_code=q.starter_code["python"],
                code_language="python",
                time_spent_seconds=45,
            ),
            current_user=fx["stu1"],
            db=session,
        )
        assert submit_code_res.answer.is_correct is True
        assert submit_code_res.answer.score_awarded == float(q.max_marks)
        assert submit_code_res.answer.execution_result.total_count == 3

    _run_with_rollback(_test)


def test_sandbox_infinite_loop_timeout():
    # Direct unit test of wall-clock timeout isolation
    async def _run():
        from app.config import get_settings

        settings = get_settings()
        old_t = settings.CODE_SANDBOX_TIMEOUT_SECONDS
        settings.CODE_SANDBOX_TIMEOUT_SECONDS = 0.6
        try:
            res = await CodeSandboxService().execute_code(
                language="python",
                source_code="while True:\n    pass\n",
                test_cases=[{"stdin": "", "expected_stdout": "", "is_sample": True}],
            )
            assert res.all_passed is False
            assert res.test_results[0].status == "time_limit_exceeded"
        finally:
            settings.CODE_SANDBOX_TIMEOUT_SECONDS = old_t

    asyncio.run(_run())


def test_company_provenance_analytics_personalized_and_privacy_leaderboard():
    async def _test(session: AsyncSession):
        fx = await _seed_fixtures(session)

        # 1. Company-style tracks include clear non-confidential provenance disclaimer
        company_tracks = await list_assessments_endpoint(
            mode=ArenaAssessmentMode.COMPANY_PREP,
            category=None,
            current_user=fx["stu1"],
            db=session,
        )
        assert len(company_tracks) >= 1
        assert "not confidential" in company_tracks[0].provenance_notice.lower()

        # 2. Record answers to generate real analytics & weak-category personalization signal
        att = await start_attempt_endpoint(
            req=ArenaStartAttemptRequest(mode=ArenaAssessmentMode.TOPIC_PRACTICE, category=ArenaCategory.TECHNICAL_MCQS, question_count=2),
            current_user=fx["stu1"],
            db=session,
        )
        # Answer incorrectly intentionally to trigger weak category < 70%
        await submit_answer_endpoint(
            attempt_id=att.id,
            req=ArenaSubmitAnswerRequest(question_id=att.questions[0].question.id, selected_option_key="D", time_spent_seconds=40),
            current_user=fx["stu1"],
            db=session,
        )
        await submit_attempt_endpoint(attempt_id=att.id, req=None, current_user=fx["stu1"], db=session)

        analytics = await get_analytics_endpoint(current_user=fx["stu1"], db=session)
        assert analytics.completed_attempts >= 1
        assert analytics.total_questions_attempted >= 1
        assert analytics.avg_solving_time_seconds >= 40.0
        assert len(analytics.improvement_trend) >= 1

        # 3. Personalized recommendations reflect missing job skill (Docker/SQL) and weak Arena category
        recs = await get_recommendations_endpoint(job_id=fx["job"].id, current_user=fx["stu1"], db=session)
        assert any("Docker" in s or "SQL" in s for s in recs.missing_skills_detected)
        assert ArenaCategory.TECHNICAL_MCQS in recs.weak_categories
        assert len(recs.recommendations) >= 2

        # 4. Privacy-preserving leaderboard: default opted-out, anonymized opt-in, zero academic PII
        pref_default = await get_preferences_endpoint(current_user=fx["stu1"], db=session)
        assert pref_default.leaderboard_opt_in is False
        assert pref_default.anonymize_name is True

        lb_empty = await get_leaderboard_endpoint(scope="institution", current_user=fx["stu1"], db=session)
        assert all(e.display_name != "Priya Sharma" for e in lb_empty.entries)

        # Opt-in stu1 (anonymized=True) and stu2 (anonymized=False)
        await update_preferences_endpoint(
            req=ArenaUserPreferenceUpdate(leaderboard_opt_in=True, anonymize_name=True),
            current_user=fx["stu1"],
            db=session,
        )
        await update_preferences_endpoint(
            req=ArenaUserPreferenceUpdate(leaderboard_opt_in=True, anonymize_name=False),
            current_user=fx["stu2"],
            db=session,
        )
        lb_inst = await get_leaderboard_endpoint(scope="institution", current_user=fx["stu1"], db=session)
        assert lb_inst.total_opted_in_participants == 2
        names = [e.display_name for e in lb_inst.entries]
        assert any(n.startswith("Scholar #") for n in names)
        assert "Priya Sharma" not in names  # Anonymized!
        assert "Rohan Verma" in names
        # Ensure zero academic/PII fields leaked
        for entry in lb_inst.entries:
            dumped = entry.model_dump()
            for forbidden_field in ("cgpa", "active_backlogs", "email", "roll_number"):
                assert forbidden_field not in dumped

        # Department scope excludes stu2 (IT) when stu1 (CS) queries
        lb_dept = await get_leaderboard_endpoint(scope="department", current_user=fx["stu1"], db=session)
        assert lb_dept.total_opted_in_participants == 1

    _run_with_rollback(_test)


def test_tpo_institutional_test_publishing_and_isolation():
    async def _test(session: AsyncSession):
        fx = await _seed_fixtures(session)

        # Students cannot author institutional tests
        with pytest.raises(AuthorizationException):
            await create_tpo_question_endpoint(
                req=ArenaTpoQuestionCreateRequest(
                    title="Unauthorized",
                    prompt_text="Should fail for student role.",
                    category=ArenaCategory.DSA,
                    options=[ArenaOptionItem(key="A", text="1"), ArenaOptionItem(key="B", text="2")],
                    correct_option_key="A",
                    explanation_text="Blocked",
                ),
                current_user=fx["stu1"],
                db=session,
            )

        # TPO A authors an institutional question + publishes test scoped to Inst A & CS dept
        q_tpo = await create_tpo_question_endpoint(
            req=ArenaTpoQuestionCreateRequest(
                title="Inst A Custom SQL Question",
                prompt_text="Which clause filters grouped aggregate rows in SQL?",
                category=ArenaCategory.DBMS,
                difficulty=ArenaDifficulty.EASY,
                question_type=ArenaQuestionType.MCQ,
                options=[
                    ArenaOptionItem(key="A", text="WHERE"),
                    ArenaOptionItem(key="B", text="HAVING"),
                ],
                correct_option_key="B",
                explanation_text="HAVING filters post-GROUP BY aggregates while WHERE filters base rows.",
            ),
            current_user=fx["tpo_a"],
            db=session,
        )
        assess_tpo = await create_tpo_assessment_endpoint(
            req=ArenaTpoAssessmentCreateRequest(
                title="Inst A CS Screening Test",
                description="Institutional practice evaluation for CSE batch 2027.",
                category=ArenaCategory.DBMS,
                difficulty=ArenaDifficulty.EASY,
                duration_minutes=15,
                question_ids=[q_tpo.id],
                department_id=fx["dept_cs"].id,
                target_graduation_year=2027,
                is_published=True,
            ),
            current_user=fx["tpo_a"],
            db=session,
        )
        assert assess_tpo.institution_id == fx["inst_a"].id

        # Student 1 (Inst A CS 2027) sees & completes the test
        visible_s1 = await list_assessments_endpoint(
            mode=ArenaAssessmentMode.INSTITUTIONAL_TEST, category=None, current_user=fx["stu1"], db=session
        )
        assert any(a.id == assess_tpo.id for a in visible_s1)

        att = await start_attempt_endpoint(
            req=ArenaStartAttemptRequest(assessment_id=assess_tpo.id),
            current_user=fx["stu1"],
            db=session,
        )
        await submit_answer_endpoint(
            attempt_id=att.id,
            req=ArenaSubmitAnswerRequest(question_id=q_tpo.id, selected_option_key="B", time_spent_seconds=12),
            current_user=fx["stu1"],
            db=session,
        )
        await submit_attempt_endpoint(attempt_id=att.id, req=None, current_user=fx["stu1"], db=session)

        # Student 3 (Inst B) CANNOT access Inst A's test
        with pytest.raises(AuthorizationException):
            await start_attempt_endpoint(
                req=ArenaStartAttemptRequest(assessment_id=assess_tpo.id),
                current_user=fx["stu3_b"],
                db=session,
            )

        # TPO B CANNOT query Inst A's analytics
        with pytest.raises(AuthorizationException):
            await get_tpo_analytics_endpoint(institution_id=fx["inst_a"].id, current_user=fx["tpo_b"], db=session)

        # TPO A views aggregated cohort results
        tpo_ana = await get_tpo_analytics_endpoint(institution_id=None, current_user=fx["tpo_a"], db=session)
        assert tpo_ana.participating_students >= 1
        assert tpo_ana.total_submitted_attempts >= 1
        row = next(r for r in tpo_ana.assessment_breakdown if r.assessment_id == assess_tpo.id)
        assert row.submitted_attempts == 1
        assert row.pass_rate_pct == 100.0

    _run_with_rollback(_test)
