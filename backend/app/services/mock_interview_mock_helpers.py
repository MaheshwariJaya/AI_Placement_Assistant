"""Deterministic, grounded mock responses for MockAIProvider in the AI Mock Interview Studio."""
import re
from typing import Dict, List, Optional

from app.schemas.mock_interview import (
    ADVISORY_MOCK_INTERVIEW_DISCLAIMER,
    CriteriaBreakdownScores,
    FollowUpDecisionAIOutput,
    GeneratedInterviewPlan,
    GeneratedMockQuestion,
    MockInterviewEvaluationAIOutput,
    QuestionEvaluationAIItem,
)
from app.services.cse_40_subjects_data import CSE_40_INTERVIEW_BLUEPRINTS


def _extract_tag(prompt: str, tag: str, default: str = "") -> str:
    match = re.search(rf"<{tag}>(.*?)</{tag}>", prompt, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else default


def _parse_csv_field(block: str, label: str) -> List[str]:
    pattern = rf"{re.escape(label)}:\s*(.+)"
    m = re.search(pattern, block, re.IGNORECASE)
    if not m:
        return []
    val = m.group(1).strip()
    if not val or val.lower() in ("none", "none listed", "not specified", "n/a"):
        return []
    return [item.strip() for item in val.split(",") if item.strip()]


def synthesize_mock_interview_plan(user_prompt: str) -> GeneratedInterviewPlan:
    meta = _extract_tag(user_prompt, "INTERVIEW_CONFIG", user_prompt)
    profile = _extract_tag(user_prompt, "STUDENT_CONTEXT", user_prompt)
    job_ctx = _extract_tag(user_prompt, "JOB_CONTEXT", "")

    cat_m = re.search(r"Category:\s*(\w+)", meta, re.IGNORECASE)
    diff_m = re.search(r"Difficulty:\s*(\w+)", meta, re.IGNORECASE)
    cnt_m = re.search(r"Question Count:\s*(\d+)", meta, re.IGNORECASE)
    role_m = re.search(r"Target Role:\s*(.+)", meta, re.IGNORECASE)

    category = (cat_m.group(1).lower() if cat_m else "technical").strip()
    difficulty = (diff_m.group(1).lower() if diff_m else "intermediate").strip()
    count = int(cnt_m.group(1)) if cnt_m else 5
    count = max(1, min(10, count))
    target_role = (role_m.group(1).strip() if role_m else "Software Engineer")

    skills = _parse_csv_field(profile, "Verified Skills")
    projects = _parse_csv_field(profile, "Verified Projects")
    job_skills = _parse_csv_field(job_ctx, "Mandatory Skills") + _parse_csv_field(job_ctx, "Preferred Skills")

    primary_skill = job_skills[0] if job_skills else (skills[0] if skills else "Python and Data Structures")
    secondary_skill = (
        job_skills[1] if len(job_skills) > 1 else (skills[1] if len(skills) > 1 else "Relational Databases & SQL")
    )
    primary_project = projects[0] if projects else f"your core {target_role} academic capstone"

    diff_prefix = {
        "beginner": "fundamental",
        "intermediate": "practical design and trade-off",
        "advanced": "deep architecture, scalability, and edge-case",
    }.get(difficulty, "practical")

    dept_m = re.search(r"Department:\s*([^\n\r]+)", profile, re.IGNORECASE)
    dept_str = (dept_m.group(1).lower() if dept_m else "").strip()

    if "civil" in dept_str or "struct" in dept_str:
        q3 = GeneratedMockQuestion(
            topic="Structural Mechanics & Load Paths",
            question_text="Explain the fundamental difference between determinate and indeterminate structural systems. When modeling a continuous frame in STAAD.Pro or AutoCAD, how do you verify load transfer and joint equilibrium?",
            expected_key_points=["Equilibrium vs compatibility equations", "Degree of static indeterminacy", "Verification of bending moment & shear force diagrams"],
            model_answer="Determinate systems require only static equilibrium equations, whereas indeterminate systems require compatibility relations. Verify support reactions against total applied load and check shear/moment continuity at joints.",
            difficulty_hint=difficulty,
        )
        q4 = GeneratedMockQuestion(
            topic="Concrete Technology & Mix Durability",
            question_text="How do water-cement ratio, workability (slump test), and curing conditions govern characteristic compressive strength and durability according to IS 456 / standard specifications?",
            expected_key_points=["Abram's water-cement ratio law", "Slump cone test for consistency", "Curing duration and hydration heat control"],
            model_answer="Compressive strength is inversely proportional to water-cement ratio. Proper grading and plasticizers ensure workability without excess water, and 28-day moist curing ensures optimal C-S-H gel formation.",
            difficulty_hint=difficulty,
        )
        q5 = GeneratedMockQuestion(
            topic="Geotechnical & Site Execution Quality",
            question_text="Describe standard geotechnical testing procedures before foundation design. How do you assess bearing capacity, and what measures prevent differential settlement?",
            expected_key_points=["Standard Penetration Test (SPT N-value)", "Terzaghi bearing capacity equation", "Soil compaction and raft/pile foundation selection"],
            model_answer="Conduct SPT boreholes to measure N-values and shear parameters (c, phi). Choose raft or deep pile foundations when safe bearing capacity is low to distribute stresses and eliminate differential settlement.",
            difficulty_hint=difficulty,
        )
    elif "mech" in dept_str:
        q3 = GeneratedMockQuestion(
            topic="Thermodynamics & Power Cycles",
            question_text="Compare the thermodynamic thermal efficiencies of the Otto, Diesel, and Rankine cycles. Which irreversible losses most significantly reduce real-world engine performance?",
            expected_key_points=["Compression ratio relationship", "Heat addition at constant volume vs pressure", "Frictional, throttling, and heat dissipation losses"],
            model_answer="Otto cycle efficiency depends directly on compression ratio. Real cycles suffer from friction, incomplete combustion, throttling through valves, and exhaust heat loss.",
            difficulty_hint=difficulty,
        )
        q4 = GeneratedMockQuestion(
            topic="Strength of Materials & Failure Criteria",
            question_text="Contrast von Mises yield criterion with Tresca maximum shear stress theory. When is von Mises specifically preferred in ductile machine component design?",
            expected_key_points=["Distortion energy theory vs max shear stress", "Yield locus representation", "Application to ductile metals under multiaxial stress"],
            model_answer="Von Mises predicts yielding when distortion energy reaches that of simple tension. It is more accurate and less overly conservative for ductile metals subjected to combined bending and torsion.",
            difficulty_hint=difficulty,
        )
        q5 = GeneratedMockQuestion(
            topic="Manufacturing & CAD/CAM Integration",
            question_text="In CNC manufacturing and CAD modeling (e.g. SolidWorks/ANSYS), explain how geometric dimensioning and tolerancing (GD&T) ensures interchangeability and reduces machining costs.",
            expected_key_points=["Datum references and feature control frames", "True position vs coordinate tolerances", "Machinability and surface roughness parameters"],
            model_answer="GD&T defines functional datum features and cylindrical tolerance zones, allowing larger manufacturing tolerances while strictly ensuring assembly fit and reducing scrap rates.",
            difficulty_hint=difficulty,
        )
    elif "elec" in dept_str or "eee" in dept_str:
        q3 = GeneratedMockQuestion(
            topic="Power Systems & Grid Stability",
            question_text="Explain transient stability in high-voltage AC power transmission. How does the swing equation describe rotor angle dynamics following a three-phase fault?",
            expected_key_points=["Equal Area Criterion", "Critical clearing angle and time", "Inertia constant H and mechanical vs electrical power balance"],
            model_answer="Transient stability measures the system ability to maintain synchronism after severe disturbances. The swing equation correlates rotor acceleration with power imbalance; fast breaker clearing prevents rotor angle runaway.",
            difficulty_hint=difficulty,
        )
        q4 = GeneratedMockQuestion(
            topic="Electrical Machines & Drive Control",
            question_text="Compare field-oriented vector control (FOC) with direct torque control (DTC) for three-phase induction motor drives in industrial traction.",
            expected_key_points=["d-q coordinate transformation", "Decoupled flux and torque control", "Switching frequency and torque ripple trade-offs"],
            model_answer="FOC transforms stator currents into rotating d-q coordinates to decouple flux and torque control like a DC motor, offering smooth torque and fixed switching frequency at the expense of computational overhead.",
            difficulty_hint=difficulty,
        )
        q5 = GeneratedMockQuestion(
            topic="Protection & Switchgear Automation",
            question_text="Describe differential protection schemes for power transformers. How does harmonic restraint prevent nuisance tripping during inrush currents?",
            expected_key_points=["Merz-Price circulating current principle", "CT ratio matching and phase compensation", "Second harmonic filtering for magnetizing inrush"],
            model_answer="Differential relays compare primary and secondary currents. Second-harmonic restraint filters out the prominent 2nd harmonic characteristic of magnetizing inrush during energization.",
            difficulty_hint=difficulty,
        )
    elif "ece" in dept_str or "electronics" in dept_str or "embedded" in dept_str:
        q3 = GeneratedMockQuestion(
            topic="Digital Logic & VLSI Synthesis",
            question_text="Explain setup time (t_setup) and hold time (t_hold) in synchronous sequential circuits. How do you resolve setup violations vs hold violations in clock-tree synthesis?",
            expected_key_points=["Flip-flop timing constraints", "Clock skew and data path delay", "Buffer insertion for hold fix vs logic optimization for setup"],
            model_answer="Setup time requires data to remain stable before the clock edge; hold time requires stability after. Fix setup by optimizing combinatorial logic or lowering clock frequency; fix hold by adding delay buffers in the data path.",
            difficulty_hint=difficulty,
        )
        q4 = GeneratedMockQuestion(
            topic="Microcontrollers & Low-Power Firmware",
            question_text="In ARM Cortex-M architecture, explain interrupt latency and the purpose of tail-chaining in the Nested Vectored Interrupt Controller (NVIC).",
            expected_key_points=["Hardware stack push/pop overhead", "Tail-chaining execution optimization", "Priority preemption and interrupt masking"],
            model_answer="NVIC tail-chaining skips the unstacking and restacking steps when back-to-back interrupts occur, reducing latency from ~12-16 cycles down to ~6 cycles.",
            difficulty_hint=difficulty,
        )
        q5 = GeneratedMockQuestion(
            topic="Signal Processing & Communication",
            question_text="Explain the Nyquist-Shannon sampling theorem and the role of anti-aliasing low-pass filters before analog-to-digital conversion.",
            expected_key_points=["Sampling frequency fs > 2 * f_max", "Spectral folding / aliasing distortion", "Analog low-pass filter rolloff requirements"],
            model_answer="Sampling below the Nyquist rate causes high-frequency components to alias into the baseband spectrum. An analog anti-aliasing filter attenuates frequencies above fs/2 before ADC quantization.",
            difficulty_hint=difficulty,
        )
    elif "chem" in dept_str:
        q3 = GeneratedMockQuestion(
            topic="Mass Transfer & Distillation Design",
            question_text="Using the McCabe-Thiele method, explain how reflux ratio affects the number of theoretical stages in a continuous binary distillation column.",
            expected_key_points=["Minimum reflux vs total reflux", "Operating lines and feed q-line", "Trade-off between capital column cost and reboiler energy"],
            model_answer="Increasing reflux ratio shifts operating lines closer to the 45-degree line, decreasing the required theoretical stages but increasing reboiler heat and condenser cooling duties.",
            difficulty_hint=difficulty,
        )
        q4 = GeneratedMockQuestion(
            topic="Chemical Reaction Kinetics & Reactor Sizing",
            question_text="Compare the conversion and temperature control characteristics of a Continuous Stirred Tank Reactor (CSTR) versus a Plug Flow Reactor (PFR) for exothermic reactions.",
            expected_key_points=["Residence time distribution", "Space-time and space-velocity", "Thermal runaway prevention and heat exchange area"],
            model_answer="PFR requires smaller volume for positive-order reactions due to higher reactant concentration, but CSTR operates at uniform exit conditions, making temperature control of exothermic reactions easier.",
            difficulty_hint=difficulty,
        )
        q5 = GeneratedMockQuestion(
            topic="Process Dynamics & Plant Safety",
            question_text="Explain Layer of Protection Analysis (LOPA) and Safety Integrity Level (SIL) allocation for hazardous petrochemical units.",
            expected_key_points=["Independent protection layers (IPL)", "Hazard and operability (HAZOP) integration", "Safety Instrumented Systems (SIS) design"],
            model_answer="LOPA quantifies the risk reduction provided by independent protection layers against initiated events, determining the required SIL (1 to 4) for safety instrumented functions.",
            difficulty_hint=difficulty,
        )
    elif "mine" in dept_str or "petro" in dept_str:
        q3 = GeneratedMockQuestion(
            topic="Rock Mechanics & Strata Control",
            question_text="Explain how Rock Quality Designation (RQD) and Rock Mass Rating (RMR) guide support design in underground openings and slope stability in open pits.",
            expected_key_points=["Core recovery percentage of sound pieces >10cm", "Bieniawski RMR parameters", "Rock bolt and shotcrete reinforcement selection"],
            model_answer="RQD measures fractured core recovery; RMR incorporates intact rock strength, joint spacing, and groundwater to classify the rock mass and design rock bolting patterns.",
            difficulty_hint=difficulty,
        )
        q4 = GeneratedMockQuestion(
            topic="Reservoir & Fluid Flow in Porous Media",
            question_text="Explain Darcy's Law for radial fluid flow into a production wellbore. How does the skin factor (s) quantify formation damage or stimulation?",
            expected_key_points=["Permeability, viscosity, pressure differential", "Positive skin vs negative skin (hydraulic fracturing)", "Productivity index calculation"],
            model_answer="Darcy's Law relates flow rate to pressure gradient, permeability, and viscosity. Positive skin indicates near-wellbore clogging requiring acidizing; negative skin indicates successful fracturing.",
            difficulty_hint=difficulty,
        )
        q5 = GeneratedMockQuestion(
            topic="Mine Safety & Atmospheric Ventilation",
            question_text="In underground mining, describe the explosive limits of methane (CH4) and coal dust, and how stone dusting prevents propagating coal dust explosions.",
            expected_key_points=["5% to 15% methane explosive range", "Incombustible stone dust (CaCO3) heat sink effect", "Continuous gas telemetry and ventilation airflow velocity"],
            model_answer="Methane ignites between 5% and 15% concentration. Dispersed limestone dust absorbs flame heat, quenching the reaction and preventing localized gas ignitions from propagating through coal dust.",
            difficulty_hint=difficulty,
        )
    elif "pie" in dept_str or "production" in dept_str or "industrial" in dept_str:
        q3 = GeneratedMockQuestion(
            topic="Operations Research & Linear Programming",
            question_text="Explain the Simplex algorithm for maximizing production output under constrained machine hours. How do shadow prices (dual variables) guide capacity expansion?",
            expected_key_points=["Feasible region corner point movement", "Slack and surplus variables", "Economic interpretation of shadow prices"],
            model_answer="The Simplex method iteratively moves along extreme points of the convex polytope. Shadow prices indicate the marginal increase in objective value per unit increase in a constrained resource.",
            difficulty_hint=difficulty,
        )
        q4 = GeneratedMockQuestion(
            topic="Lean Manufacturing & Six Sigma (DMAIC)",
            question_text="Walk through the 5 phases of DMAIC in reducing dimensional defect rates on an automated stamping line.",
            expected_key_points=["Define, Measure, Analyze, Improve, Control", "Process capability indices Cp and Cpk", "Statistical process control (SPC) charts"],
            model_answer="Define the CTQ defect, measure baseline Cpk, analyze root causes using Ishikawa/ANOVA, improve through DOE parameter optimization, and control with Shewhart X-bar/R control charts.",
            difficulty_hint=difficulty,
        )
        q5 = GeneratedMockQuestion(
            topic="Supply Chain & Inventory Optimization",
            question_text="Derive the Economic Order Quantity (EOQ) formula and explain how safety stock balances stockout risk against carrying costs under stochastic demand.",
            expected_key_points=["EOQ = sqrt(2DS/H)", "Holding cost vs ordering cost trade-off", "Service level z-score and lead time demand variance"],
            model_answer="EOQ balances ordering costs and inventory holding costs. Safety stock covers demand variability during supplier lead time based on the target customer service level.",
            difficulty_hint=difficulty,
        )
    elif "arch" in dept_str or "plan" in dept_str:
        q3 = GeneratedMockQuestion(
            topic="Urban Planning & Zoning Regulations",
            question_text="Explain Floor Area Ratio (FAR / FSI) and how mixed-use zoning and transit-oriented development (TOD) alleviate urban traffic congestion.",
            expected_key_points=["Gross floor area over parcel area", "TOD density corridors near mass transit", "Balancing utility infrastructure with built density"],
            model_answer="FAR limits total built floor space relative to plot area. TOD concentrates higher FAR near transit nodes, encouraging walking and public transit while reducing vehicular sprawl.",
            difficulty_hint=difficulty,
        )
        q4 = GeneratedMockQuestion(
            topic="BIM & Building Performance Simulation",
            question_text="In Revit and Building Information Modeling (BIM), explain Level of Development (LOD 100 to 500) and how clash detection prevents on-site spatial conflicts.",
            expected_key_points=["LOD definitions from concept to as-built", "Automated spatial interference checking (MEP vs structural)", "Lifecycle facility management integration"],
            model_answer="LOD specifies geometry and data precision from schematic (LOD 200) to fabrication (LOD 400). Clash detection finds physical intersections between structural beams and HVAC ducts before construction.",
            difficulty_hint=difficulty,
        )
        q5 = GeneratedMockQuestion(
            topic="Environmental Design & Green Architecture",
            question_text="Describe passive solar architecture strategies for warm-humid vs composite climatic zones in India. How do solar shading (chajjas) and fenestration orientation minimize cooling loads?",
            expected_key_points=["Sun path diagrams and solar azimuth/altitude", "Building envelope U-values and thermal mass", "Cross-ventilation vs daylighting optimization"],
            model_answer="Orient longest facades north-south to minimize direct low-angle solar heat gain; size horizontal overhangs to shade summer sun while maximizing cross-ventilation in warm-humid conditions.",
            difficulty_hint=difficulty,
        )
    else:
        # Check if one of the 40 CSE curriculum subjects is explicitly targeted
        subject_m = re.search(r"(?:Subject Focus|Focus Topic|Target Role):\s*([^\n\r]+)", user_prompt, re.IGNORECASE)
        candidate_text = ((subject_m.group(1) if subject_m else "") + " " + target_role + " " + user_prompt).lower()

        matched_bp = None
        for bp_key, bp_data in CSE_40_INTERVIEW_BLUEPRINTS.items():
            if bp_key in candidate_text:
                matched_bp = bp_data
                break

        if matched_bp:
            q3 = GeneratedMockQuestion(
                topic=matched_bp["topic"],
                question_text=matched_bp["question"],
                expected_key_points=matched_bp["key_points"],
                model_answer=matched_bp["model_answer"],
                difficulty_hint=difficulty,
            )
            q4 = GeneratedMockQuestion(
                topic=f"{matched_bp['topic']} - System Trade-offs",
                question_text=f"In production architectures utilizing {matched_bp['topic']}, describe the most critical latency, security, or consistency trade-offs you must navigate.",
                expected_key_points=["Asymptotic complexity and throughput constraints", "Failure mode isolation and monitoring metrics", "Testing and verification methodology"],
                model_answer=f"Articulate how {matched_bp['topic']} interfaces with surrounding infrastructure, outline specific monitoring signals (error rates, saturation), and explain fallback/circuit-breaker behavior.",
                difficulty_hint=difficulty,
            )
            q5 = GeneratedMockQuestion(
                topic=f"{matched_bp['topic']} - Edge Case & Failure Analysis",
                question_text=f"Walk through how you would diagnose and resolve an intermittent failure or performance degradation specifically within {matched_bp['topic']} under high concurrent scale.",
                expected_key_points=["Root-cause isolation via telemetry/profiling", "Reproducible testing harness", "Preventive architecture safeguards"],
                model_answer=f"Profile hot paths, isolate contention or unindexed lookups, reproduce with synthetic load, and deploy an automated regression safeguard.",
                difficulty_hint=difficulty,
            )
        else:
            # Software / Computer Science default
            q3 = GeneratedMockQuestion(
                topic="Algorithms & Problem Solving",
                question_text=f"Walk through how you would detect duplicate or conflicting records in a high-volume stream cleanly. Which data structures give optimal asymptotic bounds?",
                expected_key_points=["Hash-based vs sorted comparison", "Big-O time and memory complexity", "Handling skewed distributions or collisions"],
                model_answer="Use a hash set for O(1) average lookup / O(n) total time when memory fits; fall back to external sorting or partitioned hashing when datasets exceed RAM.",
                difficulty_hint=difficulty,
            )
            q4 = GeneratedMockQuestion(
                topic="API Reliability & Debugging",
                question_text=f"Suppose an endpoint supporting {target_role} workflows starts timing out intermittently in production. Describe your step-by-step root-cause investigation.",
                expected_key_points=["Reproducing and isolating metrics/logs", "Checking DB locks, N+1 queries, external timeouts", "Verification and regression prevention"],
                model_answer="Correlate latency spikes with logs and DB query telemetry, check lock contention or slow downstream calls, fix the bottleneck, and add automated regression checks.",
                difficulty_hint=difficulty,
            )
            q5 = GeneratedMockQuestion(
                topic="Concurrency & Failure Recovery",
                question_text="Explain how idempotency and optimistic or pessimistic locking prevent duplicate state changes when two requests arrive concurrently.",
                expected_key_points=["Race condition mechanics", "Row locks or version columns", "Idempotency keys for safe retries"],
                model_answer="Bind state transitions to database row locks (`FOR UPDATE`) or version checks inside a transaction, and require idempotency keys on non-idempotent POST actions.",
                difficulty_hint=difficulty,
            )

    bank: Dict[str, List[GeneratedMockQuestion]] = {
        "technical": [
            GeneratedMockQuestion(
                topic=f"{primary_skill} Core Concepts",
                question_text=f"For a {target_role} position at the {difficulty} level, explain a {diff_prefix} problem you would solve using {primary_skill} and how you ensure correctness and maintainability.",
                expected_key_points=[f"Core mechanics of {primary_skill}", "Time/space or execution trade-offs", "Error handling and testing strategy"],
                model_answer=f"A strong response defines the core mechanism of {primary_skill}, contrasts two implementation choices with concrete complexity or latency trade-offs, and outlines validation/unit testing.",
                difficulty_hint=difficulty,
            ),
            GeneratedMockQuestion(
                topic=f"{secondary_skill} & Data Layer",
                question_text=f"How would you design data modeling, indexing, and query optimization around {secondary_skill} under growing campus or production traffic?",
                expected_key_points=["Schema normalization or access patterns", "Indexing trade-offs (read vs write)", "Handling concurrency or transactions"],
                model_answer="Identify primary query paths first, add composite indexes aligned with filter/sort predicates, wrap multi-step writes in ACID transactions, and verify execution plans.",
                difficulty_hint=difficulty,
            ),
            q3,
            q4,
            q5,
        ],
        "project_based": [
            GeneratedMockQuestion(
                topic=f"Architecture: {primary_project}",
                question_text=f"Walk me through {primary_project} from end to end: what problem did it solve, why did you choose that architecture, and what was your personal contribution?",
                expected_key_points=["Clear problem statement and user flow", "Tech stack rationale", "Specific personal ownership and measurable outcomes"],
                model_answer="Open with the problem scope, summarize the high-level components cleanly, explain why key libraries or schemas were chosen over alternatives, and highlight what you built directly.",
                difficulty_hint=difficulty,
            ),
            GeneratedMockQuestion(
                topic="Technical Bottleneck & Trade-Offs",
                question_text=f"What was the hardest bug, performance issue, or design compromise you encountered while building {primary_project}, and how did you resolve it?",
                expected_key_points=["Root cause analysis", "Alternatives weighed", "Verification after the fix"],
                model_answer="Describe a concrete bug or bottleneck, explain diagnostic steps rather than guesswork, show why the chosen fix worked, and state what tests or safeguards prevent recurrence.",
                difficulty_hint=difficulty,
            ),
            GeneratedMockQuestion(
                topic="Scalability & Security Hardening",
                question_text=f"If {primary_project} suddenly grew to 50x its current usage and faced untrusted input, what three architectural or security upgrades would you implement first?",
                expected_key_points=["Authentication/input validation", "Caching, indexing, or async queues", "Monitoring and failure isolation"],
                model_answer="Enforce strict input validation and authorization boundaries, index hot query paths or cache read-heavy endpoints, and offload heavy work to asynchronous queues.",
                difficulty_hint=difficulty,
            ),
            GeneratedMockQuestion(
                topic="Testing & Code Quality",
                question_text=f"How did you validate correctness in {primary_project}, and what edge cases were easiest to overlook initially?",
                expected_key_points=["Unit vs integration boundaries", "Boundary/null/error test cases", "Continuous verification workflow"],
                model_answer="Combine fast unit tests for pure business logic with integration tests around API permissions, empty states, and invalid payloads.",
                difficulty_hint=difficulty,
            ),
        ],
        "behavioral": [
            GeneratedMockQuestion(
                topic="Ownership Under Ambiguity (STAR)",
                question_text=f"Tell me about a time you faced unclear requirements or a shifting deadline on a team deliverable for a {target_role}-style task. What actions did you take and what changed?",
                expected_key_points=["Situation & Task clarity", "Proactive communication and scoping", "Concrete Result and takeaway"],
                model_answer="Use STAR: frame the ambiguous deadline concisely, explain how you broke tasks down and aligned stakeholders early, quantify the delivery outcome, and note one lasting lesson.",
                difficulty_hint=difficulty,
            ),
            GeneratedMockQuestion(
                topic="Resolving Technical Disagreement",
                question_text="Describe a situation where a teammate disagreed with your proposed technical or process approach. How did you handle it constructively?",
                expected_key_points=["Active listening without ego", "Evidence-based comparison of trade-offs", "Consensus and team outcome"],
                model_answer="Focus on objective criteria (latency, complexity, timeline), test or prototype the competing options if needed, and align behind the best team decision.",
                difficulty_hint=difficulty,
            ),
            GeneratedMockQuestion(
                topic="Learning From Mistakes",
                question_text="Share an example of a mistake or missed edge case in a project or coursework. How did you take accountability and prevent a repeat?",
                expected_key_points=["Honest ownership without blaming others", "Immediate remediation", "Systemic safeguard introduced"],
                model_answer="State the mistake directly, describe how you communicated and fixed it promptly, and highlight a checklist, test, or review practice added afterward.",
                difficulty_hint=difficulty,
            ),
            GeneratedMockQuestion(
                topic="Prioritization & Time Pressure",
                question_text="Tell me about a period when you balanced competing exams, projects, or hackathon deadlines. How did you prioritize?",
                expected_key_points=["Triage framework (impact vs urgency)", "Scope management", "Outcome achieved"],
                model_answer="Explain how you ranked deliverables by deadline and dependency risk, cut non-essential scope early, and maintained consistent daily checkpoints.",
                difficulty_hint=difficulty,
            ),
        ],
        "hr": [
            GeneratedMockQuestion(
                topic=f"Motivation for {target_role}",
                question_text=f"Why are you interested in a {target_role} role, and how do your verified skills in {primary_skill} align with what teams need on day one?",
                expected_key_points=["Clear alignment between verified background and role", "Knowledge of responsibilities", "Growth mindset"],
                model_answer=f"Connect your verified coursework and project work in {primary_skill} directly to the day-to-day responsibilities of a {target_role}, showing enthusiasm and realistic career goals.",
                difficulty_hint=difficulty,
            ),
            GeneratedMockQuestion(
                topic="Strengths & Development Areas",
                question_text="What do you consider your strongest professional capability right now, and what is one skill area you are actively improving ahead of campus placements?",
                expected_key_points=["Evidence-backed strength", "Honest non-cliche growth area", "Concrete current action plan"],
                model_answer="Pair a genuine strength with a concrete example, then share an authentic improvement area alongside specific weekly practice steps already underway.",
                difficulty_hint=difficulty,
            ),
            GeneratedMockQuestion(
                topic="Team Culture & Feedback",
                question_text="What kind of engineering or workplace environment helps you do your best work, and how do you respond to critical code or performance feedback?",
                expected_key_points=["Collaborative culture fit", "Receptiveness to constructive feedback", "Examples of growth from critique"],
                model_answer="Emphasize structured mentorship, clear ownership, and treating feedback as actionable signal rather than personal criticism.",
                difficulty_hint=difficulty,
            ),
            GeneratedMockQuestion(
                topic="Career Trajectory",
                question_text="Where do you hope to grow technically and professionally over your first 12 to 18 months after graduating?",
                expected_key_points=["Realistic first-year milestones", "Reliability before scope expansion", "Continuous learning habit"],
                model_answer="Focus on mastering core codebase conventions within 90 days, owning production features reliably within a year, and mentoring newer peers.",
                difficulty_hint=difficulty,
            ),
        ],
        "aptitude": [
            GeneratedMockQuestion(
                topic="Quantitative Ratio & Rate Logic",
                question_text="Two microservices process a shared batch queue: Service A alone finishes the batch in 12 minutes, while Service A and Service B together finish in 4 minutes. How long does Service B take alone, and how do you verify it?",
                expected_key_points=["Work rate formulation (1/12 + 1/B = 1/4)", "Arithmetic accuracy (B = 6 minutes)", "Sanity check"],
                model_answer="Combined rate is 1/4 batch/min. Service A is 1/12 batch/min, so Service B = 1/4 - 1/12 = 2/12 = 1/6 batch/min -> 6 minutes alone.",
                difficulty_hint=difficulty,
            ),
            GeneratedMockQuestion(
                topic="Probability & Conditional Reasoning",
                question_text="In a campus test suite, 80% of valid submissions pass automated lint and 10% of buggy submissions still pass lint. If 70% of all submissions are valid, what is the probability a submission that passed lint is actually valid?",
                expected_key_points=["Bayes' theorem setup", "Numerator: 0.7 * 0.8 = 0.56", "Denominator: 0.56 + 0.3 * 0.1 = 0.59 -> ~94.9%"],
                model_answer="Using Bayes' rule: P(Valid | Pass) = (0.70 × 0.80) / [(0.70 × 0.80) + (0.30 × 0.10)] = 0.56 / 0.59 ≈ 94.92%.",
                difficulty_hint=difficulty,
            ),
            GeneratedMockQuestion(
                topic="Logical Deduction & Scheduling",
                question_text="Four interview panels (P, Q, R, S) run consecutively. R runs immediately before S, P cannot run first, and Q runs before R. Determine all valid orders and explain your elimination steps.",
                expected_key_points=["Treating (R, S) as an adjacent block", "Applying Q before RS constraint", "Checking all placements for P != 1st -> Q, P, R, S and Q, R, S, P"],
                model_answer="Group (R,S). Since Q precedes R and P cannot be 1st, the first slot must be Q. Remaining slots place P anywhere among {2nd, 4th}, yielding (Q, P, R, S) and (Q, R, S, P).",
                difficulty_hint=difficulty,
            ),
            GeneratedMockQuestion(
                topic="Permutations & Edge Constraints",
                question_text="How many distinct 4-character access codes can be formed using digits 1–6 without repetition if the code must be even and cannot start with 1?",
                expected_key_points=["Fixing last digit as even ({2,4,6})", "Case split or careful counting when first digit excludes 1 and last digit", "Exact final count (144)"],
                model_answer="Last digit has 3 choices {2,4,6} (all != 1). For each, first digit cannot be 1 or the last digit -> 4 choices. Remaining two middle positions have 4 × 3 = 12 choices. Total = 3 × 4 × 4 × 3 = 144.",
                difficulty_hint=difficulty,
            ),
        ],
    }

    pool = bank.get(category, bank["technical"])
    selected: List[GeneratedMockQuestion] = []
    for idx in range(count):
        base_q = pool[idx % len(pool)]
        if idx < len(pool):
            selected.append(base_q)
        else:
            selected.append(
                GeneratedMockQuestion(
                    topic=f"{base_q.topic} (Scenario {idx + 1})",
                    question_text=f"Applying {primary_skill} and {secondary_skill} in a {target_role} setting: {base_q.question_text}",
                    expected_key_points=base_q.expected_key_points,
                    model_answer=base_q.model_answer,
                    difficulty_hint=difficulty,
                )
            )
    return GeneratedInterviewPlan(questions=selected)


def synthesize_mock_followup(user_prompt: str) -> FollowUpDecisionAIOutput:
    ans = _extract_tag(user_prompt, "CANDIDATE_ANSWER", "")
    topic = _extract_tag(user_prompt, "QUESTION_TOPIC", "the current topic")
    category = _extract_tag(user_prompt, "CATEGORY", "technical").lower()

    word_count = len(ans.split())
    if word_count < 8:
        return FollowUpDecisionAIOutput(
            should_ask_followup=True,
            rationale="Answer was quite brief; prompting for concrete reasoning and an example.",
            followup_question=GeneratedMockQuestion(
                topic=f"Follow-Up: {topic}",
                question_text=f"Could you expand on your previous response with a concrete example, edge case, or measurable outcome related to {topic}?",
                expected_key_points=["Concrete example or metric", "Reasoning behind choices", "Handling edge cases"],
                model_answer="Illustrate the core point with one specific scenario, explain why that approach worked, and mention any limitation or edge case.",
                difficulty_hint="intermediate",
            ),
        )
    if word_count <= 45 and category in ("technical", "project_based", "behavioral"):
        return FollowUpDecisionAIOutput(
            should_ask_followup=True,
            rationale="Probing deeper into trade-offs and failure handling.",
            followup_question=GeneratedMockQuestion(
                topic=f"Deep Dive: {topic}",
                question_text=f"Following up on your answer: what trade-offs or failure scenarios would you monitor closely if this had to scale or run under strict constraints?",
                expected_key_points=["Explicit trade-off comparison", "Failure mode identification", "Mitigation or monitoring step"],
                model_answer="Name the primary bottleneck or failure risk introduced by your approach, explain how to detect it early, and describe a practical fallback.",
                difficulty_hint="intermediate",
            ),
        )
    return FollowUpDecisionAIOutput(should_ask_followup=False, followup_question=None, rationale=None)


def synthesize_mock_evaluation(user_prompt: str) -> MockInterviewEvaluationAIOutput:
    cat_m = re.search(r"Category:\s*(\w+)", user_prompt, re.IGNORECASE)
    category = (cat_m.group(1).lower() if cat_m else "technical").strip()

    q_blocks = re.findall(
        r'<Q_ITEM\s+order="(\d+)"\s+topic="(.*?)"\s+is_followup="(.*?)">(.*?)</Q_ITEM>',
        user_prompt,
        re.DOTALL,
    )

    question_evals: List[QuestionEvaluationAIItem] = []
    all_strengths: List[str] = []
    all_weaknesses: List[str] = []

    for order_str, topic, _is_fu, body in q_blocks:
        order = int(order_str)
        ans_m = re.search(r"<ANSWER>(.*?)</ANSWER>", body, re.DOTALL)
        model_m = re.search(r"<MODEL_ANSWER>(.*?)</MODEL_ANSWER>", body, re.DOTALL)
        kp_m = re.search(r"<KEY_POINTS>(.*?)</KEY_POINTS>", body, re.DOTALL)

        ans_text = (ans_m.group(1).strip() if ans_m else "").strip()
        model_ans = (model_m.group(1).strip() if model_m else "Provide a structured explanation covering core principles, trade-offs, and validation.").strip()
        key_points_text = (kp_m.group(1).strip() if kp_m else "")

        if not ans_text or ans_text == "[UNANSWERED]":
            scores = CriteriaBreakdownScores(
                technical_correctness=0.0,
                conceptual_understanding=0.0,
                problem_solving_approach=0.0,
                communication_clarity=0.0,
                answer_structure=0.0,
                relevance=0.0,
                project_knowledge=0.0 if category == "project_based" else None,
            )
            question_evals.append(
                QuestionEvaluationAIItem(
                    question_order=order,
                    score=0.0,
                    criteria_scores=scores,
                    feedback="No answer was submitted for this question before ending the session.",
                    strengths=[],
                    weaknesses=["Question left unanswered."],
                    improvement_tip=f"Practice answering {topic} prompts concisely before moving on.",
                    model_answer=model_ans,
                )
            )
            continue

        words = ans_text.split()
        w_len = len(words)
        lower_ans = ans_text.lower()
        kp_tokens = [t for t in re.split(r"[\s,;:|]+", key_points_text.lower()) if len(t) >= 4]
        overlap_hits = sum(1 for t in set(kp_tokens) if t in lower_ans)
        overlap_ratio = min(1.0, overlap_hits / max(1, min(6, len(set(kp_tokens)))))

        length_factor = min(1.0, w_len / 55.0)
        structure_bonus = 10.0 if any(m in lower_ans for m in ("first", "second", "because", "therefore", "trade-off", "result", "example", "1.", "- ")) else 0.0

        base = 38.0 + (34.0 * length_factor) + (20.0 * overlap_ratio) + structure_bonus
        base = max(18.0, min(94.0, round(base, 1)))

        tech = round(min(98.0, base + (3.0 if overlap_ratio > 0.3 else -4.0)), 1)
        concept = round(min(98.0, base + 1.5), 1)
        problem = round(min(98.0, base - (3.0 if w_len < 15 else 0.0)), 1)
        comm = round(min(98.0, base + (4.0 if w_len >= 18 else -6.0)), 1)
        struct = round(min(98.0, base + (5.0 if structure_bonus > 0 else -5.0)), 1)
        rel = round(min(98.0, max(30.0, base + (4.0 if w_len >= 10 else -8.0))), 1)
        proj = round(min(98.0, base), 1) if category in ("project_based", "technical") else None

        q_score = round((tech + concept + problem + comm + struct + rel + (proj if proj is not None else 0.0)) / (7.0 if proj is not None else 6.0), 1)

        q_strengths = []
        q_weaknesses = []
        if w_len >= 20:
            q_strengths.append(f"Provided substantive explanation on {topic}.")
        if structure_bonus > 0:
            q_strengths.append("Used logical structure or causal reasoning markers.")
        if not q_strengths:
            q_strengths.append("Directly attempted the prompt.")

        if w_len < 20:
            q_weaknesses.append("Response was brief; lacked deeper reasoning, examples, or edge cases.")
        if overlap_ratio < 0.25:
            q_weaknesses.append("Missed several expected technical or conceptual checkpoints.")
        if structure_bonus == 0:
            q_weaknesses.append("Could improve structure (e.g., step-by-step breakdown or STAR framing).")

        all_strengths.extend(q_strengths)
        all_weaknesses.extend(q_weaknesses)

        question_evals.append(
            QuestionEvaluationAIItem(
                question_order=order,
                score=q_score,
                criteria_scores=CriteriaBreakdownScores(
                    technical_correctness=tech,
                    conceptual_understanding=concept,
                    problem_solving_approach=problem,
                    communication_clarity=comm,
                    answer_structure=struct,
                    relevance=rel,
                    project_knowledge=proj,
                ),
                feedback=(
                    f"Strong structured coverage of {topic}."
                    if q_score >= 75
                    else f"Partial coverage of {topic}; strengthen precision, trade-offs, and concrete examples."
                ),
                strengths=q_strengths,
                weaknesses=q_weaknesses,
                improvement_tip=f"Include explicit trade-offs and a concrete verification step when discussing {topic}.",
                model_answer=model_ans,
            )
        )

    if not question_evals:
        empty_criteria = CriteriaBreakdownScores(
            technical_correctness=0.0,
            conceptual_understanding=0.0,
            problem_solving_approach=0.0,
            communication_clarity=0.0,
            answer_structure=0.0,
            relevance=0.0,
            project_knowledge=0.0 if category == "project_based" else None,
        )
        return MockInterviewEvaluationAIOutput(
            overall_score=0.0,
            criteria_scores=empty_criteria,
            question_evaluations=[],
            strengths=[],
            weaknesses=["No answered questions were available to evaluate."],
            suggested_improvements=["Complete at least a few interview prompts before submitting for evaluation."],
            recommended_topics=["Core Problem Solving", "Structured Communication (STAR)"],
            executive_summary="No answers were recorded in this session.",
            advisory_disclaimer=ADVISORY_MOCK_INTERVIEW_DISCLAIMER,
        )

    def _avg(vals: List[float]) -> float:
        return round(sum(vals) / max(1, len(vals)), 1)

    agg_tech = _avg([q.criteria_scores.technical_correctness for q in question_evals])
    agg_concept = _avg([q.criteria_scores.conceptual_understanding for q in question_evals])
    agg_prob = _avg([q.criteria_scores.problem_solving_approach for q in question_evals])
    agg_comm = _avg([q.criteria_scores.communication_clarity for q in question_evals])
    agg_struct = _avg([q.criteria_scores.answer_structure for q in question_evals])
    agg_rel = _avg([q.criteria_scores.relevance for q in question_evals])
    proj_vals = [q.criteria_scores.project_knowledge for q in question_evals if q.criteria_scores.project_knowledge is not None]
    agg_proj = _avg(proj_vals) if proj_vals else None
    overall = round(sum(q.score for q in question_evals) / len(question_evals), 1)

    dedup_strengths = list(dict.fromkeys(all_strengths))[:4]
    dedup_weaknesses = list(dict.fromkeys(all_weaknesses))[:4]
    rec_topics = [q.feedback for q in question_evals[:2]]
    topics_clean = []
    for order_str, topic, _, _ in q_blocks:
        q_item = next((x for x in question_evals if x.question_order == int(order_str)), None)
        if q_item and q_item.score < 78 and topic not in topics_clean:
            topics_clean.append(topic)
    if not topics_clean:
        topics_clean = ["System Trade-Off Analysis", "Concise STAR Storytelling"]

    return MockInterviewEvaluationAIOutput(
        overall_score=overall,
        criteria_scores=CriteriaBreakdownScores(
            technical_correctness=agg_tech,
            conceptual_understanding=agg_concept,
            problem_solving_approach=agg_prob,
            communication_clarity=agg_comm,
            answer_structure=agg_struct,
            relevance=agg_rel,
            project_knowledge=agg_proj,
        ),
        question_evaluations=question_evals,
        strengths=dedup_strengths or ["Completed practice prompts consistently."],
        weaknesses=dedup_weaknesses or ["Can add deeper quantitative evidence and edge-case analysis."],
        suggested_improvements=[
            "Lead with a 1-sentence thesis before diving into implementation or project details.",
            "Explicitly mention time/space complexity, failure modes, or measurable outcomes in every answer.",
            "Compare against the advisory model answers below and re-attempt a higher difficulty round.",
        ],
        recommended_topics=topics_clean[:4],
        executive_summary=(
            f"Completed {len(question_evals)} {category.replace('_', ' ')} interview questions with an overall advisory score of {overall}/100. "
            f"Strongest dimension: {'Communication Clarity' if agg_comm >= agg_tech else 'Technical Correctness'}; "
            f"focus next on structured trade-offs and depth."
        ),
        advisory_disclaimer=ADVISORY_MOCK_INTERVIEW_DISCLAIMER,
    )

