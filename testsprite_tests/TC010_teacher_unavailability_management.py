import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth("admin", "admin123")
TIMEOUT = 30

def test_teacher_unavailability_management():
    # Step 1: List current unavailability periods
    list_url = f"{BASE_URL}/schedule/unavailability/"
    create_url = f"{BASE_URL}/schedule/unavailability/create/"

    try:
        resp_list_before = requests.get(list_url, auth=AUTH, timeout=TIMEOUT)
        assert resp_list_before.status_code == 200, f"Expected 200 OK, got {resp_list_before.status_code}"
        unavailabilities_before = resp_list_before.json()
        assert isinstance(unavailabilities_before, list), "Unavailability list should be a JSON array"

        # Step 2: Create a new unavailability period
        # Prepare a period not conflicting with likely existing data (1 hour from now)
        start_dt = datetime.utcnow() + timedelta(hours=1)
        end_dt = start_dt + timedelta(hours=2)
        payload = {
            "start_datetime": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),  # ISO8601 UTC with Z
            "end_datetime": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        }

        resp_create = requests.post(create_url, auth=AUTH, data=payload, timeout=TIMEOUT)
        assert resp_create.status_code in (200, 201), f"Create unavailability expected 200 or 201, got {resp_create.status_code}"
        created_unavailability = resp_create.json()
        assert "id" in created_unavailability, "Created unavailability must have an 'id'"
        unavailability_id = created_unavailability["id"]
        assert created_unavailability.get("start_datetime") == payload["start_datetime"], "Start datetime mismatch"
        assert created_unavailability.get("end_datetime") == payload["end_datetime"], "End datetime mismatch"

        # Step 3: List unavailability periods again to verify the new entry appears
        resp_list_after = requests.get(list_url, auth=AUTH, timeout=TIMEOUT)
        assert resp_list_after.status_code == 200, f"Expected 200 OK, got {resp_list_after.status_code}"
        unavailabilities_after = resp_list_after.json()
        assert any(u.get("id") == unavailability_id for u in unavailabilities_after), "New unavailability not listed"

        # Step 4: (Optional) Confirm the new unavailability would cause scheduling conflicts
        # This step would require another API or session creation to test conflicts,
        # but since not defined, we ensure unavailability appears in the list as indication.

    finally:
        # Step 5: Cleanup - delete the created unavailability if possible
        if 'unavailability_id' in locals():
            delete_url = f"{BASE_URL}/schedule/unavailability/{unavailability_id}/delete/"
            # Assuming DELETE method is supported on this URL, else this step must be adapted or skipped
            try:
                resp_delete = requests.delete(delete_url, auth=AUTH, timeout=TIMEOUT)
                # Accept 204 No Content or 200 OK or 202 Accepted as success for delete
                assert resp_delete.status_code in (200, 202, 204), f"Failed to delete unavailability, status: {resp_delete.status_code}"
            except requests.RequestException:
                # If deletion endpoint doesn't exist or fails, just pass
                pass

test_teacher_unavailability_management()