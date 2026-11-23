# Architectural Decision Records (ADR)
## AI-Powered Placement Intelligence System

**Document Version:** 1.1.0  
**Status:** Active & Enforced  

---

## Index of Decisions

- [ADR-01: Modular Monolithic Architecture over Microservices](#adr-01-modular-monolithic-architecture-over-microservices)
- [ADR-02: PostgreSQL with SQLAlchemy 2.0 and Alembic as the Relational Anchor](#adr-02-postgresql-with-sqlalchemy-20-and-alembic-as-the-relational-anchor)
- [ADR-03: Local Document Parsing via PyMuPDF and python-docx over Cloud OCR](#adr-03-local-document-parsing-via-pymupdf-and-python-docx-over-cloud-ocr)
- [ADR-04: Configurable Multi-Provider AI Abstraction Layer with Strict Fail-Fast Policy](#adr-04-configurable-multi-provider-ai-abstraction-layer-with-strict-fail-fast-policy)
- [ADR-05: Decoupled Deterministic Eligibility and Weighted Compatibility Scoring](#adr-05-decoupled-deterministic-eligibility-and-weighted-compatibility-scoring)
- [ADR-06: Database-Level Unique Constraint for Application Submission](#adr-06-database-level-unique-constraint-for-application-submission)
- [ADR-07: Human-in-the-Loop Synchronization for Resume AI Extraction](#adr-07-human-in-the-loop-synchronization-for-resume-ai-extraction)
- [ADR-08: Multi-Tenant Data Scoping and Scoped Authorization Hierarchy](#adr-08-multi-tenant-data-scoping-and-scoped-authorization-hierarchy)
- [ADR-09: Private Resume Storage, Git Exclusion and Authenticated Binary Streaming](#adr-09-private-resume-storage-git-exclusion-and-authenticated-binary-streaming)
- [ADR-10: Explicit Nullability of Department Assignment on User Identity](#adr-10-explicit-nullability-of-department-assignment-on-user-identity)

---

### ADR-01: Modular Monolithic Architecture over Microservices
- **Context:** An academic minor project requires rapid local iteration, minimal DevOps overhead, and predictable execution on a local Windows development machine. Introducing microservices, Docker compose orchestration, Redis, or Celery would introduce distributed systems complexity (network partitioning, saga transactions, latency, high memory footprint) unrelated to core placement intelligence requirements.
- **Decision:** Build the backend as a single FastAPI modular monolith, organized into discrete domain packages (`auth`, `users`, `resumes`, `companies`, `jobs`, `intelligence`, `applications`, `ai_assistant`).
- **Consequences:**
  - *Positive:* Single codebase, zero inter-service network latency, atomic database transactions across domains, instant local startup (`uvicorn`).
  - *Trade-off:* All background tasks run as lightweight asynchronous Python coroutines rather than dedicated worker queues.

---

### ADR-02: PostgreSQL with SQLAlchemy 2.0 and Alembic as the Relational Anchor
- **Context:** Campus placement workflows are inherently relational and transactional (students apply to jobs, jobs belong to companies, applications transition through strict stages, TPOs audit cohort data).
- **Decision:** Use PostgreSQL 15+ managed via SQLAlchemy 2.0 ORM and Alembic migrations. Semi-structured artifacts (AI resume JSON, match explanations) are stored using PostgreSQL's native `JSONB` type.
- **Consequences:**
  - *Positive:* ACID compliance, foreign key cascades, complex joins for analytical reporting, check constraints preventing invalid CGPA/backlog values, and schema evolution tracked in Git.
  - *Trade-off:* Requires a running PostgreSQL instance locally during development.

---

### ADR-03: Local Document Parsing via PyMuPDF and python-docx over Cloud OCR
- **Context:** Students upload resumes in PDF and DOCX formats. Cloud-based document AI or OCR services (e.g. AWS Textract, Google Document AI) require recurring billing, external API keys, internet connectivity, and raise student data privacy concerns.
- **Decision:** Perform all document text and layout extraction locally on the server using **PyMuPDF (`fitz`)** for PDF files and **`python-docx`** for Word files.
- **Consequences:**
  - *Positive:* Sub-1.5s extraction times, zero external API costs, private on-premise document handling, runs completely offline on Windows.
  - *Trade-off:* Does not OCR scanned images within PDFs (standard student software engineering resumes are vector/digital text documents).

---

### ADR-04: Configurable Multi-Provider AI Abstraction Layer with Strict Fail-Fast Policy
- **Context:** The system must support both Google Gemini API and OpenAI API without vendor lock-in. Model names must not be hardcoded in application logic. Furthermore, silent provider fallback (e.g. failing on Gemini and invisibly calling OpenAI) causes unpredictable billing, non-deterministic responses, and hidden configuration bugs.
- **Decision:** Implement a unified `BaseAIProvider` interface. The active provider and target model strings are resolved dynamically from environment variables (`AI_PROVIDER`, `GEMINI_MODEL`, `OPENAI_MODEL`). If the active provider fails, the system immediately returns an explicit error to the user without attempting a silent switch. A `MockAIProvider` is included for offline development and academic demonstration.
- **Consequences:**
  - *Positive:* Clean modularity, zero hardcoded model strings, predictable costs, deterministic testing in mock mode, immediate visibility of API key or quota issues.
  - *Trade-off:* If the chosen cloud provider is down, the request fails fast rather than attempting secondary routing.

---

### ADR-05: Decoupled Deterministic Eligibility and Weighted Compatibility Scoring
- **Context:** In college campus placements, corporate eligibility cutoffs are non-negotiable legal requirements (e.g., a student with backlogs or a 7.1 CGPA cannot be shortlisted for a company requiring 7.5 CGPA, regardless of high skill proficiency). Merging eligibility into a single score leads to confusing outcomes where ineligible students rank highly.
- **Decision:** Strictly decouple evaluation into two independent outputs:
  1. **Deterministic Eligibility:** A binary boolean (`is_eligible`) evaluated via rigid business rules (CGPA, active backlogs, graduation year, permitted branches).
  2. **Compatibility Scoring:** A continuous percentage (0–100%) calculated via configurable weighted scoring (50% skills, 20% academics, 20% experience, 10% certs).
- **Consequences:**
  - *Positive:* Absolute institutional fairness and transparency. Students understand precisely why they are ineligible while still learning how well their skills match the job.
  - *Trade-off:* Requires dual presentation in the UI (eligibility badge alongside compatibility score).

---

### ADR-06: Database-Level Unique Constraint for Application Submission
- **Context:** During campus recruitment drives, hundreds of students apply simultaneously when an application window opens, creating high concurrency. Relying solely on application-level checks (`if not exists: insert`) can cause race conditions leading to duplicate submissions.
- **Decision:** Enforce a compound unique database constraint at the database schema level: `UNIQUE(job_id, student_id)` on the `applications` table.
- **Consequences:**
  - *Positive:* 100% duplicate application prevention guaranteed at the database engine level.
  - *Trade-off:* Backend code must handle PostgreSQL unique violation exceptions (`IntegrityError`) and translate them to HTTP 409 Conflict.

---

### ADR-07: Human-in-the-Loop Synchronization for Resume AI Extraction
- **Context:** Generative AI models can occasionally miscategorize a framework or misinterpret a project title. Allowing AI extraction to directly overwrite a student's official academic profile could corrupt institutional data.
- **Decision:** Treat parsed resume data as an uncommitted draft. Extracted data is presented to the student in an interactive side-by-side verification interface. The profile is only updated after the student reviews, corrects, and explicitly clicks "Synchronize with Profile".
- **Consequences:**
  - *Positive:* Eliminates data corruption, prevents AI hallucinations from polluting the database, maintains student agency.
  - *Trade-off:* Requires an extra user confirmation step rather than instant automatic profile overwrites.

---

### ADR-08: Multi-Tenant Data Scoping and Scoped Authorization Hierarchy
- **Context:** The system hosts four distinct user roles across different institutions and companies. Without strict tenancy scoping, a recruiter might see applicants for competitor companies, or a TPO might access students from other colleges.
- **Decision:** Enforce ownership boundaries at the service and query layer:
  - Students access **only** their own records (`student_profiles.user_id == current_user.id`).
  - Recruiters access **only** applicants to jobs owned by their company (`jobs.company_id == current_user.recruiter_profile.company_id`).
  - TPOs are scoped strictly to their institution (`users.institution_id == current_user.institution_id`).
  - Administrators maintain infrastructure and accounts but cannot falsify student applications or company hiring selections.
- **Consequences:**
  - *Positive:* Rock-solid multi-tenant security, prevents cross-college or cross-corporate data leakage.
  - *Trade-off:* Requires explicit filter clauses on all database repository queries.

---

### ADR-09: Private Resume Storage, Git Exclusion and Authenticated Binary Streaming
- **Context:** Student resumes contain sensitive personal details (contact numbers, home addresses, educational records). Exposing resume files via public URLs or committing them to Git poses privacy and security risks.
- **Decision:** 
  1. Store uploaded files in a private server directory (`backend/uploads/resumes/`) strictly outside the public web root.
  2. Exclude `backend/uploads/` and all `.pdf`/`.docx` files from Git via `.gitignore`.
  3. Enforce maximum upload size of 5MB and validate MIME types and file magic bytes.
  4. Serve files exclusively through authenticated streaming endpoints (`GET /api/v1/resumes/{id}/download`) that verify caller authorization.
- **Consequences:**
  - *Positive:* Complete privacy protection, zero leakage of student resumes, protection against malicious file uploads.
  - *Trade-off:* File downloads require passing an Authorization header via an authenticated client.

---

### ADR-10: Explicit Nullability of Department Assignment on User Identity
- **Context:** In early drafts, `users.department_id` was envisioned as a generic foreign key. However, while a Student must belong to an academic department (e.g. CSE), TPOs oversee the entire institution (all departments), Recruiters are external corporate employees, and Admins are platform custodians.
- **Decision:** Define `users.department_id` as explicitly **NULLABLE** in PostgreSQL and the SQLAlchemy schema. Require `department_id` validation only during Student registration (`role == "student"`).
- **Consequences:**
  - *Positive:* Eliminates the need for artificial "dummy" departments for Recruiters, TPOs, or Admins. Keeps the database schema strictly accurate to domain semantics.
  - *Trade-off:* Requires conditional validation in Pydantic schemas based on user role.
