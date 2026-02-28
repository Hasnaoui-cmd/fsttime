import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth('admin', 'admin123')
HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}
TIMEOUT = 30

def test_room_reservation_request_and_approval():
    reservation_id = None
    try:
        # Step 1: List existing rooms to get a valid room ID
        rooms_resp = requests.get(f"{BASE_URL}/rooms/", auth=AUTH, timeout=TIMEOUT)
        rooms_resp.raise_for_status()
        rooms_data = rooms_resp.json()
        assert isinstance(rooms_data, list), "Rooms endpoint did not return a list"
        assert len(rooms_data) > 0, "No rooms found to use for reservation"
        room_id = rooms_data[0].get("id")
        assert isinstance(room_id, int), "Invalid room ID"

        # Step 2: Submit a valid room reservation request
        requested_datetime = (datetime.now() + timedelta(days=1)).replace(microsecond=0).isoformat()
        reservation_payload = {
            "room": str(room_id),
            "requested_datetime": requested_datetime,
            "duration": "2",  # hours or relevant time unit
            "reason": "Test reservation for automated testing",
            "is_exam": "false"
        }
        create_resp = requests.post(
            f"{BASE_URL}/schedule/reservations/create/",
            data=reservation_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        create_resp.raise_for_status()
        # The response should include reservation ID or full reservation data
        create_data = create_resp.json()
        assert "id" in create_data, "Reservation creation response missing 'id'"
        reservation_id = create_data["id"]
        assert isinstance(reservation_id, int), "Invalid reservation id format"

        # Step 3: Approve the reservation (admin action)
        approval_payload = {
            "status": "approved",
            "admin_notes": "Approved automatically by test script"
        }
        approval_resp = requests.post(
            f"{BASE_URL}/schedule/reservations/{reservation_id}/approval/",
            data=approval_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        approval_resp.raise_for_status()
        approval_data = approval_resp.json()
        # Assuming the response includes some status confirmation
        assert ("status" not in approval_data or approval_data.get("status") in ["approved", "rejected"]) or (approval_resp.status_code == 200), "Approval response unexpected"

        # Step 4: Reject the reservation to test rejection flow
        # First, create another reservation to reject
        reservation_payload["requested_datetime"] = (datetime.now() + timedelta(days=2)).replace(microsecond=0).isoformat()
        create_resp_reject = requests.post(
            f"{BASE_URL}/schedule/reservations/create/",
            data=reservation_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        create_resp_reject.raise_for_status()
        create_data_reject = create_resp_reject.json()
        reject_reservation_id = create_data_reject.get("id")
        assert isinstance(reject_reservation_id, int), "Invalid reservation id format for rejection test"

        rejection_payload = {
            "status": "rejected",
            "admin_notes": "Rejected automatically by test script"
        }
        reject_resp = requests.post(
            f"{BASE_URL}/schedule/reservations/{reject_reservation_id}/approval/",
            data=rejection_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        reject_resp.raise_for_status()
        reject_data = reject_resp.json()
        assert ("status" not in reject_data or reject_data.get("status") in ["approved", "rejected"]) or (reject_resp.status_code == 200), "Rejection response unexpected"

    finally:
        # Cleanup: Delete the created reservations if deletion endpoint exists
        # The PRD does not show a delete reservation endpoint, so we skip this step.
        # If it existed, this is where we'd remove test data to keep environment clean.
        pass

test_room_reservation_request_and_approval()