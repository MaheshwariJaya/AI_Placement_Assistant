"""
Sandboxed Code Execution Service for Placement Preparation Arena.

SECURITY ARCHITECTURE:
- NEVER runs `exec()` or `eval()` inside the FastAPI server process.
- Delegates code execution either to an external sandbox API (`piston` / `judge0` when
  `CODE_SANDBOX_MODE` is configured) or to a tightly constrained, ephemeral OS subprocess
  (`isolated_subprocess`) featuring:
    1. Static pre-execution AST / token guard blocking dangerous OS, filesystem, process,
       reflection, and network APIs (`socket`, `subprocess`, `ctypes`, `fs`, `net`, `java.net`, etc.).
    2. Runtime module/builtin guards inside the child wrapper (blocks `builtins.open`, `socket.socket`,
       `os.system`, Node `Module._load` network/fs modules).
    3. Ephemeral temporary sandbox directory deleted after every invocation + sanitized minimal env
       (strips DATABASE_URL, SECRET_KEY, AI API keys, and user paths).
    4. OS-level resource constraints:
       - Windows: Win32 Job Object (`CreateJobObjectW` + `SetInformationJobObject`) enforcing
         hard memory cap, active process limit (prevents fork bombs), and kill-on-close.
       - POSIX: `resource.setrlimit` (`RLIMIT_AS`, `RLIMIT_CPU`, `RLIMIT_NOFILE`).
    5. Hard wall-clock timeout and bounded stdout/stderr output truncation.
"""
import ast
import asyncio
import ctypes
from ctypes import wintypes
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import get_settings
from app.schemas.arena import SandboxRunResponse, SandboxTestCaseResult

logger = logging.getLogger(__name__)
settings = get_settings()

# Strictly forbidden imports/tokens per language before launching child runtime
PYTHON_FORBIDDEN_MODULES = {
    "os",
    "sys",
    "subprocess",
    "socket",
    "ssl",
    "http",
    "urllib",
    "requests",
    "httpx",
    "aiohttp",
    "ftplib",
    "poplib",
    "imaplib",
    "smtplib",
    "telnetlib",
    "ctypes",
    "multiprocessing",
    "threading",
    "concurrent",
    "shutil",
    "pathlib",
    "tempfile",
    "glob",
    "importlib",
    "pty",
    "fcntl",
    "signal",
    "winreg",
    "msvcrt",
    "webbrowser",
    "pickle",
    "marshal",
}

PYTHON_FORBIDDEN_CALLS = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",
    "breakpoint",
    "globals",
    "locals",
    "vars",
    "getattr",
    "delattr",
    "setattr",
}

JS_FORBIDDEN_PATTERNS = [
    r"""require\s*\(\s*['"](?:fs|fs/promises|child_process|net|http|https|dgram|tls|dns|vm|worker_threads|cluster|os|path|process)['"]\s*\)""",
    r"""import\s+.*from\s+['"](?:fs|fs/promises|child_process|net|http|https|dgram|tls|dns|vm|worker_threads|cluster|os|path|process|node:.*)['"]""",
    r"""\bprocess\s*\.\s*(?:env|exit|kill|binding|dlopen|mainModule)""",
    r"""\b(?:fetch|XMLHttpRequest|WebSocket|eval|Function)\b""",
]

JAVA_FORBIDDEN_PATTERNS = [
    r"""\bjava\s*\.\s*net\b""",
    r"""\bjava\s*\.\s*nio\s*\.\s*file\b""",
    r"""\bjava\s*\.\s*io\s*\.\s*(?:File|FileWriter|FileReader|FileOutputStream|FileInputStream|RandomAccessFile)\b""",
    r"""\bjava\s*\.\s*lang\s*\.\s*reflect\b""",
    r"""\b(?:ProcessBuilder|Runtime\.getRuntime|System\.getenv|System\.getProperties|Socket|ServerSocket|URLConnection|HttpClient)\b""",
]


def _normalize_output(text: str) -> str:
    lines = [line.rstrip() for line in (text or "").replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _validate_python_code(code: str) -> Optional[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"Syntax error on line {exc.lineno}: {exc.msg}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_mod = alias.name.split(".")[0]
                if root_mod in PYTHON_FORBIDDEN_MODULES:
                    return f"Security policy violation: importing '{root_mod}' is blocked in the sandbox."
        elif isinstance(node, ast.ImportFrom):
            root_mod = (node.module or "").split(".")[0]
            if root_mod in PYTHON_FORBIDDEN_MODULES:
                return f"Security policy violation: importing from '{root_mod}' is blocked in the sandbox."
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in PYTHON_FORBIDDEN_CALLS:
                return f"Security policy violation: calling '{node.func.id}()' is blocked in the sandbox."
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") and node.attr in {"__subclasses__", "__globals__", "__builtins__", "__code__"}:
                return f"Security policy violation: access to '{node.attr}' is blocked in the sandbox."
    return None


def _validate_js_code(code: str) -> Optional[str]:
    for pattern in JS_FORBIDDEN_PATTERNS:
        if re.search(pattern, code, flags=re.IGNORECASE):
            return "Security policy violation: restricted Node.js module or system/network API detected."
    return None


def _validate_java_code(code: str) -> Optional[str]:
    for pattern in JAVA_FORBIDDEN_PATTERNS:
        if re.search(pattern, code):
            return "Security policy violation: restricted Java file/network/process API detected."
    return None


def validate_code_safety(language: str, code: str) -> Optional[str]:
    """Static security inspection prior to launching isolated child execution."""
    if not code or not code.strip():
        return "Submitted source code cannot be empty."
    if language == "python":
        return _validate_python_code(code)
    if language == "javascript":
        return _validate_js_code(code)
    if language == "java":
        return _validate_java_code(code)
    return f"Unsupported language '{language}'."


def _sanitized_env() -> Dict[str, str]:
    """Build stripped environment variables containing zero application secrets."""
    env: Dict[str, str] = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "NO_COLOR": "1",
    }
    if os.name == "nt":
        for key in ("SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP"):
            val = os.environ.get(key)
            if val:
                env[key] = val
    else:
        env["PATH"] = "/usr/bin:/bin"
    return env


# ---------------------------------------------------------------------------
# Win32 Job Object enforcement (hard memory, process count, kill-on-close)
# ---------------------------------------------------------------------------

class _IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", _IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


def _create_windows_job_object(memory_mb: int, active_process_limit: int) -> Optional[int]:
    if os.name != "nt":
        return None
    try:
        kernel32 = ctypes.windll.kernel32
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None
        info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        # 0x8=ACTIVE_PROCESS, 0x100=PROCESS_MEMORY, 0x200=JOB_MEMORY, 0x2000=KILL_ON_JOB_CLOSE
        info.BasicLimitInformation.LimitFlags = 0x8 | 0x100 | 0x200 | 0x2000
        info.BasicLimitInformation.ActiveProcessLimit = active_process_limit
        mem_bytes = max(32, memory_mb) * 1024 * 1024
        info.ProcessMemoryLimit = mem_bytes
        info.JobMemoryLimit = mem_bytes
        ok = kernel32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))
        if not ok:
            kernel32.CloseHandle(job)
            return None
        return int(job)
    except Exception:
        return None


def _run_subprocess_isolated_sync(
    cmd: List[str],
    cwd: str,
    stdin_data: str,
    timeout_seconds: float,
    memory_mb: int,
    max_output_bytes: int,
    active_process_limit: int = 1,
) -> Tuple[int, str, str, int, bool, bool]:
    """
    Execute a child process in an isolated directory with OS resource limits and timeout.
    Returns (returncode, stdout, stderr, runtime_ms, timed_out, memory_exceeded).
    """
    start_ns = time.perf_counter_ns()
    job_handle = _create_windows_job_object(memory_mb=memory_mb, active_process_limit=active_process_limit)

    def _posix_preexec():
        import resource  # POSIX only

        mem_bytes = max(64, memory_mb) * 1024 * 1024
        cpu_secs = max(1, int(timeout_seconds) + 1)
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_secs, cpu_secs))
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))

    popen_kwargs: Dict[str, Any] = {
        "stdin": subprocess.PIPE,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "cwd": cwd,
        "env": _sanitized_env(),
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    else:
        popen_kwargs["preexec_fn"] = _posix_preexec

    proc = subprocess.Popen(cmd, **popen_kwargs)
    if job_handle is not None:
        try:
            ctypes.windll.kernel32.AssignProcessToJobObject(job_handle, int(proc._handle))
        except Exception:
            pass

    timed_out = False
    memory_exceeded = False
    try:
        raw_out, raw_err = proc.communicate(
            input=(stdin_data or "").encode("utf-8"),
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            if job_handle is not None:
                ctypes.windll.kernel32.TerminateJobObject(job_handle, 1)
            else:
                proc.kill()
        except Exception:
            proc.kill()
        raw_out, raw_err = proc.communicate()
    finally:
        if job_handle is not None:
            try:
                ctypes.windll.kernel32.CloseHandle(job_handle)
            except Exception:
                pass

    runtime_ms = int((time.perf_counter_ns() - start_ns) / 1_000_000)
    out_truncated = raw_out[:max_output_bytes].decode("utf-8", errors="replace")
    err_truncated = raw_err[:max_output_bytes].decode("utf-8", errors="replace")

    if len(raw_out) > max_output_bytes:
        out_truncated += "\n...[output truncated]"
    if len(raw_err) > max_output_bytes:
        err_truncated += "\n...[stderr truncated]"

    err_lower = err_truncated.lower()
    if (
        "memoryerror" in err_lower
        or "out of memory" in err_lower
        or "outofmemoryerror" in err_lower
        or "fatal error: reached heap limit" in err_lower
        or proc.returncode in (-11, -9, 3, 134, 137)
    ):
        memory_exceeded = True

    return proc.returncode or 0, out_truncated, err_truncated, runtime_ms, timed_out, memory_exceeded


PYTHON_RUNTIME_WRAPPER = """
import builtins as _b
_blocked_open = lambda *a, **kw: (_ for _ in ()).throw(PermissionError("File I/O is disabled in sandbox."))
_b.open = _blocked_open
try:
    import socket as _sock
    def _no_net(*a, **kw):
        raise PermissionError("Network access is disabled in sandbox.")
    _sock.socket = _no_net
    _sock.create_connection = _no_net
except Exception:
    pass
_user_code = _b.compile(open_src := %r, "<student_solution>", "exec")
_ns = {"__name__": "__main__"}
_b.exec(_user_code, _ns)
"""

JS_RUNTIME_WRAPPER = """
'use strict';
const Module = require('module');
const origLoad = Module._load;
const blocked = new Set([
  'fs', 'fs/promises', 'child_process', 'net', 'http', 'https', 'dgram',
  'tls', 'dns', 'vm', 'worker_threads', 'cluster', 'os', 'http2', 'inspector'
]);
Module._load = function(request, parent, isMain) {
  const clean = String(request || '').replace(/^node:/, '');
  if (blocked.has(clean)) {
    throw new Error('SecurityError: Module ' + clean + ' is blocked in sandbox');
  }
  return origLoad.apply(this, arguments);
};
globalThis.fetch = () => { throw new Error('SecurityError: fetch disabled in sandbox'); };
require('./solution.js');
"""


class CodeSandboxService:
    """
    Isolated, resource-bounded execution service for Arena coding problems.
    Supports local isolated OS subprocesses and optional external Piston/Judge0 HTTP sandboxes.
    """

    @staticmethod
    def _find_runtime(language: str) -> Optional[str]:
        if language == "python":
            base_exe = getattr(sys, "_base_executable", None)
            if base_exe and os.path.exists(base_exe):
                return base_exe
            return sys.executable
        if language == "javascript":
            return shutil.which("node")
        if language == "java":
            return shutil.which("java")
        return None

    async def _run_via_external_provider(
        self,
        language: str,
        source_code: str,
        cases: List[Dict[str, Any]],
        custom_stdin: Optional[str],
    ) -> SandboxRunResponse:
        url = (settings.CODE_SANDBOX_API_URL or "").strip()
        if not url:
            raise RuntimeError("CODE_SANDBOX_API_URL must be configured when using external sandbox provider.")

        # Piston v2 /execute compatible protocol
        lang_map = {
            "python": ("python", "3.10.0"),
            "javascript": ("javascript", "18.15.0"),
            "java": ("java", "15.0.2"),
        }
        lang_name, version = lang_map[language]
        results: List[SandboxTestCaseResult] = []
        passed_count = 0
        total_ms = 0

        async with httpx.AsyncClient(timeout=settings.CODE_SANDBOX_TIMEOUT_SECONDS + 5.0) as client:
            for idx, case in enumerate(cases, start=1):
                resp = await client.post(
                    url,
                    json={
                        "language": lang_name,
                        "version": version,
                        "files": [{"content": source_code}],
                        "stdin": case.get("stdin", ""),
                        "run_timeout": int(settings.CODE_SANDBOX_TIMEOUT_SECONDS * 1000),
                        "run_memory_limit": settings.CODE_SANDBOX_MEMORY_MB * 1024 * 1024,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                run = data.get("run") or {}
                out = _normalize_output(run.get("stdout", ""))
                err = (run.get("stderr") or "").strip()
                expected = _normalize_output(case.get("expected_stdout", ""))
                ok = (run.get("code", 1) == 0) and (out == expected)
                if ok:
                    passed_count += 1
                results.append(
                    SandboxTestCaseResult(
                        test_index=idx,
                        is_sample=bool(case.get("is_sample", False)),
                        passed=ok,
                        stdin=case.get("stdin") if case.get("is_sample", False) else None,
                        expected_stdout=case.get("expected_stdout") if case.get("is_sample", False) else None,
                        actual_stdout=out,
                        stderr=err,
                        runtime_ms=0,
                        status="passed" if ok else ("runtime_error" if run.get("code", 0) != 0 else "wrong_answer"),
                    )
                )

        return SandboxRunResponse(
            language=language,
            sandbox_provider=settings.CODE_SANDBOX_MODE,
            isolated_execution=True,
            all_passed=(passed_count == len(cases) and len(cases) > 0),
            passed_count=passed_count,
            total_count=len(cases),
            runtime_ms=total_ms,
            test_results=results,
        )

    async def execute_code(
        self,
        language: str,
        source_code: str,
        test_cases: List[Dict[str, Any]],
        custom_stdin: Optional[str] = None,
    ) -> SandboxRunResponse:
        # 1. Static security policy check before touching any runtime
        violation = validate_code_safety(language=language, code=source_code)
        if violation:
            return SandboxRunResponse(
                language=language,
                sandbox_provider=settings.CODE_SANDBOX_MODE,
                isolated_execution=True,
                all_passed=False,
                passed_count=0,
                total_count=len(test_cases),
                security_violation=violation,
                test_results=[
                    SandboxTestCaseResult(
                        test_index=idx,
                        is_sample=bool(tc.get("is_sample", False)),
                        passed=False,
                        actual_stdout="",
                        stderr=violation,
                        runtime_ms=0,
                        status="security_violation",
                    )
                    for idx, tc in enumerate(test_cases, start=1)
                ],
            )

        # 2. Optional external HTTP sandbox provider
        if settings.CODE_SANDBOX_MODE in ("piston", "judge0") and settings.CODE_SANDBOX_API_URL:
            return await self._run_via_external_provider(language, source_code, test_cases, custom_stdin)

        # 3. Local isolated subprocess sandbox
        runtime_bin = self._find_runtime(language)
        if not runtime_bin:
            msg = f"Runtime for '{language}' is not installed in this environment."
            return SandboxRunResponse(
                language=language,
                sandbox_provider="isolated_subprocess",
                isolated_execution=True,
                all_passed=False,
                passed_count=0,
                total_count=len(test_cases),
                compile_error=msg,
                test_results=[
                    SandboxTestCaseResult(
                        test_index=idx,
                        is_sample=bool(tc.get("is_sample", False)),
                        passed=False,
                        stderr=msg,
                        status="runtime_unavailable",
                    )
                    for idx, tc in enumerate(test_cases, start=1)
                ],
            )

        timeout_s = float(settings.CODE_SANDBOX_TIMEOUT_SECONDS)
        mem_mb = int(settings.CODE_SANDBOX_MEMORY_MB)
        max_bytes = int(settings.CODE_SANDBOX_MAX_OUTPUT_BYTES)

        with tempfile.TemporaryDirectory(prefix="arena_sandbox_") as tmpdir:
            tmp_path = Path(tmpdir)
            active_proc_limit = 1

            if language == "python":
                runner_file = tmp_path / "runner.py"
                runner_file.write_text(PYTHON_RUNTIME_WRAPPER % source_code, encoding="utf-8")
                run_cmd = [runtime_bin, "-I", str(runner_file)]
            elif language == "javascript":
                sol_file = tmp_path / "solution.js"
                sol_file.write_text(source_code, encoding="utf-8")
                runner_file = tmp_path / "runner.js"
                runner_file.write_text(JS_RUNTIME_WRAPPER, encoding="utf-8")
                node_mem = max(32, min(mem_mb, 128))
                run_cmd = [runtime_bin, f"--max-old-space-size={node_mem}", str(runner_file)]
                active_proc_limit = 4  # Node v22 spawns libuv/V8 background threads/workers safely under Job Memory limit
            elif language == "java":
                javac_bin = shutil.which("javac")
                if not javac_bin:
                    msg = "Java compiler (javac) is not available."
                    return SandboxRunResponse(
                        language=language,
                        sandbox_provider="isolated_subprocess",
                        isolated_execution=True,
                        all_passed=False,
                        passed_count=0,
                        total_count=len(test_cases),
                        compile_error=msg,
                    )
                main_java = tmp_path / "Main.java"
                main_java.write_text(source_code, encoding="utf-8")
                rc, _, comp_err, _, timed_out, _ = await asyncio.to_thread(
                    _run_subprocess_isolated_sync,
                    [javac_bin, "Main.java"],
                    tmpdir,
                    "",
                    max(timeout_s, 6.0),
                    max(mem_mb, 256),
                    max_bytes,
                    8,
                )
                if timed_out or rc != 0:
                    return SandboxRunResponse(
                        language=language,
                        sandbox_provider="isolated_subprocess",
                        isolated_execution=True,
                        all_passed=False,
                        passed_count=0,
                        total_count=len(test_cases),
                        compile_error=(comp_err or "Java compilation failed.")[:2000],
                        test_results=[
                            SandboxTestCaseResult(
                                test_index=idx,
                                is_sample=bool(tc.get("is_sample", False)),
                                passed=False,
                                stderr=(comp_err or "Compilation error")[:1000],
                                status="compile_error",
                            )
                            for idx, tc in enumerate(test_cases, start=1)
                        ],
                    )
                run_cmd = [runtime_bin, f"-Xmx{max(48, min(mem_mb, 128))}m", "-cp", tmpdir, "Main"]
                active_proc_limit = 6
                mem_mb = max(mem_mb, 256)  # JVM reserved virtual address space vs heap cap
            else:
                return SandboxRunResponse(
                    language=language,
                    sandbox_provider="isolated_subprocess",
                    isolated_execution=True,
                    all_passed=False,
                    passed_count=0,
                    total_count=len(test_cases),
                    compile_error=f"Unsupported language: {language}",
                )

            results: List[SandboxTestCaseResult] = []
            passed_count = 0
            max_runtime_ms = 0

            for idx, tc in enumerate(test_cases, start=1):
                stdin_val = str(tc.get("stdin", ""))
                expected_val = _normalize_output(str(tc.get("expected_stdout", "")))
                is_sample = bool(tc.get("is_sample", False))

                rc, out, err, rt_ms, timed_out, mem_exceeded = await asyncio.to_thread(
                    _run_subprocess_isolated_sync,
                    run_cmd,
                    tmpdir,
                    stdin_val,
                    timeout_s,
                    mem_mb,
                    max_bytes,
                    active_proc_limit,
                )
                max_runtime_ms = max(max_runtime_ms, rt_ms)
                actual_norm = _normalize_output(out)

                if timed_out:
                    status_str = "time_limit_exceeded"
                    passed = False
                    err_msg = f"Execution exceeded wall-clock limit of {timeout_s:.1f}s."
                elif mem_exceeded:
                    status_str = "memory_limit_exceeded"
                    passed = False
                    err_msg = err or f"Process exceeded sandbox memory limit ({mem_mb} MB)."
                elif "PermissionError" in err or "SecurityError" in err:
                    status_str = "security_violation"
                    passed = False
                    err_msg = err
                elif rc != 0:
                    status_str = "runtime_error"
                    passed = False
                    err_msg = err or f"Process exited with non-zero code {rc}."
                elif actual_norm == expected_val:
                    status_str = "passed"
                    passed = True
                    err_msg = err
                    passed_count += 1
                else:
                    status_str = "wrong_answer"
                    passed = False
                    err_msg = err

                results.append(
                    SandboxTestCaseResult(
                        test_index=idx,
                        is_sample=is_sample,
                        passed=passed,
                        stdin=stdin_val if is_sample else None,
                        expected_stdout=tc.get("expected_stdout") if is_sample else None,
                        actual_stdout=actual_norm if (is_sample or not passed) else expected_val,
                        stderr=err_msg[:1500],
                        runtime_ms=rt_ms,
                        status=status_str,  # type: ignore[arg-type]
                    )
                )

            custom_stdout: Optional[str] = None
            custom_stderr: Optional[str] = None
            if custom_stdin is not None:
                rc, c_out, c_err, c_rt, c_to, c_mem = await asyncio.to_thread(
                    _run_subprocess_isolated_sync,
                    run_cmd,
                    tmpdir,
                    custom_stdin,
                    timeout_s,
                    mem_mb,
                    max_bytes,
                    active_proc_limit,
                )
                max_runtime_ms = max(max_runtime_ms, c_rt)
                custom_stdout = c_out
                if c_to:
                    custom_stderr = f"Time limit exceeded ({timeout_s:.1f}s)."
                elif c_mem:
                    custom_stderr = c_err or "Memory limit exceeded."
                else:
                    custom_stderr = c_err

        return SandboxRunResponse(
            language=language,
            sandbox_provider="isolated_subprocess",
            isolated_execution=True,
            all_passed=(passed_count == len(test_cases) and len(test_cases) > 0),
            passed_count=passed_count,
            total_count=len(test_cases),
            custom_stdout=custom_stdout,
            custom_stderr=custom_stderr,
            runtime_ms=max_runtime_ms,
            test_results=results,
        )


code_sandbox_service = CodeSandboxService()

