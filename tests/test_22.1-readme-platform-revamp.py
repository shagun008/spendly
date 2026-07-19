"""Tests for the README Platform Revamp (22.1-readme-platform-revamp)

Spec: .claude/specs/22.1-readme-platform-revamp.md

Scope:
- No new routes, no database changes, no templates — this feature is a
  full rewrite of README.md at the repository root.
- These tests validate the CONTENT and STRUCTURE of README.md against the
  spec's "Definition of done" checklist. They do not exercise Flask at all
  (no app/client fixtures) because there is no route or code to hit.
- Each test reads README.md fresh from disk so tests remain fully
  independent with no shared mutable state.
"""

import os
import re

import pytest

# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
README_PATH = os.path.join(REPO_ROOT, "README.md")


def read_readme():
    """Read README.md fresh from disk. Raises AssertionError with a clear
    message if the file is missing, rather than letting a bare IOError
    surface (keeps failures readable)."""
    assert os.path.isfile(README_PATH), f"Expected README.md at {README_PATH}"
    with open(README_PATH, encoding="utf-8") as f:
        return f.read()


def section_body(text, heading, next_heading_prefix="## "):
    """Return the substring of `text` starting at `heading` up to (but not
    including) the next heading line that starts with `next_heading_prefix`.
    Used to scope assertions (e.g. jargon checks) to a single section."""
    start = text.find(heading)
    assert start != -1, f"Expected heading '{heading}' to be present in README.md"
    search_from = start + len(heading)
    next_idx = text.find(f"\n{next_heading_prefix}", search_from)
    if next_idx == -1:
        return text[start:]
    return text[start:next_idx]


# ------------------------------------------------------------------ #
# README opens with the "platform, not a single app" framing          #
# ------------------------------------------------------------------ #


class TestReadmeOpensWithPlatformFraming:
    """DoD: 'README.md opens with a plain-English intro leading with the
    "platform, not a single app" framing.'"""

    def test_readme_starts_with_platform_heading(self):
        """The document should open with the platform-framed H1 heading."""
        text = read_readme()
        stripped = text.lstrip()
        assert stripped.startswith(
            "# Oxos Platform"
        ), "Expected README.md to open with '# Oxos Platform' heading"
        assert (
            "Spendly inside" in stripped.splitlines()[0]
        ), "Expected opening heading to reference 'Spendly inside'"

    def test_readme_has_platform_not_app_blockquote(self):
        """A blockquote framing the project as a platform, not just an app,
        should appear near the top of the document."""
        text = read_readme()
        assert (
            "It's now a platform, not just an app." in text
        ), "Expected the 'platform, not just an app' blockquote framing"

        # It should appear early in the document (within the first ~30 lines),
        # i.e. as part of the opening framing, not buried deep in the file.
        lines = text.splitlines()
        early_text = "\n".join(lines[:30])
        assert (
            "platform, not just an app" in early_text
        ), "Expected the platform framing to appear near the top of README.md"


# ------------------------------------------------------------------ #
# "Three ways to read this" menu                                      #
# ------------------------------------------------------------------ #


class TestThreeWaysToReadThisMenu:
    """DoD: 'README.md includes a "three ways to read this" menu linking
    to executive, business, and engineer sections.'"""

    def test_readme_has_three_ways_to_read_this_menu(self):
        """A menu describing the three reading tracks should exist. The
        spec's DoD says 'a "three ways to read this" menu' — the README
        phrases it as 'Three ways to read the rest of this document', which
        satisfies the intent (a routing menu with executive/business/engineer
        links). We assert the intent, not the exact wording."""
        text = read_readme().lower()
        assert (
            "three ways to read" in text
        ), "Expected a 'three ways to read' routing menu in README.md"

    def test_menu_links_precede_the_sections_they_point_to(self):
        """The menu should appear before the executive/business/engineer
        section headings it links to, so readers can self-route from the
        top of the document."""
        text = read_readme()
        lower_text = text.lower()

        menu_idx = lower_text.find("three ways to read")
        exec_idx = lower_text.find("for executives")
        business_idx = lower_text.find("for the business")

        assert menu_idx != -1, "Menu heading not found"
        assert exec_idx != -1, "Executive section not found"
        assert business_idx != -1, "Business section not found"
        assert (
            menu_idx < exec_idx
        ), "Expected 'three ways to read this' menu to precede the executive section"
        assert (
            menu_idx < business_idx
        ), "Expected 'three ways to read this' menu to precede the business section"


# ------------------------------------------------------------------ #
# Executive 30-second section                                         #
# ------------------------------------------------------------------ #


class TestExecutiveSection:
    """DoD: 'An executive 30-second section exists and is free of
    jargon.'"""

    def test_readme_has_executive_30_second_heading(self):
        """The executive section heading should exist verbatim."""
        text = read_readme()
        assert (
            "## \U0001f3e2 For executives: the 30-second version" in text
        ), "Expected the executive 30-second version heading"

    def test_executive_section_is_jargon_free(self):
        """The executive section's body text should avoid engineering
        jargon (SQLite, Flask, pytest, ORM, endpoint), deferring technical
        detail to the engineer section per the spec's UI/UX notes."""
        text = read_readme()
        body = section_body(text, "## \U0001f3e2 For executives: the 30-second version")
        body_lower = body.lower()

        jargon_terms = ["sqlite", "flask", "pytest", "orm", "endpoint"]
        found = [term for term in jargon_terms if term in body_lower]
        assert (
            not found
        ), f"Expected executive section to be jargon-free, found: {found}"


# ------------------------------------------------------------------ #
# Business / product reader section                                   #
# ------------------------------------------------------------------ #


class TestBusinessReaderSection:
    """DoD: 'A business/product reader section exists with a clear "what
    can I do today" view.'"""

    def test_readme_has_business_reader_heading(self):
        """The business/product reader section heading should exist
        verbatim."""
        text = read_readme()
        assert (
            "## \U0001f4bc For the business / product reader" in text
        ), "Expected the business/product reader section heading"

    def test_business_section_has_what_can_i_use_today_prompt(self):
        """The business section should include a 'What can I use today?'
        capability prompt, scoped near the business heading."""
        text = read_readme()
        body = section_body(text, "## \U0001f4bc For the business / product reader")
        assert (
            "What can I use today?" in body
        ), "Expected 'What can I use today?' prompt in the business section"


# ------------------------------------------------------------------ #
# Engineer section preserved (tech stack, pipeline, command table)    #
# ------------------------------------------------------------------ #


class TestEngineerSectionPreserved:
    """DoD: 'The engineer section preserves the tech-stack table, pipeline
    ASCII diagram, and command table from the previous README.'"""

    def test_engineer_section_has_tech_stack_heading(self):
        """The tech stack heading/table should still exist."""
        text = read_readme()
        assert (
            "### Tech Stack" in text
        ), "Expected '### Tech Stack' heading to be preserved"

    def test_engineer_section_references_capture_thoughts_pipeline(self):
        """The pipeline diagram (or its description) should still reference
        the /capture-thoughts step, evidence the ASCII pipeline survived
        the rewrite."""
        text = read_readme()
        assert (
            "/capture-thoughts" in text
        ), "Expected '/capture-thoughts' pipeline reference to be preserved"

    def test_engineer_section_has_command_table_with_pipeline_commands(self):
        """The command table referencing the pipeline commands should be
        preserved intact."""
        text = read_readme()
        required_commands = ["/implement-feature", "/ship-feature", "/improvement-loop"]
        missing = [cmd for cmd in required_commands if cmd not in text]
        assert (
            not missing
        ), f"Expected pipeline commands to be preserved in README.md, missing: {missing}"


# ------------------------------------------------------------------ #
# Feature counts must be internally consistent                        #
# ------------------------------------------------------------------ #


class TestFeatureCountsAreConsistent:
    """DoD: 'Inconsistent feature counts are removed (no contradictory
    hard numbers).' The old README contradicted itself with "14 features ·
    20 spec releases" in the headline vs. "15 features shipped across 21
    spec releases" in the body."""

    @pytest.mark.parametrize(
        "forbidden_phrase",
        [
            "14 features",
            "15 features shipped",
            "20 spec releases",
            "21 spec releases",
        ],
    )
    def test_no_contradictory_hardcoded_feature_counts(self, forbidden_phrase):
        """None of the old, mutually-contradictory hardcoded count phrases
        should appear anywhere in the rewritten README."""
        text = read_readme()
        assert (
            forbidden_phrase not in text
        ), f"Found stale/contradictory count phrase: '{forbidden_phrase}'"

    def test_no_duplicate_conflicting_shipped_counts_in_body(self):
        """If the document makes a 'features shipped' style numeric claim,
        it should only ever assert a single distinct number, not multiple
        conflicting counts scattered through the document."""
        text = read_readme()
        pattern = re.compile(r"(\d+)\s+features shipped", re.IGNORECASE)
        matches = set(pattern.findall(text))
        assert (
            len(matches) <= 1
        ), f"Expected at most one distinct 'N features shipped' claim, found: {matches}"


# ------------------------------------------------------------------ #
# Live-demo and roadmap accuracy                                      #
# ------------------------------------------------------------------ #


class TestLiveDemoAndRoadmapAccuracy:
    """DoD: 'The live-demo and roadmap sections remain accurate; the Oxos
    dashboard is described as authenticated and the public homepage as a
    future feature.'"""

    def test_oxos_dashboard_described_as_authenticated(self):
        """The Oxos dashboard should be described as part of the
        authenticated experience, not implied to be publicly accessible."""
        text = read_readme()
        assert (
            "authenticated experience" in text
        ), "Expected the Oxos dashboard to be described as an 'authenticated experience'"

    def test_public_homepage_described_as_future_feature(self):
        """The public homepage should be described as a future
        feature/release, not as something already live."""
        text = read_readme()
        assert (
            "future feature" in text or "future release" in text
        ), "Expected the public homepage to be described as a future feature/release"

    def test_readme_has_feature_roadmap_heading(self):
        """The Feature Roadmap table/section should still be present."""
        text = read_readme()
        assert (
            "## Feature Roadmap" in text
        ), "Expected '## Feature Roadmap' heading to be present"
