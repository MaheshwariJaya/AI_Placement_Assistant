"""
[ISOLATED DEVELOPMENT SEEDER - NOT FOR PRODUCTION STARTUP]
Comprehensive synthetic dataset seeder for the AI-Powered Placement Intelligence System.
Populates:
  - Exactly 100 diverse students across 10 engineering departments with full profiles,
    skills, projects, experiences, certifications, education, and approved resumes.
  - Exactly 100 diverse corporate companies across 12 distinct industries with associated
    recruiter accounts.
  - Diverse campus job postings (~150 jobs) with branch-aware eligibility, skill weights,
    and CTCs.
  - Institutional campus placement drive coordinating drive jobs.
  - Exactly 305 realistic application histories mapped to the official state machine
    (Applied, Under Review, Shortlisted, Interview Scheduled, Interviewed, Offered,
     Offer Accepted, Offer Declined, Rejected, Withdrawn).
  - Linked Interview rounds and CandidateEvaluations.
  - Preparation Arena attempts and ReadinessSnapshots.

Usage:
  python backend/scripts/seed_diverse_dataset.py
  (or via clean script: python backend/scripts/clean_diverse_dataset.py)
"""
import asyncio
import hashlib
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, "backend")

from sqlalchemy import delete, func, select
from app.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.arena import ArenaAssessmentMode, ArenaAttempt, ArenaAttemptStatus, ArenaCategory
from app.models.candidate_evaluation import (
    CandidateEvaluation,
    EvaluationRecommendation,
    EvaluationStage,
)
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
    ApplicationStatusHistory,
    DecisionDomain,
    DriveLifecyclePhase,
    DriveMode,
    DriveStatus,
    Interview,
    InterviewMode,
    InterviewOutcome,
    InterviewStatus,
    JobApplication,
    PlacementDrive,
    PlacementDriveJob,
    TpoScreeningStatus,
)
from app.models.readiness import ReadinessCategory, ReadinessSnapshot
from app.models.resume import Resume
from app.models.student import (
    StudentCertification,
    StudentEducation,
    StudentExperience,
    StudentProfile,
    StudentProject,
    StudentSkill,
)
from app.models.user import User, UserRole
from app.services.eligibility_service import evaluate_student_job_eligibility
from app.services.matching_engine import calculate_compatibility_score

import os

settings = get_settings()
app_env = getattr(settings, "APP_ENV", os.getenv("APP_ENV", "development")).lower()

if app_env == "production":
    print("FATAL: Synthetic dataset seeder refused to execute in PRODUCTION environment.")
    sys.exit(1)

PASSWORD_HASH = hash_password("DemoPassword2026!")

# -----------------------------------------------------------------------------
# Name Banks
# -----------------------------------------------------------------------------
FIRST_NAMES = [
    "Aarav", "Aditi", "Aditya", "Akash", "Ananya", "Ankit", "Anushka", "Arjun", "Ayush", "Bhavya",
    "Chaitanya", "Deepak", "Divya", "Gaurav", "Harsh", "Ishaan", "Jaya", "Karan", "Kavya", "Khushi",
    "Kunal", "Manish", "Mayank", "Meera", "Mohit", "Naveen", "Neha", "Nikhil", "Nisha", "Pooja",
    "Pranav", "Pratik", "Priya", "Rahul", "Rakesh", "Riya", "Rohan", "Rohit", "Sakshi", "Sameer",
    "Sanjay", "Saurabh", "Shikha", "Shivam", "Shreya", "Siddharth", "Simran", "Sneha", "Suraj", "Swati",
    "Tanmay", "Tarun", "Utkarsh", "Vaibhav", "Varun", "Vedant", "Vikas", "Vikram", "Vinay", "Vishal",
    "Yash", "Yuvraj", "Aayush", "Abhishek", "Aman", "Amita", "Aniket", "Archana", "Ashish", "Avani",
    "Barkha", "Bharat", "Chirag", "Darshan", "Devendra", "Disha", "Girish", "Himanshu", "Inder", "Jitendra",
    "Kamal", "Keshav", "Lalit", "Madhav", "Manas", "Mukul", "Nandini", "Omkar", "Pankaj", "Parth",
    "Payal", "Pradeep", "Praveen", "Rachit", "Rajesh", "Ritu", "Sanchit", "Satish", "Shubham", "Tejas",
    "Alok", "Amit", "Anita", "Anjali", "Bipin", "Chetan", "Deepika", "Garima", "Geeta", "Hemant"
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Malhotra", "Mehta", "Singh", "Patel", "Joshi", "Bhatia", "Reddy",
    "Chauhan", "Agarwal", "Bansal", "Mishra", "Pandey", "Saxena", "Trivedi", "Deshmukh", "Kulkarni", "Iyer",
    "Nair", "Rao", "Choudhary", "Rathore", "Bishnoi", "Gehlot", "Solanki", "Shekhawat", "Purohit", "Dave",
    "Dubey", "Shukla", "Pandita", "Venkatesh", "Nambiar", "Mukherjee", "Chatterjee", "Banerjee", "Bose", "Dutta"
]

# -----------------------------------------------------------------------------
# 100 Companies Specifications across 12 Industries
# -----------------------------------------------------------------------------
COMPANY_TEMPLATES = [
    # 1. IT and Software Development (20 companies)
    ("Nexus Cloud Systems", "IT and Software Development", "Enterprise cloud orchestration and distributed microservices infrastructure.", "1000+ employees", "Bengaluru"),
    ("Algorise Solutions", "IT and Software Development", "Scalable backend distributed architectures and database replication platforms.", "500-1000 employees", "Hyderabad"),
    ("CodeCraft Global", "IT and Software Development", "Full stack enterprise engineering and reactive web applications.", "200-500 employees", "Pune"),
    ("Starlight Infotech", "IT and Software Development", "Modern digital transformation, API management, and middleware systems.", "1000+ employees", "Gurugram"),
    ("PixelPulse Technologies", "IT and Software Development", "High-throughput frontend frameworks and design system engineering.", "100-200 employees", "Bengaluru"),
    ("Vortex Data Labs", "IT and Software Development", "Real-time streaming pipelines, Kafka streaming, and analytics infrastructure.", "200-500 employees", "Hyderabad"),
    ("HyperScale Tech", "IT and Software Development", "SaaS platforms, multi-tenant billing engines, and low-latency APIs.", "500-1000 employees", "Noida"),
    ("Zenith Software Works", "IT and Software Development", "Mission-critical logistics and supply chain optimization software.", "200-500 employees", "Chennai"),
    ("OmniApp Digital", "IT and Software Development", "Cross-platform mobile applications and progressive web interfaces.", "50-100 employees", "Pune"),
    ("Prism Logic Systems", "IT and Software Development", "Core operating tools, developer productivity CLI, and build toolchains.", "100-200 employees", "Bengaluru"),
    ("BlueShift Technologies", "IT and Software Development", "Serverless architectures, edge computing networks, and CDN accelerators.", "200-500 employees", "Hyderabad"),
    ("Apex Dynamic Solutions", "IT and Software Development", "Workflow automation, distributed locks, and enterprise CRM backends.", "500-1000 employees", "Gurugram"),
    ("VectorDot Systems", "IT and Software Development", "Modern web applications, GraphQL gateways, and scalable architectures.", "100-200 employees", "Mumbai"),
    ("BitWave Networks", "IT and Software Development", "High-performance network protocol stacks and telematics software.", "200-500 employees", "Bengaluru"),
    ("Syncora Technologies", "IT and Software Development", "Data synchronization engines, offline-first mobile databases, and sync tools.", "50-100 employees", "Pune"),
    ("Quantix Software", "IT and Software Development", "Distributed stateful backends and high-availability clustered architectures.", "500-1000 employees", "Hyderabad"),
    ("Aegis CodeWorks", "IT and Software Development", "Enterprise code quality, automated test harness platforms, and CI/CD tools.", "100-200 employees", "Noida"),
    ("TrueNorth Digital", "IT and Software Development", "E-commerce transactional engines and real-time inventory systems.", "1000+ employees", "Bengaluru"),
    ("DevMatrix Labs", "IT and Software Development", "Container management platforms, Kubernetes operators, and observability tools.", "200-500 employees", "Chennai"),
    ("Catalyst Software Group", "IT and Software Development", "Enterprise modernization, legacy migration, and cloud migration frameworks.", "1000+ employees", "Gurugram"),

    # 2. Fintech and Banking Technology (10 companies)
    ("FinEdge Core Payments", "Fintech and Banking Technology", "Low-latency UPI transaction switches and payment gateway infrastructure.", "1000+ employees", "Bengaluru"),
    ("CapitalForge Analytics", "Fintech and Banking Technology", "Algorithmic market microstructure analysis and quantitative trading tools.", "100-200 employees", "Mumbai"),
    ("SecurePay Gateway", "Fintech and Banking Technology", "PCI-DSS certified merchant acquiring platforms and recurring billing engines.", "500-1000 employees", "Bengaluru"),
    ("QuantVault Financial", "Fintech and Banking Technology", "Risk management modeling, portfolio VaR analytics, and algorithmic pricing.", "200-500 employees", "Mumbai"),
    ("LedgerLock Technologies", "Fintech and Banking Technology", "Distributed ledger reconciliation and cross-border settlement protocols.", "50-100 employees", "Hyderabad"),
    ("Novus Banking Cloud", "Fintech and Banking Technology", "Core banking cloud transformations, ISO20022 messaging, and loan origination.", "1000+ employees", "Chennai"),
    ("CashFlow Matrix", "Fintech and Banking Technology", "Automated working capital underwriting, GST invoicing, and B2B credit scoring.", "100-200 employees", "Pune"),
    ("EquiTrade Systems", "Fintech and Banking Technology", "Order execution management systems (OMS/EMS) and low-latency FIX protocol feeds.", "200-500 employees", "Mumbai"),
    ("TrustPay Digital", "Fintech and Banking Technology", "Smart wallet engines, QR payment networks, and retail payment terminals.", "500-1000 employees", "Bengaluru"),
    ("CrediGen Financial Labs", "Fintech and Banking Technology", "Alternative credit scoring ML models and automated retail loan appraisal.", "100-200 employees", "Gurugram"),

    # 3. Artificial Intelligence and Data Science (10 companies)
    ("CognitiveScale AI", "Artificial Intelligence and Data Science", "Generative AI foundational pipelines, retrieval-augmented generation, and agentic workflows.", "200-500 employees", "Bengaluru"),
    ("DeepVisionary Labs", "Artificial Intelligence and Data Science", "Real-time edge computer vision, facial biometrics, and industrial defect detection.", "100-200 employees", "Hyderabad"),
    ("NeuralStream Technologies", "Artificial Intelligence and Data Science", "Large-scale natural language understanding, multilingual summarization, and speech models.", "200-500 employees", "Bengaluru"),
    ("DataSphere Intelligence", "Artificial Intelligence and Data Science", "Predictive maintenance algorithms, sensor telemetry forecasting, and digital twins.", "100-200 employees", "Pune"),
    ("TensorCraft Analytics", "Artificial Intelligence and Data Science", "Deep learning optimization for high-throughput GPU inference clusters.", "50-100 employees", "Hyderabad"),
    ("Synthetix Intelligence", "Artificial Intelligence and Data Science", "Multimodal document intelligence and tabular knowledge-graph generation.", "100-200 employees", "Bengaluru"),
    ("VisionPath Systems", "Artificial Intelligence and Data Science", "Autonomous mobile robot vision, SLAM navigation, and obstacle detection.", "50-100 employees", "Bengaluru"),
    ("OmniAI Solutions", "Artificial Intelligence and Data Science", "Domain-specific LLM fine-tuning, RLHF pipelines, and AI evaluation harness.", "200-500 employees", "Gurugram"),
    ("PredictaPulse Labs", "Artificial Intelligence and Data Science", "Time-series demand forecasting and anomaly detection on financial streams.", "100-200 employees", "Mumbai"),
    ("Intellecta Informatics", "Artificial Intelligence and Data Science", "Healthcare data NLP, clinical entity recognition, and diagnostic assistant systems.", "100-200 employees", "Chennai"),

    # 4. Cybersecurity (8 companies)
    ("CyberShield Defense", "Cybersecurity", "Automated SOC intrusion detection, SIEM log parsing, and endpoint detection & response.", "500-1000 employees", "Bengaluru"),
    ("SentinelCore Security", "Cybersecurity", "Zero-trust network architecture, identity federation, and SAML/OAuth policy engines.", "200-500 employees", "Hyderabad"),
    ("ThreatGuard Analytics", "Cybersecurity", "Real-time threat intelligence feeds, MITRE ATT&CK correlation, and automated sandboxing.", "100-200 employees", "Pune"),
    ("VigilantSec Labs", "Cybersecurity", "Cloud security posture management (CSPM) and Kubernetes runtime vulnerability detection.", "100-200 employees", "Bengaluru"),
    ("IronClad Cyberworks", "Cybersecurity", "Static and dynamic application security testing (SAST/DAST) automation platforms.", "200-500 employees", "Noida"),
    ("Fortress Cryptography", "Cybersecurity", "Post-quantum cryptographic algorithms, HSM key lifecycle management, and PKI.", "50-100 employees", "Bengaluru"),
    ("NetPatrol Security", "Cybersecurity", "Deep packet inspection, DDoS mitigation scrubbing, and WAF rules engines.", "200-500 employees", "Gurugram"),
    ("RedTeam Defense Systems", "Cybersecurity", "Automated penetration testing frameworks and purple-team simulation engines.", "50-100 employees", "Hyderabad"),

    # 5. Electronics and Semiconductor (8 companies)
    ("SilicoMatrix Microelectronics", "Electronics and Semiconductor", "Sub-7nm ASIC digital design, logic synthesis, and static timing analysis.", "1000+ employees", "Bengaluru"),
    ("NanoChip Technologies", "Electronics and Semiconductor", "Analog mixed-signal IC design, power management ICs, and RF transceivers.", "500-1000 employees", "Hyderabad"),
    ("VectorVLSI Systems", "Electronics and Semiconductor", "SystemVerilog UVM verification environments and formal verification proof generation.", "200-500 employees", "Noida"),
    ("CircuitDynamics Semiconductor", "Electronics and Semiconductor", "RISC-V processor architectural exploration and FPGA hardware prototyping.", "100-200 employees", "Bengaluru"),
    ("MicroWave Embedded Labs", "Electronics and Semiconductor", "High-speed board design, PCB signal integrity analysis, and DDR5 routing.", "50-100 employees", "Chennai"),
    ("SemicoPulse Innovations", "Electronics and Semiconductor", "Automotive MCU development, ISO 26262 functional safety, and AUTOSAR firmware.", "500-1000 employees", "Pune"),
    ("TeraHertz Silicon", "Electronics and Semiconductor", "MmWave RF design, 5G baseband hardware accelerators, and phased-array radar chips.", "100-200 employees", "Bengaluru"),
    ("Apex Embedded Solutions", "Electronics and Semiconductor", "Bare-metal firmware, RTOS device drivers, and ARM Cortex-M architecture.", "100-200 employees", "Hyderabad"),

    # 6. Manufacturing and Automotive (10 companies)
    ("TorqueDrive Motors", "Manufacturing and Automotive", "Electric vehicle battery management systems, traction inverters, and motor control.", "1000+ employees", "Pune"),
    ("PrecisionKinematics Gearworks", "Manufacturing and Automotive", "Robotic gearboxes, harmonic drives, and high-precision CNC multi-axis machining.", "500-1000 employees", "Chennai"),
    ("AeroMech Dynamics", "Manufacturing and Automotive", "Aerospace structural components, titanium investment casting, and GD&T auditing.", "500-1000 employees", "Bengaluru"),
    ("AutoForm Manufacturing", "Manufacturing and Automotive", "Sheet metal stamping dies, progressive press tools, and plastic injection molding.", "200-500 employees", "Gurugram"),
    ("ThermalFlow Systems", "Manufacturing and Automotive", "Industrial HVAC chilling plants, plate heat exchangers, and CFD optimization.", "200-500 employees", "Ahmedabad"),
    ("DynamicFab Heavy Industries", "Manufacturing and Automotive", "Pressure vessel fabrication (ASME Sec VIII), automated submerged arc welding.", "1000+ employees", "Vadodara"),
    ("ElectroMotive Power", "Manufacturing and Automotive", "High-voltage EV wiring harnesses, busbars, and crash-safe chassis engineering.", "500-1000 employees", "Pune"),
    ("OmniCasting Metallurgy", "Manufacturing and Automotive", "Foundry operations, sand casting metallurgy, and spectral alloy verification.", "200-500 employees", "Coimbatore"),
    ("RoboAssemble Automation", "Manufacturing and Automotive", "Flexible assembly lines, pneumatic end-effectors, and PLC cell integration.", "100-200 employees", "Bengaluru"),
    ("Apex Industrial Hydraulics", "Manufacturing and Automotive", "Heavy equipment hydraulic cylinders, proportional valve manifolds, and test rigs.", "200-500 employees", "Jamshedpur"),

    # 7. Construction and Infrastructure (8 companies)
    ("TerraFirm MegaStructures", "Construction and Infrastructure", "High-rise commercial towers, deep diaphragm walls, and post-tensioned slabs.", "1000+ employees", "Mumbai"),
    ("TransMetro Civil Projects", "Construction and Infrastructure", "Elevated viaducts, underground metro tunneling, and precast segmental launching.", "1000+ employees", "Delhi NCR"),
    ("Apex Highway Builders", "Construction and Infrastructure", "National expressways, asphalt concrete pavement design, and culvert hydraulics.", "500-1000 employees", "Jaipur"),
    ("AquaFlow Hydrosystems", "Construction and Infrastructure", "Municipal water treatment plants, intake wells, and DI water distribution grids.", "200-500 employees", "Hyderabad"),
    ("BridgeCraft Engineering", "Construction and Infrastructure", "Cable-stayed bridge structural modeling, STAAD finite element analysis, and piers.", "200-500 employees", "Kolkata"),
    ("GeoTech Foundation Specialists", "Construction and Infrastructure", "Bored cast-in-situ piling, ground anchors, and soil stabilization grouting.", "100-200 employees", "Chennai"),
    ("SmartCity InfraWorks", "Construction and Infrastructure", "Integrated municipal utility corridors, stormwater drainage, and GIS topography.", "500-1000 employees", "Pune"),
    ("BIMVision Projects", "Construction and Infrastructure", "Building Information Modeling (BIM 4D/5D), clash detection, and quantity takeoffs.", "100-200 employees", "Bengaluru"),

    # 8. Energy and Renewable Energy (8 companies)
    ("Solaris Energy Solutions", "Energy and Renewable Energy", "Utility-scale 500MW solar photovoltaic farm design, central inverters, and switchyards.", "500-1000 employees", "Ahmedabad"),
    ("AeroWind Power Systems", "Energy and Renewable Energy", "Wind turbine pitch control systems, nacelle generators, and grid interconnection.", "500-1000 employees", "Chennai"),
    ("GridSync Power Technologies", "Energy and Renewable Energy", "Substation automation, IEC 61850 relay protection coordination, and SCADA.", "500-1000 employees", "Bengaluru"),
    ("TerraWatt Battery Storage", "Energy and Renewable Energy", "Lithium iron phosphate (LFP) grid-scale BESS and thermal runaway prevention.", "100-200 employees", "Hyderabad"),
    ("HydroPulse Generation", "Energy and Renewable Energy", "Small hydro Pelton/Francis turbine runner design and penstock fluid mechanics.", "200-500 employees", "Dehradun"),
    ("BioPower Green Fuels", "Energy and Renewable Energy", "Biomass gasification plants, biogas upgrading to CBG, and carbon accounting.", "100-200 employees", "Pune"),
    ("Apex Thermal Utilities", "Energy and Renewable Energy", "Supercritical thermal boiler optimization, steam turbine efficiency, and flue-gas desulfurization.", "1000+ employees", "Kolkata"),
    ("CleanCurrent Microgrids", "Energy and Renewable Energy", "Islanded microgrid stability, hybrid solar-diesel controllers, and inverter DROOP control.", "50-100 employees", "Bengaluru"),

    # 9. Mining and Natural Resources (5 companies)
    ("TerraMinerals Extraction", "Mining and Natural Resources", "Open-cast iron ore mining, dragline optimization, and blast pattern vibration control.", "1000+ employees", "Bhubaneswar"),
    ("GeoCore Mining Explorations", "Mining and Natural Resources", "Underground coal extraction, continuous miner ventilation, and strata monitoring.", "500-1000 employees", "Ranchi"),
    ("MineralOre Processing", "Mining and Natural Resources", "Froth flotation cells, hydrocyclone classification, and ball mill comminution circuits.", "500-1000 employees", "Udaipur"),
    ("Apex RockMechanics", "Mining and Natural Resources", "Rock mass rating (RMR), slope stability simulation in Slide2, and wire-mesh bolting.", "100-200 employees", "Nagpur"),
    ("DeepEarth Resource Corp", "Mining and Natural Resources", "Bauxite extraction, heavy earth-moving equipment (HEMM) fleet telematics, and mine GIS.", "500-1000 employees", "Raipur"),

    # 10. Consulting and Business Services (5 companies)
    ("Stratos Strategic Advisory", "Consulting and Business Services", "Management consulting, operating model redesign, and supply chain rationalization.", "1000+ employees", "Gurugram"),
    ("Apex Business Intelligence", "Consulting and Business Services", "Enterprise Power BI dashboarding, KPI telemetry, and operational cost accounting.", "200-500 employees", "Mumbai"),
    ("Vanguard Technology Consulting", "Consulting and Business Services", "IT roadmap strategy, cloud cost FinOps, and enterprise ERP implementation.", "500-1000 employees", "Bengaluru"),
    ("Optima Analytics Advisory", "Consulting and Business Services", "Retail pricing elasticity models, customer churn forecasting, and marketing mix analytics.", "100-200 employees", "Pune"),
    ("Crestview Capital Consulting", "Consulting and Business Services", "M&A technical due diligence, commercial viability studies, and financial modeling.", "100-200 employees", "Mumbai"),

    # 11. Telecom and Networking (4 companies)
    ("TeleConnect Fiber Systems", "Telecom and Networking", "DWDM optical transport networks, GPON FTTH architectures, and fiber OTDR testing.", "500-1000 employees", "Chennai"),
    ("WaveLink 5G Solutions", "Telecom and Networking", "Open RAN architectures, 5G gNodeB baseband software, and beamforming algorithms.", "200-500 employees", "Bengaluru"),
    ("SkyNet Wireless Networks", "Telecom and Networking", "Microwave backhaul radio planning, link budget calculations, and satellite VSAT telemetry.", "100-200 employees", "Gurugram"),
    ("PacketCore Routing Tech", "Telecom and Networking", "BGP/OSPF dynamic routing stacks, MPLS traffic engineering, and DPDK acceleration.", "200-500 employees", "Hyderabad"),

    # 12. Other Industries (Chemical Process, Aerospace, Biotech, Supply Chain) (4 companies)
    ("CatalystChem Process Works", "Chemical Process & Materials", "Continuous stirred tank reactors (CSTR), distillation column pinch design, and HAZOP.", "500-1000 employees", "Vadodara"),
    ("AeroFlight Avionics", "Aerospace and Defense", "DO-178C flight control computers, ARINC 429 bus telemetry, and fly-by-wire software.", "200-500 employees", "Bengaluru"),
    ("BioPharma Synthetics", "Biotechnology & Pharmaceuticals", "Bioreactor scale-up, downstream chromatography purification, and cGMP compliance.", "200-500 employees", "Hyderabad"),
    ("LogiRoute Global Logistics", "Supply Chain & Logistics", "Automated warehouse AGVs, carton sortation algorithms, and dynamic fleet dispatching.", "500-1000 employees", "Mumbai"),
]

# -----------------------------------------------------------------------------
# Department Branch Specs & Curriculum Questions Reference
# -----------------------------------------------------------------------------
BRANCH_CURRICULUM = {
    "CSE": {
        "degree": "B.Tech in Computer Science and Engineering",
        "skills": [
            ("Python", "language", "advanced"),
            ("Data Structures & Algorithms", "technical", "advanced"),
            ("FastAPI", "framework", "intermediate"),
            ("PostgreSQL", "database", "advanced"),
            ("React", "framework", "intermediate"),
            ("Docker", "tool", "intermediate"),
            ("Git & GitHub", "tool", "advanced"),
            ("Computer Networks", "technical", "intermediate"),
        ],
        "projects": [
            ("Cloud Microservices Placement Portal", "Designed asynchronous FastAPI microservices with JWT auth and PostgreSQL.", "FastAPI, PostgreSQL, React, Docker"),
            ("Distributed Cache with Raft Consensus", "Implemented leader election and log replication conforming to Raft.", "Go, gRPC, Docker"),
        ],
        "experiences": [("Google Cloud CoE", "Software Engineering Intern", "Refactored microservices reducing p99 latency by 32%.")],
        "certifications": [("AWS Certified Solutions Architect - Associate", "Amazon Web Services")],
        "arena_cat": ArenaCategory.DSA,
    },
    "IT": {
        "degree": "B.Tech in Information Technology",
        "skills": [
            ("Java", "language", "advanced"),
            ("Spring Boot", "framework", "intermediate"),
            ("SQL & MySQL", "database", "advanced"),
            ("Cloud Computing (AWS)", "technical", "intermediate"),
            ("JavaScript", "language", "advanced"),
            ("REST APIs", "technical", "advanced"),
            ("Linux System Administration", "tool", "intermediate"),
        ],
        "projects": [
            ("Secure Enterprise E-Commerce Platform", "Constructed resilient Spring Boot microservices with Redis session caching.", "Java, Spring Boot, MySQL, Redis"),
            ("Automated CI/CD Pipeline on AWS ECS", "Built automated GitLab CI pipelines deploying Docker containers to AWS ECS.", "AWS, Docker, Terraform, GitLab CI"),
        ],
        "experiences": [("Infosys Ltd.", "Cloud Solutions Intern", "Built automated provisioning scripts for cloud infrastructure.")],
        "certifications": [("Oracle Certified Professional: Java SE 11 Developer", "Oracle")],
        "arena_cat": ArenaCategory.DBMS,
    },
    "ECE": {
        "degree": "B.Tech in Electronics and Communication Engineering",
        "skills": [
            ("Verilog HDL", "language", "advanced"),
            ("Embedded C / C++", "language", "advanced"),
            ("VLSI Architecture & CMOS Design", "technical", "advanced"),
            ("FPGA Prototyping (Xilinx)", "tool", "intermediate"),
            ("Digital Signal Processing (DSP)", "technical", "intermediate"),
            ("Cadence Virtuoso", "tool", "intermediate"),
            ("Wireless Communication", "technical", "intermediate"),
        ],
        "projects": [
            ("32-Bit Pipelined RISC-V Core on Artix-7", "Designed 5-stage hazard-handling RV32I core synthesized in Xilinx Vivado.", "Verilog HDL, Vivado, ModelSim"),
            ("Low-Power IoT Telemetry Node with LoRa", "Programmed STM32 MCU for 8km range environmental data transmission.", "Embedded C, STM32CubeIDE, KiCad"),
        ],
        "experiences": [("STMicroelectronics", "Embedded Systems Intern", "Wrote SPI and I2C board support drivers for ARM Cortex-M.")],
        "certifications": [("Certified Associate: Digital IC Design", "Cadence Design Systems")],
        "arena_cat": ArenaCategory.PROGRAMMING_FUNDAMENTALS,
    },
    "EEE": {
        "degree": "B.Tech in Electrical Engineering",
        "skills": [
            ("MATLAB & Simulink", "tool", "advanced"),
            ("Power Systems Analysis", "technical", "advanced"),
            ("Power Electronics & Drives", "technical", "advanced"),
            ("Electrical Machines", "technical", "intermediate"),
            ("Control Systems", "technical", "intermediate"),
            ("ETAP", "tool", "intermediate"),
            ("PLC & SCADA Programming", "tool", "intermediate"),
        ],
        "projects": [
            ("Grid-Tied 5kW Solar Inverter with MPPT", "Simulated single-phase solar inverter in MATLAB with P&O MPPT algorithm.", "MATLAB, Simulink, Power Electronics"),
            ("33/11 kV Substation Relay Coordination in ETAP", "Modeled short-circuit fault levels and protective relay time curves.", "ETAP, IEEE Relaying Standards"),
        ],
        "experiences": [("ABB Power Grids", "Electrical Systems Intern", "Audited vacuum circuit breaker primary injection test curves.")],
        "certifications": [("Industrial Automation & PLC Specialist", "Siemens SITRAIN")],
        "arena_cat": ArenaCategory.QUANTITATIVE,
    },
    "MECH": {
        "degree": "B.Tech in Mechanical Engineering",
        "skills": [
            ("SolidWorks", "tool", "advanced"),
            ("ANSYS Mechanical", "tool", "advanced"),
            ("Thermodynamics", "technical", "advanced"),
            ("Heat & Mass Transfer", "technical", "intermediate"),
            ("Finite Element Analysis (FEA)", "technical", "advanced"),
            ("Manufacturing Processes & GD&T", "technical", "advanced"),
            ("AutoCAD Mechanical", "tool", "advanced"),
        ],
        "projects": [
            ("CFD Optimization of Shell & Tube Exchanger", "Simulated turbulent flow in ANSYS Fluent improving heat transfer by 18%.", "ANSYS Fluent, SolidWorks, MATLAB"),
            ("Automated Pneumatic Pick-and-Place Gripper", "Synthesized 4-bar linkage mechanism with FEA structural verification.", "SolidWorks, ANSYS Structural"),
        ],
        "experiences": [("Tata Motors", "Manufacturing Intern", "Executed line-balancing cycle studies on transmission assembly.")],
        "certifications": [("CSWA - Certified SOLIDWORKS Associate", "Dassault Systèmes")],
        "arena_cat": ArenaCategory.APTITUDE_LOGICAL,
    },
    "CIVIL": {
        "degree": "B.Tech in Civil Engineering",
        "skills": [
            ("AutoCAD", "tool", "advanced"),
            ("STAAD.Pro", "tool", "advanced"),
            ("Concrete Technology", "technical", "advanced"),
            ("Structural Analysis", "technical", "advanced"),
            ("Geotechnical Engineering", "technical", "intermediate"),
            ("Surveying & Geomatics", "technical", "advanced"),
            ("Transportation Engineering", "technical", "intermediate"),
        ],
        "projects": [
            ("Seismic Analysis of G+5 RCC Complex in STAAD", "Conformed 3D frame design to IS 1893 seismic code saving 14% rebar.", "STAAD.Pro, AutoCAD, MS Excel"),
            ("Fly-Ash Soil Subgrade Stabilization", "Determined California Bearing Ratio (CBR) and compaction properties.", "Soil Lab, CBR, IS 2720"),
        ],
        "experiences": [("Larsen & Toubro Construction", "Civil Trainee Intern", "Supervised foundation raft casting and bar bending schedule audits.")],
        "certifications": [("Bentley Certified STAAD.Pro Structural Designer", "Bentley Systems")],
        "arena_cat": ArenaCategory.QUANTITATIVE,
    },
    "CHEM": {
        "degree": "B.Tech in Chemical Engineering",
        "skills": [
            ("Aspen Plus", "tool", "advanced"),
            ("Chemical Reaction Engineering", "technical", "advanced"),
            ("Mass Transfer Operations", "technical", "advanced"),
            ("P&ID Equipment Sizing", "technical", "intermediate"),
            ("Process Dynamics & Control", "technical", "intermediate"),
            ("Industrial Safety & HAZOP", "technical", "advanced"),
        ],
        "projects": [
            ("Design of Binary Distillation Column in Aspen Plus", "Optimized reflux ratio for ethanol-water separation minimizing reboiler duty.", "Aspen Plus, Chemical Kinetics"),
            ("Continuous Stirred Tank Reactor HAZOP Analysis", "Conducted safety review identifying critical runaway overpressure scenarios.", "HAZOP, Process Safety"),
        ],
        "experiences": [("Reliance Industries Ltd.", "Chemical Process Intern", "Audited energy pinch curves on preheat heat exchanger trains.")],
        "certifications": [("Aspen Plus Certified User", "AspenTech")],
        "arena_cat": ArenaCategory.TECHNICAL_MCQS,
    },
    "MINE": {
        "degree": "B.Tech in Mining Engineering",
        "skills": [
            ("Mine Planning Software (Datamine/Surpac)", "tool", "intermediate"),
            ("Surface & Underground Mining Methods", "technical", "advanced"),
            ("Rock Mechanics & Strata Control", "technical", "advanced"),
            ("Blasting & Explosives Engineering", "technical", "advanced"),
            ("Mine Ventilation", "technical", "intermediate"),
            ("Mine Safety & Environmental Law", "technical", "advanced"),
        ],
        "projects": [
            ("Blast Optimization for Open-Cast Limestone Quarry", "Calculated powder factors and blast delay timing reducing PPV vibrations by 24%.", "Rock Mechanics, Seismograph"),
            ("Ventilation Network Simulation of Underground Mine", "Simulated auxiliary fan placement and airflow distribution.", "Ventsim, Mine Safety Guidelines"),
        ],
        "experiences": [("Hindustan Zinc Ltd.", "Mining Engineering Intern", "Conducted rock mass rating (RMR) and stope drilling parameter logs.")],
        "certifications": [("Mine Safety & Strata Management Certification", "DGMS Approved")],
        "arena_cat": ArenaCategory.APTITUDE_LOGICAL,
    },
    "PIE": {
        "degree": "B.Tech in Production & Industrial Engineering",
        "skills": [
            ("Operations Research & Linear Programming", "technical", "advanced"),
            ("Supply Chain & Inventory Management (EOQ)", "technical", "advanced"),
            ("Six Sigma & Quality Control (SPC)", "technical", "advanced"),
            ("CNC Machining & G-Code Programming", "technical", "intermediate"),
            ("Work Study & Ergonomics", "technical", "advanced"),
            ("Lean Manufacturing & 5S", "technical", "advanced"),
        ],
        "projects": [
            ("Value Stream Mapping and Lean Optimization on Assembly Line", "Identified bottlenecks reducing work-in-progress inventory by 35%.", "VSM, Lean, Minitab"),
            ("Multi-Objective Warehouse Layout Optimization", "Modeled integer linear program in Python Pulp minimizing forklift travel distance.", "Python, PuLP, SimPy"),
        ],
        "experiences": [("Maruti Suzuki India Ltd.", "Industrial Engineering Intern", "Streamlined bumper sub-assembly cell line balance efficiency.")],
        "certifications": [("Lean Six Sigma Green Belt (LSSGB)", "ASQ / Benchmark Six Sigma")],
        "arena_cat": ArenaCategory.QUANTITATIVE,
    },
    "AIML": {
        "degree": "B.Tech in Artificial Intelligence & Machine Learning",
        "skills": [
            ("Python", "language", "advanced"),
            ("PyTorch", "framework", "advanced"),
            ("Machine Learning (Scikit-Learn)", "technical", "advanced"),
            ("Deep Learning & CNNs", "technical", "advanced"),
            ("Natural Language Processing", "technical", "intermediate"),
            ("SQL", "database", "intermediate"),
            ("MLOps & Docker", "tool", "intermediate"),
        ],
        "projects": [
            ("Medical Chest X-Ray Diagnostic Classifier", "Trained DenseNet-121 model in PyTorch achieving 94.2% ROC-AUC on NIH dataset.", "PyTorch, Torchvision, CUDA"),
            ("Conversational Assistant with RAG Pipeline", "Constructed hybrid vector search using LangChain and pgvector.", "Python, LangChain, PostgreSQL"),
        ],
        "experiences": [("Wadhwani AI", "Applied ML Intern", "Benchmarked lightweight MobileNet vision models for crop pest detection.")],
        "certifications": [("Deep Learning Specialization", "DeepLearning.AI")],
        "arena_cat": ArenaCategory.DSA,
    },
    "AIDS": {
        "degree": "B.Tech in Artificial Intelligence & Data Science",
        "skills": [
            ("Python & R", "language", "advanced"),
            ("Data Wrangling (Pandas/NumPy)", "technical", "advanced"),
            ("Statistical Modeling & Hypothesis Testing", "technical", "advanced"),
            ("Big Data (Apache Spark)", "tool", "intermediate"),
            ("Data Visualization (Tableau/Seaborn)", "tool", "advanced"),
            ("Machine Learning Algorithms", "technical", "advanced"),
        ],
        "projects": [
            ("E-Commerce Real-time Customer Churn Prediction", "Engineered XGBoost pipeline processing 500k event streams in Spark.", "Python, PySpark, XGBoost, Streamlit"),
            ("Financial Time-Series Market Volatility Modeling", "Implemented GARCH and LSTM models predicting volatility spikes.", "Python, Statsmodels, Keras"),
        ],
        "experiences": [("Mu Sigma", "Decision Science Intern", "Authored automated exploratory analysis pipelines for retail clients.")],
        "certifications": [("IBM Certified Data Science Professional", "IBM")],
        "arena_cat": ArenaCategory.DBMS,
    },
}

# -----------------------------------------------------------------------------
# Main Seeder
# -----------------------------------------------------------------------------
async def seed_diverse_dataset():
    print("=" * 80)
    print("🚀 Starting Placement Intelligence Diverse Synthetic Dataset Generation")
    print("=" * 80)

    now_utc = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        # 1. Resolve institution and departments
        inst_res = await session.execute(select(Institution).where(Institution.id == 1))
        inst = inst_res.scalar_one_or_none()
        if not inst:
            inst = Institution(id=1, name="MBM University", code="MBMU", city="Jodhpur", is_active=True)
            session.add(inst)
            await session.flush()
        print(f"✓ Using Institution: {inst.name} (ID: {inst.id})")

        # Resolve TPO user for institution 1
        tpo_res = await session.execute(
            select(User).where(User.institution_id == inst.id, User.role == UserRole.TPO).limit(1)
        )
        tpo_user = tpo_res.scalar_one_or_none()
        if not tpo_user:
            tpo_user = User(
                email="tpo.officer@campus.example.test",
                hashed_password=PASSWORD_HASH,
                full_name="Prof. Rajesh Sharma (Head TPO)",
                role=UserRole.TPO,
                institution_id=inst.id,
                is_active=True,
                is_verified=True,
            )
            session.add(tpo_user)
            await session.flush()
        print(f"✓ Using TPO User: {tpo_user.full_name} (ID: {tpo_user.id})")

        # Resolve all required departments for inst
        dept_rows = (await session.execute(select(Department).where(Department.institution_id == inst.id))).scalars().all()
        dept_map: Dict[str, Department] = {d.code.upper().strip(): d for d in dept_rows}

        required_depts = [
            ("CSE", "Computer Science and Engineering"),
            ("IT", "Information Technology"),
            ("ECE", "Electronics and Communication Engineering"),
            ("EEE", "Electrical Engineering"),
            ("MECH", "Mechanical Engineering"),
            ("CIVIL", "Civil Engineering"),
            ("CHEM", "Chemical Engineering"),
            ("MINE", "Mining Engineering"),
            ("PIE", "Production & Industrial Engineering"),
            ("AIML", "Artificial Intelligence & Machine Learning"),
            ("AIDS", "Artificial Intelligence & Data Science"),
        ]

        for code, name in required_depts:
            if code not in dept_map:
                new_d = Department(institution_id=inst.id, name=name, code=code, is_active=True)
                session.add(new_d)
                await session.flush()
                dept_map[code] = new_d
                print(f"  + Created Department: {name} ({code})")

        # -------------------------------------------------------------------------
        # 2. Generate Exactly 100 Students
        # Branch quotas: CSE 25, IT 12, ECE 12, EEE 10, MECH 10, CIVIL 10, CHEM 6, MINE 5, PIE 5, AIML 3, AIDS 2 = 100
        # -------------------------------------------------------------------------
        print("\n--- Seeding Exactly 100 Multi-Disciplinary Students ---")
        STUDENT_QUOTAS = [
            ("CSE", 25),
            ("IT", 12),
            ("ECE", 12),
            ("EEE", 10),
            ("MECH", 10),
            ("CIVIL", 10),
            ("CHEM", 6),
            ("MINE", 5),
            ("PIE", 5),
            ("AIML", 3),
            ("AIDS", 2),
        ]

        total_students_quota = sum(q[1] for q in STUDENT_QUOTAS)
        assert total_students_quota == 100, f"Expected 100 students total, got {total_students_quota}"

        # Clean existing synthetic users if re-running
        existing_synth = (
            await session.execute(select(User.id).where(User.email.like("%@campus.example.test")))
        ).scalars().all()
        if existing_synth:
            print(f"  * Removing {len(existing_synth)} previously generated synthetic student records for idempotency...")
            # Handled cleanly via cascading or explicit delete
            await session.execute(delete(User).where(User.id.in_(existing_synth)))
            await session.flush()

        student_users: List[User] = []
        student_profiles: List[StudentProfile] = []
        student_resumes: List[Resume] = []

        student_counter = 1
        name_idx = 0

        for dept_code, count in STUDENT_QUOTAS:
            dept_obj = dept_map[dept_code]
            curric = BRANCH_CURRICULUM[dept_code]

            for i in range(count):
                first_name = FIRST_NAMES[(name_idx + 13) % len(FIRST_NAMES)]
                last_name = LAST_NAMES[(name_idx * 7) % len(LAST_NAMES)]
                full_name = f"{first_name} {last_name}"
                email = f"student.{dept_code.lower()}{i+1:02d}@campus.example.test"
                name_idx += 1

                user = User(
                    email=email,
                    hashed_password=PASSWORD_HASH,
                    full_name=full_name,
                    role=UserRole.STUDENT,
                    institution_id=inst.id,
                    department_id=dept_obj.id,
                    is_active=True,
                    is_verified=True,
                )
                session.add(user)
                await session.flush()

                # Academic performance distribution:
                # Top 15% (CGPA 9.05 - 9.85), Next 40% (CGPA 8.00 - 8.95), Next 30% (7.00 - 7.95), Next 12% (6.00 - 6.95), Bottom 3% (5.60 - 5.95)
                r_tier = student_counter % 20
                if r_tier in (0, 1, 2):  # 15%
                    cgpa = round(9.00 + (student_counter % 9) * 0.1, 2)
                    active_backlogs = 0
                    total_backlogs = 0
                elif r_tier in (3, 4, 5, 6, 7, 8, 9, 10):  # 40%
                    cgpa = round(8.00 + (student_counter % 10) * 0.09, 2)
                    active_backlogs = 0
                    total_backlogs = 0
                elif r_tier in (11, 12, 13, 14, 15, 16):  # 30%
                    cgpa = round(7.05 + (student_counter % 10) * 0.09, 2)
                    active_backlogs = 1 if student_counter % 7 == 0 else 0
                    total_backlogs = active_backlogs
                elif r_tier in (17, 18):  # 10%
                    cgpa = round(6.10 + (student_counter % 9) * 0.09, 2)
                    active_backlogs = 1 if student_counter % 2 == 0 else 0
                    total_backlogs = active_backlogs + 1
                else:  # 5% lower threshold
                    cgpa = round(5.65 + (student_counter % 4) * 0.08, 2)
                    active_backlogs = 2
                    total_backlogs = 3

                roll_number = f"22SYNTH{student_counter:04d}"

                profile = StudentProfile(
                    user_id=user.id,
                    roll_number=roll_number,
                    graduation_year=2026,
                    cgpa=cgpa,
                    active_backlogs=active_backlogs,
                    total_backlogs=total_backlogs,
                    linkedin_url=f"https://linkedin.com/in/{first_name.lower()}-{last_name.lower()}-{student_counter}",
                    github_url=f"https://github.com/{first_name.lower()}{last_name.lower()}",
                    portfolio_url=f"https://{first_name.lower()}{student_counter}.dev",
                    is_placement_ready=(active_backlogs == 0),
                )
                session.add(profile)
                await session.flush()

                # 1. Approved Resume
                raw_text = (
                    f"{full_name} | {email} | {roll_number}\n"
                    f"{curric['degree']} - MBM University (CGPA: {cgpa}/10.0)\n"
                    f"Technical Skills: {', '.join([s[0] for s in curric['skills']])}\n"
                    f"Projects: {curric['projects'][0][0]} - {curric['projects'][0][1]}\n"
                    f"Experience: {curric['experiences'][0][0]} ({curric['experiences'][0][1]})\n"
                )
                resume = Resume(
                    student_id=profile.id,
                    file_name=f"Resume_{first_name}_{last_name}.pdf",
                    file_path=f"uploads/resumes/synthetic_{student_counter:04d}.pdf",
                    file_type="pdf",
                    file_size_bytes=145000 + (student_counter * 123),
                    file_hash=hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
                    raw_extracted_text=raw_text,
                    parsed_entities_json={
                        "skills": [s[0] for s in curric["skills"]],
                        "education": [{"degree": curric["degree"], "institution": "MBM University", "cgpa": str(cgpa)}],
                        "projects": [{"title": p[0], "technologies": p[2]} for p in curric["projects"]],
                    },
                    parsing_status="approved",
                    is_active=True,
                )
                session.add(resume)
                await session.flush()

                # 2. Student Skills
                for skill_name, category, level in curric["skills"]:
                    session.add(
                        StudentSkill(
                            student_id=profile.id,
                            skill_name=skill_name,
                            category=category,
                            proficiency_level=level,
                            is_verified=True,
                        )
                    )

                # 3. Student Projects
                for p_title, p_desc, p_tech in curric["projects"]:
                    session.add(
                        StudentProject(
                            student_id=profile.id,
                            title=p_title,
                            description=p_desc,
                            technologies=p_tech,
                            project_url=f"https://github.com/projects/{p_title.lower().replace(' ', '-')[:25]}",
                        )
                    )

                # 4. Student Experience (80% of students have an internship)
                if student_counter % 5 != 0:
                    exp_co, exp_role, exp_desc = curric["experiences"][0]
                    session.add(
                        StudentExperience(
                            student_id=profile.id,
                            company_name=exp_co,
                            role_title=exp_role,
                            description=exp_desc,
                            is_current=False,
                            start_date="2025-05-15",
                            end_date="2025-07-25",
                        )
                    )

                # 5. Student Certification (70% of students have a certification)
                if student_counter % 3 != 0:
                    cert_name, cert_org = curric["certifications"][0]
                    session.add(
                        StudentCertification(
                            student_id=profile.id,
                            certificate_name=cert_name,
                            issuing_organization=cert_org,
                            issue_date="2025-03-10",
                        )
                    )

                # 6. Student Education
                session.add(
                    StudentEducation(
                        student_id=profile.id,
                        degree=curric["degree"],
                        institution_name="MBM University",
                        end_year=2026,
                        cgpa_or_percentage=str(cgpa),
                    )
                )

                student_users.append(user)
                student_profiles.append(profile)
                student_resumes.append(resume)
                student_counter += 1

        await session.commit()
        print(f"✓ Created {len(student_users)} synthetic students across {len(STUDENT_QUOTAS)} branches.")

        # -------------------------------------------------------------------------
        # 3. Generate Exactly 100 Companies across 12 Industries
        # -------------------------------------------------------------------------
        print("\n--- Seeding Exactly 100 Companies & Recruiter Accounts ---")
        assert len(COMPANY_TEMPLATES) == 100, f"Expected 100 company templates, got {len(COMPANY_TEMPLATES)}"

        # Clean existing synthetic companies if re-running
        existing_synth_comp = (
            await session.execute(select(Company.id).where(Company.name.like("%[Synthetic]%")))
        ).scalars().all()
        if existing_synth_comp:
            print(f"  * Removing {len(existing_synth_comp)} previously generated synthetic companies...")
            await session.execute(delete(Company).where(Company.id.in_(existing_synth_comp)))
            await session.flush()

        companies: List[Company] = []
        recruiter_users: List[User] = []

        for idx, (c_name, c_ind, c_desc, c_size, c_loc) in enumerate(COMPANY_TEMPLATES, start=1):
            synth_name = f"{c_name} [Synthetic]"
            domain = c_name.lower().replace(" ", "").replace("&", "and")[:16]

            comp = Company(
                name=synth_name,
                industry=c_ind,
                description=c_desc,
                company_size=c_size,
                location=c_loc,
                website=f"https://www.{domain}.example.test",
                contact_email=f"careers@{domain}.example.test",
                contact_phone=f"+91-98{idx:02d}112233",
                is_verified=True,
                is_active=True,
                institution_id=None,  # Corporate partner
            )
            session.add(comp)
            await session.flush()

            # Recruiter User
            rec_user = User(
                email=f"recruiter.c{idx:03d}@partner.example.test",
                hashed_password=PASSWORD_HASH,
                full_name=f"{FIRST_NAMES[(idx*3) % len(FIRST_NAMES)]} {LAST_NAMES[(idx*2) % len(LAST_NAMES)]} (Recruiter)",
                role=UserRole.RECRUITER,
                is_active=True,
                is_verified=True,
            )
            session.add(rec_user)
            await session.flush()

            session.add(
                RecruiterProfile(
                    user_id=rec_user.id,
                    company_id=comp.id,
                    designation="Lead Campus Talent Acquisition Partner",
                )
            )

            companies.append(comp)
            recruiter_users.append(rec_user)

        await session.commit()
        print(f"✓ Created {len(companies)} synthetic companies across 12 industries with 100 recruiter accounts.")

        # -------------------------------------------------------------------------
        # 4. Generate Diverse Campus Placement Job Postings (~150 Jobs)
        # -------------------------------------------------------------------------
        print("\n--- Seeding ~150 Diverse Job Opportunities with Branch Eligibility & Skills ---")

        # Map industry to job configurations
        def get_jobs_for_company(comp: Company, c_idx: int) -> List[Dict[str, Any]]:
            ind = comp.industry
            if "IT and Software" in ind:
                return [
                    {
                        "title": "Backend Systems Engineer",
                        "desc": "Build highly scalable microservices, low-latency gRPC APIs, and persistent storage layers.",
                        "emp_type": EmploymentType.FULL_TIME,
                        "work_mode": WorkMode.HYBRID,
                        "salary": "₹14.0 - ₹18.0 LPA",
                        "ctc": 16.0,
                        "min_cgpa": 7.0,
                        "backlogs": 0,
                        "depts": ["CSE", "IT", "AIML", "AIDS"],
                        "skills": [("Python", True), ("FastAPI", True), ("PostgreSQL", True), ("Docker", False), ("Redis", False)],
                    },
                    {
                        "title": "Software Development Engineer Intern",
                        "desc": "Summer 2026 internship developing core product features and writing clean unit tests.",
                        "emp_type": EmploymentType.INTERNSHIP,
                        "work_mode": WorkMode.REMOTE,
                        "salary": "₹45,000/month",
                        "ctc": 5.4,
                        "min_cgpa": 6.5,
                        "backlogs": 1,
                        "depts": ["CSE", "IT", "ECE", "AIML", "AIDS"],
                        "skills": [("Data Structures & Algorithms", True), ("Git & GitHub", True), ("SQL & MySQL", False)],
                    } if c_idx % 2 == 0 else {
                        "title": "Full Stack Cloud Engineer",
                        "desc": "End-to-end full stack development using modern React, TypeScript, and cloud services.",
                        "emp_type": EmploymentType.FULL_TIME,
                        "work_mode": WorkMode.ON_SITE,
                        "salary": "₹12.0 - ₹15.0 LPA",
                        "ctc": 13.5,
                        "min_cgpa": 6.8,
                        "backlogs": 0,
                        "depts": ["CSE", "IT"],
                        "skills": [("React", True), ("Node.js", True), ("TypeScript", True), ("Docker", False)],
                    }
                ]
            elif "Fintech" in ind:
                return [
                    {
                        "title": "Financial Technologies Software Engineer",
                        "desc": "High-throughput financial ledger systems, transactional ACID compliance, and payment APIs.",
                        "emp_type": EmploymentType.FULL_TIME,
                        "work_mode": WorkMode.HYBRID,
                        "salary": "₹16.0 - ₹22.0 LPA",
                        "ctc": 19.0,
                        "min_cgpa": 7.5,
                        "backlogs": 0,
                        "depts": ["CSE", "IT", "AIML"],
                        "skills": [("Java", True), ("Spring Boot", True), ("PostgreSQL", True), ("Data Structures & Algorithms", False)],
                    },
                    {
                        "title": "Quantitative Developer Trainee",
                        "desc": "Develop statistical pricing tools, real-time risk analytics, and algorithmic execution feeds.",
                        "emp_type": EmploymentType.FULL_TIME,
                        "work_mode": WorkMode.ON_SITE,
                        "salary": "₹20.0 - ₹28.0 LPA",
                        "ctc": 24.0,
                        "min_cgpa": 8.0,
                        "backlogs": 0,
                        "depts": ["CSE", "IT", "ECE", "EEE", "AIDS"],
                        "skills": [("Python", True), ("Machine Learning (Scikit-Learn)", True), ("Data Structures & Algorithms", True)],
                    }
                ]
            elif "Artificial Intelligence" in ind:
                return [
                    {
                        "title": "Machine Learning Engineer",
                        "desc": "Train, evaluate, and deploy deep learning neural networks and LLM agent architectures.",
                        "emp_type": EmploymentType.FULL_TIME,
                        "work_mode": WorkMode.HYBRID,
                        "salary": "₹18.0 - ₹25.0 LPA",
                        "ctc": 21.5,
                        "min_cgpa": 7.5,
                        "backlogs": 0,
                        "depts": ["AIML", "AIDS", "CSE", "IT"],
                        "skills": [("Python", True), ("PyTorch", True), ("Deep Learning & CNNs", True), ("Docker", False)],
                    },
                    {
                        "title": "Computer Vision & Edge AI Intern",
                        "desc": "Deploy low-latency visual inference pipelines on edge hardware accelerators.",
                        "emp_type": EmploymentType.INTERNSHIP,
                        "work_mode": WorkMode.ON_SITE,
                        "salary": "₹50,000/month",
                        "ctc": 6.0,
                        "min_cgpa": 7.0,
                        "backlogs": 0,
                        "depts": ["AIML", "ECE", "CSE"],
                        "skills": [("Python", True), ("Computer Vision", True), ("PyTorch", False)],
                    }
                ]
            elif "Cybersecurity" in ind:
                return [
                    {
                        "title": "Cyber Threat & Security Engineer",
                        "desc": "Analyze security vulnerabilities, design zero-trust policy engines, and audit codebases.",
                        "emp_type": EmploymentType.FULL_TIME,
                        "work_mode": WorkMode.HYBRID,
                        "salary": "₹12.0 - ₹16.0 LPA",
                        "ctc": 14.0,
                        "min_cgpa": 6.8,
                        "backlogs": 0,
                        "depts": ["CSE", "IT", "ECE"],
                        "skills": [("Computer Networks", True), ("Linux System Administration", True), ("Python", False)],
                    }
                ]
            elif "Semiconductor" in ind:
                return [
                    {
                        "title": "VLSI Design & Verification Engineer",
                        "desc": "RTL architecture design in Verilog, UVM testbench authoring, and FPGA emulation.",
                        "emp_type": EmploymentType.FULL_TIME,
                        "work_mode": WorkMode.ON_SITE,
                        "salary": "₹15.0 - ₹20.0 LPA",
                        "ctc": 17.5,
                        "min_cgpa": 7.2,
                        "backlogs": 0,
                        "depts": ["ECE", "EEE"],
                        "skills": [("Verilog HDL", True), ("VLSI Architecture & CMOS Design", True), ("Digital Signal Processing (DSP)", False)],
                    },
                    {
                        "title": "Embedded Firmware Developer",
                        "desc": "Low-level bare metal driver programming, RTOS kernel integration, and board debugging.",
                        "emp_type": EmploymentType.FULL_TIME,
                        "work_mode": WorkMode.ON_SITE,
                        "salary": "₹11.0 - ₹14.0 LPA",
                        "ctc": 12.5,
                        "min_cgpa": 6.5,
                        "backlogs": 1,
                        "depts": ["ECE", "EEE", "CSE"],
                        "skills": [("Embedded C / C++", True), ("Microcontrollers (STM32 / Arduino)", True), ("Verilog HDL", False)],
                    }
                ]
            elif "Manufacturing" in ind:
                return [
                    {
                        "title": "Mechanical Design Engineer",
                        "desc": "3D CAD modeling of precision mechanisms, GD&T tolerance stacks, and FEA simulation.",
                        "emp_type": EmploymentType.FULL_TIME,
                        "work_mode": WorkMode.ON_SITE,
                        "salary": "₹8.0 - ₹11.0 LPA",
                        "ctc": 9.5,
                        "min_cgpa": 6.5,
                        "backlogs": 0,
                        "depts": ["MECH", "PIE"],
                        "skills": [("SolidWorks", True), ("Finite Element Analysis (FEA)", True), ("Manufacturing Processes & GD&T", True)],
                    },
                    {
                        "title": "Industrial Production & Quality Trainee",
                        "desc": "Implement Lean Six Sigma quality tools, line-balancing workflows, and cycle-time studies.",
                        "emp_type": EmploymentType.FULL_TIME,
                        "work_mode": WorkMode.ON_SITE,
                        "salary": "₹7.5 - ₹9.5 LPA",
                        "ctc": 8.5,
                        "min_cgpa": 6.2,
                        "backlogs": 1,
                        "depts": ["PIE", "MECH"],
                        "skills": [("Operations Research & Linear Programming", True), ("Six Sigma & Quality Control (SPC)", True), ("Lean Manufacturing & 5S", False)],
                    }
                ]
            elif "Construction" in ind:
                return [
                    {
                        "title": "Structural & Bridge Design Engineer",
                        "desc": "3D structural frame analysis in STAAD.Pro conforming to IS 456 / IS 1893 seismic codes.",
                        "emp_type": EmploymentType.FULL_TIME,
                        "work_mode": WorkMode.ON_SITE,
                        "salary": "₹8.5 - ₹12.0 LPA",
                        "ctc": 10.0,
                        "min_cgpa": 6.8,
                        "backlogs": 0,
                        "depts": ["CIVIL"],
                        "skills": [("STAAD.Pro", True), ("Structural Analysis", True), ("Concrete Technology", True), ("AutoCAD", False)],
                    },
                    {
                        "title": "Site Execution & Geotechnical Trainee",
                        "desc": "Subgrade soil stabilization, concrete slump testing, and foundation bar bending supervision.",
                        "emp_type": EmploymentType.FULL_TIME,
                        "work_mode": WorkMode.ON_SITE,
                        "salary": "₹7.0 - ₹9.0 LPA",
                        "ctc": 8.0,
                        "min_cgpa": 6.0,
                        "backlogs": 1,
                        "depts": ["CIVIL"],
                        "skills": [("Concrete Technology", True), ("Surveying & Geomatics", True), ("Geotechnical Engineering", False)],
                    }
                ]
            elif "Energy" in ind:
                return [
                    {
                        "title": "Power Systems & Renewable Integration Engineer",
                        "desc": "Grid-scale solar/wind interconnection modeling, substation relay coordination in ETAP.",
                        "emp_type": EmploymentType.FULL_TIME,
                        "work_mode": WorkMode.ON_SITE,
                        "salary": "₹9.0 - ₹13.0 LPA",
                        "ctc": 11.0,
                        "min_cgpa": 6.8,
                        "backlogs": 0,
                        "depts": ["EEE", "MECH"],
                        "skills": [("Power Systems Analysis", True), ("MATLAB & Simulink", True), ("Power Electronics & Drives", False)],
                    }
                ]
            elif "Mining" in ind:
                return [
                    {
                        "title": "Graduate Mining Operations Trainee",
                        "desc": "Open-cast quarry planning, explosive blast vibration analysis, and strata monitoring.",
                        "emp_type": EmploymentType.FULL_TIME,
                        "work_mode": WorkMode.ON_SITE,
                        "salary": "₹9.5 - ₹14.0 LPA",
                        "ctc": 11.5,
                        "min_cgpa": 6.5,
                        "backlogs": 0,
                        "depts": ["MINE", "CIVIL"],
                        "skills": [("Surface & Underground Mining Methods", True), ("Rock Mechanics & Strata Control", True), ("Blasting & Explosives Engineering", False)],
                    }
                ]
            elif "Consulting" in ind:
                return [
                    {
                        "title": "Technology Strategy & Management Consultant",
                        "desc": "Assist enterprise clients with operating model redesign, IT strategy, and analytics.",
                        "emp_type": EmploymentType.FULL_TIME,
                        "work_mode": WorkMode.HYBRID,
                        "salary": "₹12.0 - ₹16.0 LPA",
                        "ctc": 14.5,
                        "min_cgpa": 7.0,
                        "backlogs": 0,
                        "depts": [],  # Open to ALL branches!
                        "skills": [("Data Analysis", False), ("Communication Skills", False)],
                    }
                ]
            elif "Telecom" in ind:
                return [
                    {
                        "title": "Telecom Network Protocol Engineer",
                        "desc": "5G Open RAN baseband signal processing, RF link planning, and packet routing.",
                        "emp_type": EmploymentType.FULL_TIME,
                        "work_mode": WorkMode.ON_SITE,
                        "salary": "₹10.0 - ₹14.0 LPA",
                        "ctc": 12.0,
                        "min_cgpa": 6.5,
                        "backlogs": 0,
                        "depts": ["ECE", "EEE", "CSE"],
                        "skills": [("Wireless Communication", True), ("Computer Networks", True), ("Embedded C / C++", False)],
                    }
                ]
            else:  # Chemical, Biotech, Aerospace
                return [
                    {
                        "title": "Chemical Process Optimization Engineer",
                        "desc": "Aspen Plus simulation of continuous chemical reaction systems, distillation columns, and HAZOP.",
                        "emp_type": EmploymentType.FULL_TIME,
                        "work_mode": WorkMode.ON_SITE,
                        "salary": "₹8.5 - ₹12.0 LPA",
                        "ctc": 10.5,
                        "min_cgpa": 6.5,
                        "backlogs": 0,
                        "depts": ["CHEM"],
                        "skills": [("Aspen Plus", True), ("Chemical Reaction Engineering", True), ("Industrial Safety & HAZOP", False)],
                    }
                ]

        created_jobs: List[Job] = []

        for c_idx, comp in enumerate(companies, start=1):
            job_configs = get_jobs_for_company(comp, c_idx)
            rec_user = recruiter_users[c_idx - 1]

            for j_spec in job_configs:
                job = Job(
                    company_id=comp.id,
                    institution_id=inst.id,  # Scoped to host institution (MBM University)
                    created_by_user_id=rec_user.id,
                    title=f"{j_spec['title']} ({comp.name.split()[0]})",
                    description=j_spec["desc"],
                    employment_type=j_spec["emp_type"],
                    work_mode=j_spec["work_mode"],
                    location=comp.location or "Bengaluru",
                    salary_range=j_spec["salary"],
                    ctc_lpa=Decimal(str(j_spec["ctc"])),
                    base_salary_lpa=Decimal(str(round(j_spec["ctc"] * 0.85, 2))),
                    min_cgpa=Decimal(str(j_spec["min_cgpa"])),
                    target_graduation_year=2026,
                    max_active_backlogs=j_spec["backlogs"],
                    max_total_backlogs=j_spec["backlogs"] + 1,
                    application_deadline=now_utc + timedelta(days=60),
                    status=JobStatus.PUBLISHED,
                    is_active=True,
                )
                session.add(job)
                await session.flush()

                # Eligible Departments
                for d_code in j_spec["depts"]:
                    if d_code in dept_map:
                        session.add(
                            JobEligibleDepartment(job_id=job.id, department_id=dept_map[d_code].id)
                        )

                # Required / Preferred Skills
                for sk_name, is_mand in j_spec["skills"]:
                    session.add(
                        JobSkill(
                            job_id=job.id,
                            skill_name=sk_name,
                            is_mandatory=is_mand,
                            weight_factor=Decimal("1.5" if is_mand else "1.0"),
                        )
                    )

                created_jobs.append(job)

        await session.commit()
        print(f"✓ Created {len(created_jobs)} published job opportunities across all 100 companies.")

        # -------------------------------------------------------------------------
        # 5. Create Institutional Placement Drive & Associate Jobs
        # -------------------------------------------------------------------------
        print("\n--- Creating Campus Placement Drive ---")
        drive_res = await session.execute(
            select(PlacementDrive).where(PlacementDrive.institution_id == inst.id, PlacementDrive.academic_year == "2025-2026").limit(1)
        )
        drive = drive_res.scalar_one_or_none()
        if not drive:
            drive = PlacementDrive(
                institution_id=inst.id,
                created_by_user_id=tpo_user.id,
                name="Annual Campus Placement Drive 2026 [Synthetic]",
                academic_year="2025-2026",
                target_graduation_year=2026,
                registration_start_date=now_utc - timedelta(days=30),
                registration_end_date=now_utc + timedelta(days=60),
                drive_mode=DriveMode.ON_CAMPUS,
                status=DriveStatus.ONGOING,
                lifecycle_phase=DriveLifecyclePhase.ONGOING,
                description="Official coordinated campus placement drive for the Class of 2026.",
            )
            session.add(drive)
            await session.flush()

        # Associate ~40 jobs to this drive for campus drive testing (the rest remain direct applications)
        drive_associated_job_ids = set()
        for idx, j in enumerate(created_jobs[:45]):
            session.add(PlacementDriveJob(drive_id=drive.id, job_id=j.id, is_active=True))
            drive_associated_job_ids.add(j.id)

        await session.commit()
        print(f"✓ Created Placement Drive '{drive.name}' (ID: {drive.id}) with {len(drive_associated_job_ids)} associated drive jobs.")

        # -------------------------------------------------------------------------
        # 6. Generate Exactly 305 Diverse Application Histories
        # Target Stage Breakdown:
        #   - Applied: 50
        #   - Under Review: 40
        #   - Shortlisted: 40
        #   - Interview Scheduled: 30
        #   - Interviewed: 25
        #   - Offered: 25
        #   - Offer Accepted: 15
        #   - Offer Declined: 10
        #   - Rejected: 55
        #   - Withdrawn: 15
        # Total = 305 applications!
        # -------------------------------------------------------------------------
        print("\n--- Generating Exactly 305 Applications Matching Official State Machine ---")

        TARGET_DISTRIBUTION = [
            (ApplicationStatus.APPLIED, 50),
            (ApplicationStatus.UNDER_REVIEW, 40),
            (ApplicationStatus.SHORTLISTED, 40),
            (ApplicationStatus.INTERVIEW_SCHEDULED, 30),
            (ApplicationStatus.INTERVIEWED, 25),
            (ApplicationStatus.OFFERED, 25),
            (ApplicationStatus.OFFER_ACCEPTED, 15),
            (ApplicationStatus.OFFER_DECLINED, 10),
            (ApplicationStatus.REJECTED, 55),
            (ApplicationStatus.WITHDRAWN, 15),
        ]

        total_apps_target = sum(d[1] for d in TARGET_DISTRIBUTION)
        assert total_apps_target == 305, f"Expected 305 target applications, got {total_apps_target}"

        # Clean existing applications for synthetic students
        synth_prof_ids = [p.id for p in student_profiles]
        existing_apps = (
            await session.execute(
                select(JobApplication.id).where(JobApplication.student_id.in_(synth_prof_ids))
            )
        ).scalars().all()
        if existing_apps:
            print(f"  * Removing {len(existing_apps)} existing applications for synthetic students...")
            await session.execute(
                delete(CandidateEvaluation).where(CandidateEvaluation.application_id.in_(existing_apps))
            )
            await session.execute(
                delete(Interview).where(Interview.application_id.in_(existing_apps))
            )
            await session.execute(
                text(f"ALTER TABLE {settings.DB_SCHEMA}.application_status_history DISABLE TRIGGER trg_application_status_history_immutable;")
            )
            try:
                await session.execute(
                    delete(ApplicationStatusHistory).where(ApplicationStatusHistory.application_id.in_(existing_apps))
                )
                await session.execute(delete(JobApplication).where(JobApplication.id.in_(existing_apps)))
                await session.flush()
            finally:
                await session.execute(
                    text(f"ALTER TABLE {settings.DB_SCHEMA}.application_status_history ENABLE TRIGGER trg_application_status_history_immutable;")
                )

        # Find eligible (student, job) pairs
        # Load jobs with their eligible_departments and skills for fast lookup
        full_jobs = (
            await session.execute(
                select(Job).where(Job.id.in_([j.id for j in created_jobs]))
            )
        ).scalars().all()
        job_lookup: Dict[int, Job] = {j.id: j for j in full_jobs}

        # Query all job skills and eligible departments
        j_dept_rows = (await session.execute(select(JobEligibleDepartment))).scalars().all()
        j_depts_map: Dict[int, List[int]] = {}
        for jd in j_dept_rows:
            j_depts_map.setdefault(jd.job_id, []).append(jd.department_id)

        j_skill_rows = (await session.execute(select(JobSkill))).scalars().all()
        j_skills_map: Dict[int, List[JobSkill]] = {}
        for js in j_skill_rows:
            j_skills_map.setdefault(js.job_id, []).append(js)

        # Match eligible pairs
        eligible_pairs: List[Tuple[int, int]] = []  # (student_idx, job_id)

        for s_idx, prof in enumerate(student_profiles):
            u = student_users[s_idx]
            s_dept_id = u.department_id

            for j in created_jobs:
                # 1. Department check
                allowed_depts = j_depts_map.get(j.id, [])
                if allowed_depts and s_dept_id not in allowed_depts:
                    continue
                # 2. CGPA check
                if float(prof.cgpa) < float(j.min_cgpa):
                    continue
                # 3. Backlog check
                if prof.active_backlogs > j.max_active_backlogs:
                    continue
                eligible_pairs.append((s_idx, j.id))

        print(f"  * Discovered {len(eligible_pairs)} fully eligible candidate-job pairing opportunities.")
        random.seed(42)
        random.shuffle(eligible_pairs)

        # Ensure we pick unique (student_id, job_id) pairs
        used_pairs = set()
        selected_pairs: List[Tuple[int, int]] = []
        for s_idx, j_id in eligible_pairs:
            if (s_idx, j_id) not in used_pairs:
                used_pairs.add((s_idx, j_id))
                selected_pairs.append((s_idx, j_id))
            if len(selected_pairs) >= total_apps_target:
                break

        assert len(selected_pairs) == total_apps_target, f"Insufficient eligible pairs ({len(selected_pairs)}) for 305 applications"

        created_applications: List[JobApplication] = []
        app_idx = 0

        for target_status, quota in TARGET_DISTRIBUTION:
            for _ in range(quota):
                s_idx, j_id = selected_pairs[app_idx]
                app_idx += 1

                u = student_users[s_idx]
                prof = student_profiles[s_idx]
                res = student_resumes[s_idx]
                j = job_lookup[j_id]

                is_drive_job = j_id in drive_associated_job_ids
                app_drive_id = drive.id if is_drive_job else None

                # Compute realistic compatibility score
                compat_score = round(65.0 + ((s_idx * 17 + j_id * 13) % 310) / 10.0, 1)  # 65.0 - 96.0%

                # Determine TPO screening status conforming to check constraints
                if app_drive_id is None:
                    tpo_status = TpoScreeningStatus.BYPASSED
                    tpo_screened_by = None
                    tpo_screened_at = None
                else:
                    if target_status == ApplicationStatus.APPLIED:
                        tpo_status = TpoScreeningStatus.PENDING
                        tpo_screened_by = None
                        tpo_screened_at = None
                    elif target_status == ApplicationStatus.REJECTED and (app_idx % 3 == 0):
                        tpo_status = TpoScreeningStatus.REJECTED
                        tpo_screened_by = tpo_user.id
                        tpo_screened_at = now_utc - timedelta(days=10)
                    else:
                        tpo_status = TpoScreeningStatus.SHORTLISTED
                        tpo_screened_by = tpo_user.id
                        tpo_screened_at = now_utc - timedelta(days=12)

                # Determine state-specific fields
                withdrawn_at = None
                withdrawal_reason = None
                if target_status == ApplicationStatus.WITHDRAWN:
                    withdrawn_at = now_utc - timedelta(days=2)
                    withdrawal_reason = random.choice([
                        "Accepted pre-placement offer from summer internship.",
                        "Pursuing higher studies (GATE / Masters admissions).",
                        "Accepted another full-time corporate offer.",
                    ])

                recruiter_decision_at = None
                recruiter_feedback = None
                if target_status in (ApplicationStatus.REJECTED, ApplicationStatus.OFFERED, ApplicationStatus.OFFER_ACCEPTED, ApplicationStatus.OFFER_DECLINED):
                    recruiter_decision_at = now_utc - timedelta(days=1)
                    if target_status == ApplicationStatus.REJECTED:
                        recruiter_feedback = random.choice([
                            "Technical assessment score did not meet current departmental hiring cutoff.",
                            "System design depth in distributed caching fell short of senior hiring bar.",
                            "Candidate demonstrated solid foundations; recommended to re-apply in next hiring cycle.",
                        ])

                offer_package_lpa = None
                offer_deadline_at = None
                offer_notes = None
                if target_status in (ApplicationStatus.OFFERED, ApplicationStatus.OFFER_ACCEPTED, ApplicationStatus.OFFER_DECLINED):
                    offer_package_lpa = j.ctc_lpa
                    offer_deadline_at = now_utc + timedelta(days=14)
                    offer_notes = f"Official campus placement offer of ₹{j.ctc_lpa} LPA extended."

                application = JobApplication(
                    job_id=j.id,
                    student_id=prof.id,
                    resume_id=res.id,
                    drive_id=app_drive_id,
                    tpo_screening_status=tpo_status,
                    tpo_screened_by_user_id=tpo_screened_by,
                    tpo_screened_at=tpo_screened_at,
                    tpo_feedback="Institutional criteria verified." if tpo_screened_by else None,
                    current_status=target_status,
                    recruiter_decision_at=recruiter_decision_at,
                    recruiter_feedback_notes=recruiter_feedback,
                    compatibility_score_at_application=Decimal(str(compat_score)),
                    cover_letter=f"I am excited to apply for the {j.title} role at {j.company.name}.",
                    withdrawn_at=withdrawn_at,
                    withdrawal_reason=withdrawal_reason,
                    offer_package_lpa=offer_package_lpa,
                    offer_deadline_at=offer_deadline_at,
                    offer_notes=offer_notes,
                    created_at=now_utc - timedelta(days=20),
                )
                session.add(application)
                await session.flush()

                # Add Audit Status History Trail
                rec_user_id = j.created_by_user_id
                session.add(
                    ApplicationStatusHistory(
                        application_id=application.id,
                        changed_by_user_id=u.id,
                        decision_domain=DecisionDomain.RECRUITMENT_LIFECYCLE,
                        from_status=None,
                        to_status=ApplicationStatus.APPLIED.value,
                        notes="Candidate applied via portal.",
                        created_at=now_utc - timedelta(days=20),
                    )
                )

                if target_status != ApplicationStatus.APPLIED:
                    if target_status == ApplicationStatus.WITHDRAWN:
                        session.add(
                            ApplicationStatusHistory(
                                application_id=application.id,
                                changed_by_user_id=u.id,
                                decision_domain=DecisionDomain.RECRUITMENT_LIFECYCLE,
                                from_status=ApplicationStatus.APPLIED.value,
                                to_status=ApplicationStatus.WITHDRAWN.value,
                                notes=withdrawal_reason,
                                created_at=withdrawn_at,
                            )
                        )
                    else:
                        session.add(
                            ApplicationStatusHistory(
                                application_id=application.id,
                                changed_by_user_id=rec_user_id,
                                decision_domain=DecisionDomain.RECRUITMENT_LIFECYCLE,
                                from_status=ApplicationStatus.APPLIED.value,
                                to_status=target_status.value,
                                notes=f"Advanced candidate to {target_status.value}.",
                                created_at=now_utc - timedelta(days=5),
                            )
                        )

                # Link Interviews and Evaluations for relevant stages
                if target_status == ApplicationStatus.INTERVIEW_SCHEDULED:
                    session.add(
                        Interview(
                            application_id=application.id,
                            round_number=1,
                            round_title="Technical Round 1",
                            interview_mode=InterviewMode.VIRTUAL,
                            scheduled_start_time=now_utc + timedelta(days=4),
                            duration_minutes=45,
                            interviewer_names="Siddharth Rao (Principal Architect)",
                            status=InterviewStatus.SCHEDULED,
                            outcome=InterviewOutcome.PENDING,
                            created_by_user_id=rec_user_id,
                        )
                    )
                elif target_status in (ApplicationStatus.INTERVIEWED, ApplicationStatus.OFFERED, ApplicationStatus.OFFER_ACCEPTED, ApplicationStatus.OFFER_DECLINED):
                    int_round1 = Interview(
                        application_id=application.id,
                        round_number=1,
                        round_title="Technical Architecture Round",
                        interview_mode=InterviewMode.VIRTUAL,
                        scheduled_start_time=now_utc - timedelta(days=6),
                        duration_minutes=45,
                        interviewer_names="Anand Kumar (Tech Lead)",
                        status=InterviewStatus.COMPLETED,
                        outcome=InterviewOutcome.PASSED,
                        feedback_notes="Strong problem-solving methodology; demonstrated clean code modularity.",
                        created_by_user_id=rec_user_id,
                    )
                    session.add(int_round1)
                    await session.flush()

                    session.add(
                        CandidateEvaluation(
                            application_id=application.id,
                            interview_id=int_round1.id,
                            interviewer_user_id=rec_user_id,
                            interviewer_name="Anand Kumar (Tech Lead)",
                            stage=EvaluationStage.TECHNICAL,
                            technical_rating=4,
                            problem_solving_rating=5,
                            communication_rating=4,
                            project_depth_rating=4,
                            cultural_fit_rating=5,
                            overall_rating=4.4,
                            recommendation=EvaluationRecommendation.STRONG_HIRE,
                            strengths="Fast algorithmic thinking and excellent communication.",
                            weaknesses="Could deepen knowledge of distributed consensus protocols.",
                            written_feedback="Demonstrated strong core fundamentals, structured problem-solving approach, and clear communication.",
                        )
                    )

                created_applications.append(application)

        await session.commit()
        print(f"✓ Successfully created {len(created_applications)} applications conforming to target state distributions.")

        # -------------------------------------------------------------------------
        # 7. Seed Preparation Arena Attempts & Readiness Snapshots
        # -------------------------------------------------------------------------
        print("\n--- Seeding Preparation Arena Attempts & Student Readiness Records ---")
        arena_attempts_count = 0
        readiness_count = 0

        for s_idx in range(50):
            prof = student_profiles[s_idx]
            u = student_users[s_idx]
            dept_code = u.department.code.upper().strip()
            curric = BRANCH_CURRICULUM.get(dept_code, BRANCH_CURRICULUM["CSE"])

            # 1. Arena Attempt
            att = ArenaAttempt(
                student_id=prof.id,
                assessment_id=None,
                mode=ArenaAssessmentMode.TOPIC_PRACTICE,
                category=curric["arena_cat"],
                title=f"{curric['arena_cat'].value.title()} Diagnostic Practice",
                status=ArenaAttemptStatus.SUBMITTED,
                total_questions=10,
                attempted_count=10,
                correct_count=7 + (s_idx % 4),
                accuracy_pct=Decimal(str(round(70.0 + (s_idx % 4) * 10.0, 1))),
                score_pct=Decimal(str(round(70.0 + (s_idx % 4) * 10.0, 1))),
                elapsed_seconds=450 + (s_idx * 15),
                started_at=now_utc - timedelta(days=12),
                submitted_at=now_utc - timedelta(days=12, minutes=-15),
            )
            session.add(att)
            arena_attempts_count += 1

            # 2. Readiness Snapshot
            if s_idx < 35:
                readiness_score = round(68.0 + (float(prof.cgpa) - 6.0) * 8.0, 1)
                readiness_score = max(55.0, min(96.0, readiness_score))
                cat = (
                    ReadinessCategory.EXCELLENT_PREPARATION
                    if readiness_score >= 88.0
                    else (
                        ReadinessCategory.PLACEMENT_READY
                        if readiness_score >= 75.0
                        else ReadinessCategory.NEEDS_IMPROVEMENT
                    )
                )
                snap = ReadinessSnapshot(
                    student_id=prof.id,
                    job_id=created_jobs[s_idx % len(created_jobs)].id,
                    target_role="Software / Core Engineering Trainee",
                    formula_version="v1.0",
                    overall_score=Decimal(str(readiness_score)),
                    category=cat,
                    weights_json={"academic": 0.35, "skills": 0.40, "arena": 0.25},
                    indicators_json=[
                        {"code": "CGPA", "score": float(prof.cgpa) * 10, "status": "verified"},
                        {"code": "ARENA_PRACTICE", "score": readiness_score, "status": "active"},
                    ],
                    academic_summary_json={"cgpa": str(prof.cgpa), "backlogs": prof.active_backlogs},
                    missing_data_fields_json=[],
                    limitations_json=["Historical diagnostic snapshot based on synthetic benchmarks."],
                    remaining_skill_gaps_json=["Docker", "System Architecture"] if readiness_score < 80 else [],
                    recommendations_json=["Review branch-specific practice drills and mock interview technical questions."],
                    transparency_notice=(
                        "Advisory diagnostic index computed for student guidance and benchmark analytics. "
                        "Not used for automated eligibility filtering or gatekeeping."
                    ),
                )
                session.add(snap)
                readiness_count += 1

        await session.commit()
        print(f"✓ Created {arena_attempts_count} Arena practice sessions and {readiness_count} ReadinessSnapshots.")

    # -------------------------------------------------------------------------
    # 8. Final Deliverables Summary
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("🎯 DIVERSE SYNTHETIC PLACEMENT DATASET SEEDING COMPLETE")
    print("=" * 80)
    print(f"• Total Synthetic Students Created:   {len(student_users)}")
    print("  - Branch Distribution:")
    for code, q in STUDENT_QUOTAS:
        print(f"    * {code:6s}: {q:2d} students")
    print(f"• Total Synthetic Companies Created:  {len(companies)}")
    print("  - Industry Distribution (12 Sectors):")
    print(f"    * IT & Software Development: 20   * Manufacturing & Automotive: 10")
    print(f"    * Fintech & Banking Tech:    10   * Construction & Infrastructure: 8")
    print(f"    * AI & Data Science:         10   * Energy & Renewable Energy:     8")
    print(f"    * Cybersecurity:              8   * Mining & Natural Resources:    5")
    print(f"    * Electronics & Semi:         8   * Consulting & Business Svcs:    5")
    print(f"    * Telecom & Networking:       4   * Chemical & Advanced Materials: 4")
    print(f"• Total Published Jobs Created:       {len(created_jobs)}")
    print(f"• Total Applications Generated:       {len(created_applications)}")
    print("  - Application Status Distribution:")
    for status, q in TARGET_DISTRIBUTION:
        print(f"    * {status.value:20s}: {q:2d}")
    print(f"• Preparation Arena Practice Records: {arena_attempts_count}")
    print(f"• Student Readiness Snapshots:        {readiness_count}")
    print("=" * 80)
    print("Sample Test Accounts for Portal Exploration:")
    print("  1. CSE Student (High CGPA 9.4, 0 Backlogs):")
    print("     Email: student.cse01@campus.example.test | Password: DemoPassword2026!")
    print("  2. Civil Student (CGPA 7.8, Infrastructure Ready):")
    print("     Email: student.civil01@campus.example.test | Password: DemoPassword2026!")
    print("  3. Mechanical Student (CGPA 8.2, Automotive CAD Skills):")
    print("     Email: student.mech01@campus.example.test | Password: DemoPassword2026!")
    print("  4. IT Corporate Recruiter (Nexus Cloud Systems):")
    print("     Email: recruiter.c001@partner.example.test | Password: DemoPassword2026!")
    print("  5. Institutional Head TPO Officer:")
    print("     Email: tpo.officer@apex.edu | Password: DemoPassword2026!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(seed_diverse_dataset())

