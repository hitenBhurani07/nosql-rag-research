"""Smoke and regression test for the Streamlit research dashboard."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

DASHBOARD_PATH = Path(__file__).resolve().parents[2] / "src" / "nosql_rag" / "dashboard" / "app.py"


def test_dashboard_renders_without_exceptions():
    """Verify that the dashboard loads all 7 tabs headlessly without throwing exceptions."""
    at = AppTest.from_file(str(DASHBOARD_PATH))
    at.run(timeout=15)

    assert len(at.exception) == 0, f"App threw exceptions on initial render: {[e.message for e in at.exception]}"
    assert len(at.tabs) == 7, f"Expected 7 tabs, found {len(at.tabs)}"


def test_dashboard_recommender_end_to_end_default():
    """Verify that clicking 'Generate Recommendation' on default inputs produces Redis with 0 exceptions."""
    at = AppTest.from_file(str(DASHBOARD_PATH))
    at.run(timeout=15)

    # Click the recommendation button
    assert len(at.button) > 0
    at.button[0].click().run(timeout=15)

    assert len(at.exception) == 0, f"App threw exceptions after button click: {[e.message for e in at.exception]}"

    # Check that 'Recommended Database' metric is present and equals Redis
    rec_metrics = [m for m in at.metric if m.label == "Recommended Database"]
    assert len(rec_metrics) == 1
    assert rec_metrics[0].value == "Redis"


def test_dashboard_recommender_vector_similarity():
    """Verify that selecting vector_similarity routes to Qdrant via Stage 1."""
    at = AppTest.from_file(str(DASHBOARD_PATH))
    at.run(timeout=15)

    # Change query_type to vector_similarity
    at.selectbox[0].select("vector_similarity")
    at.button[0].click().run(timeout=15)

    assert len(at.exception) == 0
    rec_metrics = [m for m in at.metric if m.label == "Recommended Database"]
    assert len(rec_metrics) == 1
    assert rec_metrics[0].value == "Qdrant"
