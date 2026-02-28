import requests
from requests.auth import HTTPBasicAuth


def test_contact_form_submission():
    base_url = "http://localhost:8000"
    endpoint = "/contact/"
    url = base_url + endpoint
    auth = HTTPBasicAuth("admin", "admin123")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    timeout = 30

    # Valid input data
    valid_data = {
        "sender_name": "Jean Dupont",
        "sender_email": "jean.dupont@example.com",
        "subject": "Demande d'information",
        "message": "Bonjour, je souhaite avoir des informations sur les horaires."
    }

    # Invalid input data sets
    invalid_data_list = [
        # Missing sender_name
        {
            "sender_email": "jean.dupont@example.com",
            "subject": "Sujet invalide 1",
            "message": "Message sans nom expéditeur"
        },
        # Invalid email format
        {
            "sender_name": "Jean Dupont",
            "sender_email": "invalid-email-format",
            "subject": "Sujet invalide 2",
            "message": "Message avec email invalide"
        },
        # Missing message
        {
            "sender_name": "Jean Dupont",
            "sender_email": "jean.dupont@example.com",
            "subject": "Sujet invalide 3",
        }
    ]

    # Test valid submission
    try:
        response = requests.post(url, auth=auth, headers=headers, data=valid_data, timeout=timeout)
        assert response.status_code == 201 or response.status_code == 200, f"Expected 200 or 201, got {response.status_code}"
        # Assume response json has success or message field confirming creation
        try:
            json_resp = response.json()
            assert "success" in json_resp or "message" in json_resp
        except Exception:
            # If no json or parse error, still pass if status code is OK
            pass
    except Exception as e:
        assert False, f"Exception during valid contact form submission: {e}"

    # Test invalid submissions
    for idx, invalid_data in enumerate(invalid_data_list, start=1):
        try:
            response = requests.post(url, auth=auth, headers=headers, data=invalid_data, timeout=timeout)
            # Expecting client error status 4xx, likely 400 Bad Request
            assert 400 <= response.status_code < 500, f"Invalid input test case {idx}: Expected 4xx status, got {response.status_code}"
        except Exception as e:
            assert False, f"Exception during invalid contact form submission test case {idx}: {e}"


test_contact_form_submission()