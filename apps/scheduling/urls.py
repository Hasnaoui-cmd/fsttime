"""
URL patterns for scheduling app.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Reservations
    path('reservations/', views.ReservationListView.as_view(), name='reservation_list'),
    path('reservations/create/', views.TeacherRoomReservationCreateView.as_view(), name='reservation_create'),
    path('reservations/<int:pk>/', views.ReservationDetailView.as_view(), name='reservation_detail'),
    path('reservations/<int:pk>/approve/', views.ReservationApprovalView.as_view(), name='reservation_approval'),
    
    # Sessions
    path('sessions/', views.SessionListView.as_view(), name='session_list'),
    path('sessions/create/', views.SessionCreateView.as_view(), name='session_create'),
    path('sessions/<int:pk>/edit/', views.SessionUpdateView.as_view(), name='session_update'),
    path('sessions/<int:pk>/delete/', views.SessionDeleteView.as_view(), name='session_delete'),
    
    # ==========================================
    # SEMESTER TIMETABLE SYSTEM (PRIMARY)
    # ==========================================
    # Main timetable list - now uses semester-based system
    path('timetables/', views.SemesterTimetableListView.as_view(), name='timetable_list'),
    path('timetables/create/', views.SemesterTimetableCreateView.as_view(), name='timetable_create'),
    path('timetables/<int:pk>/', views.SemesterTimetableDetailView.as_view(), name='timetable_detail'),
    path('timetables/<int:pk>/edit/', views.SemesterTimetableEditView.as_view(), name='timetable_edit'),
    path('timetables/<int:pk>/export/', views.ExportTimetableView.as_view(), name='timetable_export'),
    path('timetables/<int:pk>/delete/', views.SemesterTimetableDeleteView.as_view(), name='timetable_delete'),
    path('my-timetable/', views.MyTimetableView.as_view(), name='my_timetable'),
    path('my-timetable/export/', views.ExportMyTimetableView.as_view(), name='my_timetable_export'),
    
    # ==========================================
    # LEGACY GENERATOR (ARCHIVED)
    # ==========================================
    path('timetable/generate-legacy/', views.TimetableGeneratorView.as_view(), name='timetable_generator_legacy'),
    path('timetable/<int:pk>/view-legacy/', views.TimetableDisplayView.as_view(), name='timetable_display_legacy'),
    
    # Teacher Unavailability
    path('unavailability/', views.TeacherUnavailabilityListView.as_view(), name='unavailability_list'),
    path('unavailability/create/', views.TeacherUnavailabilityCreateView.as_view(), name='unavailability_create'),
    
    # Room Availability Timeline
    path('availability/timeline/', views.RoomAvailabilityTimelineView.as_view(), name='room_availability_timeline'),
    
    # Advanced Teacher Reservation
    path('teacher/reservation/', views.TeacherRoomReservationCreateView.as_view(), name='teacher_reservation_create'),

    # Change Requests
    path('change-requests/', views.TimetableChangeRequestListView.as_view(), name='change_request_list'),
    path('change-requests/create/', views.TimetableChangeRequestCreateView.as_view(), name='change_request_create'),
    
    # API Endpoints for AJAX
    path('api/check-program-availability/', views.check_program_availability_api, name='check_program_availability_api'),
    path('api/get-program-groups/<int:program_id>/', views.get_program_groups_api, name='get_program_groups_api'),
    path('api/check-room-availability/', views.check_room_availability_api, name='check_room_availability_api'),
    path('api/get-available-dates/', views.get_available_dates_api, name='get_available_dates_api'),
    path('api/get-available-time-slots/', views.get_available_time_slots_api, name='get_available_time_slots_api'),
    
    # Subject Management API
    path('api/subjects/', views.get_subjects_by_program_api, name='get_subjects_api'),
    path('api/subjects/create/', views.subject_create_api, name='subject_create_api'),
    path('api/subjects/<int:pk>/delete/', views.subject_delete_api, name='subject_delete_api'),
    
    # Reservation Actions API
    path('api/reservations/<int:pk>/approve/', views.ReservationApproveAPIView.as_view(), name='reservation_approve_api'),
    path('api/reservations/<int:pk>/reject/', views.ReservationRejectAPIView.as_view(), name='reservation_reject_api'),
    
    # Timetable Entry Drag-Drop API
    path('api/timetable/check-conflict/', views.check_conflict_api, name='check_conflict_api'),
    path('api/timetable/entry/create/', views.timetable_entry_create_api, name='timetable_entry_create_api'),
    path('api/timetable/entry/move/', views.timetable_entry_move_api, name='timetable_entry_move_api'),
    path('api/timetable/entry/update/', views.timetable_entry_update_api, name='timetable_entry_update_api'),
    path('api/timetable/entry/delete/', views.timetable_entry_delete_api, name='timetable_entry_delete_api'),
    path('api/timetable/<int:pk>/entries/', views.timetable_entries_api, name='timetable_entries_api'),
    
    # Admin Teacher Timetable
    path('admin/teacher-timetable/', views.AdminTeacherTimetableView.as_view(), name='admin_teacher_timetable'),
    path('api/teacher/<int:teacher_id>/sessions/', views.get_teacher_sessions_api, name='get_teacher_sessions_api'),
    path('api/session/<int:pk>/update/', views.update_session_api, name='update_session_api'),
    
    # Change Request Actions API
    path('api/change-request/<int:pk>/approve/', views.change_request_approve_api, name='change_request_approve_api'),
    path('api/change-request/<int:pk>/reject/', views.change_request_reject_api, name='change_request_reject_api'),
]
