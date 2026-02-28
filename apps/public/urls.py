"""
URL patterns for public pages.
"""

from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', views.LandingPageView.as_view(), name='home'),
    path('rooms/search/', views.PublicRoomSearchView.as_view(), name='public_room_search'),
    path('programs/', RedirectView.as_view(pattern_name='program_list', permanent=False), name='public_program_list'),  # Redirect to Core Program List
    path('about/', views.AboutView.as_view(), name='about'),
]
