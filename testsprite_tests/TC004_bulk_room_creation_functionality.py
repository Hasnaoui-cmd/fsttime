import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
BULK_CREATE_ENDPOINT = f"{BASE_URL}/rooms/bulk-create/"
LIST_ROOMS_ENDPOINT = f"{BASE_URL}/rooms/"

AUTH_USERNAME = "admin"
AUTH_PASSWORD = "admin123"

def test_bulk_room_creation_functionality():
    auth = HTTPBasicAuth(AUTH_USERNAME, AUTH_PASSWORD)
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    # Define bulk room creation payload
    room_prefix = "B"
    start_number = 1
    end_number = 5
    room_type = "classroom"
    capacity = 30
    building = "Main Building"
    floor = 2

    payload = {
        "room_prefix": room_prefix,
        "start_number": start_number,
        "end_number": end_number,
        "room_type": room_type,
        "capacity": capacity,
        "building": building,
        "floor": floor,
    }

    try:
        # Make bulk creation POST request
        response = requests.post(
            BULK_CREATE_ENDPOINT,
            auth=auth,
            headers=headers,
            data=payload,
            timeout=30
        )
        # Assert successful creation (assume 201 Created or 200 OK)
        assert response.status_code in (200, 201), f"Unexpected status code: {response.status_code}"
        # Response might be empty or contain details; validate basic JSON response if any
        if response.headers.get("Content-Type", "").startswith("application/json"):
            response_json = response.json()
            # Expect at least a count or list of created rooms or success indicator
            assert response_json, "Empty JSON response for bulk create"

        # Verify created rooms by listing and filtering prefix and floor/building/type
        list_params = {
            "building": building,
            "floor": floor,
            "type": room_type,
            "min_capacity": capacity,
        }
        list_response = requests.get(
            LIST_ROOMS_ENDPOINT,
            auth=auth,
            headers={"Accept": "application/json"},
            params=list_params,
            timeout=30
        )
        assert list_response.status_code == 200, f"Failed to list rooms, status: {list_response.status_code}"
        rooms = list_response.json()
        # Filter rooms with the prefix and numbering in expected range
        # Assuming rooms have "name" or "room_name" field to check the prefix and number
        created_room_names = {
            f"{room_prefix}{num}" for num in range(start_number, end_number + 1)
        }
        found_room_names = set()
        for room in rooms:
            # The exact field for room name is not given explicitly; assuming 'name' or 'room_name'
            room_name = room.get("name") or room.get("room_name")
            if not room_name:
                continue
            if room_name in created_room_names:
                found_room_names.add(room_name)
                # Validate attributes match expected
                assert room.get("room_type") == room_type, f"Room type mismatch for {room_name}"
                assert room.get("capacity") == capacity, f"Capacity mismatch for {room_name}"
                assert room.get("building") == building, f"Building mismatch for {room_name}"
                assert room.get("floor") == floor, f"Floor mismatch for {room_name}"

        assert found_room_names == created_room_names, f"Some rooms not found: Missing {created_room_names - found_room_names}"
    finally:
        # Cleanup: Attempt to delete created rooms
        # We don't have an explicit delete endpoint in PRD; guessing it might be DELETE /rooms/{id}/
        # First, get all rooms with the prefix to find their IDs
        list_all_response = requests.get(
            LIST_ROOMS_ENDPOINT,
            auth=auth,
            headers={"Accept": "application/json"},
            timeout=30
        )
        if list_all_response.status_code == 200:
            all_rooms = list_all_response.json()
            for room in all_rooms:
                room_name = room.get("name") or room.get("room_name")
                if room_name and room_name.startswith(room_prefix):
                    room_number_part = room_name[len(room_prefix):]
                    if room_number_part.isdigit():
                        num = int(room_number_part)
                        if start_number <= num <= end_number:
                            # Delete this room
                            room_id = room.get("id")
                            if room_id is not None:
                                delete_url = f"{BASE_URL}/rooms/{room_id}/"
                                try:
                                    del_response = requests.delete(delete_url, auth=auth, timeout=30)
                                    # Accept 204 No Content or 200 OK for successful deletion
                                    assert del_response.status_code in (200, 204), f"Failed to delete room {room_name} with id {room_id}"
                                except Exception:
                                    # Log or ignore error during cleanup
                                    pass

test_bulk_room_creation_functionality()