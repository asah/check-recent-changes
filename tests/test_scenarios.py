"""Integration tests that invoke the skill via `claude -p`.

Marked with @pytest.mark.integration -- these are SLOW (~30-90s each).

Run explicitly:     pytest -m integration
Skip in fast CI:    pytest -m "not integration"
"""

import pytest

from tests.conftest import run_skill
from tests.fixtures.repo_builders import (
    build_boolean_flag_flip,
    build_dependency_bump,
    build_signature_change,
    build_uncommitted_change,
    build_unrelated_changes,
)

pytestmark = pytest.mark.integration


def assert_verdict(output: str, expected_keyword: str):
    """Fuzzy-match the verdict keyword in the LLM output (case-insensitive)."""
    normalized = output.upper()
    assert expected_keyword.upper() in normalized, (
        f"Expected verdict '{expected_keyword}' not found in output.\n"
        f"Output (first 500 chars): {output[:500]}"
    )


def assert_mentions_file(output: str, filename: str):
    assert filename in output, (
        f"Expected mention of file '{filename}' in output.\n"
        f"Output (first 500 chars): {output[:500]}"
    )


def assert_mentions_commit(output: str, short_hash: str):
    assert short_hash in output, (
        f"Expected commit hash '{short_hash}' in output.\n"
        f"Output (first 500 chars): {output[:500]}"
    )


def assert_has_recommendation(output: str):
    assert "recommendation" in output.lower(), (
        f"Expected 'Recommendation' section in output.\n"
        f"Output (first 500 chars): {output[:500]}"
    )


class TestBooleanFlagFlip:
    """Scenario 1: DEBUG flag flipped from True to False."""

    def test_detects_flag_flip(self, make_test_repo):
        repo = make_test_repo("bool_flag")
        meta = build_boolean_flag_flip(repo)
        output = run_skill(repo, meta["error_message"])

        assert_verdict(output, meta["expected_verdict"])
        assert_mentions_file(output, meta["breaking_file"])
        assert_mentions_commit(output, meta["breaking_commit"])
        assert_has_recommendation(output)


class TestSignatureChange:
    """Scenario 2: Function gained a required parameter."""

    def test_detects_signature_change(self, make_test_repo):
        repo = make_test_repo("sig_change")
        meta = build_signature_change(repo)
        output = run_skill(repo, meta["error_message"])

        assert_verdict(output, meta["expected_verdict"])
        assert_mentions_file(output, meta["breaking_file"])
        assert_mentions_commit(output, meta["breaking_commit"])
        assert_has_recommendation(output)


class TestUnrelatedChanges:
    """Scenario 3: Error NOT explained by recent changes."""

    def test_correctly_reports_not_in_recent(self, make_test_repo):
        repo = make_test_repo("unrelated")
        meta = build_unrelated_changes(repo)
        output = run_skill(repo, meta["error_message"])

        assert_verdict(output, meta["expected_verdict"])
        assert_has_recommendation(output)


class TestDependencyBump:
    """Scenario 4: Dependency version bump caused an import error."""

    def test_detects_dep_bump(self, make_test_repo):
        repo = make_test_repo("dep_bump")
        meta = build_dependency_bump(repo)
        output = run_skill(repo, meta["error_message"])

        assert_verdict(output, meta["expected_verdict"])
        assert_mentions_file(output, meta["breaking_file"])
        assert_mentions_commit(output, meta["breaking_commit"])
        assert_has_recommendation(output)


class TestUncommittedChange:
    """Scenario 5: Breaking change is uncommitted."""

    def test_detects_uncommitted_rename(self, make_test_repo):
        repo = make_test_repo("uncommitted")
        meta = build_uncommitted_change(repo)
        output = run_skill(repo, meta["error_message"])

        assert_verdict(output, meta["expected_verdict"])
        assert_mentions_file(output, meta["breaking_file"])
        assert_has_recommendation(output)
        # Should indicate the change is uncommitted
        normalized = output.lower()
        assert any(w in normalized for w in [
            "uncommit", "working", "unstaged", "not committed",
            "git diff head",
        ]), "Should indicate the change is uncommitted"
