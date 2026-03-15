"""Validate uploaded agent code zip files before deployment."""

import ast
import io
import json
import zipfile
from dataclasses import dataclass, field


BANNED_MODULES = {"subprocess", "ctypes", "importlib"}
BANNED_OS_CALLS = {"os.system", "os.execl", "os.execle", "os.execlp", "os.execlpe",
                   "os.execv", "os.execve", "os.execvp", "os.execvpe", "os.popen"}
BANNED_SOCKET_CALLS = {"socket.bind", "socket.listen"}
BANNED_PACKAGES = {"boto3", "paramiko", "fabric", "ansible"}
VALID_RUNTIMES = {"python3.12", "python3.11", "nodejs20.x"}
MAX_ZIP_SIZE = 50 * 1024 * 1024


@dataclass
class ValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    agent_json: dict | None = None

    def fail(self, msg: str):
        self.valid = False
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)


def validate(zip_bytes: bytes) -> ValidationResult:
    result = ValidationResult()

    if len(zip_bytes) > MAX_ZIP_SIZE:
        result.fail(f"Zip file too large: {len(zip_bytes)} bytes (max {MAX_ZIP_SIZE})")
        return result

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        result.fail("Invalid zip file")
        return result

    names = zf.namelist()

    if "agent.json" not in names:
        result.fail("Missing agent.json in zip root")
        return result

    try:
        agent_json = json.loads(zf.read("agent.json"))
        result.agent_json = agent_json
    except (json.JSONDecodeError, Exception) as e:
        result.fail(f"Invalid agent.json: {e}")
        return result

    for field_name in ("name", "description", "skills", "runtime", "price_per_task"):
        if field_name not in agent_json:
            result.fail(f"agent.json missing required field: {field_name}")

    if "skills" in agent_json and not isinstance(agent_json["skills"], list):
        result.fail("agent.json 'skills' must be an array")
    elif "skills" in agent_json and len(agent_json["skills"]) == 0:
        result.fail("agent.json 'skills' must not be empty")

    runtime = agent_json.get("runtime", "python3.12")
    if runtime not in VALID_RUNTIMES:
        result.fail(f"Invalid runtime '{runtime}'. Must be one of: {', '.join(VALID_RUNTIMES)}")

    memory_mb = agent_json.get("memory_mb", 256)
    if not isinstance(memory_mb, int) or memory_mb < 128 or memory_mb > 1024:
        result.fail(f"memory_mb must be between 128 and 1024, got {memory_mb}")

    timeout_sec = agent_json.get("timeout_sec", 60)
    if not isinstance(timeout_sec, int) or timeout_sec < 5 or timeout_sec > 300:
        result.fail(f"timeout_sec must be between 5 and 300, got {timeout_sec}")

    entrypoint = agent_json.get("entrypoint", "handler.py")
    if entrypoint not in names:
        result.fail(f"Missing entrypoint file: {entrypoint}")
    else:
        _validate_handler(zf.read(entrypoint).decode("utf-8"), entrypoint, result)

    if "requirements.txt" in names:
        _validate_requirements(zf.read("requirements.txt").decode("utf-8"), result)
    else:
        result.warn("No requirements.txt found - agent has no dependencies")

    return result


def _validate_handler(source: str, filename: str, result: ValidationResult):
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as e:
        result.fail(f"Syntax error in {filename}: {e}")
        return

    handle_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "handle":
            handle_found = True
            positional = len(node.args.args)
            if positional != 1:
                result.fail(f"handle() must accept exactly 1 parameter, found {positional}")
            break

    if not handle_found:
        result.fail(f"{filename} must define a handle(task) function")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                if mod in BANNED_MODULES:
                    result.fail(f"Banned import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod = node.module.split(".")[0]
                if mod in BANNED_MODULES:
                    result.fail(f"Banned import: from {node.module}")
                full = node.module
                for alias in node.names:
                    call = f"{full}.{alias.name}" if not full.endswith(alias.name) else full
                    if call in BANNED_OS_CALLS or call in BANNED_SOCKET_CALLS:
                        result.fail(f"Banned call: {call}")
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                call = f"{node.value.id}.{node.attr}"
                if call in BANNED_OS_CALLS or call in BANNED_SOCKET_CALLS:
                    result.fail(f"Banned call: {call}")


def _validate_requirements(content: str, result: ValidationResult):
    for line in content.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        pkg = line.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0].split("!=")[0].split("[")[0].strip().lower()
        if pkg in BANNED_PACKAGES:
            result.fail(f"Banned package in requirements.txt: {pkg}")
