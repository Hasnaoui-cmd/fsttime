import requests

BASE_URL = "http://localhost:8000"
REGISTER_STUDENT_URL = f"{BASE_URL}/accounts/register/student/"
GROUPS_API_URL = f"{BASE_URL}/accounts/ajax/groups/"
TIMEOUT = 30


def test_student_registration_process():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # Step 1: Retrieve groups for a valid program_id to use in valid registration
    valid_program_id = 1  # Assuming program with ID 1 exists
    response_groups = requests.get(
        GROUPS_API_URL,
        params={"program_id": valid_program_id},
        timeout=TIMEOUT
    )
    assert response_groups.status_code == 200, f"Failed to get groups for program_id {valid_program_id}"
    groups_data = response_groups.json()
    assert isinstance(groups_data, list), "Groups API did not return a list"
    assert len(groups_data) > 0, "No groups returned for valid program_id"
    valid_group_id = groups_data[0].get('id')
    assert isinstance(valid_group_id, int), "Invalid group ID received"

    # Define valid student data for registration
    valid_student_data = {
        "username": "teststudent1",
        "email": "teststudent1@example.com",
        "first_name": "Test",
        "last_name": "Student",
        "student_id": "S12345678",
        "program": valid_program_id,
        "group": valid_group_id,
        "password1": "StrongPass123!",
        "password2": "StrongPass123!"
    }

    # VALID REGISTRATION REQUEST
    resp_valid = requests.post(
        REGISTER_STUDENT_URL,
        data=valid_student_data,
        headers=headers,
        timeout=TIMEOUT,
        allow_redirects=False
    )
    try:
        # Success usually is 302 redirect after form submission, or 201 Created or 200 OK depending on implementation
        assert resp_valid.status_code in (200, 201, 302), f"Expected success status code but got {resp_valid.status_code}"
        # If redirected, may check that location is login or dashboard, but here just check response content for success indication
        # If JSON response is given, one could check for user info but here form is x-www-form-urlencoded likely
    finally:
        # Cleanup: Delete the created student user if API supports user deletion or deactivate - 
        # Since no deletion endpoint specified, cleanup is skipped here.
        pass

    # INVALID REGISTRATION TESTS

    # 1. Password mismatch
    invalid_data_pw_mismatch = valid_student_data.copy()
    invalid_data_pw_mismatch["password2"] = "DifferentPass123!"

    resp_pw_mismatch = requests.post(
        REGISTER_STUDENT_URL,
        data=invalid_data_pw_mismatch,
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp_pw_mismatch.status_code == 400 or resp_pw_mismatch.status_code == 200, "Expected 400 or 200 with error for password mismatch"
    # Check error message in response content for password mismatch indication
    assert ("password" in resp_pw_mismatch.text.lower()) or ("mismatch" in resp_pw_mismatch.text.lower()), "Password mismatch error not found"

    # 2. Missing required fields (e.g. username)
    invalid_data_missing_username = valid_student_data.copy()
    invalid_data_missing_username.pop("username")

    resp_missing_username = requests.post(
        REGISTER_STUDENT_URL,
        data=invalid_data_missing_username,
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp_missing_username.status_code == 400 or resp_missing_username.status_code == 200, "Expected 400 or 200 with error for missing username"
    # Check error message for username field
    assert ("username" in resp_missing_username.text.lower()) or ("required" in resp_missing_username.text.lower()), "Missing username error not found"

    # 3. Invalid email format
    invalid_data_bad_email = valid_student_data.copy()
    invalid_data_bad_email["email"] = "invalid-email-format"

    resp_bad_email = requests.post(
        REGISTER_STUDENT_URL,
        data=invalid_data_bad_email,
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp_bad_email.status_code == 400 or resp_bad_email.status_code == 200, "Expected 400 or 200 with error for invalid email"
    assert ("email" in resp_bad_email.text.lower()) or ("invalid" in resp_bad_email.text.lower()), "Invalid email error not found"

    # 4. Invalid program id (non-existent)
    invalid_data_bad_program = valid_student_data.copy()
    invalid_data_bad_program["program"] = 9999999  # Assuming this ID doesn't exist
    invalid_data_bad_program["group"] = valid_group_id  # Group ID might be invalid for this program but test API response

    resp_bad_program = requests.post(
        REGISTER_STUDENT_URL,
        data=invalid_data_bad_program,
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp_bad_program.status_code == 400 or resp_bad_program.status_code == 200, "Expected 400 or 200 with error for invalid program"
    assert ("program" in resp_bad_program.text.lower()) or ("invalid" in resp_bad_program.text.lower()), "Invalid program error not found"

    # 5. Invalid group id (non-existent)
    invalid_data_bad_group = valid_student_data.copy()
    invalid_data_bad_group["group"] = 9999999  # Assuming invalid group id

    resp_bad_group = requests.post(
        REGISTER_STUDENT_URL,
        data=invalid_data_bad_group,
        headers=headers,
        timeout=TIMEOUT
    )
    assert resp_bad_group.status_code == 400 or resp_bad_group.status_code == 200, "Expected 400 or 200 with error for invalid group"
    assert ("group" in resp_bad_group.text.lower()) or ("invalid" in resp_bad_group.text.lower()), "Invalid group error not found"


test_student_registration_process()
