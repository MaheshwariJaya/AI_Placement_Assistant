"""Deterministic offline recommendation generator for MockAIProvider."""
import re
from typing import List

from app.schemas.readiness import (
    AIRecommendationSuggestion,
    ReadinessRecommendationsAIOutput,
)


def _extract_tag(prompt: str, tag: str) -> str:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", prompt, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def generate_mock_readiness_recommendations(user_prompt: str) -> ReadinessRecommendationsAIOutput:
    """Build grounded, actionable preparation suggestions from indicator & skill-gap context."""
    missing_mand = _extract_tag(user_prompt, "MISSING_MANDATORY_SKILLS")
    missing_pref = _extract_tag(user_prompt, "MISSING_PREFERRED_SKILLS")
    weak_indicators = _extract_tag(user_prompt, "WEAK_OR_MISSING_INDICATORS")
    target_role = _extract_tag(user_prompt, "TARGET_ROLE") or "campus placement roles"
    student_dept = _extract_tag(user_prompt, "STUDENT_DEPARTMENT").lower()

    suggestions: List[AIRecommendationSuggestion] = []

    # Branch-specific project & technical topics
    if "civil" in student_dept:
        proj_title = "Complete a Capstone or Structural/Civil Design Project"
        proj_desc = f"Deliver a core engineering design project relevant to {target_role} (e.g. AutoCAD/STAAD.Pro seismic analysis, soil stabilization, or highway geometric design) with full calculation sheets."
        assess_desc = "Attempt at least two Aptitude and Technical sessions in the Preparation Arena to benchmark Structural Analysis, Geotechnical principles, and quantitative speed."
    elif "mech" in student_dept:
        proj_title = "Complete a Mechanical Design or Thermal Simulation Project"
        proj_desc = f"Deliver a CAD/CAM or thermal simulation capstone relevant to {target_role} (e.g. SolidWorks/Ansys stress simulation, IC engine cycle analysis, or CFD pipe flow) with documented engineering trade-offs."
        assess_desc = "Attempt at least two Aptitude and Technical sessions in the Preparation Arena to benchmark Thermodynamics, Fluid Mechanics, Strength of Materials, and quantitative speed."
    elif "electr" in student_dept and "comm" not in student_dept:
        proj_title = "Complete a Power Systems or Electrical Machine Project"
        proj_desc = f"Deliver an electrical engineering project relevant to {target_role} (e.g. MATLAB/Simulink motor drive simulation, power system fault analysis, or buck-boost converter prototype) with clear waveforms."
        assess_desc = "Attempt at least two Aptitude and Technical sessions in the Preparation Arena to benchmark Electrical Machines, Power Systems, Circuit Theory, and quantitative speed."
    elif "ece" in student_dept or "comm" in student_dept:
        proj_title = "Complete an Embedded Systems or VLSI Design Project"
        proj_desc = f"Deliver a hardware/embedded project relevant to {target_role} (e.g. ARM/ESP32 sensor interface, Verilog HDL digital module, or Op-Amp active filter) with documented schematic and timing diagrams."
        assess_desc = "Attempt at least two Aptitude and Technical sessions in the Preparation Arena to benchmark Digital Electronics, Analog Circuits, Signals, and quantitative speed."
    elif "chem" in student_dept:
        proj_title = "Complete a Chemical Process Simulation or Reactor Project"
        proj_desc = f"Deliver a chemical engineering project relevant to {target_role} (e.g. Aspen/DWSIM distillation column simulation, continuous reactor kinetic study, or heat exchanger network) with mass-energy balances."
        assess_desc = "Attempt at least two Aptitude and Technical sessions in the Preparation Arena to benchmark Reaction Engineering, Mass Transfer, Heat Transfer, and quantitative speed."
    else:
        proj_title = "Complete and Document a Capstone or Domain Project"
        proj_desc = f"Deliver an end-to-end project relevant to {target_role} with clear architecture notes, source repository, and measurable performance benchmarks."
        assess_desc = "Attempt at least two Aptitude and Technical sessions in the Preparation Arena to benchmark core discipline concepts, logic, and quantitative speed."

    if missing_mand and missing_mand.lower() != "none":
        top_skills = ", ".join([s.strip() for s in missing_mand.split(",") if s.strip()][:3])
        suggestions.append(
            AIRecommendationSuggestion(
                title=f"Close Mandatory Skill Gaps ({top_skills})",
                description=(
                    f"Practice hands-on problems and build a focused module using {top_skills} tailored to {target_role}, "
                    f"then record verified skill evidence in your portfolio."
                ),
                category="skills",
                priority="high",
                estimated_impact="+8 to +15 pts on skill & role alignment",
            )
        )

    weak_lower = weak_indicators.lower()
    if "resume" in weak_lower:
        suggestions.append(
            AIRecommendationSuggestion(
                title="Strengthen & Approve Resume Project Descriptions",
                description=(
                    "Upload an updated PDF/DOCX resume with quantified STAR project bullets (problem, architecture, outcome), "
                    "and review Resume Intelligence suggestions before campus drives."
                ),
                category="resume",
                priority="high",
                estimated_impact="+7 to +12 pts on resume completeness",
            )
        )

    if "project" in weak_lower:
        suggestions.append(
            AIRecommendationSuggestion(
                title=proj_title,
                description=proj_desc,
                category="projects",
                priority="high",
                estimated_impact="+6 to +12 pts on project portfolio",
            )
        )

    if "aptitude" in weak_lower or "assessment" in weak_lower:
        suggestions.append(
            AIRecommendationSuggestion(
                title="Complete Timed Aptitude & Technical Assessments",
                description=assess_desc,
                category="aptitude",
                priority="medium",
                estimated_impact="+5 to +10 pts on assessment readiness",
            )
        )

    if "interview" in weak_lower:
        suggestions.append(
            AIRecommendationSuggestion(
                title="Practice Behavioral & Project-Based Mock Interviews",
                description=(
                    "Complete structured STAR behavioral and project deep-dive rounds in Interview Studio to improve "
                    "answer structure, clarity, and trade-off explanations."
                ),
                category="interview",
                priority="medium",
                estimated_impact="+5 to +10 pts on interview readiness",
            )
        )

    if "certif" in weak_lower or (missing_pref and missing_pref.lower() != "none"):
        pref_text = f" ({missing_pref[:80]})" if (missing_pref and missing_pref.lower() != "none") else ""
        suggestions.append(
            AIRecommendationSuggestion(
                title="Earn or Record Relevant Technical Certifications",
                description=(
                    f"Add verifiable cloud, database, or core engineering credentials{pref_text} with credential URLs "
                    "to reinforce domain depth."
                ),
                category="certifications",
                priority="low",
                estimated_impact="+3 to +6 pts on certification profile",
            )
        )

    if "profile" in weak_lower or not suggestions:
        suggestions.append(
            AIRecommendationSuggestion(
                title="Complete Technical Profile & Portfolio Links",
                description=(
                    "Ensure your GitHub, LinkedIn, portfolio link, and contact details are up to date and align with your resume."
                ),
                category="profile",
                priority="medium",
                estimated_impact="+4 to +8 pts on profile completeness",
            )
        )

    if len(suggestions) < 3:
        suggestions.append(
            AIRecommendationSuggestion(
                title="Strengthen DSA & SQL Query Fundamentals",
                description=(
                    "Solve timed core data-structure and relational database indexing exercises weekly and explain time/space "
                    "trade-offs aloud during mock practice."
                ),
                category="skills",
                priority="medium",
                estimated_impact="Builds consistent interview readiness",
            )
        )

    return ReadinessRecommendationsAIOutput(recommendations=suggestions[:6])

