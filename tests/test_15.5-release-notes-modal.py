"""Feature 15.5 — Release Notes Modal

Tests the modal that shows test reports and code review reports when clicking
on Tested/Reviewed stage dots on the roadmap page.
"""

import importlib

import psycopg2
import psycopg2.extras
import pytest

import database.db as db_module
from database.db import init_db, seed_features
import database.queries as queries_module


@pytest.fixture(scope="module", autouse=True)
def _reseed_after_module():
    """Re-seed the live DB after all tests in this module complete."""
    yield
    seed_features()


SHIPPED_TS = "2026-05-01 00:00:00"

SAMPLE_TEST_REPORT = (
    "Testing Pipeline Report — sample-feature\n\n"
    "Step 1 — Tests Written\n"
    "test_example: Validates example behaviour\n\n"
    "Step 2 — Test Results\n"
    "1 tests collected, 1 passed, 0 failed.\n\n"
    "Verdict: Ready for code review"
)

SAMPLE_REVIEW_REPORT = (
    "Code Review Report — sample-feature\n\n"
    "Security Findings\n"
    "No security vulnerabilities identified.\n\n"
    "Quality Findings\n"
    "APPROVED\n\n"
    "Overall Verdict: APPROVED — ready to commit"
)

SAMPLE_TEST_REPORT_WITH_HTML = (
    "Testing Pipeline Report — html-test\n\n"
    "Found <script>alert('xss')</script> attempt — safely escaped.\n"
)


@pytest.fixture
def _patched_get_db(monkeypatch):
    init_db()
    _real_conn = db_module.get_db()

    class _NoCloseProxy:
        def close(self): pass
        def __getattr__(self, name): return getattr(_real_conn, name)

    conn = _NoCloseProxy()
    def _fake_get_db(): return conn
    monkeypatch.setattr(db_module, "get_db", _fake_get_db)
    monkeypatch.setattr(queries_module, "get_db", _fake_get_db)

    cur = _real_conn.cursor()
    cur.execute("TRUNCATE features RESTART IDENTITY CASCADE")
    _real_conn.commit()
    cur.close()

    yield conn

    _real_conn.rollback()
    cur = _real_conn.cursor()
    cur.execute("TRUNCATE features RESTART IDENTITY CASCADE")
    _real_conn.commit()
    cur.close()
    _real_conn.close()


@pytest.fixture
def client(_patched_get_db, monkeypatch):
    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"
    cur = _patched_get_db.cursor()
    cur.execute("TRUNCATE features RESTART IDENTITY CASCADE")
    _patched_get_db.commit()
    cur.close()
    with app_module.app.test_client() as c:
        yield c


@pytest.fixture
def seeded_client(_patched_get_db, monkeypatch):
    seed_features()
    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"
    with app_module.app.test_client() as c:
        yield c


def _body(response):
    return response.get_data(as_text=True)


def _extract_table(body):
    table_start = body.find('<table class="roadmap-table">')
    if table_start == -1:
        return ""
    return body[table_start:]


def _insert_feature_row(conn, number, title, slug, ftype="feature",
                       release_subtype=None, parent_number=None,
                       captured_at=None, planned_at=None, spec_at=None,
                       implemented_at=None, tested_at=None, reviewed_at=None,
                       shipped_at=None, test_report=None, review_report=None):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "INSERT INTO features"
        " (number, parent_number, title, slug, type, release_subtype,"
        "  captured_at, planned_at, spec_at, implemented_at,"
        "  tested_at, reviewed_at, shipped_at, test_report, review_report)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        " RETURNING id",
        (number, parent_number, title, slug, ftype, release_subtype,
         captured_at, planned_at, spec_at, implemented_at,
         tested_at, reviewed_at, shipped_at, test_report, review_report),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    return row["id"]


class TestDbColumnsExist:
    def test_test_report_column_null_by_default(self, _patched_get_db):
        _insert_feature_row(_patched_get_db, "DB01", "Null Test Report", "db-null-tr")
        result = queries_module.get_all_features()
        row = next((f for f in result if f["number"] == "DB01"), None)
        assert row is not None
        assert row["test_report"] is None

    def test_review_report_column_null_by_default(self, _patched_get_db):
        _insert_feature_row(_patched_get_db, "DB02", "Null Review Report", "db-null-rr")
        result = queries_module.get_all_features()
        row = next((f for f in result if f["number"] == "DB02"), None)
        assert row is not None
        assert row["review_report"] is None


class TestSeedFeaturesIncludesNewColumns:
    def test_seed_features_completes_without_error(self, _patched_get_db):
        seed_features()
        # Use a fresh connection to verify seed data was committed
        import os, psycopg2
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM features")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert count > 0, f"Expected seeded rows, got {count}"

    def test_seeded_rows_have_none_for_report_columns(self, _patched_get_db):
        seed_features()
        result = queries_module.get_all_features()
        for row in result:
            if row["number"] == "15.5":
                assert row["test_report"] is not None, "15.5 should have test_report"
                assert row["review_report"] is not None, "15.5 should have review_report"
            else:
                assert row["test_report"] is None, f"Row '{row['number']}' must have test_report=None"
                assert row["review_report"] is None, f"Row '{row['number']}' must have review_report=None"

    def test_all_required_keys_present_after_seeding(self, _patched_get_db):
        seed_features()
        result = queries_module.get_all_features()
        required = {"number", "parent_number", "title", "slug", "type",
                    "release_subtype", "description", "status",
                    "captured_at", "planned_at", "spec_at", "implemented_at",
                    "tested_at", "reviewed_at", "shipped_at",
                    "test_report", "review_report"}
        for row in result:
            missing = required - set(row.keys())
            assert not missing, f"Row '{row['number']}' missing keys: {missing}"


class TestGetAllFeaturesSelectsNewColumns:
    def test_feature_row_has_test_report_key(self, _patched_get_db):
        _insert_feature_row(_patched_get_db, "QF01", "Test Report Key", "qf-tr")
        result = queries_module.get_all_features()
        row = next((f for f in result if f["number"] == "QF01"), None)
        assert row is not None
        assert "test_report" in row

    def test_feature_row_has_review_report_key(self, _patched_get_db):
        _insert_feature_row(_patched_get_db, "QF02", "Review Report Key", "qf-rr")
        result = queries_module.get_all_features()
        row = next((f for f in result if f["number"] == "QF02"), None)
        assert row is not None
        assert "review_report" in row

    def test_report_values_roundtrip_when_set(self, _patched_get_db):
        _insert_feature_row(_patched_get_db, "QF03", "Roundtrip", "qf-rt",
                           test_report=SAMPLE_TEST_REPORT, review_report=SAMPLE_REVIEW_REPORT)
        result = queries_module.get_all_features()
        row = next((f for f in result if f["number"] == "QF03"), None)
        assert row is not None
        assert row["test_report"] == SAMPLE_TEST_REPORT
        assert row["review_report"] == SAMPLE_REVIEW_REPORT


class TestClickableDotConditions:
    def test_tested_dot_clickable_when_report_exists_and_parent_set(self, client, _patched_get_db):
        _insert_feature_row(_patched_get_db, "CD01-1", "Tested Clickable", "cd-tested",
                           ftype="release", parent_number="CD01",
                           tested_at=SHIPPED_TS, test_report=SAMPLE_TEST_REPORT)
        body = _body(client.get("/roadmap"))
        table_html = _extract_table(body)
        assert "roadmap-dot--clickable" in table_html
        assert 'data-report="test"' in table_html

    def test_reviewed_dot_clickable_when_report_exists_and_parent_set(self, client, _patched_get_db):
        _insert_feature_row(_patched_get_db, "CD02-1", "Reviewed Clickable", "cd-reviewed",
                           ftype="release", parent_number="CD02",
                           reviewed_at=SHIPPED_TS, review_report=SAMPLE_REVIEW_REPORT)
        body = _body(client.get("/roadmap"))
        table_html = _extract_table(body)
        assert "roadmap-dot--clickable" in table_html
        assert 'data-report="review"' in table_html

    def test_tested_dot_not_clickable_when_report_null(self, client, _patched_get_db):
        _insert_feature_row(_patched_get_db, "CD03-1", "Tested Not Clickable", "cd-tested-null",
                           ftype="release", parent_number="CD03",
                           tested_at=SHIPPED_TS, test_report=None)
        body = _body(client.get("/roadmap"))
        table_html = _extract_table(body)
        # Find the specific row and check it has no clickable dots
        idx = table_html.find("CD03-1")
        assert idx != -1
        row_end = table_html.find("</tr>", idx)
        row_html = table_html[idx:row_end]
        assert "roadmap-dot--clickable" not in row_html

    def test_reviewed_dot_not_clickable_when_report_null(self, client, _patched_get_db):
        _insert_feature_row(_patched_get_db, "CD04-1", "Reviewed Not Clickable", "cd-reviewed-null",
                           ftype="release", parent_number="CD04",
                           reviewed_at=SHIPPED_TS, review_report=None)
        body = _body(client.get("/roadmap"))
        table_html = _extract_table(body)
        idx = table_html.find("CD04-1")
        assert idx != -1
        row_end = table_html.find("</tr>", idx)
        row_html = table_html[idx:row_end]
        assert "roadmap-dot--clickable" not in row_html

    def test_tested_dot_not_clickable_on_parent_row(self, client, _patched_get_db):
        _insert_feature_row(_patched_get_db, "CD05", "Parent No Clickable", "cd-parent",
                           ftype="feature", parent_number=None,
                           tested_at=SHIPPED_TS, test_report=SAMPLE_TEST_REPORT)
        body = _body(client.get("/roadmap"))
        table_html = _extract_table(body)
        idx = table_html.find("CD05</td>")
        assert idx != -1
        row_end = table_html.find("</tr>", idx)
        row_html = table_html[idx:row_end]
        assert "roadmap-dot--clickable" not in row_html

    def test_reviewed_dot_not_clickable_on_parent_row(self, client, _patched_get_db):
        _insert_feature_row(_patched_get_db, "CD06", "Parent Review No Clickable", "cd-parent-rr",
                           ftype="feature", parent_number=None,
                           reviewed_at=SHIPPED_TS, review_report=SAMPLE_REVIEW_REPORT)
        body = _body(client.get("/roadmap"))
        table_html = _extract_table(body)
        idx = table_html.find("CD06</td>")
        assert idx != -1
        row_end = table_html.find("</tr>", idx)
        row_html = table_html[idx:row_end]
        assert "roadmap-dot--clickable" not in row_html

    def test_other_stage_dots_never_clickable(self, client, _patched_get_db):
        _insert_feature_row(_patched_get_db, "CD07-1", "Other Stages", "cd-other",
                           ftype="release", parent_number="CD07",
                           captured_at=SHIPPED_TS, planned_at=SHIPPED_TS,
                           spec_at=SHIPPED_TS, implemented_at=SHIPPED_TS,
                           tested_at=SHIPPED_TS, reviewed_at=SHIPPED_TS,
                           shipped_at=SHIPPED_TS,
                           test_report=SAMPLE_TEST_REPORT, review_report=SAMPLE_REVIEW_REPORT)
        body = _body(client.get("/roadmap"))
        table_html = _extract_table(body)
        idx = table_html.find("CD07-1")
        assert idx != -1
        row_end = table_html.find("</tr>", idx)
        row_html = table_html[idx:row_end]
        # Only Tested and Reviewed should be clickable (2), not other stages
        assert row_html.count("roadmap-dot--clickable") == 2

    def test_both_dots_clickable_when_both_reports_exist(self, client, _patched_get_db):
        _insert_feature_row(_patched_get_db, "CD08-1", "Both Clickable", "cd-both",
                           ftype="release", parent_number="CD08",
                           tested_at=SHIPPED_TS, reviewed_at=SHIPPED_TS,
                           test_report=SAMPLE_TEST_REPORT, review_report=SAMPLE_REVIEW_REPORT)
        body = _body(client.get("/roadmap"))
        table_html = _extract_table(body)
        idx = table_html.find("CD08-1")
        assert idx != -1
        row_end = table_html.find("</tr>", idx)
        row_html = table_html[idx:row_end]
        assert row_html.count("roadmap-dot--clickable") == 2

    def test_only_tested_clickable_when_only_test_report(self, client, _patched_get_db):
        _insert_feature_row(_patched_get_db, "CD09-1", "Only Tested", "cd-only-t",
                           ftype="release", parent_number="CD09",
                           tested_at=SHIPPED_TS, reviewed_at=SHIPPED_TS,
                           test_report=SAMPLE_TEST_REPORT, review_report=None)
        body = _body(client.get("/roadmap"))
        table_html = _extract_table(body)
        idx = table_html.find("CD09-1")
        assert idx != -1
        row_end = table_html.find("</tr>", idx)
        row_html = table_html[idx:row_end]
        assert row_html.count("roadmap-dot--clickable") == 1

    def test_only_reviewed_clickable_when_only_review_report(self, client, _patched_get_db):
        _insert_feature_row(_patched_get_db, "CD10-1", "Only Reviewed", "cd-only-r",
                           ftype="release", parent_number="CD10",
                           tested_at=SHIPPED_TS, reviewed_at=SHIPPED_TS,
                           test_report=None, review_report=SAMPLE_REVIEW_REPORT)
        body = _body(client.get("/roadmap"))
        table_html = _extract_table(body)
        idx = table_html.find("CD10-1")
        assert idx != -1
        row_end = table_html.find("</tr>", idx)
        row_html = table_html[idx:row_end]
        assert row_html.count("roadmap-dot--clickable") == 1


class TestModalMarkup:
    def test_modal_overlay_present(self, client, _patched_get_db):
        _insert_feature_row(_patched_get_db, "MM01", "Modal Test", "mm-test")
        body = _body(client.get("/roadmap"))
        assert "roadmap-modal-overlay" in body

    def test_modal_has_dialog_role(self, client, _patched_get_db):
        _insert_feature_row(_patched_get_db, "MM02", "Dialog Test", "mm-dialog")
        body = _body(client.get("/roadmap"))
        assert 'role="dialog"' in body
        assert 'aria-modal="true"' in body

    def test_modal_has_close_button(self, client, _patched_get_db):
        _insert_feature_row(_patched_get_db, "MM03", "Close Test", "mm-close")
        body = _body(client.get("/roadmap"))
        assert "roadmap-modal-close" in body
        assert 'aria-label="Close"' in body

    def test_clickable_dot_has_data_attributes(self, client, _patched_get_db):
        _insert_feature_row(_patched_get_db, "MM04-1", "Data Attrs Test", "mm-attrs",
                           ftype="release", parent_number="MM04",
                           tested_at=SHIPPED_TS, test_report=SAMPLE_TEST_REPORT)
        body = _body(client.get("/roadmap"))
        table_html = _extract_table(body)
        assert 'data-feature-number="MM04-1"' in table_html
        assert 'data-feature-title="Data Attrs Test"' in table_html
        assert 'data-report="test"' in table_html
        assert "data-report-content=" in table_html

    def test_report_content_is_html_escaped(self, client, _patched_get_db):
        _insert_feature_row(_patched_get_db, "MM05-1", "Escape Test", "mm-escape",
                           ftype="release", parent_number="MM05",
                           tested_at=SHIPPED_TS, test_report=SAMPLE_TEST_REPORT_WITH_HTML)
        body = _body(client.get("/roadmap"))
        table_html = _extract_table(body)
        idx = table_html.find("MM05-1")
        assert idx != -1
        row_end = table_html.find("</tr>", idx)
        row_html = table_html[idx:row_end]
        assert "<script>" not in row_html
        assert "&lt;script&gt;" in row_html


class TestExistingBehaviourPreserved:
    def test_non_clickable_dots_still_have_data_date(self, client, _patched_get_db):
        _insert_feature_row(_patched_get_db, "EB01-1", "Data Date Test", "eb-date",
                           ftype="release", parent_number="EB01",
                           tested_at=SHIPPED_TS, test_report=None)
        body = _body(client.get("/roadmap"))
        table_html = _extract_table(body)
        assert "data-date=" in table_html

    def test_expand_in_place_still_works(self, client, _patched_get_db):
        cur = _patched_get_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "INSERT INTO features"
            " (number, parent_number, title, slug, type, release_subtype, description)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            ("EB02", None, "Expand Test", "eb-expand", "feature", None,
             "Test description for expand-in-place"),
        )
        row = cur.fetchone()
        _patched_get_db.commit()
        cur.close()
        assert row is not None
        body = _body(client.get("/roadmap"))
        assert "roadmap-row--clickable" in body
        assert "roadmap-detail-row" in body
        assert "aria-expanded" in body

    def test_page_200_with_mixed_null_and_set_reports(self, client, _patched_get_db):
        _insert_feature_row(_patched_get_db, "EB03-1", "Mixed Test", "eb-mixed",
                           ftype="release", parent_number="EB03",
                           tested_at=SHIPPED_TS, test_report=SAMPLE_TEST_REPORT)
        _insert_feature_row(_patched_get_db, "EB03-2", "Mixed Null", "eb-mixed-null",
                           ftype="release", parent_number="EB03",
                           tested_at=SHIPPED_TS, test_report=None)
        resp = client.get("/roadmap")
        assert resp.status_code == 200

    def test_seeded_data_renders_without_errors(self, seeded_client):
        resp = seeded_client.get("/roadmap")
        assert resp.status_code == 200

    def test_seeded_data_has_clickable_dots_for_15_5(self, seeded_client):
        """15.5 has both test_report and review_report, so its Tested and Reviewed
        dots should be clickable."""
        resp = seeded_client.get("/roadmap")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        # Verify clickable dots exist (15.5 has both reports)
        assert "roadmap-dot--clickable" in body
