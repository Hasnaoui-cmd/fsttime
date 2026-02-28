import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
import uuid

BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth("admin", "admin123")
TIMEOUT = 30
HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}

def test_session_creation_and_management():
    session_types = ["cours", "td", "tp"]

    # We need some existing teacher, room, and group to link sessions to.
    # We'll get the first teacher, room, and group from their respective lists if available.
    # If not available, we skip test.

    # Fetch users (teachers)
    try:
        users_resp = requests.get(f"{BASE_URL}/accounts/ajax/groups/", auth=AUTH, timeout=TIMEOUT)
        # This endpoint is for groups by program, not users, so instead get users via /accounts/dashboard/ or another way?
        # The PRD does not give exact GET for teachers, so we try getting rooms/groups for IDs, else we create stub minimal resources.

        # We'll get rooms list to pick a room id
        rooms_resp = requests.get(f"{BASE_URL}/rooms/", auth=AUTH, timeout=TIMEOUT)
        rooms_resp.raise_for_status()
        rooms_data = rooms_resp.json()
        if not isinstance(rooms_data, list):
            raise Exception("Rooms list response format unexpected")
        room_id = rooms_data[0]["id"] if rooms_data else None

        # Fetch groups by a program ID - first get any available program ID from groups endpoint or skip
        # Since /accounts/ajax/groups/ requires a 'program_id', this is tricky.
        # We'll try program_id=1 as a guess.
        groups_resp = requests.get(f"{BASE_URL}/accounts/ajax/groups/", params={"program_id":1}, auth=AUTH, timeout=TIMEOUT)
        if groups_resp.status_code == 200:
            groups = groups_resp.json()
        else:
            groups = []
        group_id = groups[0]["id"] if groups else None

        # For teacher id, since PRD doesn't specify an API, we will create a teacher user via /accounts/register/student/ or use 1 if exists
        # We'll just use teacher id = 1 for testing as no direct teacher retrieval endpoint given.
        teacher_id = 1

        if room_id is None or group_id is None or teacher_id is None:
            raise Exception("Required room, group, or teacher not found for testing.")
    except Exception as e:
        raise Exception(f"Setup failed: {str(e)}")

    created_session_ids = []

    try:
        # Create one session per type with valid data
        for session_type in session_types:
            now = datetime.utcnow()
            start_dt = now + timedelta(hours=1)
            end_dt = start_dt + timedelta(hours=2)

            payload = {
                "session_type": session_type,
                "subject": f"Test Subject {uuid.uuid4().hex[:6]}",
                "teacher": teacher_id,
                "room": room_id,
                "groups": [group_id],
                "start_datetime": start_dt.isoformat(timespec='seconds') + 'Z',
                "end_datetime": end_dt.isoformat(timespec='seconds') + 'Z',
                "is_exam": False
            }

            # groups is array type, form-urlencoded needs special format e.g. groups=1&groups=2
            # Prepare data accordingly
            data = {
                "session_type": payload["session_type"],
                "subject": payload["subject"],
                "teacher": str(payload["teacher"]),
                "room": str(payload["room"]),
                "start_datetime": payload["start_datetime"],
                "end_datetime": payload["end_datetime"],
                "is_exam": "true" if payload["is_exam"] else "false"
            }
            for g in payload["groups"]:
                data.setdefault("groups", [])
                if isinstance(data["groups"], list):
                    data["groups"].append(str(g))

            # since requests with form-urlencoded expects list as multiple params: groups=1&groups=2...
            # we need to prepare list of tuples
            data_tuples = []
            for key, value in data.items():
                if isinstance(value, list):
                    for v in value:
                        data_tuples.append((key, v))
                else:
                    data_tuples.append((key, value))

            response = requests.post(f"{BASE_URL}/schedule/sessions/create/", auth=AUTH, headers=HEADERS, data=data_tuples, timeout=TIMEOUT)
            assert response.status_code in (200, 201), f"Failed to create session of type {session_type}, status_code: {response.status_code}, response: {response.text}"
            resp_json = response.json()
            assert "id" in resp_json, f"Response missing session id for type {session_type}"
            session_id = resp_json["id"]
            created_session_ids.append(session_id)

        # Attempt to create a conflicting session to test conflict validation
        # Use the same room, teacher, and group within overlapping time to cause conflict

        conflict_start = start_dt + timedelta(minutes=30)
        conflict_end = conflict_start + timedelta(hours=1)

        conflict_payload = {
            "session_type": "cours",
            "subject": "Conflict Test Session",
            "teacher": teacher_id,
            "room": room_id,
            "groups": [group_id],
            "start_datetime": conflict_start.isoformat(timespec='seconds') + 'Z',
            "end_datetime": conflict_end.isoformat(timespec='seconds') + 'Z',
            "is_exam": False
        }

        conflict_data = {
            "session_type": conflict_payload["session_type"],
            "subject": conflict_payload["subject"],
            "teacher": str(conflict_payload["teacher"]),
            "room": str(conflict_payload["room"]),
            "start_datetime": conflict_payload["start_datetime"],
            "end_datetime": conflict_payload["end_datetime"],
            "is_exam": "true" if conflict_payload["is_exam"] else "false"
        }
        for g in conflict_payload["groups"]:
            conflict_data.setdefault("groups", [])
            if isinstance(conflict_data["groups"], list):
                conflict_data["groups"].append(str(g))

        conflict_data_tuples = []
        for key, value in conflict_data.items():
            if isinstance(value, list):
                for v in value:
                    conflict_data_tuples.append((key, v))
            else:
                conflict_data_tuples.append((key, value))

        conflict_response = requests.post(f"{BASE_URL}/schedule/sessions/create/", auth=AUTH, headers=HEADERS, data=conflict_data_tuples, timeout=TIMEOUT)
        # We expect a conflict validation error; usually HTTP 400 or similar with error message
        assert conflict_response.status_code == 400, f"Expected 400 conflict error but got {conflict_response.status_code}"
        conflict_resp_json = conflict_response.json()
        # Check expected conflict validation message or keys
        assert any("conflict" in str(v).lower() for v in conflict_resp_json.values()), f"Conflict validation message not found in response: {conflict_resp_json}"
    finally:
        # Cleanup created sessions
        for sid in created_session_ids:
            try:
                delete_resp = requests.delete(f"{BASE_URL}/schedule/sessions/{sid}/", auth=AUTH, timeout=TIMEOUT)
                # If API does not have delete, this may fail; silently ignore or log
            except Exception:
                pass

test_session_creation_and_management()