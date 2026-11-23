# RESTful API Specification
## AI-Powered Placement Intelligence System

**Document Version:** 1.1.0  
**Base URL:** `http://localhost:8000/api/v1`  
**Authentication Scheme:** Bearer Token (HTTP Authorization Header: `Bearer <jwt_token>`)  

---

## 1. Global Standards, Status Codes & Authorization Bounds

All API endpoints return JSON payloads encoded in UTF-8.

### 1.1 Scoped Data Ownership & Authorization Rules
Access control is enforced at the controller and service layer through strict tenancy checks:
1. **Student Isolation:** A student user can access **only** their own private profile, uploaded resumes, and application records (`student_profiles.user_id == current_user.id`). Any attempt to access another student's data returns `HTTP 403 Forbidden`.
2. **Recruiter Company Isolation:** A recruiter user can access **only** job postings, applicant pipelines, and resumes belonging to their own company (`jobs.company_id == current_user.recruiter_profile.company_id`). Querying applicants for other companies returns `HTTP 403 Forbidden`.
3. **TPO Institutional Scoping:** A TPO user can access **only** students, departments, job drives, and placement analytics belonging to their own institution (`users.institution_id == current_user.institution_id`).
4. **Explicit Administrator Bounds:** Administrators manage tenant setup, user activation/deactivation, and AI diagnostics. Administrators cannot submit applications on behalf of students or alter recruiter hiring decisions (Shortlisted/Selected/Rejected).

### 1.2 Standard Response Envelopes
#### Standard Error Envelope
```json
{
  "success": false,
  "error": {
    "code": "AUTHORIZATION_OWNERSHIP_VIOLATION",
    "message": "You are not authorized to view applicant data outside your company.",
    "details": { "requested_job_id": 14, "recruiter_company_id": 3 }
  }
}
```

### 1.3 Standard HTTP Status Codes
- `200 OK`: Request succeeded.
- `201 Created`: Resource successfully created.
- `400 Bad Request`: Invalid request parameters or business logic violation.
- `401 Unauthorized`: Token missing, malformed, or expired.
- `403 Forbidden`: Authenticated user lacks required role permissions or fails ownership check.
- `404 Not Found`: Target resource not found.
- `409 Conflict`: Conflict state (e.g. duplicate email or application).
- `413 Payload Too Large`: Uploaded file exceeds 5MB limit.
- `422 Unprocessable Entity`: Request body failed schema or magic byte validation.
- `500 Internal Server Error`: Server failure.

---

## 2. Module 1: Authentication & User Profiles (M1)

### 2.1 `POST /auth/register`
- **Purpose:** Register a new user account (Student or Recruiter).
- **Permitted Roles:** Public (Unauthenticated)
- **Validation Rules:**
  - `department_id` is mandatory for Students (`role = "student"`).
  - `department_id` is optional/null for Recruiters (`role = "recruiter"`).
  - Password must be at least 8 characters with at least one number and special character.
- **Request Body:**
  ```json
  {
    "email": "student@college.edu",
    "password": "SecurePassword123!",
    "full_name": "Arjun Sharma",
    "phone": "+91-9876543210",
    "role": "student",
    "institution_id": 1,
    "department_id": 1,
    "student_data": {
      "roll_number": "2022CSE104",
      "graduation_year": 2026,
      "cgpa": 8.45,
      "active_backlogs": 0,
      "total_backlogs": 0
    }
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "success": true,
    "message": "Registration successful. Please verify your email.",
    "user_id": 101,
    "email": "student@college.edu",
    "role": "student"
  }
  ```

### 2.2 `POST /auth/login`
- **Purpose:** Authenticate user and issue scoped JWT token.
- **Permitted Roles:** Public
- **Request Body:**
  ```json
  {
    "email": "student@college.edu",
    "password": "SecurePassword123!"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in_hours": 24,
    "user": {
      "id": 101,
      "email": "student@college.edu",
      "full_name": "Arjun Sharma",
      "role": "student",
      "institution_id": 1,
      "department_id": 1,
      "department_name": "Computer Science & Engineering"
    }
  }
  ```

### 2.3 `GET /auth/me`
- **Purpose:** Retrieve currently authenticated user context, role, and scoping IDs.
- **Permitted Roles:** All Authenticated (`student`, `tpo`, `recruiter`, `admin`)
- **Headers:** `Authorization: Bearer <token>`
- **Response (200 OK):** User context object.

### 2.4 `GET /students/profile`
- **Purpose:** Fetch detailed profile of current student or target student.
- **Permitted Roles & Scope:**
  - `student`: Can access **only** own profile (`student_id` parameter ignored).
  - `tpo`: Can access any student profile where `student.user.institution_id == current_user.institution_id`.
  - `recruiter`: Can access student profile **only** if that student has an active application to a job owned by recruiter's company.
  - `admin`: Read access for system audits.
- **Query Params:** `student_id` (optional for TPO/Recruiter/Admin; defaults to self for Student)
- **Response (200 OK):** Detailed student academic and portfolio profile.

### 2.5 `PUT /students/profile`
- **Purpose:** Update student academic and portfolio attributes.
- **Permitted Roles & Scope:**
  - `student`: Can update own portfolio (skills, projects, certifications).
  - `tpo`: Can update official academic fields (CGPA, backlogs, verification status) for students within own institution.
- **Response (200 OK):** Updated profile object.

---

## 3. Module 2: Resume Intelligence (M2)

### 3.1 `POST /resumes/upload`
- **Purpose:** Upload resume document, extract text locally using PyMuPDF/python-docx, and invoke AI entity extraction.
- **Permitted Roles:** `student` (uploads to own profile only)
- **Content-Type:** `multipart/form-data`
- **Validation Guardrails:**
  - **File Size:** Maximum **5 MB (5,242,880 bytes)**. Files > 5MB are rejected with `HTTP 413 Payload Too Large`.
  - **File Extensions Allowed:** `.pdf`, `.docx`.
  - **Magic Byte Verification:**
    - PDF: First 4 bytes must match `%PDF` (`0x25 0x50 0x44 0x46`).
    - DOCX: First 4 bytes must match PK ZIP header (`0x50 0x4B 0x03 0x04`).
- **Storage Location:** Stored in private server path `backend/uploads/resumes/{student_id}_{uuid}.pdf` (excluded from Git).
- **Response (200 OK):**
  ```json
  {
    "resume_id": 12,
    "file_name": "Arjun_Sharma_Resume.pdf",
    "parsing_status": "extracted",
    "extracted_data": {
      "contact_info": { "name": "Arjun Sharma", "email": "student@college.edu", "phone": "+91-9876543210" },
      "education": [
        { "institution": "ABC Institute of Technology", "degree": "B.Tech CSE", "year": 2026, "cgpa": 8.45 }
      ],
      "skills": [
        { "name": "Python", "category": "Languages" },
        { "name": "PostgreSQL", "category": "Databases" }
      ],
      "projects": [
        { "title": "AI Placement Portal", "description": "Built modular web app with FastAPI and React." }
      ],
      "certifications": ["AWS Certified Cloud Practitioner"],
      "experiences": []
    }
  }
  ```

### 3.2 `POST /resumes/{resume_id}/sync-profile`
- **Purpose:** Commit student-verified extracted entities into student's normalized database profile.
- **Permitted Roles & Scope:** `student` (verified on own resume only).
- **Request Body:** Verified data payload containing confirmed skills, projects, and certifications.
- **Response (200 OK):** Count of synchronized entities.

### 3.3 `GET /resumes/{resume_id}/download`
- **Purpose:** Securely stream resume PDF/DOCX binary file from private backend storage.
- **Permitted Roles & Scope:**
  - `student`: Can download **only** own uploaded resume.
  - `recruiter`: Can download **only** if student has an active application to a job owned by recruiter's company (`jobs.company_id == current_user.recruiter_profile.company_id`).
  - `tpo`: Can download **only** for students belonging to their own institution (`user.institution_id == current_user.institution_id`).
  - `admin`: Permitted for compliance/audit.
  - *Unauthorized access returns `HTTP 403 Forbidden`.*
- **Response (200 OK):** File binary stream (`application/pdf` or `application/vnd.openxmlformats-officedocument.wordprocessingml.document`).

---

## 4. Module 3: Company & Job Management (M3)

### 4.1 `GET /companies`
- **Purpose:** List registered hiring companies.
- **Permitted Roles:** All Authenticated
- **Response (200 OK):** List of company objects.

### 4.2 `POST /companies`
- **Purpose:** Register a new corporate hiring partner.
- **Permitted Roles:** `tpo`, `admin`, `recruiter`
- **Response (201 Created):** Created company entity.

### 4.3 `GET /jobs`
- **Purpose:** Fetch list of jobs with active filtering, pagination, and student eligibility flags.
- **Permitted Roles:** All Authenticated
- **Response (200 OK):** Paginated list of jobs.

### 4.4 `POST /jobs`
- **Purpose:** Create and publish a new job opportunity with strict eligibility criteria.
- **Permitted Roles & Scope:**
  - `recruiter`: Can create jobs **only** for their associated company (`company_id == current_user.recruiter_profile.company_id`).
  - `tpo`: Can create jobs on behalf of verified partner companies for campus drives.
  - `admin`: Administrative creation.
- **Request Body:** Job criteria, cutoffs, and weighted required skills.
- **Response (201 Created):** Created job object with ID.

---

## 5. Module 4: Placement Intelligence Engine (M4)

### 5.1 `GET /intelligence/jobs/{job_id}/evaluate`
- **Purpose:** Evaluate student against specific job returning separated deterministic eligibility, weighted compatibility score, skill gaps, and explainability summary.
- **Permitted Roles & Scope:**
  - `student`: Can evaluate **only** self.
  - `recruiter`: Can evaluate candidate **only** if candidate applied to recruiter's company job.
  - `tpo`: Can evaluate any student in own institution against any campus drive job.
- **Response (200 OK):** Separated deterministic eligibility and weighted compatibility breakdown.

### 5.2 `GET /intelligence/recommended-jobs`
- **Purpose:** Retrieve list of jobs ranked by compatibility score specifically for authenticated student.
- **Permitted Roles:** `student` (own recommendations).
- **Response (200 OK):** Array of ranked job cards.

### 5.3 `GET /intelligence/jobs/{job_id}/applicants-ranked`
- **Purpose:** Retrieve all applicants for a job ranked by compatibility score with filter for eligibility.
- **Permitted Roles & Scope:**
  - `recruiter`: Only for jobs owned by their company (`job.company_id == current_user.recruiter_profile.company_id`).
  - `tpo`: For jobs associated with their campus drives.
- **Response (200 OK):** Array of ranked candidates.

---

## 6. Module 5: AI Career Assistant (M5)

*Note: All AI endpoints dynamically resolve the active provider and model from environment variables (`AI_PROVIDER`, `GEMINI_MODEL`, `OPENAI_MODEL`). No model identifiers are hardcoded.*

### 6.1 `POST /ai-assistant/chat`
- **Purpose:** Placement coaching conversational interaction with student context.
- **Permitted Roles:** `student`
- **Request Body:** User message and conversation history.
- **Response (200 OK):**
  ```json
  {
    "provider_used": "gemini",
    "model_used": "gemini-1.5-flash",
    "response": "To prepare for an SDE-1 interview...",
    "suggested_followups": ["Explain Python GIL", "Common SQL queries"]
  }
  ```

### 6.2 `POST /ai-assistant/interview-prep`
- **Purpose:** Generate role-specific technical & behavioral interview questions based on job description and student resume.
- **Permitted Roles:** `student`
- **Response (200 OK):** Tailored technical and HR questions.

### 6.3 `POST /ai-assistant/learning-roadmap`
- **Purpose:** Generate structured, phased learning roadmap to resolve identified skill gaps for a target job.
- **Permitted Roles:** `student`
- **Response (200 OK):** Phased weekly learning roadmap.

---

## 7. Module 6: Placement & Recruitment Management (M6)

### 7.1 `POST /applications`
- **Purpose:** Submit job application for authenticated student.
- **Permitted Roles & Scope:** `student` (submits for self).
- **Constraint:** Database-level compound unique constraint `UNIQUE(job_id, student_id)` prevents duplicate submissions.
- **Response (201 Created):** Created application entity.
- **Error (409 Conflict):** If student already applied for this job.

### 7.2 `GET /applications/my-applications`
- **Purpose:** List all job applications submitted by the authenticated student.
- **Permitted Roles:** `student` (own applications only).
- **Response (200 OK):** Array of student applications with statuses.

### 7.3 `GET /applications/job/{job_id}`
- **Purpose:** List all candidate applications for a specific job posting.
- **Permitted Roles & Scope:**
  - `recruiter`: Strictly limited to jobs owned by recruiter's company (`job.company_id == current_user.recruiter_profile.company_id`). Unauthorized queries return `HTTP 403 Forbidden`.
  - `tpo`: Permitted for campus recruitment drives within their institution.
- **Response (200 OK):** Paginated candidate list.

### 7.4 `PATCH /applications/{application_id}/status`
- **Purpose:** Advance candidate pipeline status (`Applied`, `Under Review`, `Shortlisted`, `Interview Scheduled`, `Selected`, `Rejected`).
- **Permitted Roles & Scope:**
  - `recruiter`: Strictly for applicants to jobs owned by recruiter's company.
  - `tpo`: Permitted for drives coordinated with the company.
- **Request Body:**
  ```json
  {
    "status": "shortlisted",
    "feedback_notes": "Passed technical screening."
  }
  ```
- **Response (200 OK):** Updated application status.

### 7.5 `POST /applications/{application_id}/finalize-offer`
- **Purpose:** Record official placement acceptance and create verified institutional placement record.
- **Permitted Roles & Scope:**
  - `tpo`: Strictly for students belonging to their own institution.
  - `admin`: Permitted.
- **Response (201 Created):** Created `placement_records` entry.

---

## 8. Analytics & Admin Endpoints

### 8.1 `GET /analytics/tpo/overview`
- **Purpose:** Fetch campus-wide placement metrics, departmental breakdown, and active recruitment drive KPIs.
- **Permitted Roles & Scope:** `tpo` (strictly scoped to `current_user.institution_id`), `admin`.
- **Response (200 OK):** Institutional metrics and department breakdown.

### 8.2 `GET /analytics/admin/system-stats`
- **Purpose:** Platform operational statistics and user distribution across all institutions.
- **Permitted Roles:** `admin` (System Administrator only).
- **Response (200 OK):** Counts of users by role, active DB connections, active AI provider status.
