import psycopg2, os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("DATABASE_URL")
report = "Code Review Report - 21.1-oxos-profile-page-mvp - Security Findings - No security vulnerabilities detected. The /platform route is public. - Uses target and rel attributes for external link safety. Quality Findings - Template properly extends base.html - Uses Jinja blocks correctly - CSS uses only CSS variables - Follows existing design system patterns - All 11 tests pass. Overall Verdict: APPROVED"
if not url:
    print("Warning: DATABASE_URL not set")
else:
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        now = datetime.now(timezone.utc)
        cur.execute(
            "UPDATE features SET reviewed_at = COALESCE(reviewed_at, %s), shipped_at = %s, review_report = %s WHERE number = %s",
            (now, now, report, "21.1"),
        )
        print("Rows updated:", cur.rowcount)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB stamp failed: {e}")
