"""Schema/lint tests for SKILL.md -- no LLM calls, purely structural."""

import re


class TestFrontmatter:
    """Validate the YAML frontmatter block."""

    def test_has_name(self, skill_metadata):
        assert "name" in skill_metadata
        assert isinstance(skill_metadata["name"], str)
        assert len(skill_metadata["name"]) > 0

    def test_name_is_kebab_case(self, skill_metadata):
        name = skill_metadata["name"]
        assert re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", name), (
            f"Skill name '{name}' is not kebab-case"
        )

    def test_has_description(self, skill_metadata):
        assert "description" in skill_metadata
        assert isinstance(skill_metadata["description"], str)
        assert len(skill_metadata["description"]) >= 10

    def test_has_argument_hint(self, skill_metadata):
        assert "argument-hint" in skill_metadata

    def test_context_is_valid(self, skill_metadata):
        valid_contexts = {"fork", "full", "none"}
        if "context" in skill_metadata:
            assert skill_metadata["context"] in valid_contexts, (
                f"context must be one of {valid_contexts}"
            )

    def test_agent_is_valid(self, skill_metadata):
        valid_agents = {"general-purpose", "code", "research"}
        if "agent" in skill_metadata:
            assert skill_metadata["agent"] in valid_agents, (
                f"agent must be one of {valid_agents}"
            )

    def test_allowed_tools_present(self, skill_metadata):
        assert "allowed-tools" in skill_metadata

    def test_allowed_tools_is_string(self, skill_metadata):
        assert isinstance(skill_metadata["allowed-tools"], str)


class TestBody:
    """Validate the markdown body."""

    def test_arguments_placeholder_present(self, skill_body):
        assert "$ARGUMENTS" in skill_body

    def test_arguments_placeholder_count(self, skill_body):
        count = skill_body.count("$ARGUMENTS")
        assert count >= 1

    def test_has_output_format_section(self, skill_body):
        assert "## Output format" in skill_body

    def test_verdict_keywords_documented(self, skill_body):
        for keyword in [
            "EXPLAINED BY RECENT CHANGES",
            "NOT IN RECENT CHANGES",
            "PARTIAL",
        ]:
            assert keyword in skill_body, (
                f"Output format must document verdict keyword: {keyword}"
            )

    def test_has_recommendation_section(self, skill_body):
        assert "**Recommendation**" in skill_body


class TestToolConsistency:
    """Verify allowed-tools is consistent with commands in the body."""

    def test_body_only_uses_git_commands(self, skill_metadata, skill_body):
        allowed = skill_metadata.get("allowed-tools", "")
        assert "git" in allowed

        code_blocks = re.findall(r"`(git [^`]+)`", skill_body)
        assert len(code_blocks) >= 3, (
            f"Body should contain at least 3 git commands (found {len(code_blocks)})"
        )

    def test_no_non_git_bash_commands(self, skill_body):
        """Body should not instruct running non-git shell commands."""
        inline_code = re.findall(r"`([a-zA-Z]\S*(?:\s[^`]*)?)`", skill_body)
        non_git_commands = []
        safe_prefixes = (
            "git", "e.g.", "go.", "package.", "requirements.",
            "Cargo.", "HEAD", "abc", "EXPLAINED", "NOT", "PARTIAL",
            "Revert", "Root",
        )
        for code in inline_code:
            if any(code.startswith(p) for p in safe_prefixes):
                continue
            if code.startswith("$"):
                continue
            if " " in code and code[0].islower():
                non_git_commands.append(code)
        assert non_git_commands == [], (
            f"Body references non-git commands but allowed-tools "
            f"is Bash(git *): {non_git_commands}"
        )


class TestOverallStructure:
    """High-level structural checks."""

    def test_skill_md_not_empty(self, skill):
        assert len(skill.content) > 100

    def test_has_phases(self, skill_body):
        assert "### Phase 1" in skill_body
        assert "### Phase 2" in skill_body
        assert "### Phase 3" in skill_body

    def test_steps_are_numbered(self, skill_body):
        for i in range(1, 8):
            assert f"{i}." in skill_body, f"Missing step {i}"
