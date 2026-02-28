import requests

BASE_URL = "http://localhost:8000"
LOGIN_ENDPOINT = "/accounts/login/"
TIMEOUT = 30

def test_user_login_functionality():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # Valid credentials test
    valid_payload = {
        "username": "admin",
        "password": "admin123"
    }

    try:
        response = requests.post(
            f"{BASE_URL}{LOGIN_ENDPOINT}",
            data=valid_payload,
            headers=headers,
            timeout=TIMEOUT
        )
    except requests.RequestException as e:
        assert False, f"Request failed with exception: {e}"

    assert response.status_code == 200, f"Expected status code 200 for valid credentials, got {response.status_code}"

    assert "sessionid" in response.cookies or response.is_redirect or 'success' in response.text.lower() or 'dashboard' in response.text.lower(), \
        "Login success indication not found in response"

    # Invalid credentials test
    invalid_payload = {
        "username": "admin",
        "password": "wrongpassword"
    }

    try:
        response_invalid = requests.post(
            f"{BASE_URL}{LOGIN_ENDPOINT}",
            data=invalid_payload,
            headers=headers,
            timeout=TIMEOUT
        )
    except requests.RequestException as e:
        assert False, f"Request failed with exception on invalid credentials: {e}"

    assert response_invalid.status_code in (200, 401, 403), f"Expected status code 200, 401, or 403 for invalid login, got {response_invalid.status_code}"

    failure_indicators = ['invalid', 'error', 'failed', 'incorrect', 'credentials']
    assert any(word in response_invalid.text.lower() for word in failure_indicators), \
        "Expected error message in response for invalid login but none found"

test_user_login_functionality()
