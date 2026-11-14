import os
import json

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core", "breakthroughs_manager.py")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Normalize CRLF
content = content.replace("\r\n", "\n")

old_paths = """STORE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "breakthroughs_store.json")
BOOKMARKS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "breakthroughs_bookmarks.json")"""

new_paths = """BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_data_dir() -> str:
    \"\"\"Returns active data directory, supporting test isolation via BIOWRITER_DATA_DIR.\"\"\"
    return os.environ.get("BIOWRITER_DATA_DIR") or (
        os.path.join("/tmp", "data") if os.environ.get("VERCEL") else os.path.join(BASE_DIR, "data")
    )


def get_store_file() -> str:
    \"\"\"Returns active breakthroughs store file path.\"\"\"
    return os.path.join(get_data_dir(), "breakthroughs_store.json")


def get_bookmarks_file() -> str:
    \"\"\"Returns active breakthroughs bookmarks file path.\"\"\"
    return os.path.join(get_data_dir(), "breakthroughs_bookmarks.json")


# Backward compatibility references
STORE_FILE = get_store_file()
BOOKMARKS_FILE = get_bookmarks_file()"""

assert old_paths in content, "old_paths not found"
content = content.replace(old_paths, new_paths, 1)

old_funcs = """def load_stored_breakthroughs() -> List[Dict[str, Any]]:
    \"\"\"Loads stored live discoveries from JSON file.\"\"\"
    if os.path.exists(STORE_FILE):
        try:
            with open(STORE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return list(DEFAULT_RECENT_BREAKTHROUGHS)


def save_stored_breakthroughs(breakthroughs: List[Dict[str, Any]]) -> None:
    \"\"\"Saves live discoveries to JSON file.\"\"\"
    os.makedirs(os.path.dirname(STORE_FILE), exist_ok=True)
    try:
        with open(STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(breakthroughs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving breakthroughs: {e}")


def load_bookmarks() -> List[str]:
    \"\"\"Loads bookmarked breakthrough IDs.\"\"\"
    if os.path.exists(BOOKMARKS_FILE):
        try:
            with open(BOOKMARKS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []


def save_bookmarks(bookmarks: List[str]) -> None:
    \"\"\"Saves bookmarked breakthrough IDs.\"\"\"
    os.makedirs(os.path.dirname(BOOKMARKS_FILE), exist_ok=True)
    try:
        with open(BOOKMARKS_FILE, "w", encoding="utf-8") as f:
            json.dump(bookmarks, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving bookmarks: {e}")"""

new_funcs = """def load_stored_breakthroughs() -> List[Dict[str, Any]]:
    \"\"\"Loads stored live discoveries from JSON file.\"\"\"
    store_file = get_store_file()
    if os.path.exists(store_file):
        try:
            with open(store_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return list(DEFAULT_RECENT_BREAKTHROUGHS)


def save_stored_breakthroughs(breakthroughs: List[Dict[str, Any]]) -> None:
    \"\"\"Saves live discoveries to JSON file.\"\"\"
    store_file = get_store_file()
    os.makedirs(os.path.dirname(store_file), exist_ok=True)
    try:
        with open(store_file, "w", encoding="utf-8") as f:
            json.dump(breakthroughs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving breakthroughs: {e}")


def load_bookmarks() -> List[str]:
    \"\"\"Loads bookmarked breakthrough IDs.\"\"\"
    bookmarks_file = get_bookmarks_file()
    if os.path.exists(bookmarks_file):
        try:
            with open(bookmarks_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []


def save_bookmarks(bookmarks: List[str]) -> None:
    \"\"\"Saves bookmarked breakthrough IDs.\"\"\"
    bookmarks_file = get_bookmarks_file()
    os.makedirs(os.path.dirname(bookmarks_file), exist_ok=True)
    try:
        with open(bookmarks_file, "w", encoding="utf-8") as f:
            json.dump(bookmarks, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving bookmarks: {e}")"""

assert old_funcs in content, "old_funcs not found"
content = content.replace(old_funcs, new_funcs, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Successfully patched upload/core/breakthroughs_manager.py")
