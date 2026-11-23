"""Curated subjects, metadata, practice questions, and interview blueprints for the 40 CSE curriculum subjects."""
from typing import Any, Dict, List
from app.models.arena import ArenaCategory, ArenaDifficulty, ArenaQuestionType

# 1. Complete ordered list of the 40 official CSE Subjects
CSE_40_CATEGORIES_LIST: List[ArenaCategory] = [
    ArenaCategory.PROGRAMMING_FUNDAMENTALS,    # 1. Introduction to Computer Programming
    ArenaCategory.CS_MATHS_FOR_COMPUTING,     # 2. MATHS FOR COMPUTING
    ArenaCategory.CS_POPL,                    # 3. PRINCIPLES OF PROGRAMMING LANGUAGES
    ArenaCategory.OOP,                        # 4. OBJECT ORIENTED PROGRAMMING
    ArenaCategory.DSA,                        # 5. DATA STRUCTURES AND ALGORITHMS
    ArenaCategory.CS_LOGIC_DESIGN,            # 6. LOGIC DESIGN
    ArenaCategory.CS_CYBER_LAW_ETHICS,        # 7. PROFESSIONAL PRACTICE, CYBER LAW AND ETHICS
    ArenaCategory.CS_DAA,                     # 8. DESIGN AND ANALYSIS OF ALGORITHMS
    ArenaCategory.CS_WEB_TECHNOLOGIES,        # 9. WEB TECHNOLOGIES
    ArenaCategory.COMPUTER_NETWORKS,          # 10. COMPUTER NETWORKS
    ArenaCategory.DBMS,                       # 11. DATABASE MANAGEMENT SYSTEMS
    ArenaCategory.CS_COA,                     # 12. COMPUTER ORGANIZATION AND ARCHITECTURE
    ArenaCategory.CS_SOFTWARE_ENGINEERING,    # 13. SOFTWARE ENGINEERING
    ArenaCategory.OPERATING_SYSTEMS,          # 14. OPERATING SYSTEMS
    ArenaCategory.CS_THEORY_OF_COMPUTATION,   # 15. THEORY OF COMPUTATION
    ArenaCategory.CS_AIML,                    # 16. ARTIFICIAL INTELLIGENCE AND MACHINE LEARNING
    ArenaCategory.CS_MICROPROCESSORS,         # 17. MICROPROCESSORS AND ASSEMBLY PROGRAMMING
    ArenaCategory.CS_COMPUTER_GRAPHICS,       # 18. COMPUTER GRAPHICS
    ArenaCategory.CS_JAVA_PROGRAMMING,        # 19. JAVA PROGRAMMING
    ArenaCategory.CS_ROBOTICS_EMBEDDED,       # 20. ROBOTICS AND EMBEDDED SYSTEM
    ArenaCategory.CS_COMPILER_DESIGN,         # 21. PRINCIPLES OF COMPILER DESIGN
    ArenaCategory.CS_IMAGE_PROCESSING,        # 22. IMAGE PROCESSING
    ArenaCategory.CS_SYSTEM_PROGRAMMING,      # 23. SYSTEM PROGRAMMING
    ArenaCategory.CS_ADVANCED_ML,             # 24. ADVANCED MACHINE LEARNING
    ArenaCategory.CS_GRAPHS_NETWORKS,         # 25. GRAPHS AND SOCIAL NETWORKS
    ArenaCategory.CS_NLP,                     # 26. NATURAL LANGUAGE PROCESSING
    ArenaCategory.CS_ECOMMERCE_BI,            # 27. ECOMMERCE AND BUSINESS INTELLIGENCE
    ArenaCategory.CS_WIRELESS_MOBILE,         # 28. WIRELESS AND MOBILE COMPUTING
    ArenaCategory.CS_MODERN_WEB_DEV,          # 29. MODERN WEB DEVELOPMENT
    ArenaCategory.CS_DISTRIBUTED_COMPUTING,   # 30. DISTRIBUTED COMPUTING
    ArenaCategory.CS_DATA_SCIENCE_ANALYTICS,  # 31. DATA SCIENCE & ANALYTICS
    ArenaCategory.CS_CRYPTOGRAPHY_SECURITY,   # 32. CRYPTOGRAPHY AND NETWORK SECURITY
    ArenaCategory.CS_BLOCKCHAIN,              # 33. BLOCKCHAIN
    ArenaCategory.CS_BIOMETRICS_BIOSIGNAL,    # 34. BIOMETRICS AND BIO-SIGNAL PROCESSING
    ArenaCategory.CS_PARALLEL_GPU,            # 35. PARALLEL AND GPU COMPUTING
    ArenaCategory.CS_DEEP_LEARNING,           # 36. DEEP LEARNING
    ArenaCategory.CS_COMPUTER_VISION,         # 37. COMPUTER VISION
    ArenaCategory.CS_IOT,                     # 38. INTERNET OF THINGS
    ArenaCategory.CS_BIG_DATA_IR,             # 39. INFORMATION RETRIEVAL AND BIG DATA
    ArenaCategory.CS_CYBER_SECURITY,          # 40. CYBER SECURITY
]

# 2. Metadata: Official titles & placement-oriented syllabus descriptions
CSE_40_METADATA: Dict[ArenaCategory, Dict[str, str]] = {
    ArenaCategory.PROGRAMMING_FUNDAMENTALS: {
        "label": "Introduction to Computer Programming",
        "description": "Variables, data types, conditional branching, loops, functions, memory layout, and basic recursion.",
    },
    ArenaCategory.CS_MATHS_FOR_COMPUTING: {
        "label": "Maths for Computing",
        "description": "Discrete mathematics, propositional logic, set theory, combinatorics, probability, and linear algebra for CS.",
    },
    ArenaCategory.CS_POPL: {
        "label": "Principles of Programming Languages",
        "description": "Language paradigms, syntax & semantics, type systems, memory management, closures, and runtime environments.",
    },
    ArenaCategory.OOP: {
        "label": "Object Oriented Programming",
        "description": "Encapsulation, inheritance, polymorphism, abstraction, design patterns, SOLID principles, and interfaces.",
    },
    ArenaCategory.DSA: {
        "label": "Data Structures and Algorithms",
        "description": "Arrays, linked lists, stacks, queues, trees, heaps, graphs, hashing, sorting, and algorithmic complexity.",
    },
    ArenaCategory.CS_LOGIC_DESIGN: {
        "label": "Logic Design",
        "description": "Boolean algebra, Karnaugh maps, combinational logic, sequential circuits, flip-flops, counters, and finite state machines.",
    },
    ArenaCategory.CS_CYBER_LAW_ETHICS: {
        "label": "Professional Practice, Cyber Law and Ethics",
        "description": "IT Act, data privacy, intellectual property, cybercrime, software licensing, and professional engineering ethics.",
    },
    ArenaCategory.CS_DAA: {
        "label": "Design and Analysis of Algorithms",
        "description": "Divide and conquer, greedy algorithms, dynamic programming, branch and bound, amortized analysis, and NP-completeness.",
    },
    ArenaCategory.CS_WEB_TECHNOLOGIES: {
        "label": "Web Technologies",
        "description": "HTML5, CSS3, DOM manipulation, client-server architecture, HTTP protocol, RESTful APIs, and basic web security.",
    },
    ArenaCategory.COMPUTER_NETWORKS: {
        "label": "Computer Networks",
        "description": "OSI and TCP/IP stack, IP addressing, subnetting, routing protocols, flow & congestion control, TCP vs UDP.",
    },
    ArenaCategory.DBMS: {
        "label": "Database Management Systems",
        "description": "Relational algebra, SQL, normalization (1NF-BCNF), transactions, ACID properties, indexing, and query optimization.",
    },
    ArenaCategory.CS_COA: {
        "label": "Computer Organization and Architecture",
        "description": "Instruction set architecture (RISC/CISC), pipelining, hazards, memory hierarchy, cache mapping, and I/O organization.",
    },
    ArenaCategory.CS_SOFTWARE_ENGINEERING: {
        "label": "Software Engineering",
        "description": "SDLC models, Agile/Scrum, requirement engineering, UML modeling, software testing (black-box/white-box), CI/CD.",
    },
    ArenaCategory.OPERATING_SYSTEMS: {
        "label": "Operating Systems",
        "description": "Process management, threads, CPU scheduling, inter-process communication, synchronization, deadlocks, paging, virtual memory.",
    },
    ArenaCategory.CS_THEORY_OF_COMPUTATION: {
        "label": "Theory of Computation",
        "description": "Regular languages, finite automata (DFA/NFA), context-free grammars, pushdown automata, Turing machines, and decidability.",
    },
    ArenaCategory.CS_AIML: {
        "label": "Artificial Intelligence and Machine Learning",
        "description": "Search heuristics (A*), minimax, supervised learning, regression, classification, clustering, evaluation metrics (F1/AUC).",
    },
    ArenaCategory.CS_MICROPROCESSORS: {
        "label": "Microprocessors and Assembly Programming",
        "description": "8085/8086 architectures, x86/ARM registers, addressing modes, assembly instructions, interrupts, and peripheral interfacing.",
    },
    ArenaCategory.CS_COMPUTER_GRAPHICS: {
        "label": "Computer Graphics",
        "description": "Rasterization, Bresenham line algorithm, 2D/3D transformations, projection, viewing pipeline, clipping, and shading models.",
    },
    ArenaCategory.CS_JAVA_PROGRAMMING: {
        "label": "Java Programming",
        "description": "JVM architecture, bytecode, memory model, Garbage Collection, multithreading, concurrency, Collections framework, Generics.",
    },
    ArenaCategory.CS_ROBOTICS_EMBEDDED: {
        "label": "Robotics and Embedded System",
        "description": "Microcontrollers, RTOS scheduling, GPIO/timers/UART/SPI/I2C, sensor integration, actuator control, kinematics.",
    },
    ArenaCategory.CS_COMPILER_DESIGN: {
        "label": "Principles of Compiler Design",
        "description": "Lexical analysis (lex/flex), parsing (LL, LR, LALR), intermediate representations, syntax-directed translation, code optimization.",
    },
    ArenaCategory.CS_IMAGE_PROCESSING: {
        "label": "Image Processing",
        "description": "Spatial filtering, convolution, Fourier transform, edge detection (Sobel, Canny), histogram equalization, morphological operations.",
    },
    ArenaCategory.CS_SYSTEM_PROGRAMMING: {
        "label": "System Programming",
        "description": "Linkers, loaders, macro processors, ELF binaries, POSIX system calls, process control (fork/exec), signal handling.",
    },
    ArenaCategory.CS_ADVANCED_ML: {
        "label": "Advanced Machine Learning",
        "description": "Ensemble methods (Random Forest, XGBoost), SVMs, kernel methods, dimensionality reduction (PCA, t-SNE), Bayesian learning.",
    },
    ArenaCategory.CS_GRAPHS_NETWORKS: {
        "label": "Graphs and Social Networks",
        "description": "Network centrality measures (degree, betweenness, PageRank), community detection, random graph models, graph algorithms.",
    },
    ArenaCategory.CS_NLP: {
        "label": "Natural Language Processing",
        "description": "Tokenization, lemmatization, N-grams, TF-IDF, Word2Vec, GloVe, recurrent networks (LSTM/GRU), and transformers (BERT/GPT).",
    },
    ArenaCategory.CS_ECOMMERCE_BI: {
        "label": "Ecommerce and Business Intelligence",
        "description": "Data warehousing, OLAP cubes, ETL pipelines, recommendation systems, customer churn analysis, conversion metrics.",
    },
    ArenaCategory.CS_WIRELESS_MOBILE: {
        "label": "Wireless and Mobile Computing",
        "description": "Cellular concepts (handoff, frequency reuse), Wi-Fi (802.11), Mobile IP, wireless routing (AODV/DSR), 4G/5G architectures.",
    },
    ArenaCategory.CS_MODERN_WEB_DEV: {
        "label": "Modern Web Development",
        "description": "Single-page applications (React/Next), Virtual DOM, asynchronous state management, WebSockets, SSR/SSG, responsive design.",
    },
    ArenaCategory.CS_DISTRIBUTED_COMPUTING: {
        "label": "Distributed Computing",
        "description": "CAP theorem, Paxos/Raft consensus, distributed clocks (Lamport/Vector), RPC/gRPC, microservices, horizontal scaling.",
    },
    ArenaCategory.CS_DATA_SCIENCE_ANALYTICS: {
        "label": "Data Science & Analytics",
        "description": "Exploratory data analysis, Pandas/NumPy, hypothesis testing, A/B testing, statistical inference, feature engineering.",
    },
    ArenaCategory.CS_CRYPTOGRAPHY_SECURITY: {
        "label": "Cryptography and Network Security",
        "description": "Symmetric/asymmetric ciphers (AES, RSA, ECC), cryptographic hashing (SHA-256), HMAC, digital signatures, PKI, TLS/SSL.",
    },
    ArenaCategory.CS_BLOCKCHAIN: {
        "label": "Blockchain",
        "description": "Distributed ledgers, proof-of-work/proof-of-stake, Merkle trees, smart contracts (Solidity), gas optimization, decentralization.",
    },
    ArenaCategory.CS_BIOMETRICS_BIOSIGNAL: {
        "label": "Biometrics and Bio-Signal Processing",
        "description": "Fingerprint/iris recognition, FAR/FRR metrics, ECG/EEG signal acquisition, bandpass filtering, feature extraction.",
    },
    ArenaCategory.CS_PARALLEL_GPU: {
        "label": "Parallel and GPU Computing",
        "description": "OpenMP, MPI message passing, CUDA threads/warps/blocks, shared vs global GPU memory, parallel speedup (Amdahl's law).",
    },
    ArenaCategory.CS_DEEP_LEARNING: {
        "label": "Deep Learning",
        "description": "Backpropagation, gradient descent variants (Adam), CNNs, RNNs, vanishing gradients, attention mechanisms, normalization.",
    },
    ArenaCategory.CS_COMPUTER_VISION: {
        "label": "Computer Vision",
        "description": "Feature detectors (SIFT/ORB), optical flow, object detection (YOLO, Faster R-CNN), semantic segmentation (U-Net).",
    },
    ArenaCategory.CS_IOT: {
        "label": "Internet of Things",
        "description": "IoT protocols (MQTT, CoAP), edge computing, low-power sensor networks (Zigbee/LoRa), gateway architectures.",
    },
    ArenaCategory.CS_BIG_DATA_IR: {
        "label": "Information Retrieval and Big Data",
        "description": "Inverted index, vector space model, BM25, MapReduce, Apache Spark, HDFS, distributed caching, stream processing (Kafka).",
    },
    ArenaCategory.CS_CYBER_SECURITY: {
        "label": "Cyber Security",
        "description": "Vulnerability scanning, penetration testing, OWASP Top 10 (SQLi, XSS, CSRF), zero-trust architecture, threat modeling.",
    },
}

# 3. Authentic Placement MCQs for the newly added subjects
CSE_40_QUESTIONS: List[Dict[str, Any]] = [
    # 2. MATHS FOR COMPUTING
    {
        "title": "Recurrence Relation Solution via Master Theorem",
        "prompt_text": "Consider the recurrence relation T(n) = 4T(n/2) + n^2. According to the Master Theorem, what is the tight asymptotic bound for T(n)?",
        "category": ArenaCategory.CS_MATHS_FOR_COMPUTING,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 90,
        "company_tag": "Amazon",
        "role_tags": ["cse", "maths_computing", "algorithms"],
        "options": [
            {"key": "A", "text": "Theta(n^2)"},
            {"key": "B", "text": "Theta(n^2 log n)"},
            {"key": "C", "text": "Theta(n^3)"},
            {"key": "D", "text": "Theta(n log n)"},
        ],
        "correct_option_key": "B",
        "explanation_text": "Here a = 4, b = 2, so n^(log_b a) = n^(log_2 4) = n^2. Since f(n) = n^2 = Theta(n^(log_b a)), this falls into Case 2 of Master Theorem, giving T(n) = Theta(n^2 log n).",
    },
    {
        "title": "Eigenvalues of Idempotent Matrix in Dimensionality Analysis",
        "prompt_text": "In computer vision and data transformations, a projection matrix P satisfies P^2 = P. What are the only possible eigenvalues of P?",
        "category": ArenaCategory.CS_MATHS_FOR_COMPUTING,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Microsoft",
        "role_tags": ["cse", "maths_computing", "linear_algebra"],
        "options": [
            {"key": "A", "text": "-1 and 1"},
            {"key": "B", "text": "0 and 1"},
            {"key": "C", "text": "Any real number"},
            {"key": "D", "text": "0 and -1"},
        ],
        "correct_option_key": "B",
        "explanation_text": "If lambda is an eigenvalue of P with eigenvector x, then P x = lambda x. Since P^2 = P, P^2 x = lambda^2 x = lambda x. Thus lambda^2 - lambda = 0 => lambda = 0 or 1.",
    },

    # 3. PRINCIPLES OF PROGRAMMING LANGUAGES
    {
        "title": "Call-by-Reference vs Call-by-Value Semantics",
        "prompt_text": "In programming language evaluation semantics, what is the primary operational distinction between Call-by-Reference and Call-by-Value-Result (copy-in copy-out)?",
        "category": ArenaCategory.CS_POPL,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 75,
        "company_tag": "Google",
        "role_tags": ["cse", "popl", "programming_languages"],
        "options": [
            {"key": "A", "text": "Call-by-Reference uses heap memory while copy-in copy-out uses registers"},
            {"key": "B", "text": "Call-by-Reference immediately mutates the actual caller variable via address aliasing, whereas Call-by-Value-Result copies the value back only upon normal function return"},
            {"key": "C", "text": "Call-by-Value-Result prevents passing pointers entirely"},
            {"key": "D", "text": "There is no semantic difference in execution outcome"},
        ],
        "correct_option_key": "B",
        "explanation_text": "In Call-by-Reference, parameter changes are instantly visible through the caller alias. In copy-in copy-out, changes happen to a local copy and are written back only when the function terminates.",
    },

    # 6. LOGIC DESIGN
    {
        "title": "Glitch Prevention in Asynchronous Ripple Counters",
        "prompt_text": "Why are synchronous counters preferred over ripple (asynchronous) counters in high-speed digital circuit and CPU designs?",
        "category": ArenaCategory.CS_LOGIC_DESIGN,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Intel",
        "role_tags": ["cse", "logic_design", "digital_circuits"],
        "options": [
            {"key": "A", "text": "Ripple counters require more flip-flops for the same modulus"},
            {"key": "B", "text": "Cumulative propagation delay through cascaded flip-flops in ripple counters causes output glitches and limits maximum clock frequency"},
            {"key": "C", "text": "Synchronous counters consume zero dynamic power"},
            {"key": "D", "text": "Ripple counters cannot count in binary format"},
        ],
        "correct_option_key": "B",
        "explanation_text": "In ripple counters, each flip-flop clock is driven by the preceding stage, accumulating propagation delay (n * t_pd). In synchronous counters, all stages are triggered simultaneously by a common clock.",
    },

    # 7. PROFESSIONAL PRACTICE, CYBER LAW AND ETHICS
    {
        "title": "Section 66A and 43A of Indian IT Act, 2000",
        "prompt_text": "Under Section 43A of the Information Technology (Amendment) Act 2008, what is a corporate body handling Sensitive Personal Data or Information (SPDI) legally mandated to maintain?",
        "category": ArenaCategory.CS_CYBER_LAW_ETHICS,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "TCS",
        "role_tags": ["cse", "cyber_law", "compliance"],
        "options": [
            {"key": "A", "text": "Mandatory storage of all user data on government servers"},
            {"key": "B", "text": "Reasonable security practices and procedures (RSPP) to prevent wrongful loss or wrongful gain"},
            {"key": "C", "text": "Open-sourcing all backend source code under GPL licenses"},
            {"key": "D", "text": "Immediate permanent deletion of all logs after 24 hours"},
        ],
        "correct_option_key": "B",
        "explanation_text": "Section 43A of the IT Act mandates that any body corporate possessing or handling sensitive personal data in a computer resource must implement and maintain reasonable security practices and procedures.",
    },

    # 8. DESIGN AND ANALYSIS OF ALGORITHMS
    {
        "title": "Dynamic Programming: Longest Common Subsequence State Transition",
        "prompt_text": "When computing the Longest Common Subsequence of strings X[1..m] and Y[1..n], what is the optimal substructure relation when X[i] == Y[j]?",
        "category": ArenaCategory.CS_DAA,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Google",
        "role_tags": ["cse", "daa", "dynamic_programming"],
        "options": [
            {"key": "A", "text": "LCS(i, j) = 1 + LCS(i-1, j-1)"},
            {"key": "B", "text": "LCS(i, j) = max(LCS(i-1, j), LCS(i, j-1))"},
            {"key": "C", "text": "LCS(i, j) = 1 + max(LCS(i-1, j), LCS(i, j-1))"},
            {"key": "D", "text": "LCS(i, j) = LCS(i-1, j-1)"},
        ],
        "correct_option_key": "A",
        "explanation_text": "When current characters match, X[i] == Y[j], that character contributes 1 to the common sequence, extending the optimal solution of the prefixes X[1..i-1] and Y[1..j-1].",
    },

    # 9. WEB TECHNOLOGIES
    {
        "title": "CORS Preflight (OPTIONS) Request Triggers",
        "prompt_text": "In modern browser security, which of the following conditions triggers a Cross-Origin Resource Sharing (CORS) preflight request using HTTP OPTIONS?",
        "category": ArenaCategory.CS_WEB_TECHNOLOGIES,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Uber",
        "role_tags": ["cse", "web_technologies", "networking"],
        "options": [
            {"key": "A", "text": "A standard GET request with Accept: text/html"},
            {"key": "B", "text": "A POST request with Content-Type: application/json"},
            {"key": "C", "text": "A POST request with Content-Type: application/x-www-form-urlencoded"},
            {"key": "D", "text": "A HEAD request without custom headers"},
        ],
        "correct_option_key": "B",
        "explanation_text": "Content-Type: application/json is not a 'simple' CORS content type (which only includes application/x-www-form-urlencoded, multipart/form-data, and text/plain), triggering an OPTIONS preflight check.",
    },

    # 12. COMPUTER ORGANIZATION AND ARCHITECTURE
    {
        "title": "Pipeline Data Hazards and Operand Forwarding",
        "prompt_text": "In a standard 5-stage RISC processor pipeline (IF, ID, EX, MEM, WB), how does operand forwarding (bypassing) mitigate data hazards?",
        "category": ArenaCategory.CS_COA,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 75,
        "company_tag": "Qualcomm",
        "role_tags": ["cse", "coa", "hardware_architecture"],
        "options": [
            {"key": "A", "text": "By pausing the clock for 3 cycles whenever an instruction reads a register"},
            {"key": "B", "text": "By routing the computed ALU result directly from EX/MEM or MEM/WB pipeline registers to the ALU input of the dependent instruction"},
            {"key": "C", "text": "By duplicating all physical CPU registers for speculative execution"},
            {"key": "D", "text": "By converting all conditional branches into unconditional jumps"},
        ],
        "correct_option_key": "B",
        "explanation_text": "Forwarding hardware detects data hazards between consecutive instructions and feeds the newly computed result directly to the ALU without waiting for the WB (Write Back) stage.",
    },

    # 13. SOFTWARE ENGINEERING
    {
        "title": "Cyclomatic Complexity Calculation",
        "prompt_text": "In McCabe's cyclomatic complexity metric for a program control flow graph with E edges, N nodes, and P connected components, what is the formula for V(G)?",
        "category": ArenaCategory.CS_SOFTWARE_ENGINEERING,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Infosys",
        "role_tags": ["cse", "software_engineering", "testing"],
        "options": [
            {"key": "A", "text": "V(G) = E - N + 2P"},
            {"key": "B", "text": "V(G) = N - E + P"},
            {"key": "C", "text": "V(G) = E + N - 2"},
            {"key": "D", "text": "V(G) = (E * N) / P"},
        ],
        "correct_option_key": "A",
        "explanation_text": "McCabe's cyclomatic complexity is given by V(G) = E - N + 2P (or E - N + 2 for a single program component where P = 1), defining the number of linearly independent paths.",
    },

    # 15. THEORY OF COMPUTATION
    {
        "title": "Pumping Lemma Application for Context-Free Languages",
        "prompt_text": "According to the Pumping Lemma for Context-Free Languages, any sufficiently long string s in CFL L can be decomposed into s = uvwxy such that which condition holds?",
        "category": ArenaCategory.CS_THEORY_OF_COMPUTATION,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 75,
        "company_tag": "Adobe",
        "role_tags": ["cse", "toc", "formal_languages"],
        "options": [
            {"key": "A", "text": "|vwx| <= p, |vx| >= 1, and u v^i w x^i y is in L for all i >= 0"},
            {"key": "B", "text": "|uv| <= p, |v| >= 1, and u v^i w is in L for all i >= 0"},
            {"key": "C", "text": "|w| >= p and u v w x y is regular"},
            {"key": "D", "text": "v = x = empty string"},
        ],
        "correct_option_key": "A",
        "explanation_text": "The CFL pumping lemma requires |vwx| <= p, |vx| >= 1 (at least one of v or x is non-empty), and for all i >= 0, pumping v and x simultaneously (u v^i w x^i y) remains in L.",
    },

    # 16. ARTIFICIAL INTELLIGENCE AND MACHINE LEARNING
    {
        "title": "Admissibility in A* Search Algorithm",
        "prompt_text": "In A* heuristic search, what condition guarantees that A* will always return an optimal (shortest path) solution when finding a path on a graph?",
        "category": ArenaCategory.CS_AIML,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Google",
        "role_tags": ["cse", "aiml", "search_algorithms"],
        "options": [
            {"key": "A", "text": "The heuristic h(n) must never underestimate the true cost to reach the goal (admissible)"},
            {"key": "B", "text": "The heuristic must always equal zero (uniform-cost search)"},
            {"key": "C", "text": "The heuristic must overestimate the cost by at least 10%"},
            {"key": "D", "text": "The graph must be a directed acyclic tree"},
        ],
        "correct_option_key": "A",
        "explanation_text": "An admissible heuristic never overestimates the actual cost to reach the goal (h(n) <= h*(n)). On tree search, admissibility guarantees optimality (and consistency/monotonicity guarantees optimality on graphs).",
    },

    # 17. MICROPROCESSORS AND ASSEMBLY PROGRAMMING
    {
        "title": "8086 Memory Segmentation and Physical Address Calculation",
        "prompt_text": "In 8086 architecture, if Data Segment DS = 2300H and Offset Register SI = 0150H, what is the resulting 20-bit physical memory address generated on the bus?",
        "category": ArenaCategory.CS_MICROPROCESSORS,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Intel",
        "role_tags": ["cse", "microprocessors", "assembly"],
        "options": [
            {"key": "A", "text": "23150H"},
            {"key": "B", "text": "24500H"},
            {"key": "C", "text": "02450H"},
            {"key": "D", "text": "23015H"},
        ],
        "correct_option_key": "A",
        "explanation_text": "Physical Address = (Segment Register * 10H) + Offset = (2300H * 10H) + 0150H = 23000H + 0150H = 23150H.",
    },

    # 18. COMPUTER GRAPHICS
    {
        "title": "Bresenham's Integer Line Drawing Algorithm",
        "prompt_text": "What is the primary computational advantage of Bresenham's line algorithm over the Digital Differential Analyzer (DDA) method?",
        "category": ArenaCategory.CS_COMPUTER_GRAPHICS,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Nvidia",
        "role_tags": ["cse", "graphics", "rasterization"],
        "options": [
            {"key": "A", "text": "It supports anti-aliasing natively"},
            {"key": "B", "text": "It uses solely fast integer addition and bit-shifts, completely eliminating floating-point multiplications and rounding operations"},
            {"key": "C", "text": "It calculates lines directly on GPU tensor cores"},
            {"key": "D", "text": "It requires only 1 bit per pixel"},
        ],
        "correct_option_key": "B",
        "explanation_text": "Bresenham's algorithm formulates the decision variable using incremental integer arithmetic only, whereas DDA requires floating-point additions and round-off conversions per step.",
    },

    # 19. JAVA PROGRAMMING
    {
        "title": "Java Memory Model: Happens-Before Guarantee of Volatile",
        "prompt_text": "In the Java Memory Model (JMM), what does declaring a field as 'volatile' guarantee across concurrent threads?",
        "category": ArenaCategory.CS_JAVA_PROGRAMMING,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Oracle",
        "role_tags": ["cse", "java", "concurrency"],
        "options": [
            {"key": "A", "text": "It acquires an exclusive re-entrant lock on the variable for atomic multi-step operations like count++"},
            {"key": "B", "text": "It ensures memory visibility (reads always see the latest write from main memory) and prevents instruction reordering around reads/writes"},
            {"key": "C", "text": "It prevents the object from being garbage collected"},
            {"key": "D", "text": "It forces the variable to be allocated in thread-local native stack memory"},
        ],
        "correct_option_key": "B",
        "explanation_text": "Volatile provides visibility and ordering guarantees via memory barriers (preventing compiler/CPU reordering), but does NOT guarantee compound atomicity (such as incrementing a counter).",
    },

    # 20. ROBOTICS AND EMBEDDED SYSTEM
    {
        "title": "Priority Inversion and Priority Ceiling Protocol",
        "prompt_text": "In Real-Time Operating Systems (RTOS), what is Priority Inversion, and how does Priority Inheritance mitigate it?",
        "category": ArenaCategory.CS_ROBOTICS_EMBEDDED,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 75,
        "company_tag": "Bosch",
        "role_tags": ["cse", "robotics", "embedded_systems"],
        "options": [
            {"key": "A", "text": "When a low-priority task is permanently terminated by a hardware watchdog"},
            {"key": "B", "text": "When a medium-priority task preempts a low-priority task that holds a mutex required by a high-priority task; mitigated by temporarily elevating the low-priority task's priority to that of the high-priority task"},
            {"key": "C", "text": "When interrupts occur faster than the CPU clock frequency"},
            {"key": "D", "text": "When the RTOS scheduler switches from preemptive to cooperative mode"},
        ],
        "correct_option_key": "B",
        "explanation_text": "Priority Inversion happens when a medium task delays a high task indirectly by preempting a low task holding a shared resource. Under Priority Inheritance, the low task inherits the high priority until releasing the resource.",
    },

    # 21. PRINCIPLES OF COMPILER DESIGN
    {
        "title": "LR(1) vs LALR(1) Parsing Table States",
        "prompt_text": "What is the key transformation that produces an LALR(1) parser from a canonical LR(1) parser?",
        "category": ArenaCategory.CS_COMPILER_DESIGN,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 75,
        "company_tag": "Apple",
        "role_tags": ["cse", "compiler_design", "parsing"],
        "options": [
            {"key": "A", "text": "Eliminating all reduce actions and replacing them with shift actions"},
            {"key": "B", "text": "Merging LR(1) states that have identical core sets of items but different lookahead sets"},
            {"key": "C", "text": "Converting non-deterministic finite automata directly into pushdown automata"},
            {"key": "D", "text": "Restricting grammar rules to Chomsky Normal Form"},
        ],
        "correct_option_key": "B",
        "explanation_text": "LALR(1) compresses the canonical LR(1) table by merging states with the same core LR(0) items, greatly reducing state count (matching SLR(1) state count) while retaining LR(1) power without introducing shift-reduce conflicts.",
    },

    # 22. IMAGE PROCESSING
    {
        "title": "Sobel Operator vs Laplacian Filter for Edge Detection",
        "prompt_text": "Why is the Sobel operator classified as a first-order derivative filter, whereas the Laplacian operator is second-order?",
        "category": ArenaCategory.CS_IMAGE_PROCESSING,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Samsung",
        "role_tags": ["cse", "image_processing", "computer_vision"],
        "options": [
            {"key": "A", "text": "Sobel detects zero-crossings, while Laplacian detects gradient magnitude peaks"},
            {"key": "B", "text": "Sobel computes directional gradient vectors (dI/dx, dI/dy), whereas Laplacian computes isotropic divergence (d^2I/dx^2 + d^2I/dy^2)"},
            {"key": "C", "text": "Sobel operates exclusively in frequency domain via FFT"},
            {"key": "D", "text": "Laplacian filter is unaffected by image noise"},
        ],
        "correct_option_key": "B",
        "explanation_text": "Sobel calculates first partial derivatives to find gradient magnitude and direction. Laplacian computes the sum of second derivatives, detecting edges at zero-crossing points (though it is highly noise-sensitive).",
    },

    # 23. SYSTEM PROGRAMMING
    {
        "title": "ELF Binary Sections and Relocation",
        "prompt_text": "In Linux Executable and Linkable Format (ELF) object files, which section holds initialized global and static variables with non-zero values?",
        "category": ArenaCategory.CS_SYSTEM_PROGRAMMING,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Red Hat",
        "role_tags": ["cse", "system_programming", "linux"],
        "options": [
            {"key": "A", "text": ".bss"},
            {"key": "B", "text": ".data"},
            {"key": "C", "text": ".text"},
            {"key": "D", "text": ".rodata"},
        ],
        "correct_option_key": "B",
        "explanation_text": ".data stores initialized global and static variables. .bss stores uninitialized/zero-initialized globals (occupying no space on disk). .text holds compiled code, and .rodata stores constants.",
    },

    # 24. ADVANCED MACHINE LEARNING
    {
        "title": "Gradient Boosting: Residual Fitting in XGBoost",
        "prompt_text": "In gradient boosting frameworks like XGBoost, how does each new weak learner (decision tree) fit into the ensemble?",
        "category": ArenaCategory.CS_ADVANCED_ML,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 75,
        "company_tag": "Meta",
        "role_tags": ["cse", "advanced_ml", "gradient_boosting"],
        "options": [
            {"key": "A", "text": "It trains on independent bootstrap samples of the original labels in parallel"},
            {"key": "B", "text": "It is sequentially trained to predict the negative gradient (pseudo-residuals) of the loss function with respect to current ensemble predictions"},
            {"key": "C", "text": "It adjusts sample weights according to AdaBoost exponential loss only"},
            {"key": "D", "text": "It applies k-means clustering to select features"},
        ],
        "correct_option_key": "B",
        "explanation_text": "Gradient boosting minimizes an arbitrary differentiable loss function by sequentially training trees on the negative gradient (residuals) of the loss function, taking gradient descent steps in function space.",
    },

    # 25. GRAPHS AND SOCIAL NETWORKS
    {
        "title": "PageRank Damping Factor Purpose",
        "prompt_text": "In Google's PageRank algorithm, why is a damping factor d (typically ~0.85) incorporated into the random surfer formulation?",
        "category": ArenaCategory.CS_GRAPHS_NETWORKS,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Google",
        "role_tags": ["cse", "graphs", "social_networks"],
        "options": [
            {"key": "A", "text": "To reduce computation time by 85%"},
            {"key": "B", "text": "To ensure the Markov transition matrix is irreducible and aperiodic, preventing the random surfer from getting trapped in rank sinks (dead ends) and cycles"},
            {"key": "C", "text": "To guarantee that outward link weights sum to zero"},
            {"key": "D", "text": "To give commercial websites higher ranking priority"},
        ],
        "correct_option_key": "B",
        "explanation_text": "The damping factor (1-d) allows a random teleport to any web page, ensuring ergodicity so the power iteration method converges to a unique stationary distribution regardless of spider traps or dead-ends.",
    },

    # 26. NATURAL LANGUAGE PROCESSING
    {
        "title": "Self-Attention Mechanism in Transformer Architecture",
        "prompt_text": "In the scaled dot-product attention formula Attention(Q, K, V) = softmax((Q K^T) / sqrt(d_k)) V, what is the role of scaling by sqrt(d_k)?",
        "category": ArenaCategory.CS_NLP,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "OpenAI",
        "role_tags": ["cse", "nlp", "transformers"],
        "options": [
            {"key": "A", "text": "To convert attention scores into normalized probabilities"},
            {"key": "B", "text": "To prevent dot products from growing excessively large for high dimensions, which would push the softmax function into regions with vanishing gradients"},
            {"key": "C", "text": "To enforce causal masking during autoregressive token generation"},
            {"key": "D", "text": "To reduce matrix multiplication memory complexity from O(N^2) to O(N)"},
        ],
        "correct_option_key": "B",
        "explanation_text": "For large d_k, dot products grow large in magnitude, causing softmax to yield extremely peaked distributions with tiny gradients. Scaling by 1/sqrt(d_k) stabilizes the variance of the dot products to 1.",
    },

    # 27. ECOMMERCE AND BUSINESS INTELLIGENCE
    {
        "title": "Star Schema vs Snowflake Schema in Data Warehousing",
        "prompt_text": "What is the structural difference between a Star Schema and a Snowflake Schema in enterprise BI analytical databases?",
        "category": ArenaCategory.CS_ECOMMERCE_BI,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Walmart",
        "role_tags": ["cse", "bi", "data_warehousing"],
        "options": [
            {"key": "A", "text": "Star schema dimension tables are completely denormalized, while Snowflake schema dimension tables are normalized into multiple related sub-tables"},
            {"key": "B", "text": "Star schema cannot store numerical metrics in fact tables"},
            {"key": "C", "text": "Snowflake schema does not support SQL queries"},
            {"key": "D", "text": "Star schema requires NoSQL columnar storage"},
        ],
        "correct_option_key": "A",
        "explanation_text": "In a Star schema, dimension tables are denormalized for simpler queries and faster OLAP joins. Snowflake schema normalizes dimensions into hierarchies to reduce data redundancy, requiring more join operations.",
    },

    # 28. WIRELESS AND MOBILE COMPUTING
    {
        "title": "Cellular Frequency Reuse and Co-Channel Interference",
        "prompt_text": "In cellular mobile systems, what determines the frequency reuse distance D for a cluster size N with cell radius R?",
        "category": ArenaCategory.CS_WIRELESS_MOBILE,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Qualcomm",
        "role_tags": ["cse", "wireless", "mobile_computing"],
        "options": [
            {"key": "A", "text": "D = R * sqrt(3N)"},
            {"key": "B", "text": "D = N / (3R)"},
            {"key": "C", "text": "D = R * N^2"},
            {"key": "D", "text": "D = 2 * R * N"},
        ],
        "correct_option_key": "A",
        "explanation_text": "The frequency reuse distance D between co-channel cell centers is given by D = R * sqrt(3N). Higher cluster size N increases reuse distance D, lowering co-channel interference at the cost of overall spectrum capacity.",
    },

    # 29. MODERN WEB DEVELOPMENT
    {
        "title": "React Virtual DOM Reconciliation (Fiber)",
        "prompt_text": "How does React's reconciliation algorithm achieve O(n) heuristic diffing complexity instead of the theoretical O(n^3) minimum tree edit distance?",
        "category": ArenaCategory.CS_MODERN_WEB_DEV,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 75,
        "company_tag": "Meta",
        "role_tags": ["cse", "web_development", "react"],
        "options": [
            {"key": "A", "text": "By executing WebAssembly binaries directly inside browser service workers"},
            {"key": "B", "text": "By assuming two elements of different types produce different trees, and utilizing developer-provided keys for stable list identity matching across renders"},
            {"key": "C", "text": "By updating the actual browser DOM synchronously on every single state change"},
            {"key": "D", "text": "By restricting applications to a maximum depth of 3 nested components"},
        ],
        "correct_option_key": "B",
        "explanation_text": "React enforces two heuristics: 1) elements of different types will produce different trees (rebuild subtree), and 2) child elements can be differentiated across renders using 'key' props, bringing diffing complexity to O(n).",
    },

    # 30. DISTRIBUTED COMPUTING
    {
        "title": "CAP Theorem Trade-Offs in Distributed Storage",
        "prompt_text": "Under Brewer's CAP Theorem, when an unavoidable network partition (P) occurs between data center nodes, what must a distributed system choose between?",
        "category": ArenaCategory.CS_DISTRIBUTED_COMPUTING,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Amazon",
        "role_tags": ["cse", "distributed_systems", "cloud"],
        "options": [
            {"key": "A", "text": "Throughput versus Encryption Strength"},
            {"key": "B", "text": "Consistency (linearizability) versus Availability (every non-failing node returns a non-error response)"},
            {"key": "C", "text": "SQL compliance versus NoSQL schema"},
            {"key": "D", "text": "CPU utilization versus Network bandwidth"},
        ],
        "correct_option_key": "B",
        "explanation_text": "Since network partitions (P) in distributed networks are inevitable, a system must either return errors/wait for partition healing to guarantee Consistency (CP), or serve potentially stale data to maintain Availability (AP).",
    },

    # 31. DATA SCIENCE & ANALYTICS
    {
        "title": "p-Value and Type I Error in Hypothesis Testing",
        "prompt_text": "In statistical hypothesis testing, rejecting a true null hypothesis H0 is known as what type of error, and what determines its threshold?",
        "category": ArenaCategory.CS_DATA_SCIENCE_ANALYTICS,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Netflix",
        "role_tags": ["cse", "data_science", "statistics"],
        "options": [
            {"key": "A", "text": "Type I error (false positive), bounded by significance level alpha (typically 0.05)"},
            {"key": "B", "text": "Type II error (false negative), bounded by statistical power (1 - beta)"},
            {"key": "C", "text": "Sampling bias, bounded by variance"},
            {"key": "D", "text": "Standard error of the mean"},
        ],
        "correct_option_key": "A",
        "explanation_text": "Type I error is the rejection of a true null hypothesis (false alarm / false positive). The maximum probability of committing a Type I error is set by the significance level alpha.",
    },

    # 32. CRYPTOGRAPHY AND NETWORK SECURITY
    {
        "title": "Diffie-Hellman Key Exchange Mathematical Basis",
        "prompt_text": "On which computational problem does the security of the classical Diffie-Hellman key exchange rely?",
        "category": ArenaCategory.CS_CRYPTOGRAPHY_SECURITY,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Cisco",
        "role_tags": ["cse", "cryptography", "security"],
        "options": [
            {"key": "A", "text": "Integer factorization of large semiprimes"},
            {"key": "B", "text": "The Discrete Logarithm Problem in finite cyclic groups"},
            {"key": "C", "text": "Polynomial time sorting of permutations"},
            {"key": "D", "text": "Finding SHA-256 pre-images"},
        ],
        "correct_option_key": "B",
        "explanation_text": "Diffie-Hellman relies on the difficulty of computing discrete logarithms in a finite field: given g, p, and g^a mod p, it is computationally intractable to determine the secret exponent 'a'.",
    },

    # 33. BLOCKCHAIN
    {
        "title": "Merkle Tree Verification in Bitcoin Blocks",
        "prompt_text": "In a blockchain block header, why is transaction data organized into a Merkle tree rather than a linear linked list of hashes?",
        "category": ArenaCategory.CS_BLOCKCHAIN,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Coinbase",
        "role_tags": ["cse", "blockchain", "distributed_ledger"],
        "options": [
            {"key": "A", "text": "It allows mining hardware to solve proof-of-work in O(1) time"},
            {"key": "B", "text": "It enables Simplified Payment Verification (SPV) clients to prove a transaction is included in a block with logarithmic O(log N) hashes instead of downloading all N transactions"},
            {"key": "C", "text": "It encrypts transaction amounts so only miners can read them"},
            {"key": "D", "text": "It eliminates the need for gas fees"},
        ],
        "correct_option_key": "B",
        "explanation_text": "A Merkle proof requires only O(log N) audit path hashes to prove membership of a transaction against the block's 32-byte Merkle root, making light clients (SPV) fast and secure.",
    },

    # 34. BIOMETRICS AND BIO-SIGNAL PROCESSING
    {
        "title": "Equal Error Rate (EER) in Biometric Authentication",
        "prompt_text": "In biometric verification systems (such as fingerprint or facial recognition), what does the Equal Error Rate (EER) signify?",
        "category": ArenaCategory.CS_BIOMETRICS_BIOSIGNAL,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Apple",
        "role_tags": ["cse", "biometrics", "signal_processing"],
        "options": [
            {"key": "A", "text": "The operating threshold point where the False Acceptance Rate (FAR) equals the False Rejection Rate (FRR)"},
            {"key": "B", "text": "The rate at which sensor hardware fails to capture a readable scan"},
            {"key": "C", "text": "The ratio between encrypted biometric template size and original raw image"},
            {"key": "D", "text": "The percentage of authenticated users with twin siblings"},
        ],
        "correct_option_key": "A",
        "explanation_text": "EER is the point on the Detection Error Tradeoff (DET) curve where False Match/Acceptance Rate equals False Non-Match/Rejection Rate. Lower EER indicates higher overall biometric accuracy.",
    },

    # 35. PARALLEL AND GPU COMPUTING
    {
        "title": "Amdahl's Law vs Gustafson's Law",
        "prompt_text": "If 20% of a computational workload is strictly sequential and cannot be parallelized, what is the theoretical maximum speedup achievable according to Amdahl's Law as processor count approaches infinity?",
        "category": ArenaCategory.CS_PARALLEL_GPU,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Nvidia",
        "role_tags": ["cse", "parallel_computing", "hpc"],
        "options": [
            {"key": "A", "text": "2x"},
            {"key": "B", "text": "5x"},
            {"key": "C", "text": "20x"},
            {"key": "D", "text": "Infinite speedup"},
        ],
        "correct_option_key": "B",
        "explanation_text": "Amdahl's Law states Speedup = 1 / (s + (1-s)/p). As p -> infinity, max Speedup = 1 / s. For s = 0.20 (20% sequential), Speedup = 1 / 0.20 = 5x.",
    },

    # 36. DEEP LEARNING
    {
        "title": "Batch Normalization Internal Covariate Shift Mitigation",
        "prompt_text": "In deep neural network training, how does Batch Normalization accelerate training stability and convergence?",
        "category": ArenaCategory.CS_DEEP_LEARNING,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Google",
        "role_tags": ["cse", "deep_learning", "neural_networks"],
        "options": [
            {"key": "A", "text": "By zeroing out 50% of activations randomly at each step like Dropout"},
            {"key": "B", "text": "By normalizing layer activations across mini-batch examples to have zero mean and unit variance, followed by learned affine scaling (gamma) and shift (beta)"},
            {"key": "C", "text": "By converting all weights into 8-bit quantized integers"},
            {"key": "D", "text": "By eliminating backpropagation during even-numbered epochs"},
        ],
        "correct_option_key": "B",
        "explanation_text": "Batch Norm normalizes each mini-batch feature to mean 0 and variance 1, then applies learned parameters gamma and beta to allow the network to restore representational power, stabilizing layer input distributions.",
    },

    # 37. COMPUTER VISION
    {
        "title": "YOLO vs Two-Stage (Faster R-CNN) Object Detectors",
        "prompt_text": "What is the architectural paradigm that allows YOLO (You Only Look Once) to achieve real-time inference speeds compared to Faster R-CNN?",
        "category": ArenaCategory.CS_COMPUTER_VISION,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Tesla",
        "role_tags": ["cse", "computer_vision", "object_detection"],
        "options": [
            {"key": "A", "text": "It frames detection as a single regression problem from full image pixels directly to bounding box coordinates and class probabilities in a single forward pass"},
            {"key": "B", "text": "It generates 2000 selective search regional proposals per frame on CPU"},
            {"key": "C", "text": "It skips feature extraction layers entirely"},
            {"key": "D", "text": "It detects objects using Hough transform circles"},
        ],
        "correct_option_key": "A",
        "explanation_text": "Two-stage detectors like Faster R-CNN first propose regions (RPN) and then classify them. YOLO is a single-stage detector that predicts bounding boxes and class probabilities simultaneously across a divided grid in one unified forward pass.",
    },

    # 38. INTERNET OF THINGS
    {
        "title": "MQTT Protocol QoS Levels",
        "prompt_text": "In the MQTT IoT publish-subscribe protocol, which Quality of Service (QoS) level guarantees that a message is delivered exactly once using a two-step four-way handshake (PUBREC/PUBREL)?",
        "category": ArenaCategory.CS_IOT,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Schneider Electric",
        "role_tags": ["cse", "iot", "embedded"],
        "options": [
            {"key": "A", "text": "QoS 0 (At most once / fire and forget)"},
            {"key": "B", "text": "QoS 1 (At least once / acknowledged)"},
            {"key": "C", "text": "QoS 2 (Exactly once / assured delivery)"},
            {"key": "D", "text": "QoS 3 (Ultra-reliable)"},
        ],
        "correct_option_key": "C",
        "explanation_text": "MQTT defines QoS 0 (at most once), QoS 1 (at least once with possible duplicates), and QoS 2 (exactly once delivery with full 4-packet confirmation flow).",
    },

    # 39. INFORMATION RETRIEVAL AND BIG DATA
    {
        "title": "BM25 Scoring Term Frequency Saturation",
        "prompt_text": "Why does the Okapi BM25 ranking function outperform traditional TF-IDF in modern web search engines?",
        "category": ArenaCategory.CS_BIG_DATA_IR,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 75,
        "company_tag": "Elastic",
        "role_tags": ["cse", "information_retrieval", "big_data"],
        "options": [
            {"key": "A", "text": "It uses quantum annealing for inverted index lookups"},
            {"key": "B", "text": "It incorporates non-linear term frequency saturation (controlled by parameter k1) and document length normalization (parameter b), preventing long keyword-stuffed documents from dominating"},
            {"key": "C", "text": "It deletes all stop words before building indexes"},
            {"key": "D", "text": "It requires zero storage overhead on disk"},
        ],
        "correct_option_key": "B",
        "explanation_text": "Unlike linear/log TF in TF-IDF, BM25 features an asymptotic upper bound on term frequency impact (saturation via k1) and adjusts for document length relative to average collection length via parameter b.",
    },

    # 40. CYBER SECURITY
    {
        "title": "SQL Injection Defense via Prepared Statements",
        "prompt_text": "Why do Parameterized Queries (Prepared Statements) fundamentally prevent SQL Injection attacks?",
        "category": ArenaCategory.CS_CYBER_SECURITY,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "max_marks": 5,
        "expected_time_seconds": 60,
        "company_tag": "Palo Alto Networks",
        "role_tags": ["cse", "cyber_security", "web_security"],
        "options": [
            {"key": "A", "text": "They escape all single quotes using regex replacements in memory"},
            {"key": "B", "text": "The database compiles and defines the query syntax tree structure before user parameters are bound, treating input strictly as literal data rather than executable SQL commands"},
            {"key": "C", "text": "They block all SQL queries containing the OR keyword"},
            {"key": "D", "text": "They encrypt the entire database table with AES-256"},
        ],
        "correct_option_key": "B",
        "explanation_text": "In prepared statements, the SQL engine parses and compiles the query template first. When parameter values are bound later, they are treated strictly as data literals, making it impossible for user input to alter the syntax tree.",
    },
]

# 4. Mock Interview Subject Blueprints for all 40 CSE Subjects
CSE_40_INTERVIEW_BLUEPRINTS: Dict[str, Dict[str, Any]] = {
    "maths for computing": {
        "topic": "Maths for Computing & Discrete Logic",
        "question": "In computational systems, explain how recurrence relations (such as in divide-and-conquer algorithms) are solved using the Master Theorem. How does the asymptotic growth of n^(log_b a) dictate whether the work is dominated by the leaves, the root, or evenly distributed?",
        "key_points": ["Recurrence relation T(n) = aT(n/b) + f(n)", "Comparison of f(n) with n^(log_b a)", "Leaf-heavy, root-heavy, or balanced tree execution"],
        "model_answer": "The Master Theorem evaluates T(n) = aT(n/b) + f(n) by comparing the cost of subproblems at the leaves, n^(log_b a), against the splitting/combining cost at the root, f(n). If leaves dominate, T(n) = Theta(n^(log_b a)); if root dominates, T(n) = Theta(f(n)); if balanced, an extra log n factor is introduced.",
    },
    "principles of programming languages": {
        "topic": "Principles of Programming Languages & Semantics",
        "question": "Compare statically-typed languages with dynamically-typed languages in terms of type checking phases, memory safety, and performance trade-offs. What are closures and how do lexical scoping rules govern variable capture?",
        "key_points": ["Compile-time vs runtime type verification", "Closures capturing surrounding lexical environment", "Activation records and heap allocation of escaping closures"],
        "model_answer": "Static typing checks types at compile time, eliminating runtime type overhead and catching errors early, whereas dynamic typing evaluates types at runtime for rapid prototyping. Closures are first-class functions that bundle references to their lexical environment; when closures outlive their enclosing scope, captured variables are promoted to heap-allocated environments.",
    },
    "logic design": {
        "topic": "Digital Logic & Sequential Circuit Design",
        "question": "Explain setup time and hold time constraints in edge-triggered D flip-flops. How do timing violations cause metastability, and what dual-stage synchronizer circuits resolve clock domain crossing (CDC) safely?",
        "key_points": ["Setup time t_setup and hold time t_hold", "Metastability state where output voltage hovers between logic levels", "Two-flip-flop synchronizers to reduce MTBF"],
        "model_answer": "Setup time requires data to stabilize before the clock edge; hold time requires it to remain stable after. Violating either causes the flip-flop to enter an indeterminate metastable state. Passing the signal through a two-stage flip-flop synchronizer gives the signal time to settle, drastically reducing the probability of failure.",
    },
    "professional practice, cyber law and ethics": {
        "topic": "Cyber Law, Compliance & IT Ethics",
        "question": "Discuss the legal and ethical responsibilities of software engineers regarding user privacy and data security under regulations like GDPR and India's Digital Personal Data Protection (DPDP) Act. What is privacy by design?",
        "key_points": ["Data minimization and purpose limitation", "Explicit user consent and right to erasure", "Security safeguards and reporting of data breaches"],
        "model_answer": "Engineers are legally bound to uphold data protection principles: purpose limitation, data minimization, and robust encryption. 'Privacy by design' requires embedding confidentiality controls directly into software architecture from the start rather than tacking them on post-production.",
    },
    "design and analysis of algorithms": {
        "topic": "Design & Analysis of Algorithms",
        "question": "When would you choose Dynamic Programming over a Greedy strategy, and how do you prove that an optimal substructure and overlapping subproblems exist in a problem like 0/1 Knapsack versus Fractional Knapsack?",
        "key_points": ["Greedy choice property vs optimal substructure with overlapping subproblems", "Fractional knapsack solved greedily by value/weight ratio", "0/1 knapsack requiring dynamic programming due to non-divisibility"],
        "model_answer": "Greedy algorithms make locally optimal decisions without backtracking, which works for problems with the greedy choice property (like fractional knapsack). 0/1 knapsack lacks this property because taking an item excludes others; it requires dynamic programming to evaluate overlapping subproblems and determine the global optimum in pseudo-polynomial time.",
    },
    "web technologies": {
        "topic": "Web Technologies & RESTful Architecture",
        "question": "Explain the differences between HTTP/1.1, HTTP/2, and HTTP/3. How do multiplexing, binary framing, and QUIC (UDP-based transport) eliminate head-of-line blocking in modern web applications?",
        "key_points": ["HTTP/1.1 head-of-line blocking on single connections", "HTTP/2 binary framing and stream multiplexing over TCP", "HTTP/3 UDP-based QUIC protocol eliminating TCP-level packet loss blocking"],
        "model_answer": "HTTP/1.1 suffered from head-of-line blocking because requests were handled sequentially on a TCP stream. HTTP/2 introduced binary frames and stream multiplexing over a single TCP connection, but packet loss stalled all streams. HTTP/3 replaces TCP with QUIC over UDP, ensuring packet loss on one stream does not block unrelated concurrent streams.",
    },
    "computer organization and architecture": {
        "topic": "Computer Architecture & Memory Hierarchy",
        "question": "Walk through the five stages of a classic RISC processor pipeline. Explain structural, data, and control hazards, and how branch prediction and forwarding buffers prevent pipeline stalls.",
        "key_points": ["IF, ID, EX, MEM, WB stages", "Data hazards (RAW, WAR, WAW) and forwarding", "Control hazards and branch prediction mechanisms"],
        "model_answer": "The stages are Instruction Fetch, Decode, Execute, Memory Access, and Write Back. Data hazards (RAW) occur when an instruction depends on a previous unwritten result; forwarding feeds the ALU output directly. Control hazards occur on branch instructions; dynamic 2-bit branch predictors predict outcomes to minimize pipeline flushes.",
    },
    "software engineering": {
        "topic": "Software Engineering & CI/CD Practices",
        "question": "Contrast Agile Scrum with traditional Waterfall methodologies for large-scale enterprise systems. How do automated unit testing, integration tests, and CI/CD deployment pipelines maintain software velocity without compromising reliability?",
        "key_points": ["Iterative sprints vs linear sequential phases", "Test pyramid: unit, integration, end-to-end", "Automated CI/CD gates preventing regressions in production"],
        "model_answer": "Waterfall relies on rigid, upfront requirements, whereas Agile uses short iterations with continuous customer feedback. A robust test pyramid (unit, integration, and E2E tests) integrated into automated CI/CD pipelines ensures that pull requests undergo automated regression checking and linting before automated staging and canary deployment.",
    },
    "theory of computation": {
        "topic": "Theory of Computation & Automata",
        "question": "Explain the Chomsky hierarchy of formal languages and their corresponding abstract machines. How do you prove that a language like L = {0^n 1^n | n >= 0} cannot be recognized by a Finite Automaton using the Pumping Lemma?",
        "key_points": ["Chomsky hierarchy: Regular, CFL, Context-Sensitive, Recursively Enumerable", "Finite Automata, Pushdown Automata, Linear Bounded, Turing Machines", "Pumping lemma showing memory limitation of finite states"],
        "model_answer": "The Chomsky hierarchy classifies languages by expressive power. Regular languages are recognized by Finite Automata with finite memory. For {0^n 1^n}, assuming it is regular, the pumping lemma yields a string 0^p 1^p where pumping y in x y z alters the count of 0s without altering 1s, producing a contradiction because an FA lacks an unbounded stack counter.",
    },
    "artificial intelligence and machine learning": {
        "topic": "AI & Machine Learning Foundations",
        "question": "Explain the Bias-Variance tradeoff in machine learning. How do regularization techniques like L1 (Lasso) and L2 (Ridge) prevent overfitting in linear and neural models?",
        "key_points": ["High bias causes underfitting; high variance causes overfitting", "L1 adds sum of absolute weights, promoting sparse feature selection", "L2 adds sum of squared weights, penalizing large magnitudes evenly"],
        "model_answer": "High bias leads to underfitting by oversimplifying assumptions; high variance leads to overfitting by modeling training noise. L1 regularization adds absolute weight penalties, driving non-essential coefficients to exact zero for feature selection. L2 adds squared weight penalties, shrinking coefficients smoothly to improve generalization.",
    },
    "microprocessors and assembly programming": {
        "topic": "Microprocessors & Low-Level Assembly",
        "question": "In x86 or ARM processors, explain how subroutine calls manipulate the call stack. What happens to the program counter, stack pointer, frame pointer, and return address during stack frame setup and cleanup?",
        "key_points": ["CALL instruction pushing return address to stack", "Frame pointer (EBP/RBP) setup for local variable access", "RET instruction popping return address back into PC/EIP"],
        "model_answer": "When calling a function, the CALL instruction pushes the next instruction address (return address) onto the stack and decrements SP. The prologue pushes the old frame pointer (BP), sets BP to SP, and allocates local space. The epilogue restores SP and BP, and RET pops the return address back into the Program Counter.",
    },
    "computer graphics": {
        "topic": "Computer Graphics & 3D Rendering Pipeline",
        "question": "Describe the stages of the 3D graphics rendering pipeline from model space to screen space. Explain the purpose of homogeneous coordinates and 4x4 transformation matrices in combining translation, rotation, and perspective projection.",
        "key_points": ["Model -> World -> View/Camera -> Projection -> Normalized Device Coordinates -> Screen", "Homogeneous coordinates allowing affine translation as matrix multiplication", "Perspective division dividing by w coordinate"],
        "model_answer": "The pipeline transforms vertices through Model, World, View (Camera), and Projection spaces. Homogeneous coordinates (x, y, z, w) allow translations, rotations, and perspective projections to be expressed as unified 4x4 matrix multiplications. Perspective division by w scales distant objects smaller, mapping coordinates to 2D screen pixels.",
    },
    "java programming": {
        "topic": "Java Programming & JVM Internals",
        "question": "Explain the internal memory structure of the Java Virtual Machine (Heap, Stack, Metaspace). How do generational garbage collectors (like G1 GC) distinguish young generation (Eden/Survivor) from old generation objects?",
        "key_points": ["Stack for local frames; Heap for objects; Metaspace for class metadata", "Young gen (Eden, S0, S1) with minor GC and object aging threshold", "Promotion to Old/Tenured generation and concurrent marking in G1 GC"],
        "model_answer": "JVM memory splits into thread-private Stacks and a shared Heap plus native Metaspace. Most objects are short-lived, so they are allocated in Young Gen (Eden). Minor GC evacuates survivors between Survivor spaces S0 and S1. Objects surviving a tenure threshold (e.g. 15 cycles) are promoted to Old Gen, where G1 GC performs region-based concurrent marking to minimize pause times.",
    },
    "robotics and embedded system": {
        "topic": "Robotics & Embedded Systems Architecture",
        "question": "In robotic control systems, contrast closed-loop PID control with open-loop control. How do proportional, integral, and derivative terms compensate for steady-state error, rise time, and overshoot?",
        "key_points": ["Feedback sensor readings vs open-loop commands", "Proportional reduces rise time but leaves steady-state error", "Integral eliminates steady-state offset; Derivative dampens oscillations"],
        "model_answer": "Open-loop systems execute commands without feedback. Closed-loop PID measures sensor feedback against setpoints: Proportional reacts to current error to speed up response, Integral accumulates past errors to eliminate steady-state offset, and Derivative anticipates future error to dampen overshoot and stabilize actuators.",
    },
    "principles of compiler design": {
        "topic": "Compiler Design & Code Generation",
        "question": "Walk through the major phases of a modern optimizing compiler (like LLVM or GCC). Explain how high-level ASTs are converted to Intermediate Representation (SSA form) and how register allocation (graph coloring) assigns physical CPU registers.",
        "key_points": ["Lexing, Parsing (AST), Semantic Analysis, IR Generation", "Static Single Assignment (SSA) form with phi nodes", "Chaitin's graph coloring for register allocation"],
        "model_answer": "The front-end lexes and parses source code into an AST and verifies types. The middle-end converts the AST into SSA (Static Single Assignment) form, where every variable is assigned once, facilitating dead code elimination and constant propagation. The back-end constructs an interference graph of variable live ranges and solves register allocation via k-graph coloring.",
    },
    "image processing": {
        "topic": "Digital Image Processing & Frequency Filtering",
        "question": "Explain 2D spatial convolution with Gaussian and high-pass kernels. What is the relationship between spatial filtering and frequency-domain filtering via the 2D Fast Fourier Transform (FFT)?",
        "key_points": ["Kernel convolution sliding across pixels", "Convolution in spatial domain is equivalent to multiplication in frequency domain", "Gaussian smoothing attenuates high frequencies; high-pass filters highlight edges"],
        "model_answer": "Spatial convolution computes weighted sums of neighboring pixels using filter kernels. By the Convolution Theorem, convolving an image with a filter in the spatial domain is mathematically equivalent to pointwise multiplying their 2D Fourier transforms in the frequency domain, enabling fast processing of large filters via FFT.",
    },
    "system programming": {
        "topic": "System Programming & OS Interfacing",
        "question": "In Unix/Linux system programming, explain the lifecycle of a child process created via fork() and execve(). What causes zombie and orphan processes, and how does the parent's waitpid() handle them?",
        "key_points": ["fork() duplicates process address space via Copy-On-Write", "execve() replaces process memory image with new binary", "Zombies occur when child terminates before parent calls waitpid(); Orphans adopted by init/systemd"],
        "model_answer": "fork() creates an identical child process using Copy-On-Write memory pages; execve() replaces the child's address space with a new executable. If the child finishes but the parent hasn't reaped its exit code with waitpid(), the child remains a Zombie in the process table. If the parent terminates first, the child becomes an Orphan and is reparented to init.",
    },
    "advanced machine learning": {
        "topic": "Advanced Machine Learning & Ensembles",
        "question": "Compare Bagging (Random Forest) with Boosting (XGBoost/LightGBM). How does bagging reduce variance while boosting reduces bias, and why are weak learners necessary in boosting?",
        "key_points": ["Bootstrap aggregation trains deep unpruned trees in parallel to cut variance", "Boosting trains shallow weak trees sequentially to reduce bias", "Regularization (learning rate, tree depth, gamma) preventing overfitting"],
        "model_answer": "Random Forest trains independent deep trees in parallel on bootstrapped samples, averaging predictions to reduce variance without increasing bias. Boosting sequentially trains shallow weak learners on residual errors, systematically reducing bias. Learning rate shrinkage and tree depth constraints prevent boosting from overfitting to noisy samples.",
    },
    "graphs and social networks": {
        "topic": "Graph Algorithms & Social Network Analysis",
        "question": "In social network analysis, explain betweenness centrality versus eigenvector centrality. How do community detection algorithms (like the Louvain method) optimize modularity in large sparse graphs?",
        "key_points": ["Betweenness measures fraction of shortest paths passing through a node (bridge nodes)", "Eigenvector / PageRank measures connection to high-scoring nodes", "Louvain method greedily optimizes modularity Q in two iterative phases"],
        "model_answer": "Betweenness centrality identifies bridge nodes that control information flow across clusters by measuring shortest paths. Eigenvector centrality measures node importance based on the importance of its neighbors. The Louvain algorithm detects communities by first locally assigning nodes to maximize modularity Q, then aggregating communities into super-nodes iteratively.",
    },
    "natural language processing": {
        "topic": "Natural Language Processing & LLMs",
        "question": "Explain word embeddings (Word2Vec CBOW vs Skip-gram) and why self-attention in Transformer architectures replaced recurrent networks (LSTMs) for long-range context modeling.",
        "key_points": ["Word2Vec predicting context from word (Skip-gram) vs word from context (CBOW)", "LSTMs sequential bottleneck and vanishing gradients over long horizons", "Self-attention computing pairwise token affinities in parallel O(1) path length"],
        "model_answer": "Word2Vec maps semantic relationships into vector space using local context prediction. While LSTMs processed tokens sequentially, leading to vanishing gradients and computational bottlenecks, Transformers compute self-attention across all tokens simultaneously with an O(1) path length, capturing long-distance dependencies and enabling massive GPU parallelism.",
    },
    "ecommerce and business intelligence": {
        "topic": "E-Commerce Systems & Business Intelligence",
        "question": "Describe collaborative filtering algorithms (user-based vs item-based) in e-commerce recommendation engines. How do matrix factorization techniques (like SVD) address the cold-start and sparsity problems in purchase matrices?",
        "key_points": ["Cosine similarity between user interaction vectors", "Item-based filtering scaling better when items < users", "SVD decomposing sparse user-item matrix into dense latent factor matrices"],
        "model_answer": "Collaborative filtering predicts user interests based on similar users or items using interaction history. Because real-world user-item matrices are over 99% sparse, Singular Value Decomposition (SVD) projects users and items into a shared low-dimensional latent factor space, capturing underlying preferences and alleviating sparsity.",
    },
    "wireless and mobile computing": {
        "topic": "Wireless Networks & Mobile Protocols",
        "question": "Explain the Hidden Terminal and Exposed Terminal problems in 802.11 Wi-Fi networks. How does the RTS/CTS (Request to Send / Clear to Send) handshake protocol solve the hidden terminal collision issue?",
        "key_points": ["Hidden nodes out of range of each other transmitting to common receiver causing collision", "RTS/CTS reserving channel and broadcasting NAV (Network Allocation Vector)", "Tradeoff of RTS/CTS overhead for small data packets"],
        "model_answer": "The hidden terminal problem occurs when two transmitters out of range of each other transmit to the same receiver simultaneously, causing packet collisions. The sender transmits an RTS frame; the receiver responds with a CTS frame, broadcasting a Network Allocation Vector (NAV) that tells all neighboring nodes to defer transmission, preventing collisions.",
    },
    "modern web development": {
        "topic": "Modern Web Architecture & Full-Stack Systems",
        "question": "Compare Server-Side Rendering (SSR), Static Site Generation (SSG), and Client-Side Rendering (CSR). When designing a modern web application in Next.js/React, how do you balance SEO, Time to First Byte (TTFB), and First Contentful Paint (FCP)?",
        "key_points": ["CSR downloads JS bundle before rendering; poor initial SEO and slow FCP", "SSG pre-builds static HTML at build time for optimal TTFB and caching", "SSR renders HTML per request for personalized dynamic data"],
        "model_answer": "CSR delivers a minimal HTML shell and renders in the browser, hurting SEO and initial load. SSG generates static HTML during build time, delivering fast TTFB and great SEO via CDNs for static pages. SSR renders HTML dynamically on each request for personalized, real-time data, balancing immediate content visibility with slight TTFB server compute overhead.",
    },
    "distributed computing": {
        "topic": "Distributed Systems & Consensus Protocols",
        "question": "Explain the Raft consensus protocol. How does Raft elect a leader, ensure log replication consistency, and guarantee safety even in the presence of network partitions and node crashes?",
        "key_points": ["Roles: Leader, Follower, Candidate", "Heartbeat timers and randomized election timeouts preventing split votes", "Log matching property: committed entries never overwritten"],
        "model_answer": "Raft achieves consensus via leader election and log replication. Nodes start as followers; if heartbeats lapse, a randomized timeout triggers candidate state to elect a leader by majority vote. The leader accepts client writes, appends them to its log, replicates them across followers, and commits entries once a majority acknowledge, ensuring all nodes execute identical state transitions safely.",
    },
    "data science & analytics": {
        "topic": "Data Science & Exploratory Analytics",
        "question": "Walk through an end-to-end data science pipeline for predicting customer churn. How do you handle missing values, skewed distributions, class imbalance (e.g. SMOTE vs downsampling), and feature collinearity?",
        "key_points": ["Missing data imputation and log/Box-Cox transformations", "Synthetic Minority Over-sampling (SMOTE) vs focal loss for imbalance", "Variance Inflation Factor (VIF) to detect and remove multicollinearity"],
        "model_answer": "Start with exploratory data analysis: impute missing values using median or iterative models, and normalize skewed features with log transforms. For class imbalance where churned users are rare, apply SMOTE to synthesize minority samples or tune class weights and evaluate using PR-AUC instead of accuracy. Check Variance Inflation Factor (VIF) to eliminate redundant collinear predictors.",
    },
    "cryptography and network security": {
        "topic": "Cryptography & PKI Security Architecture",
        "question": "Explain the TLS 1.3 handshake mechanism. How does TLS 1.3 achieve forward secrecy, and how does it reduce handshake latency down to 1-RTT (and optional 0-RTT) compared to TLS 1.2?",
        "key_points": ["Ephemeral Diffie-Hellman (ECDHE) ensuring past sessions cannot be decrypted if private key leaks", "Removal of legacy cipher suites and static RSA key exchange", "Combined ClientHello with key shares achieving 1-RTT connection setup"],
        "model_answer": "TLS 1.3 mandates ephemeral Diffie-Hellman (ECDHE) for all handshakes, providing perfect forward secrecy so compromise of a server's long-term private key cannot decrypt recorded past traffic. In TLS 1.3, the client sends speculative ECDHE key shares in its initial ClientHello, allowing negotiation and shared secret derivation in a single round-trip (1-RTT).",
    },
    "blockchain": {
        "topic": "Blockchain Architecture & Smart Contracts",
        "question": "In decentralized networks, explain the architectural difference between Proof-of-Work (PoW) and Proof-of-Stake (PoS). What is a smart contract re-entrancy attack, and how does the Checks-Effects-Interactions pattern prevent it?",
        "key_points": ["PoW computational hash difficulty vs PoS validator token staking and slashing", "Re-entrancy where an external contract calls back before state update", "Checks-Effects-Interactions pattern and nonReentrant mutex guards"],
        "model_answer": "PoW relies on miners consuming electrical energy to solve hashing puzzles; PoS selects validators based on staked capital and slashes dishonest actors. A re-entrancy attack happens when a smart contract makes an external call to transfer funds before zeroing the sender's balance, allowing the caller's fallback function to re-invoke the withdrawal recursively. Following the Checks-Effects-Interactions pattern updates internal state before making external transfers, preventing exploit.",
    },
    "biometrics and bio-signal processing": {
        "topic": "Biometrics & Bio-Signal Feature Extraction",
        "question": "Describe the signal processing pipeline for acquiring and analyzing electrocardiogram (ECG) signals. How do bandpass filtering (0.5 to 45 Hz) and the Pan-Tompkins algorithm reliably identify QRS complexes and R-peaks amidst baseline wander and muscle noise?",
        "key_points": ["Filtering power-line (50/60Hz) and baseline wander noise", "Pan-Tompkins derivative, squaring, and moving-window integration", "Adaptive thresholding to distinguish R-peaks from high T-waves"],
        "model_answer": "Raw ECG signals suffer from baseline wander and electromyographic noise. A bandpass filter (5-15 Hz) isolates the dominant QRS energy. The Pan-Tompkins algorithm then computes the derivative to emphasize slope, squares the values to accentuate peaks, applies moving-window integration to gather wave duration, and uses dual adaptive thresholds to reliably detect R-peaks for heart rate variability calculation.",
    },
    "parallel and gpu computing": {
        "topic": "Parallel GPU Architecture & CUDA Programming",
        "question": "In NVIDIA CUDA programming, explain the hierarchy of threads, warps, thread blocks, and grid. What is warp divergence, and how does coalesced memory access optimize GPU memory bandwidth?",
        "key_points": ["Grid containing Blocks executed on Streaming Multiprocessors (SMs)", "Warps of 32 threads executing in lockstep (SIMT)", "Warp divergence serializing branch execution; coalesced access merging 32-byte cache lines"],
        "model_answer": "CUDA organizes computations into a Grid of Blocks assigned to Streaming Multiprocessors, where instructions execute in warps of 32 threads. Warp divergence occurs when threads in a warp take different branches, forcing the GPU to serialize each branch path and cutting throughput. Coalesced access ensures that contiguous threads access consecutive global memory addresses, fetching entire warp requests in a single memory transaction.",
    },
    "deep learning": {
        "topic": "Deep Learning Architecture & Optimization",
        "question": "Explain the vanishing and exploding gradient problems in deep neural networks. How do Residual Connections (ResNets), proper weight initializations (He/Xavier), and Layer Normalization enable stable training of networks with hundreds of layers?",
        "key_points": ["Chain rule multiplication of small/large weight derivatives", "Residual identity shortcuts allowing gradients to flow unimpeded: d(x + F(x))/dx = 1 + dF/dx", "Variance-preserving weight initialization preventing vanishing activations"],
        "model_answer": "Deep networks suffer from vanishing gradients when backpropagating through many layers with small weights or saturating activations (like sigmoid). ResNets solve this by introducing skip/residual connections: y = F(x) + x. The gradient dLoss/dx = (dLoss/dy) * (dF/dx + 1); the '+ 1' term ensures gradients flow directly back across hundreds of layers without decaying.",
    },
    "computer vision": {
        "topic": "Computer Vision & Visual Feature Learning",
        "question": "How do Convolutional Neural Networks (CNNs) achieve translation invariance, and what are receptive fields? Walk through why 1x1 convolutions (pointwise convolutions) are used in architectures like Inception and MobileNets for dimensionality reduction.",
        "key_points": ["Shared weight kernels and pooling layers providing translation equivariance/invariance", "Receptive field growing with network depth", "1x1 convolutions pooling across feature channels to reduce parameters and compute cost"],
        "model_answer": "CNNs apply shared filter kernels across spatial locations, creating translation-equivariant feature maps, while pooling layers provide local invariance. As layers stack, the effective receptive field expands to encompass global scene context. 1x1 convolutions perform linear combinations across channel dimensions without altering spatial height/width, drastically reducing channel depth and FLOPs before expensive 3x3 or 5x5 filters.",
    },
    "internet of things": {
        "topic": "IoT Architecture, Protocols & Edge Analytics",
        "question": "In constrained IoT edge deployments, contrast MQTT with HTTP and CoAP. How do publish/subscribe brokers, compact binary/lightweight headers, and keep-alive pings minimize battery drain and cellular data consumption on edge sensor nodes?",
        "key_points": ["Stateless heavy HTTP headers vs lightweight MQTT/CoAP packet structures", "Pub/Sub decoupling producer and consumer asynchronously", "Persistent keep-alive connections avoiding frequent TCP/TLS handshakes"],
        "model_answer": "HTTP is synchronous and carries large header overhead per request. MQTT uses a lightweight 2-byte fixed header and a publish/subscribe broker, allowing low-power edge sensors to publish short telemetry and sleep. Persistent keep-alive connections avoid the energy cost of frequent TCP/TLS handshakes, and CoAP uses UDP with compact binary framing for constrained microcontroller environments.",
    },
    "information retrieval and big data": {
        "topic": "Big Data Engineering & Distributed Processing",
        "question": "Explain the architectural evolution from Hadoop MapReduce to Apache Spark. How do Resilient Distributed Datasets (RDDs), in-memory caching, and lazy execution graphs (DAGs) dramatically improve iterative machine learning and data pipelines?",
        "key_points": ["MapReduce writing intermediate stages to disk (HDFS)", "Spark RDD in-memory lineage avoiding disk I/O bottlenecks", "Catalyst query optimizer optimizing physical execution plans via DAG pipelining"],
        "model_answer": "Hadoop MapReduce forced intermediate computation stages to be serialized to disk (HDFS), creating severe I/O bottlenecks for multi-pass iterative algorithms. Apache Spark retains data in distributed memory using RDDs. Spark builds a Directed Acyclic Graph (DAG) of transformations evaluated lazily, allowing the Catalyst optimizer to pipeline operations and avoid redundant disk writes.",
    },
    "cyber security": {
        "topic": "Enterprise Cyber Security & Defensive Architecture",
        "question": "Explain the core tenets of Zero Trust Architecture ('never trust, always verify'). How do multi-factor authentication (MFA), microsegmentation, and principle of least privilege prevent lateral movement during an advanced persistent threat (APT) breach?",
        "key_points": ["Abandoning perimeter security in favor of continuous per-request identity & device verification", "Network microsegmentation preventing lateral network traversal", "Principle of least privilege (PoLP) and just-in-time access control"],
        "model_answer": "Traditional castle-and-moat security trusted anyone inside the intranet. Zero Trust assumes breaches are already present and continuously verifies every request based on identity, device health, and context. Microsegmentation isolates workloads into granular zones, and the principle of least privilege ensures compromised credentials cannot move laterally to access sensitive database records or domain controllers.",
    },
}
