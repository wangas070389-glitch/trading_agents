import os
import json
import tempfile

def atomic_save_json(filepath: str, data: dict, indent: int = 2) -> None:
    """
    Atomically save a dictionary as JSON to filepath.
    Writes to a temporary file in the same directory first, then replaces target file.
    """
    dir_name = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(dir_name, exist_ok=True)
    
    # Create temp file in the target directory to ensure same filesystem for atomic replace
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        os.replace(tmp_path, filepath)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise

def safe_load_json(filepath: str, default=None):
    """
    Safely load JSON data from filepath.
    Returns default if file does not exist or if loading fails.
    """
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load JSON from {filepath}: {e}")
        return default
