import os
import subprocess
from typing import Optional

class GeminiCLLError(RuntimeError):
    pass

def gemini_cli_generate(
    prompt: str,
    *,
    model: Optional[str] = None,
    timeout_s: int = 60,
    sandbox: bool = True,
) -> str:
    """
    Call Gemini CLI as a subprocess and return stdout text.
    - Uses --model to pick model (if provided)
    - Uses --sandbox to reduce risk
    - Uses -p for one-shot prompt (common usage) :contentReference[oaicite:6]{index=6}
    """
    exe = os.getenv("GEMINI_CLI_BIN", "gemini")
    cmd = [exe]

    if sandbox:
        cmd.append("--sandbox")  # recommended; do NOT use --yolo :contentReference[oaicite:7]{index=7}
    if model:
        cmd += ["--model", model]  # :contentReference[oaicite:8]{index=8}

    # one-shot prompt
    cmd += ["-p", prompt]

    try:
        p = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise GeminiCLLError(f"Gemini CLI timeout after {timeout_s}s") from e
    except FileNotFoundError as e:
        raise GeminiCLLError(f"Gemini CLI not found: tried '{exe}'. Install @google/gemini-cli or set GEMINI_CLI_BIN") from e

    if p.returncode != 0:
        raise GeminiCLLError(
            "Gemini CLI failed\n"
            f"cmd: {' '.join(cmd)}\n"
            f"rc: {p.returncode}\n"
            f"stderr: {p.stderr[-2000:]}"
        )

    return (p.stdout or "").strip()
