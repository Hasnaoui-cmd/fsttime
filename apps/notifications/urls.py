"""
URL patterns for notifications API and pages.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Page views
    path('', views.NotificationListView.as_view(), name='notification_list'),
    
    # API endpoints
    path('api/unread-count/', views.UnreadCountView.as_view(), name='notification_unread_count'),
    path('api/recent/', views.RecentNotificationsView.as_view(), name='notification_recent'),
    path('mark-read/<int:pk>/', views.MarkAsReadView.as_view(), name='notification_mark_read'),
    path('mark-all-read/', views.MarkAllAsReadView.as_view(), name='mark_all_as_read'),
    path('api/detail/<int:pk>/', views.NotificationDetailAPIView.as_view(), name='notification_detail_api'),
]
