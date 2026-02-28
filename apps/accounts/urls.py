"""
URL patterns for accounts app.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('register/', views.RegistrationChoiceView.as_view(), name='register'),
    path('register/student/', views.StudentRegistrationView.as_view(), name='register_student'),
    path('register/teacher/', views.TeacherRegistrationView.as_view(), name='register_teacher'),
    path('register/association/', views.AssociationRegistrationView.as_view(), name='register_association'),
    path('register/pending/', views.RegistrationPendingView.as_view(), name='registration_pending'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('associations/', views.AssociationListView.as_view(), name='association_list'),
    path('ajax/groups/', views.get_groups_by_program, name='ajax_get_groups'),
    path('my-schedule/', views.teacher_timetable_view, name='teacher_timetable'),
]

