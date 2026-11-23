# Software Requirements Specification (SRS)
## AI-Powered Placement Intelligence System

**Document Version:** 1.1.0  
**Project Status:** Academic Minor Project — Finalized Specification  
**System Architecture:** Modular Monolith  
**Author:** Lead Software Architect & Development Team  

---

## 1. Introduction

### 1.1 Purpose
This Software Requirements Specification (SRS) establishes the definitive requirements for the **AI-Powered Placement Intelligence System**. It serves as the single source of truth for architectural planning, database modeling, API contracts, UI/UX implementation, and phased delivery.

### 1.2 Project Scope
The AI-Powered Placement Intelligence System is a full-stack web application designed for collegiate placement cells. It bridges the gap between student aspirations, academic administration, and industry talent acquisition by introducing an AI-assisted, data-driven intelligence layer to campus recruitment. 

The system automates resume parsing, deterministic eligibility gating, skill compatibility scoring, recruitment pipeline tracking, and career coaching assistance while strictly adhering to lightweight, maintainable monolithic architectural standards.

### 1.3 Intended Audience
- Project Reviewers, Faculty Evaluators, and Academic Mentors
- Development Team and Software Architects
- Institutional Stakeholders (Placement Cell, Academic Departments, Recruiters, Students)

---

## 2. User Roles and Scoped Permissions

The system defines four distinct, mutually non-overlapping actor roles with strict role-based access control (RBAC) and tenancy scoping:

| Role | Description | Key Responsibilities & Scoped Permissions |
| :--- | :--- | :--- |
| **Student** | Undergraduate/Postgraduate student registered with the college. | **Private Scope:** Manages personal profile, uploads resumes, reviews extracted profile data, views eligible and recommended jobs, checks skill gaps, applies for recruitment drives, tracks application statuses, interacts with AI Career Assistant. *Can access only their own private resumes, profile, and applications.* |
| **TPO (Training & Placement Officer)** | Institutional authority overseeing campus placements. | **Institutional Scope:** Scoped strictly to their authorized institution (`users.institution_id`). Manages departments, academic branches, student batches; verifies student records; manages approved companies and job drives; monitors drive applications, shortlists, and placement offers; accesses campus-wide placement metrics. *Cannot view or manage students or drives of other institutions.* |
| **Recruiter / Company** | Corporate recruitment partner or HR representative. | **Corporate Scope:** Scoped strictly to their employer company (`jobs.company_id == recruiter.company_id`). Manages company profile; publishes and edits job postings with specific eligibility criteria and skill demands; reviews applicant resumes and scored compatibility for their company's jobs; updates applicant pipeline statuses (Shortlisted, Interviewed, Selected, Rejected). *Cannot access applicants or jobs of other companies.* |
| **Administrator** | System custodian / College IT administrator. | **Platform Scope:** Manages system users (activation, deactivation, role assignments); configures institutional metadata (institutions, departments); audits system access and error logs; monitors high-level platform health and AI diagnostics. *Explicitly prohibited from altering student application submissions or overriding company hiring decisions.* |

---

## 3. Functional Modules

### 3.1 Module 1: Authentication and User Profile Management (M1)
- **M1.1 User Authentication:** Registration for Students and Recruiters; administrative provisioning for TPOs and Admins. Email and password authentication with secure password hashing (Argon2 / bcrypt via Passlib).
- **M1.2 Account Security:** Email verification workflow and secure password reset via signed tokens.
- **M1.3 Role-Based Access Control (RBAC):** Stateless JWT-based authorization containing user ID and active role claims with endpoint-level dependency enforcement and ownership checks.
- **M1.4 Institution & Department Structure:** 
  - Hierarchical modeling: Institution -> Departments -> Academic Programs / Branches -> Graduation Batches.
  - `department_id` is **mandatory for Students** and **explicitly nullable** for TPOs, Recruiters, and Admins.
  - `institution_id` scopes Students and TPOs to their collegiate institution.
- **M1.5 Comprehensive Student Profile:**
  - *Personal Info:* Full name, email, contact number, personal links (LinkedIn, GitHub, Portfolio).
  - *Academic Info:* Institution name, department/branch, graduation year (batch), current CGPA, total active backlogs, history of arrears.
  - *Skill Taxonomy:* Technical skills (categorized by proficiency and domain) and soft skills.
  - *Portfolio Data:* Projects (title, description, technologies, project URL), Work Experience/Internships (company, role, duration, description), Certifications (title, issuer, issue date, credential URL).
- **M1.6 Recruiter Profile:** Company name, corporate email, recruiter designation, official phone, company website, headquarters location, company description.

### 3.2 Module 2: Resume Intelligence (M2)
- **M2.1 File Ingestion & Upload Validation:** 
  - Supports `.pdf` and `.docx` formats.
  - Hard file size limit: maximum **5 MB (5,242,880 bytes)**.
  - Magic byte verification (`%PDF` for PDF, PK ZIP for DOCX) and MIME type validation.
- **M2.2 Local Document Processing:** Extract raw text and structural layout locally using **PyMuPDF (`fitz`)** for PDF documents and **`python-docx`** for Word documents.
- **M2.3 AI-Powered Entity Extraction:** Structured extraction pipeline using generative AI with strict JSON output schemas:
  - Education history (institutions, degrees, graduation years, GPA/scores).
  - Categorized technical and soft skills.
  - Academic and personal projects.
  - Certifications and professional licenses.
  - Work experiences and internships.
  - *Integrity Constraint:* The extraction prompt and post-processing validation strictly prohibit the AI model from hallucinating or inventing missing qualifications, grades, or experiences.
- **M2.4 Human-in-the-Loop Review:** Students view an interactive side-by-side verification interface comparing raw extracted entities against their existing profile, enabling manual correction, addition, or deletion.
- **M2.5 Profile Synchronization:** Upon student confirmation, verified entities are committed to the student's normalized database profile.
- **M2.6 Private Resume Storage & Access Security:** Uploaded resume files are stored in a private backend filesystem directory (`backend/uploads/resumes/`) strictly outside the public web root. Direct HTTP access is blocked; documents can be downloaded only via authenticated streaming endpoints verifying ownership (Student owner, TPO of student's institution, or Recruiter for active job applicant).

### 3.3 Module 3: Company and Job Management (M3)
- **M3.1 Company Registry:** Management of registered corporate hiring partners, logos, domains, and verification status by TPOs.
- **M3.2 Job Opportunity Lifecycle:** Creation, editing, publishing, pausing, and closing of job postings by authenticated Recruiters (for own company) or TPOs.
- **M3.3 Job Posting Details:** Job title, department/specialization, job description, employment type (Full-time, Internship, 6-Month Intern + Full-time), work model (On-site, Hybrid, Remote), location, compensation (CTC, base salary, stipend), application start date, and hard application deadline.
- **M3.4 Strict Eligibility Criteria Configuration:**
  - Minimum CGPA cutoff (e.g., >= 7.5).
  - Permitted academic branches/departments (e.g., CSE, IT, ECE).
  - Eligible graduation batch/year (e.g., 2026).
  - Maximum allowable active backlogs (e.g., 0).
  - Maximum allowable historical backlogs.
  - Mandatory prerequisite skills.
  - Additional company-specific criteria.

### 3.4 Module 4: Placement Intelligence Engine (M4)
- **M4.1 Decoupled Dual Evaluation:** Strict architectural separation between **Deterministic Eligibility** (Binary Pass/Fail) and **Compatibility Matching** (Continuous 0–100% Score). A student may be 90% skill-compatible but ineligible due to backlogs, or eligible with only 40% skill compatibility.
- **M4.2 Deterministic Eligibility Rule Engine:**
  - Evaluates CGPA >= Job Minimum CGPA.
  - Evaluates Student Branch ∈ Permitted Branches.
  - Evaluates Student Graduation Year == Job Graduation Year.
  - Evaluates Student Active Backlogs <= Job Allowed Backlogs.
  - Returns boolean `is_eligible` with explicit human-readable violation flags (e.g., `["CGPA 7.1 below cutoff 7.5", "Branch Mechanical not in permitted branches"]`).
- **M4.3 Weighted Compatibility Scoring Engine:**
  - Configurable scoring formula:
    $$\text{Total Score} = (0.50 \times S_{\text{skills}}) + (0.20 \times S_{\text{academics}}) + (0.20 \times S_{\text{experience}}) + (0.10 \times S_{\text{certifications}})$$
  - *Technical Skills ($S_{\text{skills}}$, 50%):* Normalized exact and synonym overlap between student profile skills and job required/preferred skills.
  - *Academic Compatibility ($S_{\text{academics}}$, 20%):* Proportional score based on student CGPA relative to job threshold and branch alignment.
  - *Projects & Experience ($S_{\text{experience}}$, 20%):* Relevancy assessment of student projects, domain keywords, and internship experience against job domain.
  - *Certifications & Additional ($S_{\text{certifications}}$, 10%):* Relevancy of industry certifications and verified complementary competencies.
  - All weighting coefficients are centrally managed in application configuration.
- **M4.4 Skill Gap Identification:**
  - Classifies job skills into:
    1. *Matched Skills:* Present in both student profile and job posting.
    2. *Missing Mandatory Skills:* Critical skills required by the job but absent from student profile.
    3. *Recommended Growth Skills:* Secondary/good-to-have skills that would increase compatibility.
- **M4.5 Job Recommendation & Ranking:**
  - Personalized job feed for students ranked by Compatibility Score with active eligibility badges.
  - Recruiter view of applicants ranked by Compatibility Score with explicit eligibility indicators.
- **M4.6 Explainable Matching Intelligence:**
  - Generates clear, structured natural language rationale explaining why a student received a particular score, what strengths made them stand out, and the single highest-impact action they can take to qualify.

### 3.5 Module 5: AI Career Assistant (M5)
- **M5.1 Conversational Placement Guidance:** Context-aware Q&A tailored to student placement preparation, interview readiness, salary negotiation etiquette, and company research.
- **M5.2 Resume Optimization Engine:** Contextual critique of bullet points, action verbs, and quantifiable impact metrics for specific target jobs.
- **M5.3 Interview Preparation Hub:**
  - Dynamic generation of tailored technical interview questions based on job description and student's stated projects.
  - Behavioral and HR interview question preparation (STAR method coaching).
- **M5.4 Job Description Interpreter:** Translates dense industry job descriptions into clear breakdowns of daily responsibilities, core technical expectations, and suggested preparation strategies.
- **M5.5 Personalized Learning Roadmaps:** Generates prioritized 2-week, 4-week, or 8-week actionable study roadmaps targeting missing skills identified in Module 4.
- **M5.6 Configurable Multi-Provider LLM Architecture:**
  - Common unified interface supporting **Google Gemini API** and **OpenAI API**.
  - **No Hardcoded Model Identifiers:** Provider selection and model identifiers are configured dynamically via environment variables (`AI_PROVIDER`, `GEMINI_MODEL`, `OPENAI_MODEL`).
  - Built-in `mock` provider for reliable offline local testing and continuous integration without API costs.
  - **Strict Fail-Fast Policy:** Strict timeout (15s default), structured Pydantic schema validation, and fail-fast exception handling without silent fallbacks.

### 3.6 Module 6: Placement and Recruitment Management (M6)
- **M6.1 Application Submission:** Students apply to open jobs before the application deadline; system verifies profile completeness prior to submission.
- **M6.2 Duplicate Application Prevention:** Database-enforced unique constraint on `(job_id, student_id)` preventing duplicate submissions.
- **M6.3 Finite State Application Workflow:**
  $$\text{Applied} \longrightarrow \text{Under Review} \longrightarrow \text{Shortlisted} \longrightarrow \text{Interview Scheduled} \longrightarrow \begin{cases} \text{Selected} \\ \text{Rejected} \end{cases}$$
  *(With student-initiated `Withdrawn` status permitted before final selection)*
- **M6.4 Recruitment Drive Coordination:** TPOs and Recruiters configure multi-round recruitment drives (e.g., Online Assessment -> Technical Interview Round 1 -> Technical Interview Round 2 -> HR Interview).
- **M6.5 Candidate Pipeline Tracking:** Recruiters and TPOs filter applicants by eligibility, compatibility score, department, and current stage; bulk or individual state transitions.
- **M6.6 Placement Confirmation & Acceptance:** Tracking student offer letters, acceptance confirmation, and official placement records for institutional reporting.

---

## 4. Role Dashboards Specification

### 4.1 Student Dashboard (Private Scope)
- **Profile Health Meter:** Visual gauge showing profile completion percentage and missing profile sections.
- **Resume Digest:** Status of uploaded resume, parsed entities, and quick link to re-upload or edit.
- **Skill Overview:** Tag clouds of verified technical skills vs. trending industry skills.
- **Top Job Recommendations:** Curated list of jobs ranked by compatibility score with clear eligibility badges (`Eligible` / `Ineligible: Reason`).
- **Skill-Gap Radar:** Visual comparison of student skill set against target roles.
- **Application Tracker:** Timeline cards displaying active applications with live status badges.
- **AI Career Coach Quick Launcher:** One-click shortcuts for "Analyze my fit for Job X", "Generate interview questions for Job Y", and "Create learning plan".

### 4.2 TPO Dashboard (Institutional Scope)
- **Campus Placement KPI Metrics:** Total registered students, overall placement percentage, total active drives, total offers released, average and highest CTC for the institution.
- **Departmental Analytics:** Bar charts and breakdown tables of placement percentages and unplaced student counts across CSE, IT, ECE, MECH, etc.
- **Recruitment Drive Command Center:** Active drives calendar, ongoing stages, upcoming company visits, and application deadlines.
- **Student Eligibility Query Tool:** Instant query builder enabling TPOs to determine how many and which students qualify for incoming company criteria before publishing drives.
- **Offer Validation & Verification:** Queue for approving official placement records and verifying company offer letters.

### 4.3 Recruiter Dashboard (Corporate Scope)
- **Company Profile Card:** Company details, branding, active recruiters, and contact info.
- **Job Posting Management:** Grid of open, draft, and closed jobs with applicant counters for recruiter's company.
- **Candidate Pipeline Kanban/Table:** Filterable candidate view sorted by Placement Intelligence Compatibility Score, filtered by deterministic eligibility, with resume preview drawer.
- **Interview Stage Tracker:** Candidates scheduled for assessments and interviews with feedback capture fields.
- **Offers & Selection Portal:** Final selection marked candidates with salary package recording.

### 4.4 Administrator Dashboard (Platform Scope)
- **Platform Health & Metrics:** Total registered users broken down by role (Student, Recruiter, TPO, Admin), active sessions, system error rates.
- **User Management Console:** Search, filter, activate, deactivate, and assign roles to users.
- **Institutional Master Data:** Management of college name, branches/departments, degree programs, and academic grading schemas.
- **AI Diagnostics & Configuration:** View active AI provider (`gemini`, `openai`, `mock`), active model identifiers, token consumption metrics, and system configuration toggles.

---

## 5. Non-Functional Requirements

| Metric | Category | Specification |
| :--- | :--- | :--- |
| **NFR-1** | **Security & PII Protection** | Passwords hashed using bcrypt/Argon2. JWTs signed with secret key using HS256. Resumes stored in private backend directories outside public web root, excluded from Git via `.gitignore`, and served only through authenticated streaming routes. SQL injection prevented via SQLAlchemy ORM. |
| **NFR-2** | **File Upload Safeguards** | Strict 5MB size limit. MIME and magic byte validation for `.pdf` and `.docx` before processing. |
| **NFR-3** | **Performance** | Deterministic eligibility check < 50ms per job. Weighted compatibility scoring < 100ms per candidate. Document text extraction < 1.5s for standard 2-page resume. Database queries indexed for sub-100ms response times. |
| **NFR-4** | **Reliability & AI Integrity** | Configurable AI provider and model names via environment variables. AI provider timeouts capped at 15s with graceful user-facing error messaging. Strict fail-fast policy (no silent provider fallback). |
| **NFR-5** | **Usability** | Fully responsive layout across mobile (375px+), tablet (768px+), and desktop (1280px+). Clean Tailwind CSS design system with distinct visual states (loading, empty, error, success). |
| **NFR-6** | **Maintainability** | Clean modular monolith with separation of concerns: domain models, Pydantic schemas, service layer, and API route controllers. Single database migration history managed by Alembic. |
| **NFR-7** | **Compatibility** | 100% locally runnable on Windows 10/11 using standard Python virtual environments (`.venv`), Node.js (v18+), and local PostgreSQL instance without mandatory Docker, Redis, or Celery. |
