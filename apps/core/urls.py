"""
URL patterns for core app.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Rooms
    path('rooms/', views.RoomListView.as_view(), name='room_list'),
    path('rooms/create/', views.RoomCreateView.as_view(), name='room_create'),
    path('rooms/bulk-create/', views.BulkRoomCreateView.as_view(), name='bulk_room_create'),
    path('rooms/<int:pk>/', views.RoomDetailView.as_view(), name='room_detail'),
    path('rooms/<int:pk>/edit/', views.RoomUpdateView.as_view(), name='room_update'),
    path('rooms/<int:pk>/delete/', views.RoomDeleteView.as_view(), name='room_delete'),
    
    # Contact
    path('contact/', views.ContactSubmitView.as_view(), name='contact'),
    path('contact/success/', views.ContactSuccessView.as_view(), name='contact_success'),
    path('contact/list/', views.ContactListView.as_view(), name='contact_list'),
    path('contact/<int:pk>/', views.ContactDetailView.as_view(), name='contact_detail'),
    
    # Programs
    path('programs/', views.ProgramListView.as_view(), name='program_list'),
    path('programs/<int:pk>/', views.ProgramDetailView.as_view(), name='program_detail'),
    path('programs/create/', views.ProgramCreateView.as_view(), name='program_create'),
    path('programs/<int:pk>/update/', views.ProgramUpdateView.as_view(), name='program_update'),
    
    # Equipment
    path('equipment/', views.EquipmentListView.as_view(), name='equipment_list'),
    
    # API Endpoints
    path('api/programs/<int:program_id>/delete/', views.ProgramDeleteAPIView.as_view(), name='program_delete_api'),
    path('api/rooms/<int:room_id>/delete/', views.RoomDeleteAPIView.as_view(), name='room_delete_api'),
    path('api/contact/<int:message_id>/mark-read/', views.ContactMarkReadAPIView.as_view(), name='contact_mark_read_api'),
    path('api/contact/<int:message_id>/delete/', views.ContactDeleteAPIView.as_view(), name='contact_delete_api'),
    path('api/contact/mark-all-read/', views.ContactMarkAllReadAPIView.as_view(), name='contact_mark_all_read_api'),
]


