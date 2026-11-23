"""Curated original Placement Preparation Arena question bank across all 11 required categories."""
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arena import (
    ArenaAssessment,
    ArenaAssessmentMode,
    ArenaCategory,
    ArenaContentSource,
    ArenaDifficulty,
    ArenaQuestion,
    ArenaQuestionType,
)

CATEGORY_METADATA: Dict[ArenaCategory, Dict[str, str]] = {
    ArenaCategory.DSA: {
        "label": "Data Structures & Algorithms",
        "description": "Arrays, hashing, trees, graphs, sorting, dynamic programming, and time-space tradeoffs.",
    },
    ArenaCategory.PROGRAMMING_FUNDAMENTALS: {
        "label": "Programming Fundamentals",
        "description": "Control flow, recursion, pointers/references, complexity analysis, and string manipulation.",
    },
    ArenaCategory.DBMS: {
        "label": "Database Management Systems",
        "description": "Normalization, SQL joins, indexing, ACID transactions, concurrency, and query optimization.",
    },
    ArenaCategory.OPERATING_SYSTEMS: {
        "label": "Operating Systems",
        "description": "Processes, threads, CPU scheduling, deadlocks, virtual memory, paging, and synchronization.",
    },
    ArenaCategory.COMPUTER_NETWORKS: {
        "label": "Computer Networks",
        "description": "TCP/UDP, HTTP/HTTPS, DNS, TLS handshakes, OSI model, routing, and subnetting.",
    },
    ArenaCategory.OOP: {
        "label": "Object-Oriented Programming",
        "description": "Encapsulation, inheritance, polymorphism, abstraction, SOLID principles, and design patterns.",
    },
    ArenaCategory.APTITUDE_LOGICAL: {
        "label": "Aptitude & Logical Reasoning",
        "description": "Deductions, syllogisms, seating arrangements, blood relations, and pattern recognition.",
    },
    ArenaCategory.QUANTITATIVE: {
        "label": "Quantitative Ability",
        "description": "Probability, permutations, percentages, ratios, time-speed-distance, and number theory.",
    },
    ArenaCategory.VERBAL: {
        "label": "Verbal Ability",
        "description": "Grammar precision, sentence completion, para-jumbles, analogies, and reading comprehension.",
    },
    ArenaCategory.TECHNICAL_MCQS: {
        "label": "Technical MCQs",
        "description": "Core engineering fundamentals, structural mechanics, power systems, thermal sciences, chemical processes, architecture, APIs, and modern engineering practices.",
    },
    ArenaCategory.HR_BEHAVIORAL: {
        "label": "HR & Behavioral Preparation",
        "description": "STAR storytelling, conflict resolution, ownership, leadership, and situational judgment.",
    },
}

# Merge all multi-branch placement core category metadata
from app.services.branch_arena_question_bank import (
    BRANCH_CATEGORY_METADATA,
    BRANCH_CURATED_QUESTIONS,
)
CATEGORY_METADATA.update(BRANCH_CATEGORY_METADATA)

COMPANY_PROVENANCE_NOTICE = (
    "Original preparation track modeled on public industry engineering patterns. "
    "These curated exercises are NOT confidential or actual company exam questions."
)
CURATED_PROVENANCE_NOTICE = "Original curated educational problem authored for placement readiness practice."
STAFF_PROVENANCE_NOTICE = "Published by institutional TPO / Admin staff for cohort preparation."


CURATED_QUESTIONS: List[Dict[str, Any]] = [
    # --- 1. Data Structures & Algorithms (Coding + MCQs) ---
    {
        "title": "Two Sum Pair Indices",
        "prompt_text": (
            "Given an integer `target` on line 1 and space-separated integers `nums` on line 2, "
            "print the two 0-based indices `i j` (with `i < j`) such that `nums[i] + nums[j] == target`.\n"
            "Assume exactly one valid pair exists."
        ),
        "category": ArenaCategory.DSA,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.CODING,
        "company_tag": "ApexCloud Engineering Pattern",
        "role_tags": ["python", "java", "javascript", "backend", "software engineer", "algorithms"],
        "starter_code": {
            "python": (
                "target = int(input().strip())\n"
                "nums = list(map(int, input().strip().split()))\n"
                "seen = {}\n"
                "for idx, val in enumerate(nums):\n"
                "    comp = target - val\n"
                "    if comp in seen:\n"
                "        print(f\"{seen[comp]} {idx}\")\n"
                "        break\n"
                "    seen[val] = idx\n"
            ),
            "javascript": (
                "let raw = '';\n"
                "process.stdin.on('data', d => raw += d);\n"
                "process.stdin.on('end', () => {\n"
                "  const parts = raw.trim().split(/\\n+/);\n"
                "  const target = parseInt(parts[0], 10);\n"
                "  const nums = parts[1].trim().split(/\\s+/).map(Number);\n"
                "  const map = new Map();\n"
                "  for (let i = 0; i < nums.length; i++) {\n"
                "    const need = target - nums[i];\n"
                "    if (map.has(need)) { console.log(`${map.get(need)} ${i}`); return; }\n"
                "    map.set(nums[i], i);\n"
                "  }\n"
                "});\n"
            ),
            "java": (
                "import java.util.*;\n"
                "public class Main {\n"
                "    public static void main(String[] args) {\n"
                "        Scanner sc = new Scanner(System.in);\n"
                "        int target = Integer.parseInt(sc.nextLine().trim());\n"
                "        String[] tokens = sc.nextLine().trim().split(\"\\\\s+\");\n"
                "        Map<Integer, Integer> map = new HashMap<>();\n"
                "        for (int i = 0; i < tokens.length; i++) {\n"
                "            int val = Integer.parseInt(tokens[i]);\n"
                "            if (map.containsKey(target - val)) {\n"
                "                System.out.println(map.get(target - val) + \" \" + i);\n"
                "                return;\n"
                "            }\n"
                "            map.put(val, i);\n"
                "        }\n"
                "    }\n"
                "}\n"
            ),
        },
        "test_cases": [
            {"stdin": "9\n2 7 11 15\n", "expected_stdout": "0 1", "is_sample": True},
            {"stdin": "6\n3 2 4\n", "expected_stdout": "1 2", "is_sample": True},
            {"stdin": "10\n1 5 5 8\n", "expected_stdout": "1 2", "is_sample": False},
        ],
        "explanation_text": "Using a hash map to record seen value->index reduces lookup from O(n^2) to O(n) time and O(n) space.",
        "sample_solution_text": "Iterate once tracking seen[value] = index; whenever (target - value) exists in seen, return seen[target - value] and current index.",
        "expected_time_seconds": 600,
        "max_marks": 20,
    },
    {
        "title": "Maximum Subarray Sum (Kadane Pattern)",
        "prompt_text": (
            "Given space-separated integers on a single line, find the contiguous subarray "
            "(containing at least one integer) which has the largest sum and print that sum."
        ),
        "category": ArenaCategory.DSA,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.CODING,
        "company_tag": "FinCore Systems Pattern",
        "role_tags": ["python", "java", "algorithms", "backend", "sde"],
        "starter_code": {
            "python": (
                "nums = list(map(int, input().split()))\n"
                "# Write Kadane's O(n) solution and print the maximum sum\n"
                "curr = best = nums[0]\n"
                "for x in nums[1:]:\n"
                "    curr = max(x, curr + x)\n"
                "    best = max(best, curr)\n"
                "print(best)\n"
            ),
            "javascript": (
                "let raw = '';\n"
                "process.stdin.on('data', d => raw += d);\n"
                "process.stdin.on('end', () => {\n"
                "  const nums = raw.trim().split(/\\s+/).map(Number);\n"
                "  let curr = nums[0], best = nums[0];\n"
                "  for (let i = 1; i < nums.length; i++) {\n"
                "    curr = Math.max(nums[i], curr + nums[i]);\n"
                "    best = Math.max(best, curr);\n"
                "  }\n"
                "  console.log(best);\n"
                "});\n"
            ),
            "java": (
                "import java.util.*;\n"
                "public class Main {\n"
                "    public static void main(String[] args) {\n"
                "        Scanner sc = new Scanner(System.in);\n"
                "        String[] tokens = sc.nextLine().trim().split(\"\\\\s+\");\n"
                "        int curr = Integer.parseInt(tokens[0]), best = curr;\n"
                "        for (int i = 1; i < tokens.length; i++) {\n"
                "            int x = Integer.parseInt(tokens[i]);\n"
                "            curr = Math.max(x, curr + x);\n"
                "            best = Math.max(best, curr);\n"
                "        }\n"
                "        System.out.println(best);\n"
                "    }\n"
                "}\n"
            ),
        },
        "test_cases": [
            {"stdin": "-2 1 -3 4 -1 2 1 -5 4\n", "expected_stdout": "6", "is_sample": True},
            {"stdin": "-5 -2 -9\n", "expected_stdout": "-2", "is_sample": True},
            {"stdin": "5 4 -1 7 8\n", "expected_stdout": "23", "is_sample": False},
        ],
        "explanation_text": "Kadane's algorithm decides at each element whether to extend the running subarray or start fresh at the current element: O(n) time, O(1) space.",
        "sample_solution_text": "Maintain curr = max(x, curr + x) and best = max(best, curr) initialized at nums[0].",
        "expected_time_seconds": 600,
        "max_marks": 20,
    },
    {
        "title": "Binary Heap Insertion & Extraction Complexity",
        "prompt_text": "What are the worst-case time complexities for inserting an element into and extracting the minimum from an n-element binary min-heap?",
        "category": ArenaCategory.DSA,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "company_tag": "ApexCloud Engineering Pattern",
        "role_tags": ["algorithms", "backend", "data structures"],
        "options": [
            {"key": "A", "text": "O(1) insert, O(n) extract-min"},
            {"key": "B", "text": "O(log n) insert, O(log n) extract-min"},
            {"key": "C", "text": "O(log n) insert, O(1) extract-min"},
            {"key": "D", "text": "O(n log n) insert, O(log n) extract-min"},
        ],
        "correct_option_key": "B",
        "explanation_text": "A complete binary tree of n nodes has height floor(log2 n). Both sift-up during insert and sift-down during extract-min traverse at most O(log n) levels.",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },
    {
        "title": "Detecting Cycle in Directed Graph",
        "prompt_text": "Which traversal state set reliably detects a back-edge (cycle) during DFS on a directed graph?",
        "category": ArenaCategory.DSA,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["algorithms", "sde"],
        "options": [
            {"key": "A", "text": "A single visited boolean array marking every visited vertex"},
            {"key": "B", "text": "Three-color states: unvisited, active on recursion stack, and completely finished"},
            {"key": "C", "text": "Counting total edge degrees without storing direction"},
            {"key": "D", "text": "BFS shortest path distance modulo 2"},
        ],
        "correct_option_key": "B",
        "explanation_text": "In directed graphs, reaching an already finished vertex via a cross/forward edge is NOT a cycle. Only an edge to a vertex currently active in the recursion stack indicates a cycle.",
        "expected_time_seconds": 90,
        "max_marks": 10,
    },

    # --- 2. Programming Fundamentals (Coding + MCQ) ---
    {
        "title": "Balanced Brackets Validator",
        "prompt_text": (
            "Given a string containing only `(`, `)`, `{`, `}`, `[`, `]` on a single line, "
            "print `YES` if the brackets are properly nested and balanced, otherwise print `NO`."
        ),
        "category": ArenaCategory.PROGRAMMING_FUNDAMENTALS,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.CODING,
        "company_tag": "ApexCloud Engineering Pattern",
        "role_tags": ["python", "javascript", "java", "programming", "stack"],
        "starter_code": {
            "python": (
                "s = input().strip()\n"
                "pairs = {')': '(', ']': '[', '}': '{'}\n"
                "stack = []\n"
                "valid = True\n"
                "for ch in s:\n"
                "    if ch in '([{':\n"
                "        stack.append(ch)\n"
                "    elif not stack or stack.pop() != pairs.get(ch):\n"
                "        valid = False\n"
                "        break\n"
                "print('YES' if valid and not stack else 'NO')\n"
            ),
            "javascript": (
                "let raw = '';\n"
                "process.stdin.on('data', d => raw += d);\n"
                "process.stdin.on('end', () => {\n"
                "  const s = raw.trim();\n"
                "  const pairs = { ')': '(', ']': '[', '}': '{' };\n"
                "  const stack = [];\n"
                "  let ok = true;\n"
                "  for (const ch of s) {\n"
                "    if ('([{'.includes(ch)) stack.push(ch);\n"
                "    else if (!stack.length || stack.pop() !== pairs[ch]) { ok = false; break; }\n"
                "  }\n"
                "  console.log(ok && stack.length === 0 ? 'YES' : 'NO');\n"
                "});\n"
            ),
            "java": (
                "import java.util.*;\n"
                "public class Main {\n"
                "    public static void main(String[] args) {\n"
                "        Scanner sc = new Scanner(System.in);\n"
                "        String s = sc.hasNextLine() ? sc.nextLine().trim() : \"\";\n"
                "        Deque<Character> st = new ArrayDeque<>();\n"
                "        boolean ok = true;\n"
                "        for (char c : s.toCharArray()) {\n"
                "            if (c == '(' || c == '[' || c == '{') st.push(c);\n"
                "            else if (st.isEmpty()) { ok = false; break; }\n"
                "            else {\n"
                "                char top = st.pop();\n"
                "                if ((c == ')' && top != '(') || (c == ']' && top != '[') || (c == '}' && top != '{')) { ok = false; break; }\n"
                "            }\n"
                "        }\n"
                "        System.out.println((ok && st.isEmpty()) ? \"YES\" : \"NO\");\n"
                "    }\n"
                "}\n"
            ),
        },
        "test_cases": [
            {"stdin": "({[]})\n", "expected_stdout": "YES", "is_sample": True},
            {"stdin": "([)]\n", "expected_stdout": "NO", "is_sample": True},
            {"stdin": "((()\n", "expected_stdout": "NO", "is_sample": False},
        ],
        "explanation_text": "Push opening brackets onto a stack; on each closing bracket verify the stack is non-empty and matches its corresponding opener. At the end, the stack must be empty.",
        "expected_time_seconds": 480,
        "max_marks": 20,
    },
    {
        "title": "Recursion & Call Stack Space",
        "prompt_text": "A recursive binary search on a sorted array of N elements executes at most how much auxiliary call-stack space in the standard recursive formulation?",
        "category": ArenaCategory.PROGRAMMING_FUNDAMENTALS,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["python", "java", "c++", "fundamentals"],
        "options": [
            {"key": "A", "text": "O(1)"},
            {"key": "B", "text": "O(log N)"},
            {"key": "C", "text": "O(N)"},
            {"key": "D", "text": "O(N log N)"},
        ],
        "correct_option_key": "B",
        "explanation_text": "Without tail-call elimination, each halving step adds one stack frame, creating recursion depth O(log N).",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },

    # --- 3. Database Management Systems ---
    {
        "title": "Third Normal Form (3NF) Guarantee",
        "prompt_text": "A relation already in 2NF violates Third Normal Form (3NF) specifically when it contains which type of dependency?",
        "category": ArenaCategory.DBMS,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "company_tag": "FinCore Systems Pattern",
        "role_tags": ["sql", "postgresql", "database", "backend"],
        "options": [
            {"key": "A", "text": "A transitive dependency where a non-prime attribute determines another non-prime attribute"},
            {"key": "B", "text": "A primary key that consists of a single integer column"},
            {"key": "C", "text": "An index created on a foreign key column"},
            {"key": "D", "text": "Any foreign key referencing another table"},
        ],
        "correct_option_key": "A",
        "explanation_text": "3NF eliminates transitive functional dependencies (X -> Y -> Z where X is superkey and Y, Z are non-prime attributes).",
        "expected_time_seconds": 75,
        "max_marks": 10,
    },
    {
        "title": "B-Tree Index Selectivity & Range Queries",
        "prompt_text": "On a composite B-Tree index `(department_id, graduation_year, cgpa)`, which query condition CANNOT leverage the leading leftmost prefix efficiently?",
        "category": ArenaCategory.DBMS,
        "difficulty": ArenaDifficulty.HARD,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["sql", "postgresql", "database", "backend"],
        "options": [
            {"key": "A", "text": "WHERE department_id = 3 AND graduation_year = 2027"},
            {"key": "B", "text": "WHERE department_id = 3 AND cgpa >= 8.0"},
            {"key": "C", "text": "WHERE cgpa >= 8.5 ORDER BY cgpa DESC"},
            {"key": "D", "text": "WHERE department_id = 3 ORDER BY graduation_year"},
        ],
        "correct_option_key": "C",
        "explanation_text": "Composite B-Tree indexes require the leftmost leading column (`department_id`) for fast prefix lookup. Filtering solely on `cgpa` skips the leading keys.",
        "expected_time_seconds": 90,
        "max_marks": 10,
    },

    # --- 4. Operating Systems ---
    {
        "title": "Coffman Deadlock Conditions",
        "prompt_text": "Which of the following is NOT one of the four necessary conditions for a resource deadlock to occur?",
        "category": ArenaCategory.OPERATING_SYSTEMS,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["systems", "backend", "os"],
        "options": [
            {"key": "A", "text": "Mutual exclusion"},
            {"key": "B", "text": "Hold and wait"},
            {"key": "C", "text": "Preemptive scheduling"},
            {"key": "D", "text": "Circular wait"},
        ],
        "correct_option_key": "C",
        "explanation_text": "The four Coffman conditions are Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait. Preemption prevents deadlock rather than causing it.",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },
    {
        "title": "Virtual Memory Page Fault Handling",
        "prompt_text": "When a process accesses a virtual page whose present/valid bit is 0 in the page table, what sequence happens first?",
        "category": ArenaCategory.OPERATING_SYSTEMS,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["systems", "c++", "os"],
        "options": [
            {"key": "A", "text": "The MMU triggers a page fault trap to the OS kernel"},
            {"key": "B", "text": "The CPU immediately terminates the process with SIGSEGV before checking swap"},
            {"key": "C", "text": "The L1 cache directly fetches the block from disk bypassing the kernel"},
            {"key": "D", "text": "The TLB rewrites the physical frame number automatically without OS intervention"},
        ],
        "correct_option_key": "A",
        "explanation_text": "When valid=0, the MMU raises a page fault exception; the OS inspects permissions, loads the page from backing store/allocates a zeroed frame, updates the page table, and restarts the instruction.",
        "expected_time_seconds": 90,
        "max_marks": 10,
    },

    # --- 5. Computer Networks ---
    {
        "title": "TCP vs UDP Reliability & Ordering",
        "prompt_text": "Why do real-time video conferencing and DNS lookups frequently prefer UDP over TCP?",
        "category": ArenaCategory.COMPUTER_NETWORKS,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["networking", "backend", "cloud"],
        "options": [
            {"key": "A", "text": "UDP guarantees ordered packet delivery without headers"},
            {"key": "B", "text": "UDP avoids three-way handshake and head-of-line retransmission stalls"},
            {"key": "C", "text": "UDP operates at the Physical Layer directly over Ethernet frames"},
            {"key": "D", "text": "UDP encrypts payloads natively at Layer 4"},
        ],
        "correct_option_key": "B",
        "explanation_text": "UDP sends single datagrams with minimal overhead and no retransmission/head-of-line blocking, minimizing latency for short queries (DNS) and live media.",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },
    {
        "title": "HTTPS TLS Handshake Purpose",
        "prompt_text": "In HTTPS (HTTP over TLS 1.3), why is asymmetric cryptography used during the handshake while symmetric encryption encrypts the actual HTTP traffic?",
        "category": ArenaCategory.COMPUTER_NETWORKS,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "company_tag": "ApexCloud Engineering Pattern",
        "role_tags": ["security", "networking", "backend", "cloud"],
        "options": [
            {"key": "A", "text": "Symmetric encryption cannot secure HTTP headers"},
            {"key": "B", "text": "Asymmetric crypto authenticates identity and negotiates ephemeral session keys, while symmetric AEAD is orders of magnitude faster for bulk data"},
            {"key": "C", "text": "Browsers forbid symmetric ciphers for payloads larger than 4 KB"},
            {"key": "D", "text": "Asymmetric crypto compresses JSON bodies automatically"},
        ],
        "correct_option_key": "B",
        "explanation_text": "TLS uses asymmetric signatures/ECDHE key exchange for authentication and forward secrecy, then switches to fast symmetric ciphers (AES-GCM / ChaCha20-Poly1305).",
        "expected_time_seconds": 90,
        "max_marks": 10,
    },

    # --- 6. Object-Oriented Programming ---
    {
        "title": "Liskov Substitution Principle (SOLID)",
        "prompt_text": "Which violation illustrates breaking the Liskov Substitution Principle (LSP)?",
        "category": ArenaCategory.OOP,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "company_tag": "FinCore Systems Pattern",
        "role_tags": ["java", "oop", "design", "python", "backend"],
        "options": [
            {"key": "A", "text": "Subclass implements an optional caching decorator while honoring interface contracts"},
            {"key": "B", "text": "Subclass overrides a base method and throws UnsupportedOperationException where callers expect a valid return"},
            {"key": "C", "text": "Injecting a repository interface via constructor parameters"},
            {"key": "D", "text": "Declaring helper methods private inside a concrete class"},
        ],
        "correct_option_key": "B",
        "explanation_text": "LSP requires subclasses to honor all preconditions, postconditions, and behavioral expectations of their base type so callers work transparently.",
        "expected_time_seconds": 75,
        "max_marks": 10,
    },
    {
        "title": "Composition vs Inheritance",
        "prompt_text": "Why do software architecture guidelines commonly recommend 'favor composition over inheritance'?",
        "category": ArenaCategory.OOP,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["java", "python", "oop", "software engineer"],
        "options": [
            {"key": "A", "text": "Composition avoids deep fragile base-class hierarchies and enables runtime behavior swapping"},
            {"key": "B", "text": "Inheritance is disallowed in modern typed languages"},
            {"key": "C", "text": "Composition eliminates all memory allocations"},
            {"key": "D", "text": "Composition prevents unit testing"},
        ],
        "correct_option_key": "A",
        "explanation_text": "Composition couples classes through narrow interfaces, reducing tight coupling to superclass internals and allowing dynamic delegation.",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },

    # --- 7. Aptitude & Logical Reasoning ---
    {
        "title": "Syllogism Validity Check",
        "prompt_text": (
            "Statements:\n"
            "1. All backend engineers know SQL.\n"
            "2. Some database analysts are backend engineers.\n\n"
            "Which conclusion follows with 100% logical certainty?"
        ),
        "category": ArenaCategory.APTITUDE_LOGICAL,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "company_tag": "Campus Screening Pattern",
        "role_tags": ["aptitude", "analyst", "software engineer"],
        "options": [
            {"key": "A", "text": "All database analysts know SQL"},
            {"key": "B", "text": "Some database analysts know SQL"},
            {"key": "C", "text": "No SQL developers are database analysts"},
            {"key": "D", "text": "All SQL experts are backend engineers"},
        ],
        "correct_option_key": "B",
        "explanation_text": "Since some database analysts belong to the set of backend engineers, and all backend engineers know SQL, those overlapping analysts must know SQL.",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },
    {
        "title": "Sequential Server Scheduling Puzzle",
        "prompt_text": (
            "Five jobs A, B, C, D, E run sequentially once each. "
            "B must run immediately before D. E cannot run first or last. "
            "C runs immediately after A. If A is scheduled 1st, which job runs 5th (last)?"
        ),
        "category": ArenaCategory.APTITUDE_LOGICAL,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["aptitude", "logic"],
        "options": [
            {"key": "A", "text": "E"},
            {"key": "B", "text": "B"},
            {"key": "C", "text": "D"},
            {"key": "D", "text": "C"},
        ],
        "correct_option_key": "C",
        "explanation_text": "A=1 implies C=2. The remaining slots 3,4,5 hold {B-D consecutive, E}. Since E cannot be 5th, E=3 and (B,D)=(4,5), so D runs 5th.",
        "expected_time_seconds": 90,
        "max_marks": 10,
    },

    # --- 8. Quantitative Ability ---
    {
        "title": "Conditional Probability in Quality Control",
        "prompt_text": "Two fair dice are rolled independently. What is the probability that the sum of their faces is at least 10?",
        "category": ArenaCategory.QUANTITATIVE,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "company_tag": "FinCore Systems Pattern",
        "role_tags": ["quant", "data", "analyst"],
        "options": [
            {"key": "A", "text": "1/12"},
            {"key": "B", "text": "1/6"},
            {"key": "C", "text": "5/36"},
            {"key": "D", "text": "7/36"},
        ],
        "correct_option_key": "B",
        "explanation_text": "Favorable outcomes out of 36: (4,6),(5,5),(6,4),(5,6),(6,5),(6,6) = 6 outcomes. 6/36 = 1/6.",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },
    {
        "title": "Throughput Work-Rate Problem",
        "prompt_text": "Worker Node A processes a batch in 12 minutes and Node B processes the same batch in 15 minutes. Working together in parallel, how long do they take to complete one batch?",
        "category": ArenaCategory.QUANTITATIVE,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["quant", "aptitude"],
        "options": [
            {"key": "A", "text": "6 minutes 40 seconds"},
            {"key": "B", "text": "7 minutes 15 seconds"},
            {"key": "C", "text": "13 minutes 30 seconds"},
            {"key": "D", "text": "6 minutes 00 seconds"},
        ],
        "correct_option_key": "A",
        "explanation_text": "Combined rate = 1/12 + 1/15 = (5+4)/60 = 9/60 = 3/20 batch/min. Time = 20/3 min = 6 min 40 sec.",
        "expected_time_seconds": 75,
        "max_marks": 10,
    },
    {
        "title": "Compound Growth and Depreciation",
        "prompt_text": "A tech server worth $10,000 depreciates in value by 20% in its first year and 10% in its second year. What is its book value at the end of two years?",
        "category": ArenaCategory.QUANTITATIVE,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["quant", "percentages", "aptitude"],
        "options": [
            {"key": "A", "text": "$7,200"},
            {"key": "B", "text": "$7,000"},
            {"key": "C", "text": "$6,800"},
            {"key": "D", "text": "$7,500"},
        ],
        "correct_option_key": "A",
        "explanation_text": "After year 1: $10,000 * 0.80 = $8,000. After year 2: $8,000 * 0.90 = $7,200.",
        "expected_time_seconds": 45,
        "max_marks": 10,
    },
    {
        "title": "Time, Speed and Relative Motion",
        "prompt_text": "Two trains 150m and 250m long run on parallel tracks towards each other at 54 km/h and 90 km/h respectively. In how many seconds will they clear each other after meeting?",
        "category": ArenaCategory.QUANTITATIVE,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["quant", "speed_distance", "aptitude"],
        "options": [
            {"key": "A", "text": "10 seconds"},
            {"key": "B", "text": "12 seconds"},
            {"key": "C", "text": "15 seconds"},
            {"key": "D", "text": "8 seconds"},
        ],
        "correct_option_key": "A",
        "explanation_text": "Total distance = 150 + 250 = 400m. Relative speed = 54 + 90 = 144 km/h = 144 * (5/18) = 40 m/s. Time = 400 / 40 = 10 seconds.",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },
    {
        "title": "Permutations of Server Cluster Keys",
        "prompt_text": "In how many distinct ways can the letters of the word 'CLUSTER' be arranged such that all vowels (U, E) always stay together?",
        "category": ArenaCategory.QUANTITATIVE,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["quant", "permutations", "aptitude"],
        "options": [
            {"key": "A", "text": "1440"},
            {"key": "B", "text": "720"},
            {"key": "C", "text": "5040"},
            {"key": "D", "text": "2880"},
        ],
        "correct_option_key": "A",
        "explanation_text": "Treat (UE) as 1 unit with 5 consonants (C,L,S,T,R) -> 6 items arranged in 6! = 720 ways. Vowels arrange in 2! = 2 ways. Total = 720 * 2 = 1440.",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },
    {
        "title": "Number Series Pattern Identification",
        "prompt_text": "Identify the missing number in the sequence: 4, 9, 25, 49, 121, ?",
        "category": ArenaCategory.APTITUDE_LOGICAL,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["logic", "series", "aptitude"],
        "options": [
            {"key": "A", "text": "169"},
            {"key": "B", "text": "144"},
            {"key": "C", "text": "196"},
            {"key": "D", "text": "225"},
        ],
        "correct_option_key": "A",
        "explanation_text": "The terms are squares of consecutive prime numbers: 2^2=4, 3^2=9, 5^2=25, 7^2=49, 11^2=121. The next prime is 13, so 13^2 = 169.",
        "expected_time_seconds": 45,
        "max_marks": 10,
    },
    {
        "title": "Blood Relations Logical Deduction",
        "prompt_text": "Pointing to a photograph, Rohit said: 'Her mother's only son is my father.' How is the woman in the photograph related to Rohit?",
        "category": ArenaCategory.APTITUDE_LOGICAL,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["logic", "blood_relations", "aptitude"],
        "options": [
            {"key": "A", "text": "Paternal Aunt (Father's Sister)"},
            {"key": "B", "text": "Mother"},
            {"key": "C", "text": "Sister"},
            {"key": "D", "text": "Grandmother"},
        ],
        "correct_option_key": "A",
        "explanation_text": "Her mother's only son = her brother. That brother is Rohit's father. Thus, the woman is Rohit's father's sister, which is his paternal aunt.",
        "expected_time_seconds": 45,
        "max_marks": 10,
    },
    {
        "title": "Direction Sense and Displacement",
        "prompt_text": "An autonomous rover moves 8 km East, turns right and drives 6 km South, then turns right again and moves 16 km West. How far and in what direction is the rover from its starting origin?",
        "category": ArenaCategory.APTITUDE_LOGICAL,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["logic", "directions", "aptitude"],
        "options": [
            {"key": "A", "text": "10 km South-West"},
            {"key": "B", "text": "10 km South-East"},
            {"key": "C", "text": "14 km West"},
            {"key": "D", "text": "8 km South"},
        ],
        "correct_option_key": "A",
        "explanation_text": "Net displacement: East-West = 8 - 16 = -8 km (West). North-South = -6 km (South). Distance = sqrt((-8)^2 + (-6)^2) = sqrt(64+36) = 10 km South-West.",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },

    # --- 9. Verbal Ability ---
    {
        "title": "Technical Sentence Precision",
        "prompt_text": "Choose the grammatically crisp, idiomatic sentence for a production post-mortem report:",
        "category": ArenaCategory.VERBAL,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["verbal", "communication"],
        "options": [
            {"key": "A", "text": "Neither the primary replica nor the standby nodes was responding to health checks."},
            {"key": "B", "text": "Neither the primary replica nor the standby nodes were responding to health checks."},
            {"key": "C", "text": "Neither the primary replica or the standby nodes were responding to health checks."},
            {"key": "D", "text": "The primary replica neither nor standby nodes responded to health checks."},
        ],
        "correct_option_key": "B",
        "explanation_text": "With 'neither ... nor', the verb agrees with the nearer subject ('standby nodes' -> plural 'were').",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },
    {
        "title": "Concise Technical Inference",
        "prompt_text": (
            "Passage: 'While microservices decouple team deployments, premature splitting of tightly coupled domain tables "
            "turns local ACID transactions into fragile distributed sagas.'\n"
            "What is the author's primary engineering recommendation?"
        ),
        "category": ArenaCategory.VERBAL,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["verbal", "architecture"],
        "options": [
            {"key": "A", "text": "Microservices should always be avoided in enterprise software."},
            {"key": "B", "text": "Avoid splitting tightly coupled data boundaries prematurely before domain isolation is clear."},
            {"key": "C", "text": "ACID transactions do not work inside modular monoliths."},
            {"key": "D", "text": "Distributed sagas require less coordination than local SQL transactions."},
        ],
        "correct_option_key": "B",
        "explanation_text": "The passage balances benefits of microservices against the cost of premature decomposition across coupled domain data.",
        "expected_time_seconds": 90,
        "max_marks": 10,
    },

    # --- 10. Technical MCQs ---
    {
        "title": "HTTP Idempotency Semantics",
        "prompt_text": "Which HTTP methods are defined by the HTTP specification as idempotent (repeating identical requests leaves server resource state equivalent to one execution)?",
        "category": ArenaCategory.TECHNICAL_MCQS,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "company_tag": "ApexCloud Engineering Pattern",
        "role_tags": ["rest", "api", "fastapi", "react", "backend"],
        "options": [
            {"key": "A", "text": "POST and PUT"},
            {"key": "B", "text": "GET, PUT, and DELETE"},
            {"key": "C", "text": "POST, PATCH, and CONNECT"},
            {"key": "D", "text": "Only POST"},
        ],
        "correct_option_key": "B",
        "explanation_text": "GET, HEAD, PUT, and DELETE are idempotent in RFC semantics; POST is non-idempotent because repeated calls typically create multiple resources.",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },
    {
        "title": "Container Layer Caching Optimization",
        "prompt_text": "When authoring a multi-stage Dockerfile for a Python FastAPI service, why should `COPY requirements.txt` and `pip install` precede `COPY . .`?",
        "category": ArenaCategory.TECHNICAL_MCQS,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["docker", "devops", "cloud", "python"],
        "options": [
            {"key": "A", "text": "So frequent application code edits reuse the cached dependency installation layer"},
            {"key": "B", "text": "Because Python refuses to import modules copied after pip install"},
            {"key": "C", "text": "Because Docker cannot copy hidden files before requirements.txt"},
            {"key": "D", "text": "It eliminates the need for a base OS image"},
        ],
        "correct_option_key": "A",
        "explanation_text": "Docker invalidates cache for an instruction and all subsequent layers whenever copied files change. Copying dependencies first preserves layer cache across code changes.",
        "expected_time_seconds": 75,
        "max_marks": 10,
    },
    {
        "title": "Simply Supported Beam Maximum Bending Moment",
        "prompt_text": "For a simply supported beam of span length `L` carrying a uniformly distributed load (UDL) of intensity `w` per unit length across its entire span, what is the maximum bending moment and where does it occur?",
        "category": ArenaCategory.TECHNICAL_MCQS,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["civil", "structural", "mechanics", "structures"],
        "options": [
            {"key": "A", "text": "(w * L^2) / 8 at mid-span (x = L / 2)"},
            {"key": "B", "text": "(w * L^2) / 4 at the quarter-span"},
            {"key": "C", "text": "(w * L) / 2 at both support ends"},
            {"key": "D", "text": "(w * L^2) / 12 at the fixed end"},
        ],
        "correct_option_key": "A",
        "explanation_text": "For a simply supported beam with full UDL, the shear force crosses zero at mid-span (L/2), producing the maximum positive bending moment of M_max = (w * L^2) / 8.",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },
    {
        "title": "Euler Critical Buckling Load for Pin-Ended Column",
        "prompt_text": "According to Euler's buckling theory, the critical buckling load P_cr for an ideal elastic column of length L, modulus of elasticity E, and minimum moment of inertia I with both ends pinned is given by:",
        "category": ArenaCategory.TECHNICAL_MCQS,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["structural", "civil", "mechanical", "solid_mechanics"],
        "options": [
            {"key": "A", "text": "(pi^2 * E * I) / L^2"},
            {"key": "B", "text": "(4 * pi^2 * E * I) / L^2"},
            {"key": "C", "text": "(pi^2 * E * I) / (4 * L^2)"},
            {"key": "D", "text": "(2 * pi * E * I) / L"},
        ],
        "correct_option_key": "A",
        "explanation_text": "For both ends pinned (effective length Le = L), Euler's formula yields P_cr = (pi^2 * E * I) / L^2. Fixed-fixed would be 4*pi^2*E*I/L^2 and fixed-free would be pi^2*E*I/(4*L^2).",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },
    {
        "title": "Carnot Heat Engine Theoretical Maximum Efficiency",
        "prompt_text": "A heat engine operates reversibly between a hot source at temperature T_H (in Kelvin) and a cold sink at T_C (in Kelvin). What is the theoretical maximum thermal efficiency achievable according to the Second Law of Thermodynamics?",
        "category": ArenaCategory.TECHNICAL_MCQS,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["mechanical", "thermal", "thermodynamics", "chemical"],
        "options": [
            {"key": "A", "text": "1 - (T_C / T_H)"},
            {"key": "B", "text": "(T_H - T_C) / T_C"},
            {"key": "C", "text": "1 - (T_H / T_C)"},
            {"key": "D", "text": "T_C / T_H"},
        ],
        "correct_option_key": "A",
        "explanation_text": "Carnot efficiency represents the upper bound for any thermodynamic power cycle: eta = (W_net / Q_in) = 1 - (T_C / T_H), where temperatures must be in absolute Kelvin.",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },
    {
        "title": "Economic Order Quantity (EOQ) Optimal Trade-off",
        "prompt_text": "In industrial engineering and inventory control, the classical Ford W. Harris Economic Order Quantity (EOQ) model determines the order size that minimizes which total cost combination?",
        "category": ArenaCategory.TECHNICAL_MCQS,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["industrial", "production", "operations", "supply_chain"],
        "options": [
            {"key": "A", "text": "Sum of annual ordering / setup costs and annual inventory holding / carrying costs"},
            {"key": "B", "text": "Raw material purchase price minus supplier bulk discounts"},
            {"key": "C", "text": "Shipping freight charges and warehouse depreciation costs only"},
            {"key": "D", "text": "Factory overtime labor wages and machine calibration costs"},
        ],
        "correct_option_key": "A",
        "explanation_text": "EOQ balances fixed order costs (which decrease per unit as batch size rises) with holding costs (which increase linearly with batch size), reaching the minimum where annual ordering cost equals annual holding cost.",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },
    {
        "title": "Maximum Power Transfer Theorem in DC Circuits",
        "prompt_text": "According to the Maximum Power Transfer Theorem, maximum electrical power is transferred from a linear DC source with Thevenin resistance R_th to a variable resistive load R_L when:",
        "category": ArenaCategory.TECHNICAL_MCQS,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["electrical", "electronics", "circuit_theory", "power_systems"],
        "options": [
            {"key": "A", "text": "R_L = R_th"},
            {"key": "B", "text": "R_L = 0 (short circuit)"},
            {"key": "C", "text": "R_L = infinity (open circuit)"},
            {"key": "D", "text": "R_L = 2 * R_th"},
        ],
        "correct_option_key": "A",
        "explanation_text": "Maximum power transfer occurs when load resistance R_L equals source internal Thevenin resistance R_th (efficiency is 50% under maximum power condition).",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },
    {
        "title": "Nyquist-Shannon Sampling Theorem Minimum Rate",
        "prompt_text": "In signal processing and communications, to avoid aliasing and achieve exact reconstruction of a continuous-time bandlimited signal with highest frequency component f_max, what is the minimum sampling frequency f_s required?",
        "category": ArenaCategory.TECHNICAL_MCQS,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["electronics", "communication", "signal_processing", "telecom"],
        "options": [
            {"key": "A", "text": "f_s >= 2 * f_max (Nyquist rate)"},
            {"key": "B", "text": "f_s = f_max"},
            {"key": "C", "text": "f_s = f_max / 2"},
            {"key": "D", "text": "f_s = 4 * f_max^2"},
        ],
        "correct_option_key": "A",
        "explanation_text": "The Nyquist-Shannon sampling criterion requires f_s >= 2 * f_max so that spectral replicas do not overlap, preventing frequency aliasing.",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },
    {
        "title": "Fluid Flow Regime Criterion in Circular Conduits",
        "prompt_text": "In chemical process engineering and fluid mechanics, fluid flow inside a smooth circular pipe is universally considered laminar when the dimensionless Reynolds number Re is:",
        "category": ArenaCategory.TECHNICAL_MCQS,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["chemical", "petroleum", "fluid_dynamics", "process"],
        "options": [
            {"key": "A", "text": "Re < 2100 (or Re <= 2000)"},
            {"key": "B", "text": "Re > 10000"},
            {"key": "C", "text": "2300 < Re < 4000"},
            {"key": "D", "text": "Re = 0"},
        ],
        "correct_option_key": "A",
        "explanation_text": "In pipe flow, Re = (rho * v * D) / mu. Flows with Re < 2100 are governed by viscous damping (laminar); above ~4000 flow is fully turbulent.",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },
    {
        "title": "Darcy's Law for Flow Through Porous Reservoir Rocks",
        "prompt_text": "In reservoir and petroleum engineering, Darcy's Law describes fluid flow through porous media. If flow rate is Q, permeability is k, cross-sectional area is A, dynamic viscosity is mu, and pressure drop over length L is Delta_P, what is the fundamental relationship?",
        "category": ArenaCategory.TECHNICAL_MCQS,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["petroleum", "mining", "reservoir", "geology"],
        "options": [
            {"key": "A", "text": "Q = (k * A * Delta_P) / (mu * L)"},
            {"key": "B", "text": "Q = (mu * L * Delta_P) / (k * A)"},
            {"key": "C", "text": "Q = (k * mu * A) / (Delta_P * L)"},
            {"key": "D", "text": "Q = (k * A) / (mu * Delta_P)"},
        ],
        "correct_option_key": "A",
        "explanation_text": "Darcy's Law states that fluid volume flow rate Q is directly proportional to permeability k, cross-sectional area A, and pressure gradient (Delta_P / L), inversely proportional to fluid viscosity mu.",
        "expected_time_seconds": 75,
        "max_marks": 10,
    },
    {
        "title": "Underground Coal Mine Safety and Methane Gas Monitoring",
        "prompt_text": "In underground coal mining ventilation and safety engineering, why is continuous atmospheric monitoring of methane (CH4) critical, and within what concentration range in air does methane form an explosive mixture (firedamp)?",
        "category": ArenaCategory.TECHNICAL_MCQS,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["mining", "safety", "ventilation", "geotechnical"],
        "options": [
            {"key": "A", "text": "Methane forms an explosive mixture between approximately 5% and 15% in atmospheric air with peak explosibility at ~9.5%"},
            {"key": "B", "text": "Methane is only explosive at concentrations exceeding 50% by volume"},
            {"key": "C", "text": "Methane is strictly a toxic nerve agent and non-flammable"},
            {"key": "D", "text": "Methane is explosive between 0.1% and 0.5% in ambient air"},
        ],
        "correct_option_key": "A",
        "explanation_text": "Methane explosive limits in air are 5% (lower explosive limit, LEL) to 15% (upper explosive limit, UEL). Mining regulations mandate electrical shutdown when concentrations reach 1.0% to 1.5% as safety margins.",
        "expected_time_seconds": 75,
        "max_marks": 10,
    },
    {
        "title": "Floor Area Ratio (FAR) and Urban Development Control",
        "prompt_text": "In architectural planning and municipal zoning bye-laws, what does Floor Area Ratio (FAR, also known as Floor Space Index / FSI) represent, and how is it calculated?",
        "category": ArenaCategory.TECHNICAL_MCQS,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.MCQ,
        "role_tags": ["architecture", "planning", "urban_design", "zoning"],
        "options": [
            {"key": "A", "text": "Total gross floor area of all building floors divided by the total area of the plot"},
            {"key": "B", "text": "Ground coverage footprint area divided by total plot area"},
            {"key": "C", "text": "Carpet area divided by built-up area"},
            {"key": "D", "text": "Height of the building divided by the front road width"},
        ],
        "correct_option_key": "A",
        "explanation_text": "FAR / FSI is defined as (Total Covered Floor Area of All Storeys) / (Total Plot Area). It regulates building density, population load, and municipal infrastructure capacity.",
        "expected_time_seconds": 60,
        "max_marks": 10,
    },

    # --- 11. HR & Behavioral Preparation ---
    {
        "title": "Handling Tight Deadline Trade-offs (STAR)",
        "prompt_text": (
            "Describe a project situation where an unexpected bug or scope change threatened a hard deadline. "
            "Structure your response using Situation, Task, Action, and measurable Result, focusing on engineering trade-offs and communication."
        ),
        "category": ArenaCategory.HR_BEHAVIORAL,
        "difficulty": ArenaDifficulty.MEDIUM,
        "question_type": ArenaQuestionType.BEHAVIORAL,
        "company_tag": "ApexCloud Engineering Pattern",
        "role_tags": ["behavioral", "hr", "leadership", "communication"],
        "explanation_text": (
            "Strong STAR answers clarify constraints quickly (Situation/Task), highlight your own ownership and prioritization decision "
            "(Action — e.g., isolating root cause, negotiating scope/test coverage), and quantify the outcome (Result — delivered on schedule with zero regressions)."
        ),
        "sample_solution_text": (
            "Situation: 48 hours before demo, our ingestion service timed out on large PDFs. "
            "Task: Stabilize throughput without losing accuracy. "
            "Action: Profiled parser hotspots, added streaming chunk limits + unit regression tests, and aligned stakeholders on async queue UX. "
            "Result: Cut p95 latency from 14s to 2.1s and shipped on time."
        ),
        "expected_time_seconds": 240,
        "max_marks": 10,
    },
    {
        "title": "Constructive Disagreement in Code Review",
        "prompt_text": (
            "Tell us about a time you disagreed with a teammate or senior peer on a technical approach. "
            "How did you evaluate evidence and reach alignment?"
        ),
        "category": ArenaCategory.HR_BEHAVIORAL,
        "difficulty": ArenaDifficulty.EASY,
        "question_type": ArenaQuestionType.BEHAVIORAL,
        "role_tags": ["behavioral", "teamwork", "hr"],
        "explanation_text": (
            "Interviewers look for psychological safety, data-driven benchmarks instead of ego, active listening, and commitment to the final team decision."
        ),
        "sample_solution_text": (
            "Focus on comparing concrete metrics (latency, maintainability, migration cost) through a small proof-of-concept rather than debating opinions."
        ),
        "expected_time_seconds": 180,
        "max_marks": 10,
    },
]

# Append branch-specific curated questions
CURATED_QUESTIONS.extend(BRANCH_CURATED_QUESTIONS)


CURATED_ASSESSMENTS: List[Dict[str, Any]] = [
    {
        "title": "Core CS Foundations Timed Mock",
        "description": "Balanced 20-minute timed assessment spanning DSA, DBMS, Operating Systems, Computer Networks, and OOP.",
        "mode": ArenaAssessmentMode.TIMED_TEST,
        "category": None,
        "difficulty": ArenaDifficulty.MEDIUM,
        "company_name_style": None,
        "provenance_notice": CURATED_PROVENANCE_NOTICE,
        "duration_minutes": 20,
        "passing_percentage": 60.0,
        "department_code": "CSE",
        "question_titles": [
            "Binary Heap Insertion & Extraction Complexity",
            "Third Normal Form (3NF) Guarantee",
            "Coffman Deadlock Conditions",
            "TCP vs UDP Reliability & Ordering",
            "Liskov Substitution Principle (SOLID)",
        ],
    },
    {
        "title": "ApexCloud Software Engineer Pattern Prep",
        "description": "Original multi-format engineering prep combining coding, system fundamentals, HTTP semantics, and behavioral STAR readiness.",
        "mode": ArenaAssessmentMode.COMPANY_PREP,
        "category": None,
        "difficulty": ArenaDifficulty.MEDIUM,
        "company_name_style": "ApexCloud Engineering Pattern",
        "provenance_notice": COMPANY_PROVENANCE_NOTICE,
        "duration_minutes": 35,
        "passing_percentage": 60.0,
        "department_code": "CSE",
        "question_titles": [
            "Two Sum Pair Indices",
            "Balanced Brackets Validator",
            "HTTPS TLS Handshake Purpose",
            "HTTP Idempotency Semantics",
            "Handling Tight Deadline Trade-offs (STAR)",
        ],
    },
    {
        "title": "FinCore Systems & Quant Pattern Prep",
        "description": "Original screening prep covering Kadane optimization, relational normalization, OOP contracts, and probability.",
        "mode": ArenaAssessmentMode.COMPANY_PREP,
        "category": None,
        "difficulty": ArenaDifficulty.MEDIUM,
        "company_name_style": "FinCore Systems Pattern",
        "provenance_notice": COMPANY_PROVENANCE_NOTICE,
        "duration_minutes": 30,
        "passing_percentage": 60.0,
        "department_code": "CSE",
        "question_titles": [
            "Maximum Subarray Sum (Kadane Pattern)",
            "Third Normal Form (3NF) Guarantee",
            "Liskov Substitution Principle (SOLID)",
            "Conditional Probability in Quality Control",
        ],
    },
    {
        "title": "Campus Aptitude, Quant & Verbal Screening",
        "description": "Timed 15-minute campus Stage-1 aptitude, quantitative reasoning, and technical verbal screening drill.",
        "mode": ArenaAssessmentMode.TIMED_TEST,
        "category": ArenaCategory.APTITUDE_LOGICAL,
        "difficulty": ArenaDifficulty.EASY,
        "company_name_style": "Campus Screening Pattern",
        "provenance_notice": CURATED_PROVENANCE_NOTICE,
        "duration_minutes": 15,
        "passing_percentage": 60.0,
        "department_code": None,
        "question_titles": [
            "Syllogism Validity Check",
            "Sequential Server Scheduling Puzzle",
            "Conditional Probability in Quality Control",
            "Throughput Work-Rate Problem",
            "Technical Sentence Precision",
        ],
    },
]


async def ensure_arena_seed_data(db: AsyncSession) -> None:
    """Idempotently populate curated Arena questions and assessments if missing."""
    from app.services.branch_arena_question_bank import BRANCH_CURATED_QUESTIONS, BRANCH_CURATED_ASSESSMENTS
    from app.models.organization import Department

    depts = (await db.execute(select(Department))).scalars().all()
    dept_by_code: Dict[str, int] = {d.code.upper(): d.id for d in depts if d.code}

    existing_rows = (
        await db.execute(
            select(ArenaQuestion).where(
                ArenaQuestion.institution_id.is_(None),
                ArenaQuestion.content_source == ArenaContentSource.CURATED_ORIGINAL,
            )
        )
    ).scalars().all()
    by_title: Dict[str, ArenaQuestion] = {q.title: q for q in existing_rows}

    added_any = False
    all_q_specs = list(CURATED_QUESTIONS) + list(BRANCH_CURATED_QUESTIONS)
    for spec in all_q_specs:
        if spec["title"] in by_title:
            existing_q = by_title[spec["title"]]
            if spec.get("starter_code") and existing_q.starter_code_json != spec.get("starter_code"):
                existing_q.starter_code_json = spec["starter_code"]
                added_any = True
            continue
        q = ArenaQuestion(
            title=spec["title"],
            prompt_text=spec["prompt_text"],
            category=spec["category"],
            difficulty=spec["difficulty"],
            question_type=spec["question_type"],
            content_source=ArenaContentSource.CURATED_ORIGINAL,
            company_tag=spec.get("company_tag"),
            role_tags_json=spec.get("role_tags", []),
            options_json=spec.get("options"),
            correct_option_key=spec.get("correct_option_key"),
            starter_code_json=spec.get("starter_code"),
            test_cases_json=spec.get("test_cases"),
            explanation_text=spec["explanation_text"],
            sample_solution_text=spec.get("sample_solution_text"),
            expected_time_seconds=spec.get("expected_time_seconds", 90),
            max_marks=spec.get("max_marks", 10),
            institution_id=None,
            is_active=True,
        )
        db.add(q)
        await db.flush()
        by_title[q.title] = q
        added_any = True

    existing_assess = (
        await db.execute(
            select(ArenaAssessment).where(ArenaAssessment.institution_id.is_(None))
        )
    ).scalars().all()
    assess_by_title: Dict[str, ArenaAssessment] = {}
    for a in existing_assess:
        if a.title in assess_by_title:
            # Clean duplicate
            await db.delete(a)
            added_any = True
        else:
            assess_by_title[a.title] = a

    all_assess_specs = list(CURATED_ASSESSMENTS) + list(BRANCH_CURATED_ASSESSMENTS)
    for spec in all_assess_specs:
        target_dept_id = dept_by_code.get(spec["department_code"]) if spec.get("department_code") else None
        if spec["title"] in assess_by_title:
            existing_a = assess_by_title[spec["title"]]
            if target_dept_id is not None and existing_a.department_id != target_dept_id:
                existing_a.department_id = target_dept_id
                added_any = True
            continue
        q_ids = [by_title[t].id for t in spec["question_titles"] if t in by_title]
        if not q_ids:
            continue
        assess = ArenaAssessment(
            title=spec["title"],
            description=spec["description"],
            mode=spec["mode"],
            category=spec.get("category"),
            difficulty=spec["difficulty"],
            company_name_style=spec.get("company_name_style"),
            provenance_notice=spec["provenance_notice"],
            duration_minutes=spec["duration_minutes"],
            question_ids_json=q_ids,
            passing_percentage=spec["passing_percentage"],
            institution_id=None,
            department_id=target_dept_id,
            is_published=True,
        )
        db.add(assess)
        assess_by_title[assess.title] = assess
        added_any = True

    if added_any:
        await db.commit()

