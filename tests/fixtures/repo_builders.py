"""Functions that build test git repos for integration scenarios.

Each function takes a repo_dir (Path to an already-initialized git repo)
and populates it with commits and optionally uncommitted changes.
Returns a metadata dict so tests can assert against it.
"""

import subprocess
import textwrap
from pathlib import Path


def _run(cmd: str, cwd: Path) -> str:
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def _commit(cwd: Path, msg: str) -> str:
    _run("git add -A", cwd)
    _run(f'git commit -m "{msg}"', cwd)
    return _run("git rev-parse --short HEAD", cwd)


# ─── Scenario 1: Boolean flag flip breaks tests ───────────────────────

def build_boolean_flag_flip(repo_dir: Path) -> dict:
    """DEBUG flag flipped from True to False, breaking tests that expect
    debug output."""
    app_py = repo_dir / "app.py"
    app_py.write_text(textwrap.dedent("""\
        DEBUG = True

        def get_log_level():
            return "DEBUG" if DEBUG else "INFO"

        def process(data):
            if DEBUG:
                print(f"Processing: {data}")
            return data.upper()
    """))

    test_py = repo_dir / "test_app.py"
    test_py.write_text(textwrap.dedent("""\
        from app import process, get_log_level

        def test_log_level():
            assert get_log_level() == "DEBUG"

        def test_process_prints_debug(capsys):
            process("hello")
            captured = capsys.readouterr()
            assert "Processing:" in captured.out
    """))

    _commit(repo_dir, "Initial: app with DEBUG=True")

    app_py.write_text(textwrap.dedent("""\
        DEBUG = False

        def get_log_level():
            return "DEBUG" if DEBUG else "INFO"

        def process(data):
            if DEBUG:
                print(f"Processing: {data}")
            return data.upper()
    """))

    hash2 = _commit(repo_dir, "Disable debug mode for production")

    return {
        "breaking_commit": hash2,
        "breaking_file": "app.py",
        "error_message": (
            "AssertionError: expected debug output in log, got empty string. "
            "test_log_level fails: assert get_log_level() == 'DEBUG' returns 'INFO'. "
            "test_process_prints_debug fails: no output captured."
        ),
        "expected_verdict": "EXPLAINED BY RECENT CHANGES",
    }


# ─── Scenario 2: Function signature change ────────────────────────────

def build_signature_change(repo_dir: Path) -> dict:
    """A required parameter was added to calculate() but callers not updated."""
    utils_py = repo_dir / "utils.py"
    utils_py.write_text(textwrap.dedent("""\
        def calculate(price, quantity):
            return price * quantity

        def format_currency(amount):
            return f"${amount:.2f}"
    """))

    main_py = repo_dir / "main.py"
    main_py.write_text(textwrap.dedent("""\
        from utils import calculate, format_currency

        def checkout(cart):
            total = sum(calculate(item["price"], item["qty"]) for item in cart)
            return format_currency(total)
    """))

    _commit(repo_dir, "Initial: basic pricing utils")

    readme = repo_dir / "README.md"
    readme.write_text("# My App\nA pricing application.\n")
    _commit(repo_dir, "Add README")

    utils_py.write_text(textwrap.dedent("""\
        def calculate(price, quantity, tax_rate):
            subtotal = price * quantity
            return subtotal * (1 + tax_rate)

        def format_currency(amount):
            return f"${amount:.2f}"
    """))

    hash3 = _commit(repo_dir, "Add tax calculation to pricing")

    return {
        "breaking_commit": hash3,
        "breaking_file": "utils.py",
        "error_message": (
            "TypeError: calculate() missing 1 required positional argument: 'tax_rate'. "
            "Traceback points to main.py line 4, calling calculate(item['price'], item['qty'])."
        ),
        "expected_verdict": "EXPLAINED BY RECENT CHANGES",
    }


# ─── Scenario 3: Bug NOT in recent changes ────────────────────────────

def build_unrelated_changes(repo_dir: Path) -> dict:
    """Recent changes are docs/CI only. Error is a database timeout."""
    db_py = repo_dir / "db.py"
    db_py.write_text(textwrap.dedent("""\
        import os

        DB_HOST = os.environ.get("DB_HOST", "localhost")
        DB_PORT = int(os.environ.get("DB_PORT", "5432"))
        DB_TIMEOUT = 30

        def connect():
            return {"host": DB_HOST, "port": DB_PORT, "timeout": DB_TIMEOUT}
    """))

    _commit(repo_dir, "Initial: database connection module")

    readme = repo_dir / "README.md"
    readme.write_text("# App\n\n## Setup\nRun `pip install -r requirements.txt`\n")
    _commit(repo_dir, "Update README with setup instructions")

    ci_dir = repo_dir / ".github" / "workflows"
    ci_dir.mkdir(parents=True)
    ci_yml = ci_dir / "ci.yml"
    ci_yml.write_text(textwrap.dedent("""\
        name: CI
        on: [push]
        jobs:
          test:
            runs-on: ubuntu-latest
            steps:
              - uses: actions/checkout@v4
              - run: pytest
    """))
    _commit(repo_dir, "Add CI workflow")

    return {
        "breaking_commit": None,
        "breaking_file": None,
        "error_message": (
            "ConnectionError: database connection timed out after 30s. "
            "Traceback in db.py connect(). The DB server may be down or unreachable."
        ),
        "expected_verdict": "NOT IN RECENT CHANGES",
    }


# ─── Scenario 4: Dependency version bump ──────────────────────────────

def build_dependency_bump(repo_dir: Path) -> dict:
    """requirements.txt bump from requests 2.28.0 to 2.31.0 breaks an import."""
    api_client_py = repo_dir / "api_client.py"
    api_client_py.write_text(textwrap.dedent("""\
        from requests.auth import HTTPBasicAuth

        def make_request(url, user, password):
            auth = HTTPBasicAuth(user, password)
            return {"url": url, "auth": auth}
    """))

    req_txt = repo_dir / "requirements.txt"
    req_txt.write_text("requests==2.28.0\nflask==2.3.0\n")

    _commit(repo_dir, "Initial: API client with requests 2.28.0")

    req_txt.write_text("requests==2.31.0\nflask==2.3.0\n")
    hash2 = _commit(repo_dir, "Bump requests to 2.31.0")

    return {
        "breaking_commit": hash2,
        "breaking_file": "requirements.txt",
        "error_message": (
            "ImportError: cannot import name 'HTTPBasicAuth' from 'requests.auth'. "
            "This broke after the latest deployment. "
            "Traceback in api_client.py line 1."
        ),
        "expected_verdict": "EXPLAINED BY RECENT CHANGES",
    }


# ─── Scenario 5: Uncommitted change ───────────────────────────────────

def build_uncommitted_change(repo_dir: Path) -> dict:
    """Breaking change is uncommitted: config key renamed from 'username'
    to 'user'."""
    config_py = repo_dir / "config.py"
    config_py.write_text(textwrap.dedent("""\
        DEFAULTS = {
            "username": "admin",
            "password": "secret",
            "host": "localhost",
            "port": 8080,
        }

        def get_config(key):
            return DEFAULTS[key]
    """))

    server_py = repo_dir / "server.py"
    server_py.write_text(textwrap.dedent("""\
        from config import get_config

        def start():
            user = get_config("username")
            passwd = get_config("password")
            host = get_config("host")
            return f"{user}:{passwd}@{host}"
    """))

    _commit(repo_dir, "Initial: config and server modules")

    changelog = repo_dir / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n## v1.0.0\n- Initial release\n")
    _commit(repo_dir, "Add changelog")

    # Uncommitted change: rename "username" to "user"
    config_py.write_text(textwrap.dedent("""\
        DEFAULTS = {
            "user": "admin",
            "password": "secret",
            "host": "localhost",
            "port": 8080,
        }

        def get_config(key):
            return DEFAULTS[key]
    """))

    return {
        "breaking_commit": None,
        "breaking_file": "config.py",
        "error_message": (
            "KeyError: 'username' in config.py get_config(). "
            "server.py calls get_config('username') but the key no longer exists."
        ),
        "expected_verdict": "EXPLAINED BY RECENT CHANGES",
        "is_uncommitted": True,
    }
