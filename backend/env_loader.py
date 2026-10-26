import os
from pathlib import Path

def load_environment(override=False):
    """
    Loads environment variables from the project .env file.
    Tries python-dotenv first; falls back to a clean native parser
    if python-dotenv is not installed.
    """
    base_dir = Path(__file__).resolve().parent
    candidates = [
        base_dir / ".env",
        base_dir.parent / ".env",
        Path.cwd() / ".env"
    ]

    env_path = next((p for p in candidates if p.is_file()), None)
    if not env_path:
        return

    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_path, override=override)
        return
    except ImportError:
        pass

    # Native fallback parser
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    # Strip wrapping quotes if present
                    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    if key:
                        if override or (key not in os.environ):
                            os.environ[key] = value
    except Exception:
        pass

# Automatically load environment variables upon module import
load_environment()
