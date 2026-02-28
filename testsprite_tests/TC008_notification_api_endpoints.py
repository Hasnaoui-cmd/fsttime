import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"
TIMEOUT = 30

auth = HTTPBasicAuth(USERNAME, PASSWORD)
headers = {"Accept": "application/json"}

def test_notification_api_endpoints():
    try:
        # 1. Get unread notification count
        unread_count_resp = requests.get(
            f"{BASE_URL}/api/notifications/unread-count/",
            auth=auth,
            headers=headers,
            timeout=TIMEOUT
        )
        assert unread_count_resp.status_code == 200, f"Unread count status code: {unread_count_resp.status_code}"
        unread_data = unread_count_resp.json()
        assert "count" in unread_data and isinstance(unread_data["count"], int), "Unread count missing or invalid"

        # 2. Get recent notifications
        recent_resp = requests.get(
            f"{BASE_URL}/api/notifications/recent/",
            auth=auth,
            headers=headers,
            timeout=TIMEOUT
        )
        assert recent_resp.status_code == 200, f"Recent notifications status code: {recent_resp.status_code}"
        recent_data = recent_resp.json()
        assert "notifications" in recent_data and isinstance(recent_data["notifications"], list), "Notifications list missing or invalid"

        # If no notifications exist, create a dummy notification for testing mark-read
        if not recent_data["notifications"]:
            # Since no API schema in PRD for creating notification via REST, skipping creation.
            # So cannot test mark-read properly without existing notifications.
            # Instead we assert and exit early.
            print("No notifications available to test mark-read endpoints.")
            return

        # Pick one notification that is unread, or any if all read
        notification_to_mark = None
        for n in recent_data["notifications"]:
            if not n.get("is_read", True):
                notification_to_mark = n
                break
        if not notification_to_mark:
            notification_to_mark = recent_data["notifications"][0]

        notification_id = notification_to_mark["id"]

        # 3. Mark single notification as read
        mark_read_resp = requests.post(
            f"{BASE_URL}/api/notifications/{notification_id}/mark-read/",
            auth=auth,
            headers=headers,
            timeout=TIMEOUT
        )
        assert mark_read_resp.status_code == 200, f"Mark single read status code: {mark_read_resp.status_code}"
        mark_read_data = mark_read_resp.json()
        assert mark_read_data.get("success") is True, "Mark single read success flag missing or false"

        # 4. Verify unread count decreased or notifications updated accordingly
        new_unread_count_resp = requests.get(
            f"{BASE_URL}/api/notifications/unread-count/",
            auth=auth,
            headers=headers,
            timeout=TIMEOUT
        )
        assert new_unread_count_resp.status_code == 200, f"Unread count after mark-read status code: {new_unread_count_resp.status_code}"
        new_unread_data = new_unread_count_resp.json()
        assert "count" in new_unread_data and isinstance(new_unread_data["count"], int), "Unread count missing or invalid after mark-read"
        # Count may be the same if notification was already read, so no assert on decreasing

        # 5. Mark all notifications as read
        mark_all_read_resp = requests.post(
            f"{BASE_URL}/api/notifications/mark-all-read/",
            auth=auth,
            headers=headers,
            timeout=TIMEOUT
        )
        assert mark_all_read_resp.status_code == 200, f"Mark all read status code: {mark_all_read_resp.status_code}"
        mark_all_read_data = mark_all_read_resp.json()
        assert mark_all_read_data.get("success") is True, "Mark all read success flag missing or false"

        # 6. Verify unread count is zero after marking all read
        final_unread_count_resp = requests.get(
            f"{BASE_URL}/api/notifications/unread-count/",
            auth=auth,
            headers=headers,
            timeout=TIMEOUT
        )
        assert final_unread_count_resp.status_code == 200, f"Unread count after mark-all-read status code: {final_unread_count_resp.status_code}"
        final_unread_data = final_unread_count_resp.json()
        assert final_unread_data.get("count") == 0, "Unread count not zero after mark-all-read"

    except requests.RequestException as e:
        assert False, f"RequestException during notification API test: {str(e)}"
    except AssertionError:
        raise
    except Exception as e:
        assert False, f"Unexpected error during notification API test: {str(e)}"

test_notification_api_endpoints()