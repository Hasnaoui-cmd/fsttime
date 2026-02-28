
# TestSprite AI Testing Report(MCP)

---

## 1️⃣ Document Metadata
- **Project Name:** FSTTIME
- **Date:** 2026-01-31
- **Prepared by:** TestSprite AI Team

---

## 2️⃣ Requirement Validation Summary

#### Test TC001 user login functionality
- **Test Code:** [TC001_user_login_functionality.py](./TC001_user_login_functionality.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 55, in <module>
  File "<string>", line 28, in test_user_login_functionality
AssertionError: Expected status code 200 for valid credentials, got 403

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/3e88956c-6414-4377-ac30-1df649e35e42/88abb13d-8ed7-43af-9a48-156b79e98943
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC002 student registration process
- **Test Code:** [TC002_student_registration_process.py](./TC002_student_registration_process.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 130, in <module>
  File "<string>", line 51, in test_student_registration_process
AssertionError: Expected success status code but got 403

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/3e88956c-6414-4377-ac30-1df649e35e42/22973ae4-6fc0-4825-aa24-4f65b643cf80
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC003 association registration and approval workflow
- **Test Code:** [TC003_association_registration_and_approval_workflow.py](./TC003_association_registration_and_approval_workflow.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 82, in <module>
  File "<string>", line 38, in test_association_registration_and_approval_workflow
AssertionError: Expected 200 or 201 on registration, got 403

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/3e88956c-6414-4377-ac30-1df649e35e42/465d0a06-6261-4654-a893-4b956b5b0629
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC004 bulk room creation functionality
- **Test Code:** [TC004_bulk_room_creation_functionality.py](./TC004_bulk_room_creation_functionality.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 119, in <module>
  File "<string>", line 45, in test_bulk_room_creation_functionality
AssertionError: Unexpected status code: 404

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/3e88956c-6414-4377-ac30-1df649e35e42/525bcacc-fdd6-4389-868f-1578d805f4e4
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC005 room reservation request and approval
- **Test Code:** [TC005_room_reservation_request_and_approval.py](./TC005_room_reservation_request_and_approval.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 98, in <module>
  File "<string>", line 15, in test_room_reservation_request_and_approval
  File "/var/task/requests/models.py", line 1024, in raise_for_status
    raise HTTPError(http_error_msg, response=self)
requests.exceptions.HTTPError: 404 Client Error: Not Found for url: http://localhost:8000/rooms/

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/3e88956c-6414-4377-ac30-1df649e35e42/d11ed61d-e641-4c85-bb14-5b0fb9c90cb3
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC006 session creation and management
- **Test Code:** [TC006_session_creation_and_management.py](./TC006_session_creation_and_management.py)
- **Test Error:** Traceback (most recent call last):
  File "<string>", line 26, in test_session_creation_and_management
  File "/var/task/requests/models.py", line 1024, in raise_for_status
    raise HTTPError(http_error_msg, response=self)
requests.exceptions.HTTPError: 404 Client Error: Not Found for url: http://localhost:8000/rooms/

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 158, in <module>
  File "<string>", line 49, in test_session_creation_and_management
Exception: Setup failed: 404 Client Error: Not Found for url: http://localhost:8000/rooms/

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/3e88956c-6414-4377-ac30-1df649e35e42/167590bf-862e-41e5-a13e-41c6830be014
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC007 weekly timetable view by user role
- **Test Code:** [TC007_weekly_timetable_view_by_user_role.py](./TC007_weekly_timetable_view_by_user_role.py)
- **Test Error:** Traceback (most recent call last):
  File "<string>", line 19, in test_weekly_timetable_view_by_user_role
  File "/var/task/requests/models.py", line 1024, in raise_for_status
    raise HTTPError(http_error_msg, response=self)
requests.exceptions.HTTPError: 404 Client Error: Not Found for url: http://localhost:8000/schedule/timetable/

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 59, in <module>
  File "<string>", line 21, in test_weekly_timetable_view_by_user_role
AssertionError: Request to http://localhost:8000/schedule/timetable/ failed: 404 Client Error: Not Found for url: http://localhost:8000/schedule/timetable/

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/3e88956c-6414-4377-ac30-1df649e35e42/2129b8d4-e239-4948-8662-d177a2bb2d07
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC008 notification api endpoints
- **Test Code:** [TC008_notification_api_endpoints.py](./TC008_notification_api_endpoints.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 107, in <module>
  File "<string>", line 21, in test_notification_api_endpoints
AssertionError: Unread count status code: 404

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/3e88956c-6414-4377-ac30-1df649e35e42/1aca8956-84e0-41a1-b87a-079e3573611c
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC009 contact form submission
- **Test Code:** [TC009_contact_form_submission.py](./TC009_contact_form_submission.py)
- **Test Error:** Traceback (most recent call last):
  File "<string>", line 49, in test_contact_form_submission
AssertionError: Expected 200 or 201, got 404

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 70, in <module>
  File "<string>", line 58, in test_contact_form_submission
AssertionError: Exception during valid contact form submission: Expected 200 or 201, got 404

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/3e88956c-6414-4377-ac30-1df649e35e42/21272435-9497-4647-8479-67e58c15afbd
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC010 teacher unavailability management
- **Test Code:** [TC010_teacher_unavailability_management.py](./TC010_teacher_unavailability_management.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 60, in <module>
  File "<string>", line 16, in test_teacher_unavailability_management
AssertionError: Expected 200 OK, got 404

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/3e88956c-6414-4377-ac30-1df649e35e42/ebc24521-6a76-494b-9a2e-3a7e377dd430
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---


## 3️⃣ Coverage & Matching Metrics

- **0.00** of tests passed

| Requirement        | Total Tests | ✅ Passed | ❌ Failed  |
|--------------------|-------------|-----------|------------|
| ...                | ...         | ...       | ...        |
---


## 4️⃣ Key Gaps / Risks
{AI_GNERATED_KET_GAPS_AND_RISKS}
---