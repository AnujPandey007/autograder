import shlex
import subprocess
import uuid
from pathlib import Path

IMAGE = "autograder-c:1"
EXECUTION_NOTE = (
    "Basic Docker runner with time, memory, CPU and process limits. "
    "Network disabled. No output-size limit or compiler-flag validation. "
    "Sanitizers use the instructor memory limit; leak detection is disabled."
)


# Shared function for compilation and test execution.
def run(command, folder=None, input_text="", seconds=1, memory_mb=64, writable=False):
    name = "grader-" + uuid.uuid4().hex

    # Start Docker with resource limits.
    options = [
        "docker", "run", "--rm", "-i", "--name", name,
        "--network=none", "--cpus=1", "--pids-limit=64",
        "--memory", str(memory_mb) + "m",
        "--memory-swap", str(memory_mb) + "m"
    ]

    # Share the submission folder as /work inside Docker.
    if folder is not None:
        mount = f"type=bind,source={Path(folder).resolve()},target=/work"
        if not writable:
            mount += ",readonly"
        options += ["--mount", mount]

    # Stop the command when its time limit is reached.
    options += [IMAGE, "timeout", "-k", "1s", str(seconds) + "s"]
    options += command

    try:
        completed = subprocess.run(
            options, input=input_text, capture_output=True,
            text=True, errors="replace", timeout=seconds + 15
        )
    except subprocess.TimeoutExpired:
        subprocess.run(
            ["docker", "rm", "-f", name],
            capture_output=True, timeout=10
        )
        return {
            "status": "unavailable", "returncode": None,
            "stdout": "", "stderr": "Docker did not finish in time."
        }
    except OSError as error:
        return {
            "status": "unavailable", "returncode": None,
            "stdout": "", "stderr": str(error)
        }

    status = "runtime_error"
    if completed.returncode == 0:
        status = "ok"
    elif completed.returncode == 124:
        status = "timeout"
    elif completed.returncode in (125, 126, 127):
        status = "unavailable"

    return {
        "status": status,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr
    }


# Used by grader.py to include the GCC version in the report.
def compiler_info():
    answer = run(["gcc", "--version"], seconds=10, memory_mb=128)
    if answer["status"] != "ok":
        raise RuntimeError(answer["stderr"] or "Could not start GCC.")

    return {
        "command": "gcc in " + IMAGE,
        "version": answer["stdout"].splitlines()[0]
    }


# Used by grader.py, syntax.py and memory_safety.py.
def compile(folder, flags="-std=c11", name="program"):
    executable = "/work/" + name
    command = ["gcc"] + shlex.split(flags)
    command += ["/work/submission.c", "-o", executable]

    answer = run(command, folder, seconds=20, memory_mb=768, writable=True)
    answer["executable"] = executable
    return answer


# Used by correctness.py to run a test.
def execute(compiled, folder, test, rules, sanitizer=False):
    return run(
        command=[compiled["executable"]],
        folder=folder,
        input_text=test["input"],
        seconds=rules["time_limit_s"],
        memory_mb=rules["memory_limit_mb"]
    )