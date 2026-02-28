import requests
from requests.auth import HTTPBasicAuth
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

admin_username = "admin"
admin_password = "admin123"

def test_association_registration_and_approval_workflow():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    # Step 1: Register a new association (no prior resource id provided)
    registration_url = f"{BASE_URL}/accounts/register/association/"
    timestamp = int(time.time())
    association_data = {
        "username": f"assoc_test_{timestamp}",
        "email": f"assoc_test_{timestamp}@example.com",
        "association_name": "Test Association",
        "description": "This is a test association for automated testing.",
        "president_name": "Test President",
        "phone": "+33123456789",
        "password1": "StrongPass123!",
        "password2": "StrongPass123!"
    }

    association_id = None
    try:
        # Register the association without session to avoid CSRF issues
        response = requests.post(
            registration_url,
            data=association_data,
            headers=headers,
            timeout=TIMEOUT
        )
        assert response.status_code == 201 or response.status_code == 200, f"Expected 200 or 201 on registration, got {response.status_code}"
        resp_json = response.json()
        created_username = resp_json.get("username") or association_data["username"]
        assert created_username == association_data["username"], "Returned username does not match registration username"

        # Now authenticate as admin for approval steps
        session = requests.Session()
        session.auth = HTTPBasicAuth(admin_username, admin_password)

        # Step 2: approve via admin endpoints
        pending_url = f"{BASE_URL}/accounts/associations/pending/"
        approve_url = f"{BASE_URL}/accounts/associations/{created_username}/approve/"

        pending_assoc = None
        for _ in range(3):
            resp = session.get(pending_url, timeout=TIMEOUT)
            if resp.status_code == 200:
                pending_list = resp.json()
                if any(a.get("username") == created_username for a in pending_list):
                    pending_assoc = created_username
                    break
            time.sleep(5)
        assert pending_assoc == created_username, "Association did not appear in pending approvals"

        approve_response = session.post(approve_url, timeout=TIMEOUT)
        assert approve_response.status_code == 200, f"Failed to approve association, got {approve_response.status_code}"

        detail_url = f"{BASE_URL}/accounts/associations/{created_username}/"
        detail_resp = session.get(detail_url, timeout=TIMEOUT)
        assert detail_resp.status_code == 200, "Failed to get association detail after approval"
        detail_json = detail_resp.json()
        assert detail_json.get("is_active", False) is True, "Association account is not active after approval"

    finally:
        # Cleanup: delete the association account created
        session = requests.Session()
        session.auth = HTTPBasicAuth(admin_username, admin_password)
        delete_url = f"{BASE_URL}/accounts/associations/{association_data['username']}/"
        try:
            del_resp = session.delete(delete_url, timeout=TIMEOUT)
            assert del_resp.status_code in (200, 204), f"Failed to delete test association, status {del_resp.status_code}"
        except Exception:
            pass

test_association_registration_and_approval_workflow()
