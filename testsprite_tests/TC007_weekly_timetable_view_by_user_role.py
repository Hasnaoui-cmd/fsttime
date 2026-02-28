import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"


def test_weekly_timetable_view_by_user_role():
    session = requests.Session()
    session.auth = HTTPBasicAuth(USERNAME, PASSWORD)
    headers = {
        "Accept": "application/json",
    }
    url = f"{BASE_URL}/schedule/timetable/"

    try:
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Request to {url} failed: {e}"

    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"

    try:
        data = response.json()
    except ValueError:
        assert False, "Response content is not valid JSON"

    # Assert the response is a dict which contains weekly timetable relevant data
    assert isinstance(data, dict), "Response JSON is not an object"

    # Based on PRD description: Weekly timetable should include sessions and exams for the user's role
    # Check some reasonable fields presence e.g. "sessions" or "timetable" or similar (since schema not explicit)
    # We assume key "sessions" or "timetable" or "week" might exist, verify at least one is present
    found_expected_key = any(
        key in data for key in ("sessions", "timetable", "week", "weekly_schedule", "data")
    )
    assert found_expected_key, "Response JSON does not contain expected timetable data keys"

    # Additional possible checks: list-type of sessions if present
    if "sessions" in data:
        assert isinstance(data["sessions"], list), "'sessions' should be a list"
        # Each session should have at least minimal keys like 'id' and 'role' or 'type'
        if len(data["sessions"]) > 0:
            session_item = data["sessions"][0]
            assert isinstance(session_item, dict), "Session item should be an object"
            assert "id" in session_item, "Session item missing 'id'"
            # Role-based filtering check: role may be in response, it must correspond to the authenticated 'admin' role
    # If the role or user info is present in the response, assert it matches admin
    if "user_role" in data:
        assert isinstance(data["user_role"], str), "'user_role' should be string"
        assert data["user_role"].lower() == "admin", "User role in response does not match authenticated user role 'admin'"

    # If there's any error field, assert it is empty or not present
    assert "error" not in data or data["error"] in (None, "", False), "Response contains error field"


test_weekly_timetable_view_by_user_role()