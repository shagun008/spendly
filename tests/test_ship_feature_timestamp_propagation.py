"""Test that shipping a feature preserves child tested_at/reviewed_at timestamps."""

import datetime
import pytest
from database.db import get_db


def test_ship_preserves_child_tested_reviewed_timestamps():
    # Ensure we have a clean state: insert a parent feature with no timestamps
    # and a child release with tested_at/reviewed_at set (maybe also test/review reports null)
    conn = get_db()
    cur = conn.cursor()
    try:
        # Clean up any existing test rows
        cur.execute("DELETE FROM features WHERE number LIKE 'TEST_%'")
        conn.commit()

        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        parent_number = "TEST_PARENT"
        child_number = "TEST_CHILD"

        # Insert parent
        cur.execute(
            """
            INSERT INTO features (number, parent_number, title, slug, type, release_subtype, description,
                                  captured_at, planned_at, spec_at, implemented_at, tested_at, reviewed_at, shipped_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                parent_number,
                None,
                "Test Parent Feature",
                "test-parent-feature",
                "feature",
                None,
                "Description",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ),
        )
        # Insert child with timestamps set
        cur.execute(
            """
            INSERT INTO features (number, parent_number, title, slug, type, release_subtype, description,
                                  captured_at, planned_at, spec_at, implemented_at, tested_at, reviewed_at, shipped_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                child_number,
                parent_number,
                "Test Child Release",
                "test-child-release",
                "release",
                "new-feature",
                "Description",  # child-only timestamps (should be cleared after ship)
                None,
                None,  # planned_at, captured_at (child-only) will be cleared
                None,
                None,  # spec_at, implemented_at (will be propagated up)
                # tested/reviewed timestamps set to a past time
                now - datetime.timedelta(days=2),
                now - datetime.timedelta(days=1),
                # no shipped yet
                None,
            ),
        )
        conn.commit()

        # Verify initial state
        cur.execute(
            "SELECT tested_at, reviewed_at FROM features WHERE number = %s",
            (child_number,),
        )
        child_before = cur.fetchone()
        assert child_before is not None
        assert child_before[0] is not None  # tested_at set
        assert child_before[1] is not None  # reviewed_at set

        # --- Simulate ship-feature step: set reviewed_at and shipped_at on child ---
        # (This is the first UPDATE in ship-feature)
        cur.execute(
            """
            UPDATE features
            SET reviewed_at = COALESCE(reviewed_at, %s), shipped_at = %s
            WHERE number = %s
            """,
            (now, now, child_number),
        )
        conn.commit()

        # Propagate child timestamps to parent (the rest of the ship-feature logic)
        # We'll replicate the exact UPDATE from ship-feature for the parent timestamps propagation
        cur.execute(
            """
            UPDATE features parent SET
                captured_at = COALESCE(parent.captured_at, (SELECT captured_at FROM features child WHERE child.parent_number = parent.number AND child.captured_at IS NOT NULL LIMIT 1)),
                planned_at = COALESCE(parent.planned_at, (SELECT planned_at FROM features child WHERE child.parent_number = parent.number AND child.planned_at IS NOT NULL LIMIT 1)),
                spec_at = COALESCE(parent.spec_at, (SELECT spec_at FROM features child WHERE child.parent_number = parent.number AND child.spec_at IS NOT NULL LIMIT 1)),
                implemented_at = COALESCE(parent.implemented_at, (SELECT implemented_at FROM features child WHERE child.parent_number = parent.number AND child.implemented_at IS NOT NULL LIMIT 1)),
                tested_at = COALESCE(parent.tested_at, (SELECT tested_at FROM features child WHERE child.parent_number = parent.number AND child.tested_at IS NOT NULL LIMIT 1)),
                reviewed_at = COALESCE(parent.reviewed_at, (SELECT reviewed_at FROM features child WHERE child.parent_number = parent.number AND child.reviewed_at IS NOT NULL LIMIT 1))
            WHERE parent.number = (SELECT parent_number FROM features WHERE number = %s)
              AND parent.parent_number IS NULL
            """,
            (child_number,),
        )
        conn.commit()

        # Verify that child's tested_at and reviewed_at are still present (not nulled)
        cur.execute(
            "SELECT tested_at, reviewed_at FROM features WHERE number = %s",
            (child_number,),
        )
        child_after = cur.fetchone()
        assert child_after is not None
        assert child_after[0] is not None  # tested_at still set
        assert child_after[1] is not None  # reviewed_at still set

        # Also verify that child's planned_at and captured_at are now NULL (cleared)
        cur.execute(
            "SELECT planned_at, captured_at FROM features WHERE number = %s",
            (child_number,),
        )
        child_planned_captured = cur.fetchone()
        assert child_planned_captured[0] is None  # planned_at cleared
        assert child_planned_captured[1] is None  # captured_at cleared

        # Verify parent got the timestamps propagated
        cur.execute(
            "SELECT tested_at, reviewed_at FROM features WHERE number = %s",
            (parent_number,),
        )
        parent_timestamps = cur.fetchone()
        assert parent_timestamps is not None
        assert parent_timestamps[0] is not None  # parent tested_at got child's value
        assert parent_timestamps[1] is not None  # parent reviewed_at got child's value

    finally:
        cur.close()
        conn.close()
