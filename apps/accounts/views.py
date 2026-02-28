"""
Views for user authentication and registration.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import CreateView, TemplateView, UpdateView, ListView
from django.urls import reverse_lazy
from django.http import JsonResponse

from .forms import (
    LoginForm, StudentRegistrationForm, 
    AssociationRegistrationForm, UserProfileForm,
    TeacherRegistrationForm
)
from .models import User, Association
from apps.core.models import Group



class CustomLoginView(LoginView):
    """Custom login view with French UI"""
    
    form_class = LoginForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('dashboard')
    
    def form_valid(self, form):
        messages.success(self.request, f"Bienvenue, {form.get_user().get_full_name()}!")
        return super().form_valid(form)


class CustomLogoutView(LogoutView):
    """Custom logout view"""
    
    next_page = 'home'
    
    def dispatch(self, request, *args, **kwargs):
        messages.info(request, "Vous avez été déconnecté avec succès.")
        return super().dispatch(request, *args, **kwargs)


class StudentRegistrationView(CreateView):
    """View for student registration"""
    
    form_class = StudentRegistrationForm
    template_name = 'accounts/register_student.html'
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Votre compte étudiant a été créé avec succès. Vous pouvez maintenant vous connecter."
        )
        return response


class AssociationRegistrationView(CreateView):
    """View for association registration"""
    
    form_class = AssociationRegistrationForm
    template_name = 'accounts/register_association.html'
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Votre demande d'inscription a été soumise avec succès. "
            "Votre compte sera activé après approbation par l'administration. "
            "Vous recevrez une notification une fois approuvé."
        )
        return response


class TeacherRegistrationView(CreateView):
    """View for teacher registration"""
    
    form_class = TeacherRegistrationForm
    template_name = 'accounts/register_teacher.html'
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Votre compte enseignant a été créé avec succès! "
            "Vous pouvez maintenant vous connecter."
        )
        return response


class RegistrationPendingView(TemplateView):
    """View shown after association registration"""
    
    template_name = 'accounts/registration_pending.html'


class RegistrationChoiceView(TemplateView):
    """View for choosing registration type"""
    
    template_name = 'accounts/register_choice.html'


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Dashboard view that redirects to role-specific dashboard.
    """
    
    template_name = 'accounts/dashboard.html'
    
    def get_template_names(self):
        user = self.request.user
        role_templates = {
            'admin': 'accounts/dashboard_admin.html',
            'teacher': 'accounts/dashboard_teacher.html',
            'student': 'accounts/dashboard_student.html',
            'association': 'accounts/dashboard_association.html',
        }
        return [role_templates.get(user.role, 'accounts/dashboard.html')]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.role == 'admin':
            from apps.scheduling.models import RoomReservationRequest
            from apps.core.models import ContactMessage, Room
            from apps.accounts.models import Association, User as UserModel
            
            context['pending_reservations'] = RoomReservationRequest.objects.filter(
                status='pending'
            ).count()
            context['pending_contacts'] = ContactMessage.objects.filter(
                status='pending'
            ).count()
            context['pending_associations'] = Association.objects.filter(
                is_approved=False
            ).count()
            context['total_rooms'] = Room.objects.filter(is_active=True).count()
            
            # Chart data: reservation breakdown by status
            context['res_approved'] = RoomReservationRequest.objects.filter(status='approved').count()
            context['res_rejected'] = RoomReservationRequest.objects.filter(status='rejected').count()
            context['res_pending'] = context['pending_reservations']
            
            # Chart data: users by role
            context['count_students'] = UserModel.objects.filter(role='student').count()
            context['count_teachers'] = UserModel.objects.filter(role='teacher').count()
            context['count_associations'] = UserModel.objects.filter(role='association').count()
            context['count_admins'] = UserModel.objects.filter(role='admin').count()
            
            # Chart data: rooms
            context['rooms_active'] = context['total_rooms']
            context['rooms_inactive'] = Room.objects.filter(is_active=False).count()
            
            # Total contacts
            context['contacts_pending'] = context['pending_contacts']
            context['contacts_resolved'] = ContactMessage.objects.filter(status='resolved').count()
            context['contacts_in_progress'] = ContactMessage.objects.filter(status='in_progress').count()
            
        elif user.role == 'teacher':
            from apps.scheduling.models import Session, RoomReservationRequest
            from django.utils import timezone
            
            context['my_sessions'] = Session.objects.filter(
                teacher=user.teacher_profile,
                start_datetime__gte=timezone.now(),
                is_validated=True
            ).select_related('room').prefetch_related('groups__program').order_by('start_datetime')[:5]
            context['my_reservations'] = RoomReservationRequest.objects.filter(
                teacher=user.teacher_profile
            ).order_by('-created_at')[:5]
            context['weekly_hours'] = user.teacher_profile.get_weekly_hours()

            
        elif user.role == 'student':
            if hasattr(user, 'student_profile') and user.student_profile.group:
                from apps.scheduling.models import Session
                
                context['my_sessions'] = Session.objects.filter(
                    groups=user.student_profile.group
                ).order_by('start_datetime')[:10]
                context['group'] = user.student_profile.group
                
        elif user.role == 'association':
            from apps.scheduling.models import RoomReservationRequest
            
            if hasattr(user, 'association_profile'):
                context['my_reservations'] = RoomReservationRequest.objects.filter(
                    association=user.association_profile
                ).order_by('-created_at')[:5]
                context['is_approved'] = user.association_profile.is_approved
        
        return context


class ProfileView(LoginRequiredMixin, UpdateView):
    """User profile view and update"""
    
    model = User
    form_class = UserProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('profile')
    
    def get_object(self):
        return self.request.user
    
    def form_valid(self, form):
        messages.success(self.request, "Votre profil a été mis à jour avec succès.")
        return super().form_valid(form)


def get_groups_by_program(request):
    """AJAX view to get groups by program"""
    
    program_id = request.GET.get('program_id')
    groups = Group.objects.filter(program_id=program_id).values('id', 'name')
    return JsonResponse(list(groups), safe=False)


class AssociationListView(LoginRequiredMixin, ListView):
    """List association reservation requests (admin only)"""
    
    template_name = 'accounts/association_list.html'
    context_object_name = 'reservations'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'admin':
            from django.shortcuts import redirect
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        from django.db.models import Q
        from apps.scheduling.models import RoomReservationRequest
        
        queryset = RoomReservationRequest.objects.filter(
            requester_type='association'
        ).select_related('association__user', 'room', 'program')
        
        # Status filter
        status = self.request.GET.get('status')
        if status in ('pending', 'approved', 'rejected'):
            queryset = queryset.filter(status=status)
        
        # Search filter
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(association__name__icontains=q) |
                Q(room__name__icontains=q) |
                Q(subject__icontains=q) |
                Q(reason__icontains=q)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        from apps.scheduling.models import RoomReservationRequest
        
        context = super().get_context_data(**kwargs)
        base_qs = RoomReservationRequest.objects.filter(requester_type='association')
        context['total_count'] = base_qs.count()
        context['pending_count'] = base_qs.filter(status='pending').count()
        context['approved_count'] = base_qs.filter(status='approved').count()
        context['rejected_count'] = base_qs.filter(status='rejected').count()
        context['current_status'] = self.request.GET.get('status', '')
        return context


from django.contrib.auth.decorators import login_required

@login_required
def student_timetable_view(request):
    """View for students to see their timetable based on their program"""
    user = request.user
    timetable = None
    current_program = None
    error_message = None
    entries_by_day = {}
    
    # Verify user is a student
    if not user.is_student:
        error_message = "Cette page est réservée aux étudiants."
    else:
        try:
            student = user.student_profile
            # Get program directly or through group
            current_program = student.program or (student.group.program if student.group else None)
            
            if current_program:
                from apps.scheduling.models import Timetable
                timetable = Timetable.objects.filter(
                    program=current_program,
                    is_published=True
                ).order_by('-created_at').first()
                
                if timetable:
                    # Organize entries by day for the timetable grid
                    for entry in timetable.entries.all().select_related('subject', 'room', 'time_slot').order_by('time_slot__slot_number'):
                        day = entry.day_of_week
                        if day not in entries_by_day:
                            entries_by_day[day] = []
                        entries_by_day[day].append(entry)
                else:
                    error_message = "Aucun emploi du temps n'a encore été publié pour votre filière."
            else:
                error_message = "Vous n'êtes associé à aucune filière. Veuillez contacter l'administration."
        except Exception as e:
            error_message = f"Profil étudiant non trouvé."
    
    # Days order for display
    days_order = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
    days_labels = {
        'MON': 'Lundi',
        'TUE': 'Mardi', 
        'WED': 'Mercredi',
        'THU': 'Jeudi',
        'FRI': 'Vendredi',
        'SAT': 'Samedi'
    }
    
    context = {
        'timetable': timetable,
        'error_message': error_message,
        'program': current_program,
        'entries_by_day': entries_by_day,
        'days_order': days_order,
        'days_labels': days_labels,
    }
    return render(request, 'accounts/student_timetable.html', context)


@login_required
def teacher_timetable_view(request):
    """
    Task 4: Teacher Timetable View - Single Source of Truth
    Queries the main Session table where teacher == current_user.
    This ensures that Admin changes to Program timetables are automatically reflected.
    """
    user = request.user
    sessions_by_day = {}
    error_message = None
    teacher = None
    
    # Verify user is a teacher
    if not user.is_teacher:
        error_message = "Cette page est réservée aux enseignants."
    else:
        try:
            teacher = user.teacher_profile
            
            # Task 4: Query the main Session table directly
            # Filter sessions where teacher == current user
            from apps.scheduling.models import Session
            sessions = Session.objects.filter(
                teacher=teacher,
                is_validated=True
            ).select_related('subject', 'room').prefetch_related('groups').order_by('start_datetime')
            
            if sessions.exists():
                # Organize sessions by day of week
                for session in sessions:
                    day = session.start_datetime.weekday()
                    day_codes = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT'}
                    day_code = day_codes.get(day, 'MON')
                    
                    if day_code not in sessions_by_day:
                        sessions_by_day[day_code] = []
                    sessions_by_day[day_code].append(session)
            else:
                error_message = "Aucune séance ne vous est affectée pour le moment."
                
        except Exception as e:
            error_message = "Profil enseignant non trouvé."
    
    # Days order for display
    days_order = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
    days_labels = {
        'MON': 'Lundi',
        'TUE': 'Mardi', 
        'WED': 'Mercredi',
        'THU': 'Jeudi',
        'FRI': 'Vendredi',
        'SAT': 'Samedi'
    }
    
    context = {
        'teacher': teacher,
        'error_message': error_message,
        'sessions_by_day': sessions_by_day,
        'days_order': days_order,
        'days_labels': days_labels,
    }
    return render(request, 'accounts/teacher_timetable.html', context)

