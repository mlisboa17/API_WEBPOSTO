from src.interfaces.http.app import create_app


def test_sprint_7_and_8_routes_are_registered():
    paths = {route.path for route in create_app().routes}
    assert "/api/v1/departmental-governance/alerts" in paths
    assert "/api/v1/departmental-governance/alerts/evaluate" in paths
    assert "/api/v1/departmental-governance/alerts/{alert_id}/acknowledge" in paths
    assert "/api/v1/departmental-governance/alerts/{alert_id}/close" in paths
    assert "/api/v1/departmental-governance/health" in paths
    assert "/api/v1/departmental-governance/daily-report" in paths
    assert "/api/v1/departmental-governance/weekly-report" in paths
    assert "/api/v1/departmental-governance/schedule" in paths
    assert "/api/v1/departmental-governance/schedule/run-due" in paths
    assert "/api/v1/departmental-governance/schedule/history" in paths
    assert "/api/v1/departmental-kpis/goals" in paths
