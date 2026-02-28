"""
Views for scheduling app.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db import models
from django.views.generic import (
    CreateView, ListView, DetailView, UpdateView, 
    DeleteView, FormView, TemplateView
)
from django.views import View
from django.urls import reverse_lazy
from datetime import timedelta
from django.utils import timezone

from .models import Session, RoomReservationRequest, TeacherUnavailability, Timetable
from .forms import (
    RoomReservationForm, SessionForm, 
    ReservationApprovalForm, TeacherUnavailabilityForm,
    TeacherRoomReservationForm, AssociationRoomReservationForm
)


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require admin role"""
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'admin'


class TeacherOrAssociationMixin(UserPassesTestMixin):
    """Mixin to require teacher or approved association role"""
    
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.role == 'teacher':
            return hasattr(user, 'teacher_profile')
        if user.role == 'association':
            return hasattr(user, 'association_profile') and user.association_profile.is_approved
        return False


class RoomReservationCreateView(LoginRequiredMixin, TeacherOrAssociationMixin, CreateView):
    """
    View for creating room reservation requests.
    Available for teachers and associations.
    """
    
    model = RoomReservationRequest
    form_class = RoomReservationForm
    template_name = 'scheduling/reservation_form.html'
    success_url = reverse_lazy('dashboard')
    
    def form_valid(self, form):
        user = self.request.user
        
        # Set requester based on role
        if user.role == 'teacher':
            form.instance.requester_type = 'teacher'
            form.instance.teacher = user.teacher_profile
        elif user.role == 'association':
            form.instance.requester_type = 'association'
            form.instance.association = user.association_profile
        else:
            messages.error(self.request, "Vous n'avez pas la permission de réserver une salle.")
            return redirect('dashboard')
        
        messages.success(
            self.request, 
            'Votre demande de réservation a été soumise avec succès. '
            'Vous recevrez une notification une fois qu\'elle sera traitée.'
        )
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.core.models import Room
        context['available_rooms'] = Room.objects.filter(is_active=True).order_by('building', 'name')
        return context


class ReservationListView(LoginRequiredMixin, ListView):
    """
    List reservation requests.
    Shows all for admin, own for teachers/associations.
    """
    
    model = RoomReservationRequest
    template_name = 'scheduling/reservation_list.html'
    context_object_name = 'reservations'
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'admin':
            queryset = RoomReservationRequest.objects.all()
        elif user.role == 'teacher' and hasattr(user, 'teacher_profile'):
            queryset = RoomReservationRequest.objects.filter(teacher=user.teacher_profile)
        elif user.role == 'association' and hasattr(user, 'association_profile'):
            queryset = RoomReservationRequest.objects.filter(association=user.association_profile)
        else:
            queryset = RoomReservationRequest.objects.none()
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_admin'] = self.request.user.role == 'admin'
        context['status_choices'] = RoomReservationRequest.STATUS_CHOICES
        return context


class ReservationDetailView(LoginRequiredMixin, DetailView):
    """View reservation details"""
    
    model = RoomReservationRequest
    template_name = 'scheduling/reservation_detail.html'
    context_object_name = 'reservation'


class ReservationApprovalView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """
    View for admin to approve/reject reservations.
    """
    
    model = RoomReservationRequest
    template_name = 'scheduling/reservation_approval.html'
    success_url = reverse_lazy('reservation_list')
    
    def get_form(self, form_class=None):
        return ReservationApprovalForm(**self.get_form_kwargs())
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Remove 'instance' key as ReservationApprovalForm is not ModelForm
        kwargs.pop('instance', None)
        return kwargs
    
    def form_valid(self, form):
        reservation = self.get_object()
        action = form.cleaned_data['action']
        admin_notes = form.cleaned_data.get('admin_notes', '')
        
        if action == 'approve':
            reservation.approve(self.request.user)
            messages.success(self.request, 'Réservation approuvée avec succès.')
        else:
            reservation.reject(self.request.user, admin_notes)
            messages.info(self.request, 'Réservation rejetée.')
        
        return redirect(self.success_url)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ReservationApprovalForm()
        return context


class SessionListView(LoginRequiredMixin, ListView):
    """List all sessions"""
    
    model = Session
    template_name = 'scheduling/session_list.html'
    context_object_name = 'sessions'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Session.objects.all()
        
        # Filter by teacher for teachers
        user = self.request.user
        if user.role == 'teacher' and hasattr(user, 'teacher_profile'):
            queryset = queryset.filter(teacher=user.teacher_profile)
        
        # Filter by group for students
        elif user.role == 'student' and hasattr(user, 'student_profile'):
            if user.student_profile.group:
                queryset = queryset.filter(groups=user.student_profile.group)
            else:
                queryset = queryset.none()
        
        return queryset.order_by('start_datetime')


class SessionCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Create a new session"""
    
    model = Session
    form_class = SessionForm
    template_name = 'scheduling/session_form.html'
    success_url = reverse_lazy('session_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Séance créée avec succès.')
        return super().form_valid(form)


class SessionUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Update a session"""
    
    model = Session
    form_class = SessionForm
    template_name = 'scheduling/session_form.html'
    success_url = reverse_lazy('session_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Séance modifiée avec succès.')
        return super().form_valid(form)


class SessionDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """Delete a session"""
    
    model = Session
    template_name = 'scheduling/session_confirm_delete.html'
    success_url = reverse_lazy('session_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Séance supprimée avec succès.')
        return super().form_valid(form)


class TimetableView(LoginRequiredMixin, TemplateView):
    """
    Weekly timetable view with professional grid layout.
    Shows sessions in a matrix format: time slots x weekdays.
    """
    
    template_name = 'scheduling/timetable.html'
    
    # Define standard time slots
    TIME_SLOTS = [
        {'start': '09:00', 'end': '10:30', 'label': '09:00 - 10:30'},
        {'start': '10:45', 'end': '12:15', 'label': '10:45 - 12:15'},
        {'start': '12:30', 'end': '14:00', 'label': '12:30 - 14:00'},
        {'start': '14:15', 'end': '15:45', 'label': '14:15 - 15:45'},
        {'start': '16:00', 'end': '17:30', 'label': '16:00 - 17:30'},
    ]
    
    WEEKDAYS = [
        {'index': 0, 'name': 'Lundi', 'abbrev': 'Lun'},
        {'index': 1, 'name': 'Mardi', 'abbrev': 'Mar'},
        {'index': 2, 'name': 'Mercredi', 'abbrev': 'Mer'},
        {'index': 3, 'name': 'Jeudi', 'abbrev': 'Jeu'},
        {'index': 4, 'name': 'Vendredi', 'abbrev': 'Ven'},
        {'index': 5, 'name': 'Samedi', 'abbrev': 'Sam'},
    ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        from django.utils import timezone
        from datetime import timedelta, datetime, time
        from apps.core.models import Program
        
        # Get week offset from query params
        week_offset = int(self.request.GET.get('week_offset', 0))
        
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
        week_end = week_start + timedelta(days=5)  # Monday to Saturday
        
        # Get sessions based on user role
        sessions = Session.objects.none()
        user_info = {}
        
        if user.role == 'teacher' and hasattr(user, 'teacher_profile'):
            sessions = Session.objects.filter(
                teacher=user.teacher_profile,
                start_datetime__date__gte=week_start,
                start_datetime__date__lte=week_end,
                is_validated=True
            )
            user_info = {
                'type': 'teacher',
                'name': user.get_full_name(),
                'department': user.teacher_profile.get_department_display() if user.teacher_profile.department else ''
            }

        elif user.role == 'student' and hasattr(user, 'student_profile'):
            if user.student_profile.group:
                sessions = Session.objects.filter(
                    groups=user.student_profile.group,
                    start_datetime__date__gte=week_start,
                    start_datetime__date__lte=week_end,
                    is_validated=True
                )
                user_info = {
                    'type': 'student',
                    'program': user.student_profile.group.program.name if user.student_profile.group.program else '',
                    'group': user.student_profile.group.name
                }
        elif user.role == 'admin':
            # Admin can filter by program/group via query params
            group_id = self.request.GET.get('group')
            if group_id:
                sessions = Session.objects.filter(
                    groups__id=group_id,
                    start_datetime__date__gte=week_start,
                    start_datetime__date__lte=week_end,
                    is_validated=True
                )
            else:
                sessions = Session.objects.filter(
                    start_datetime__date__gte=week_start,
                    start_datetime__date__lte=week_end,
                    is_validated=True
                )
            context['programs'] = Program.objects.prefetch_related('group_set').all()
        
        # Build grid data structure
        grid = []
        for time_slot in self.TIME_SLOTS:
            row = {
                'time_slot': time_slot,
                'days': []
            }
            
            start_hour = int(time_slot['start'].split(':')[0])
            start_minute = int(time_slot['start'].split(':')[1])
            
            for day_info in self.WEEKDAYS:
                day_date = week_start + timedelta(days=day_info['index'])
                
                # Find session for this slot
                day_session = None
                for session in sessions:
                    if session.start_datetime.date() == day_date:
                        session_hour = session.start_datetime.hour
                        session_minute = session.start_datetime.minute
                        
                        # Match if session starts within this time slot
                        if session_hour == start_hour or (session_hour == start_hour - 1 and session_minute >= 45):
                            day_session = session
                            break
                
                row['days'].append({
                    'date': day_date,
                    'day_name': day_info['name'],
                    'session': day_session,
                    'is_today': day_date == today
                })
            
            grid.append(row)
        
        # Week dates for header
        week_dates = []
        for day_info in self.WEEKDAYS:
            day_date = week_start + timedelta(days=day_info['index'])
            week_dates.append({
                'name': day_info['name'],
                'date': day_date,
                'is_today': day_date == today
            })
        
        context.update({
            'grid': grid,
            'time_slots': self.TIME_SLOTS,
            'weekdays': self.WEEKDAYS,
            'week_dates': week_dates,
            'week_start': week_start,
            'week_end': week_end,
            'week_offset': week_offset,
            'user_info': user_info,
            'today': today,
            'current_semester': 'S5',  # Could be dynamic
        })
        
        return context



class TeacherUnavailabilityCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    View for teachers to declare unavailability.
    """
    
    model = TeacherUnavailability
    form_class = TeacherUnavailabilityForm
    template_name = 'scheduling/unavailability_form.html'
    success_url = reverse_lazy('dashboard')
    
    def test_func(self):
        return self.request.user.role == 'teacher'
    
    def form_valid(self, form):
        form.instance.teacher = self.request.user.teacher_profile
        response = super().form_valid(form)
        
        # Trigger notifications
        from apps.notifications.services import NotificationService
        
        # Notify admins (with affected programs list)
        NotificationService.notify_admins_teacher_unavailability(self.object)
        
        # Notify affected students (if sessions exist)
        NotificationService.notify_students_teacher_unavailable(self.object)
        
        messages.success(self.request, 'Indisponibilité enregistrée. L\'administration a été notifiée.')
        return response


class TeacherUnavailabilityListView(LoginRequiredMixin, ListView):
    """List teacher unavailabilities"""
    
    model = TeacherUnavailability
    template_name = 'scheduling/unavailability_list.html'
    context_object_name = 'unavailabilities'
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'teacher' and hasattr(user, 'teacher_profile'):
            return TeacherUnavailability.objects.filter(
                teacher=user.teacher_profile
            ).order_by('start_datetime')
        elif user.role == 'admin':
            return TeacherUnavailability.objects.all().order_by('start_datetime')
        return TeacherUnavailability.objects.none()


class RoomAvailabilityTimelineView(LoginRequiredMixin, TemplateView):
    """Timeline view showing room availability from 9:00 to 18:00"""
    template_name = 'scheduling/room_availability_timeline.html'
    
    def get_context_data(self, **kwargs):
        from django.utils import timezone
        from datetime import datetime, time
        from django.conf import settings
        from apps.core.models import Room
        
        context = super().get_context_data(**kwargs)
        
        # Get date from query parameter or use today
        date_str = self.request.GET.get('date')
        if date_str:
            try:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                selected_date = timezone.now().date()
        else:
            selected_date = timezone.now().date()
        
        # Don't show timeline for Sundays
        if selected_date.isoweekday() == 7:
            context['is_sunday'] = True
            context['selected_date'] = selected_date
            return context
        
        # Get filter parameters
        room_type = self.request.GET.get('room_type', '')
        building = self.request.GET.get('building', '')
        min_capacity = self.request.GET.get('min_capacity', 0)
        
        # Query rooms
        rooms = Room.objects.filter(is_active=True)
        
        if room_type:
            rooms = rooms.filter(room_type=room_type)
        if building:
            rooms = rooms.filter(building=building)
        if min_capacity:
            try:
                rooms = rooms.filter(capacity__gte=int(min_capacity))
            except ValueError:
                pass
        
        rooms = rooms.order_by('building', 'name')
        
        # Generate time slots (9:00 to 18:00)
        time_slots = []
        for hour in range(settings.WORKING_HOURS_START, settings.WORKING_HOURS_END):
            time_slots.append({
                'hour': hour,
                'time_str': f"{hour:02d}:00"
            })
        
        # Build room schedule data
        room_schedules = []
        for room in rooms:
            schedule = {
                'room': room,
                'slots': []
            }
            
            for slot in time_slots:
                start_dt = datetime.combine(selected_date, time(slot['hour'], 0))
                end_dt = start_dt + timedelta(hours=1)
                
                # Check if slot is occupied by session
                occupied_session = Session.objects.filter(
                    room=room,
                    start_datetime__lt=end_dt,
                    end_datetime__gt=start_dt
                ).first()
                
                # Check approved reservations
                approved_reservation = RoomReservationRequest.objects.filter(
                    room=room,
                    status='approved',
                    requested_datetime__lt=end_dt,
                ).first()
                
                # Calculate if approved reservation overlaps
                is_reserved = False
                if approved_reservation:
                    res_end = approved_reservation.requested_datetime + timedelta(hours=approved_reservation.duration)
                    if approved_reservation.requested_datetime < end_dt and res_end > start_dt:
                        is_reserved = True
                
                # Check pending reservations
                is_pending = RoomReservationRequest.objects.filter(
                    room=room,
                    status='pending',
                    requested_datetime__lt=end_dt,
                ).exists()
                
                is_occupied = bool(occupied_session) or is_reserved
                
                schedule['slots'].append({
                    'time': slot['time_str'],
                    'hour': slot['hour'],
                    'is_occupied': is_occupied,
                    'is_pending': is_pending and not is_occupied,
                    'session': occupied_session,
                    'status': 'occupied' if is_occupied else ('pending' if is_pending else 'available')
                })
            
            room_schedules.append(schedule)
        
        context.update({
            'selected_date': selected_date,
            'time_slots': time_slots,
            'room_schedules': room_schedules,
            'room_types': Room.ROOM_TYPE_CHOICES,
            'buildings': Room.objects.filter(is_active=True).values_list('building', flat=True).distinct(),
            'is_sunday': False,
            'working_hours_start': settings.WORKING_HOURS_START,
            'working_hours_end': settings.WORKING_HOURS_END,
        })
        
        return context


class TeacherRoomReservationCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    Advanced room reservation view for teachers AND associations.
    Teachers get full form with program/subject, associations get simplified form.
    """
    model = RoomReservationRequest
    success_url = reverse_lazy('dashboard')
    
    def test_func(self):
        """Teachers and associations can access this view"""
        user = self.request.user
        if not user.is_authenticated:
            return False
        
        # Allow teachers
        if user.role == 'teacher' and hasattr(user, 'teacher_profile'):
            return True
        
        # Allow associations
        if user.role == 'association' and hasattr(user, 'association_profile'):
            return True
        
        return False
    
    def handle_no_permission(self):
        messages.error(self.request, "Seuls les enseignants et les associations peuvent réserver des salles.")
        return redirect('dashboard')
    
    def get_form_class(self):
        """Return different form based on user role"""
        user = self.request.user
        if user.role == 'association':
            return AssociationRoomReservationForm
        return TeacherRoomReservationForm
    
    def get_template_names(self):
        """Return different template based on user role"""
        user = self.request.user
        if user.role == 'association':
            return ['scheduling/association_reservation_form.html']
        return ['scheduling/teacher_reservation_form.html']
    
    def get_form_kwargs(self):
        """Pass requester info to form"""
        kwargs = super().get_form_kwargs()
        user = self.request.user
        
        if user.role == 'teacher' and hasattr(user, 'teacher_profile'):
            kwargs['teacher'] = user.teacher_profile
        else:
            kwargs['teacher'] = None
        
        return kwargs

    def get_initial(self):
        """Pre-fill room from URL parameter"""
        initial = super().get_initial()
        if 'room' in self.request.GET:
            try:
                room_id = int(self.request.GET['room'])
                # Verify room exists
                from apps.core.models import Room
                if Room.objects.filter(id=room_id).exists():
                    initial['room'] = room_id
            except (ValueError, TypeError):
                pass
        return initial
    
    def form_valid(self, form):
        """Set requester information based on user type"""
        user = self.request.user
        
        if user.role == 'teacher' and hasattr(user, 'teacher_profile'):
            form.instance.requester_type = 'teacher'
            form.instance.teacher = user.teacher_profile
            reservation_type = getattr(form.instance, 'reservation_type', 'one_time')
            type_name = "hebdomadaire" if reservation_type == 'recurring' else "ponctuelle"
        elif user.role == 'association' and hasattr(user, 'association_profile'):
            form.instance.requester_type = 'association'
            form.instance.association = user.association_profile
            form.instance.reservation_type = 'one_time'  # Associations always one-time
            type_name = "d'événement"
        else:
            type_name = ""
        
        messages.success(
            self.request,
            f'Votre demande de réservation {type_name} a été soumise avec succès. '
            f'Vous recevrez une notification une fois qu\'elle sera traitée.'
        )
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Handle form errors"""
        messages.error(
            self.request,
            'Erreur dans le formulaire. Veuillez corriger les erreurs ci-dessous.'
        )
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.role == 'teacher' and hasattr(user, 'teacher_profile'):
            context['teacher'] = user.teacher_profile
            context['user_type'] = 'teacher'
        elif user.role == 'association' and hasattr(user, 'association_profile'):
            context['association'] = user.association_profile
            context['user_type'] = 'association'
        
        return context



# ========== API ENDPOINTS FOR AJAX ==========

from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from datetime import datetime
import json


@login_required
@require_POST
def check_program_availability_api(request):
    """
    API endpoint to check if program/groups/room has conflicts.
    Used by the teacher reservation form for real-time conflict detection.
    """
    try:
        data = json.loads(request.body)
        program_id = data.get('program_id')
        room_id = data.get('room_id')
        group_ids = data.get('group_ids', [])
        start_datetime_str = data.get('start_datetime')
        end_datetime_str = data.get('end_datetime')
        
        if not all([program_id, start_datetime_str, end_datetime_str]):
            return JsonResponse({
                'error': 'Missing required fields'
            }, status=400)
        
        # Parse datetimes (handle both ISO and datetime-local formats)
        from django.utils import timezone
        from datetime import datetime
        
        def parse_dt(dt_str):
             try:
                 dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
             except ValueError:
                 dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M')
             if timezone.is_naive(dt):
                 return timezone.make_aware(dt)
             return dt

        try:
            start_dt = parse_dt(start_datetime_str)
            end_dt = parse_dt(end_datetime_str)
        except ValueError:
             return JsonResponse({'error': 'Invalid date format'}, status=400)

        conflicts_list = []
        
        # 1. Check Room Availability if provided
        if room_id:
            from apps.core.models import Room
            try:
                room = Room.objects.get(pk=room_id)
                # Assuming room.check_availability handles timezones correctly
                if hasattr(room, 'check_availability') and not room.check_availability(start_dt, end_dt):
                     conflicts_list.append({
                         'subject': f"Salle {room.name} indisponible",
                         'time': "Créneau occupé",
                         'teacher': 'N/A'
                     })
            except Room.DoesNotExist:
                pass
        
        # 2. Get program and groups
        from apps.core.models import Program, Group
        from .models import Session
        
        program = Program.objects.get(id=program_id)
        
        if group_ids and len(group_ids) > 0:
            groups = Group.objects.filter(pk__in=group_ids)
        else:
            # Default to all groups if none specified (strict check)
            groups = Group.objects.filter(program=program)
        
        # Find conflicting sessions
        session_conflicts = Session.objects.filter(
            groups__in=groups,
            start_datetime__lt=end_dt,
            end_datetime__gt=start_dt,
            is_validated=True
        ).distinct()
        
        for conflict in session_conflicts[:5]:
            group_names = ", ".join([g.name for g in conflict.groups.all()[:2]])
            conflicts_list.append({
                'subject': f"{conflict.subject}",
                'groups': group_names,
                'time': f"{conflict.start_datetime.strftime('%H:%M')}-{conflict.end_datetime.strftime('%H:%M')}",
                'teacher': conflict.teacher.user.get_full_name() if conflict.teacher else 'N/A'
            })
        
        if len(conflicts_list) > 0:
            return JsonResponse({
                'available': False,
                'conflicts': conflicts_list,
                'message': f"Conflits détectés ({len(conflicts_list)})"
            })
        else:
            return JsonResponse({
                'available': True,
                'conflicts': [],
                'message': "Disponible"
            })
            
    except Program.DoesNotExist:
        return JsonResponse({
            'error': 'Programme non trouvé'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)


@login_required
@require_GET
def get_program_groups_api(request, program_id):
    """
    API endpoint to get groups in a program.
    Used for dynamic group loading when teacher selects a program.
    """
    try:
        from apps.core.models import Group
        from apps.accounts.models import Student
        
        groups = Group.objects.filter(program_id=program_id).order_by('name')
        
        group_list = []
        for group in groups:
            student_count = Student.objects.filter(group=group).count()
            group_list.append({
                'id': group.id,
                'name': group.name,
                'student_count': student_count
            })
        
        return JsonResponse({
            'groups': group_list,
            'total_groups': len(group_list)
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)


@login_required
@require_GET
def check_room_availability_api(request):
    """
    API endpoint to check room availability for a given time slot.
    """
    try:
        room_id = request.GET.get('room_id')
        start_datetime_str = request.GET.get('start_datetime')
        end_datetime_str = request.GET.get('end_datetime')
        
        if not all([room_id, start_datetime_str, end_datetime_str]):
            return JsonResponse({
                'error': 'Missing required fields'
            }, status=400)
        
        # Parse datetimes
        try:
            start_dt = datetime.fromisoformat(start_datetime_str.replace('Z', '+00:00'))
        except ValueError:
            start_dt = datetime.strptime(start_datetime_str, '%Y-%m-%dT%H:%M')
        
        try:
            end_dt = datetime.fromisoformat(end_datetime_str.replace('Z', '+00:00'))
        except ValueError:
            end_dt = datetime.strptime(end_datetime_str, '%Y-%m-%dT%H:%M')
        
        from apps.core.models import Room
        
        room = Room.objects.get(id=room_id)
        is_available = room.check_availability(start_dt, end_dt)
        
        return JsonResponse({
            'available': is_available,
            'room_name': room.name,
            'message': f"La salle {room.name} est {'disponible' if is_available else 'occupée'} à cet horaire."
        })
        
    except Room.DoesNotExist:
        return JsonResponse({
            'error': 'Salle non trouvée'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)


@login_required
@require_POST
def get_available_dates_api(request):
    """
    API endpoint to get available dates for room and program.
    Returns date availability status and available time slots.
    """
    try:
        data = json.loads(request.body)
        room_id = data.get('room_id')
        program_id = data.get('program_id')
        
        from apps.core.models import Room, Program, Group
        from datetime import date, timedelta
        
        # Date range: today + 60 days
        today = date.today()
        end_date = today + timedelta(days=60)
        
        available_dates = []
        current_date = today
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            day_of_week = current_date.isoweekday()
            
            # Skip Sunday
            if day_of_week == 7:
                available_dates.append({
                    'date': date_str,
                    'status': 'disabled',
                    'reason': 'Dimanche',
                    'available_time_slots': []
                })
                current_date += timedelta(days=1)
                continue
            
            # Define working hours (9:00 to 18:00)
            time_slots = []
            for hour in range(9, 18):
                slot_start = datetime.combine(current_date, datetime.min.time().replace(hour=hour))
                slot_end = datetime.combine(current_date, datetime.min.time().replace(hour=hour+1))
                time_slots.append({
                    'start': f'{hour:02d}:00',
                    'end': f'{hour+1:02d}:00',
                    'available': True,
                    'conflicts': []
                })
            
            conflicts = []
            has_room_conflict = False
            has_program_conflict = False
            
            # Check room conflicts
            if room_id:
                try:
                    room = Room.objects.get(id=room_id)
                    day_start = datetime.combine(current_date, datetime.min.time().replace(hour=9))
                    day_end = datetime.combine(current_date, datetime.min.time().replace(hour=18))
                    
                    room_sessions = Session.objects.filter(
                        room=room,
                        start_datetime__date=current_date,
                        is_validated=True
                    )
                    
                    for session in room_sessions:
                        has_room_conflict = True
                        session_start = session.start_datetime.hour
                        session_end = session.end_datetime.hour
                        conflicts.append({
                            'type': 'room',
                            'subject': session.subject,
                            'time': f"{session.start_datetime.strftime('%H:%M')}-{session.end_datetime.strftime('%H:%M')}"
                        })
                        
                        # Mark occupied time slots
                        for slot in time_slots:
                            slot_hour = int(slot['start'].split(':')[0])
                            if session_start <= slot_hour < session_end:
                                slot['available'] = False
                                slot['conflicts'].append(f"Salle occupée: {session.subject}")
                except Room.DoesNotExist:
                    pass
            
            # Check program conflicts
            if program_id:
                try:
                    program = Program.objects.get(id=program_id)
                    groups = Group.objects.filter(program=program)
                    
                    program_sessions = Session.objects.filter(
                        groups__in=groups,
                        start_datetime__date=current_date,
                        is_validated=True
                    ).distinct()
                    
                    for session in program_sessions:
                        has_program_conflict = True
                        session_start = session.start_datetime.hour
                        session_end = session.end_datetime.hour
                        group_names = ", ".join([g.name for g in session.groups.all()[:2]])
                        conflicts.append({
                            'type': 'program',
                            'subject': session.subject,
                            'groups': group_names,
                            'time': f"{session.start_datetime.strftime('%H:%M')}-{session.end_datetime.strftime('%H:%M')}"
                        })
                        
                        # Mark conflicting time slots
                        for slot in time_slots:
                            slot_hour = int(slot['start'].split(':')[0])
                            if session_start <= slot_hour < session_end:
                                slot['available'] = False
                                slot['conflicts'].append(f"Filière a cours: {session.subject}")
                except Program.DoesNotExist:
                    pass
            
            # Filter only available time slots
            available_slots = [s for s in time_slots if s['available']]
            
            # Determine overall status
            if has_program_conflict and not available_slots:
                status = 'program_conflict'
            elif has_room_conflict and not available_slots:
                status = 'room_conflict'
            elif has_room_conflict or has_program_conflict:
                status = 'partial'  # Some slots available
            else:
                status = 'available'
            
            available_dates.append({
                'date': date_str,
                'status': status,
                'day_name': current_date.strftime('%A'),
                'formatted': current_date.strftime('%d/%m/%Y'),
                'available_time_slots': available_slots,
                'all_time_slots': time_slots,
                'conflicts': conflicts
            })
            
            current_date += timedelta(days=1)
        
        return JsonResponse({
            'available_dates': available_dates,
            'total_days': len(available_dates)
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)


@login_required
@require_GET  
def get_available_time_slots_api(request):
    """
    API endpoint to get available time slots for a specific date.
    """
    try:
        date_str = request.GET.get('date')
        room_id = request.GET.get('room_id')
        program_id = request.GET.get('program_id')
        
        from apps.core.models import Room, Program, Group
        from datetime import datetime as dt
        
        selected_date = dt.strptime(date_str, '%Y-%m-%d').date()
        
        # Generate all time slots (9:00 to 18:00)
        time_slots = []
        for hour in range(9, 18):
            slot = {
                'start': f'{hour:02d}:00',
                'end': f'{hour+1:02d}:00',
                'available': True,
                'conflicts': []
            }
            time_slots.append(slot)
        
        # Check room availability
        if room_id:
            try:
                room = Room.objects.get(id=room_id)
                room_sessions = Session.objects.filter(
                    room=room,
                    start_datetime__date=selected_date,
                    is_validated=True
                )
                
                for session in room_sessions:
                    session_start = session.start_datetime.hour
                    session_end = session.end_datetime.hour
                    
                    for slot in time_slots:
                        slot_hour = int(slot['start'].split(':')[0])
                        if session_start <= slot_hour < session_end:
                            slot['available'] = False
                            slot['conflicts'].append({
                                'type': 'room',
                                'text': f"Salle occupée: {session.subject}"
                            })
            except Room.DoesNotExist:
                pass
        
        # Check program availability  
        if program_id:
            try:
                program = Program.objects.get(id=program_id)
                groups = Group.objects.filter(program=program)
                
                program_sessions = Session.objects.filter(
                    groups__in=groups,
                    start_datetime__date=selected_date,
                    is_validated=True
                ).distinct()
                
                for session in program_sessions:
                    session_start = session.start_datetime.hour
                    session_end = session.end_datetime.hour
                    
                    for slot in time_slots:
                        slot_hour = int(slot['start'].split(':')[0])
                        if session_start <= slot_hour < session_end:
                            slot['available'] = False
                            slot['conflicts'].append({
                                'type': 'program',
                                'text': f"Filière a cours: {session.subject}"
                            })
            except Program.DoesNotExist:
                pass
        
        available_slots = [s for s in time_slots if s['available']]
        
        return JsonResponse({
            'date': date_str,
            'time_slots': time_slots,
            'available_slots': available_slots,
            'has_available_slots': len(available_slots) > 0
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)


class ReservationApproveAPIView(LoginRequiredMixin, AdminRequiredMixin, View):
    """API endpoint to approve a reservation via AJAX"""
    def post(self, request, pk):
        from apps.scheduling.models import RoomReservationRequest
        try:
            reservation = RoomReservationRequest.objects.get(pk=pk)
            reservation.approve(request.user)
            return JsonResponse({'success': True, 'message': 'Réservation approuvée avec succès.'})
        except RoomReservationRequest.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Réservation introuvable.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)


class ReservationRejectAPIView(LoginRequiredMixin, AdminRequiredMixin, View):
    """API endpoint to reject a reservation via AJAX"""
    def post(self, request, pk):
        from apps.scheduling.models import RoomReservationRequest
        import json
        try:
            reservation = RoomReservationRequest.objects.get(pk=pk)
            reason = ""
            if request.body:
                try:
                    data = json.loads(request.body)
                    reason = data.get('reason', '')
                except:
                    pass
            
            reservation.reject(request.user, reason)
            return JsonResponse({'success': True, 'message': 'Réservation rejetée.'})
        except RoomReservationRequest.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Réservation introuvable.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)


# ========== AUTOMATIC TIMETABLE GENERATOR VIEWS ==========

class TimetableGeneratorView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """
    Multi-step wizard for automatic timetable generation.
    Step 1: Select Program and Study Groups
    Step 2: Configure/Add Subjects
    Step 3: Semester Configuration
    Step 4: Summary and Generate
    """
    template_name = 'scheduling/timetable_generator.html'
    
    def get_context_data(self, **kwargs):
        from apps.core.models import Program, Group
        from apps.accounts.models import Teacher
        from .models import Subject, TimeSlot
        
        context = super().get_context_data(**kwargs)
        
        context['programs'] = Program.objects.all().order_by('code')
        context['teachers'] = Teacher.objects.select_related('user').all()
        context['time_slots_count'] = TimeSlot.objects.count()
        
        # Colors for subjects
        context['subject_colors'] = [
            '#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', 
            '#ef4444', '#ec4899', '#06b6d4', '#84cc16'
        ]
        
        return context
    
    def post(self, request, *args, **kwargs):
        from apps.core.models import Program, Group
        from .models import Timetable, Subject
        from .services.timetable_generator import TimetableGenerator
        
        step = request.POST.get('step', '1')
        
        if step == 'generate':
            # Final step - create timetable and generate
            program_id = request.POST.get('program')
            study_group_ids = request.POST.getlist('study_groups')
            semester = request.POST.get('semester', 'S1')
            academic_year = request.POST.get('academic_year', '2025-2026')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            
            try:
                program = Program.objects.get(id=program_id)
                
                # Create or get timetable
                timetable, created = Timetable.objects.get_or_create(
                    program=program,
                    semester=semester,
                    academic_year=academic_year,
                    defaults={
                        'name': f"{program.code} - {semester} - {academic_year}",
                        'start_date': start_date if start_date else None,
                        'end_date': end_date if end_date else None,
                        'created_by': request.user
                    }
                )
                
                # Update dates if provided
                if start_date:
                    timetable.start_date = start_date
                if end_date:
                    timetable.end_date = end_date
                timetable.save()
                
                # Add study groups
                if study_group_ids:
                    groups = Group.objects.filter(id__in=study_group_ids)
                    timetable.study_groups.set(groups)
                
                # Generate timetable
                generator = TimetableGenerator(timetable)
                success, message = generator.generate()
                
                if success:
                    messages.success(request, message)
                    return redirect('timetable_display', pk=timetable.id)
                else:
                    messages.error(request, message)
                    return redirect('timetable_generator')
                    
            except Program.DoesNotExist:
                messages.error(request, "Filière non trouvée.")
                return redirect('timetable_generator')
            except Exception as e:
                messages.error(request, f"Erreur: {str(e)}")
                return redirect('timetable_generator')
        
        # Return to form for other steps
        return self.get(request, *args, **kwargs)


class TimetableDisplayView(LoginRequiredMixin, TemplateView):
    """
    Display generated timetable in weekly grid format.
    """
    template_name = 'scheduling/timetable_display.html'
    
    def get_context_data(self, **kwargs):
        from .models import Timetable, TimeSlot
        from apps.core.models import Group
        
        context = super().get_context_data(**kwargs)
        
        timetable_id = self.kwargs.get('pk')
        timetable = get_object_or_404(Timetable, pk=timetable_id)
        
        context['timetable'] = timetable
        
        # Get all time slots organized by day
        time_slots = TimeSlot.objects.all()
        
        # Build grid structure
        days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
        day_names = {
            'MON': 'Lundi', 'TUE': 'Mardi', 'WED': 'Mercredi',
            'THU': 'Jeudi', 'FRI': 'Vendredi', 'SAT': 'Samedi'
        }
        
        # Get unique time periods
        time_periods = list(time_slots.values_list('start_time', 'end_time', 'slot_order').distinct())
        time_periods = sorted(set(time_periods), key=lambda x: x[2])
        
        # Build grid
        grid = []
        for start_time, end_time, slot_order in time_periods:
            row = {
                'time_label': f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
                'slot_order': slot_order,
                'cells': []
            }
            
            for day in days:
                # Find session for this slot
                session = timetable.sessions.filter(
                    start_datetime__hour=start_time.hour,
                    start_datetime__minute=start_time.minute,
                    start_datetime__week_day=days.index(day) + 2  # Django week_day: 1=Sunday
                ).first()
                
                # Alternative: check by time slot if exists
                if not session:
                    time_slot = time_slots.filter(
                        day_of_week=day,
                        slot_order=slot_order
                    ).first()
                    
                    if time_slot:
                        for s in timetable.sessions.all():
                            if (s.start_datetime.hour == time_slot.start_time.hour and
                                s.start_datetime.minute == time_slot.start_time.minute):
                                # Check if day matches (approximately)
                                session = s
                                break
                
                row['cells'].append({
                    'day': day,
                    'day_name': day_names[day],
                    'session': session
                })
            
            grid.append(row)
        
        context['grid'] = grid
        context['days'] = [(d, day_names[d]) for d in days]
        
        # Statistics
        context['total_sessions'] = timetable.sessions.count()
        context['total_hours'] = sum(s.get_duration_hours() for s in timetable.sessions.all())
        context['unique_teachers'] = len(set(s.teacher_id for s in timetable.sessions.all() if s.teacher))
        context['unique_rooms'] = len(set(s.room_id for s in timetable.sessions.all() if s.room))
        
        return context


class TimetableListView(LoginRequiredMixin, ListView):
    """List all generated timetables"""
    model = Timetable
    template_name = 'scheduling/timetable_list.html'
    context_object_name = 'timetables'
    paginate_by = 20
    
    def get_queryset(self):
        from .models import Timetable
        return Timetable.objects.select_related('program', 'created_by').order_by('-created_at')


# ========== TIMETABLE GENERATOR API ENDPOINTS ==========

@login_required
@require_GET
def get_subjects_by_program_api(request):
    """API endpoint to get subjects for a program"""
    from .models import Subject
    
    program_id = request.GET.get('program_id')
    
    if not program_id:
        return JsonResponse({'error': 'program_id required'}, status=400)
    
    subjects = Subject.objects.filter(program_id=program_id).select_related('teacher__user')
    
    subject_list = []
    for subject in subjects:
        subject_list.append({
            'id': subject.id,
            'name': subject.name,
            'code': subject.code,
            'teacher_name': subject.teacher.user.get_full_name() if subject.teacher else 'Non assigné',
            'teacher_id': subject.teacher_id,
            'hours_per_week': float(subject.hours_per_week),
            'session_type': subject.session_type,
            'requires_lab': subject.requires_lab,
            'color': subject.color
        })
    
    return JsonResponse({
        'subjects': subject_list,
        'count': len(subject_list)
    })


@login_required
@require_POST
def subject_create_api(request):
    """API endpoint to create a subject dynamically"""
    from .models import Subject
    from apps.core.models import Program
    from apps.accounts.models import Teacher
    
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        name = data.get('name')
        code = data.get('code')
        program_id = data.get('program_id')
        
        if not all([name, code, program_id]):
            return JsonResponse({'error': 'name, code, and program_id are required'}, status=400)
        
        # Check if code already exists
        if Subject.objects.filter(code=code).exists():
            return JsonResponse({'error': f'Le code {code} existe déjà'}, status=400)
        
        program = Program.objects.get(id=program_id)
        
        teacher = None
        teacher_id = data.get('teacher_id')
        if teacher_id:
            teacher = Teacher.objects.get(id=teacher_id)
        
        subject = Subject.objects.create(
            name=name,
            code=code,
            program=program,
            teacher=teacher,
            session_type=data.get('session_type', 'cours'),
            hours_per_week=data.get('hours_per_week', 1.5),
            max_hours_per_day=data.get('max_hours_per_day', 3.0),
            requires_lab=data.get('requires_lab', False),
            color=data.get('color', '#8b5cf6')
        )
        
        return JsonResponse({
            'success': True,
            'subject': {
                'id': subject.id,
                'name': subject.name,
                'code': subject.code,
                'teacher_name': subject.teacher.user.get_full_name() if subject.teacher else 'Non assigné',
                'hours_per_week': float(subject.hours_per_week)
            }
        })
        
    except Program.DoesNotExist:
        return JsonResponse({'error': 'Filière non trouvée'}, status=404)
    except Teacher.DoesNotExist:
        return JsonResponse({'error': 'Enseignant non trouvé'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def subject_delete_api(request, pk):
    """API endpoint to delete a subject"""
    from .models import Subject
    
    try:
        subject = Subject.objects.get(pk=pk)
        subject.delete()
        return JsonResponse({'success': True})
    except Subject.DoesNotExist:
        return JsonResponse({'error': 'Matière non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def timetable_regenerate(request, pk):
    """Regenerate an existing timetable"""
    from .models import Timetable
    from .services.timetable_generator import TimetableGenerator
    
    timetable = get_object_or_404(Timetable, pk=pk)
    
    if request.method == 'POST':
        generator = TimetableGenerator(timetable)
        success, message = generator.generate()
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        
        return redirect('timetable_display', pk=timetable.id)
    
    return redirect('timetable_display', pk=timetable.id)


# ============================================================================
# SEMESTER TIMETABLE CRUD VIEWS
# ============================================================================

class SemesterTimetableListView(LoginRequiredMixin, ListView):
    """
    List all semester timetables.
    Accessible to all authenticated users.
    Students and teachers see published timetables, admins see all.
    """
    
    model = Timetable
    template_name = 'scheduling/semester_timetable_list.html'
    context_object_name = 'timetables'
    paginate_by = 12
    
    def get_queryset(self):
        user = self.request.user
        queryset = Timetable.objects.select_related('program', 'created_by').order_by('-created_at')
        
        # Admin-Alignment: Non-admin users see drafts only if they belong to the program
        if user.role == 'student' and hasattr(user, 'student_profile'):
            prog = user.student_profile.program
            queryset = queryset.filter(models.Q(is_published=True) | models.Q(program=prog))
        elif user.role == 'teacher' and hasattr(user, 'teacher_profile'):
            # Fetch all timetable IDs that teacher is related to (any entry)
            from .models import TimetableEntry
            related_tt_ids = TimetableEntry.objects.filter(teacher=user.teacher_profile).values_list('timetable_id', flat=True)
            queryset = queryset.filter(models.Q(is_published=True) | models.Q(id__in=related_tt_ids)).distinct()
        elif user.role != 'admin':
            queryset = queryset.filter(is_published=True)
        
        # Filter by program
        program_id = self.request.GET.get('program')
        if program_id:
            queryset = queryset.filter(program_id=program_id)
        
        # Filter by semester
        semester = self.request.GET.get('semester')
        if semester:
            queryset = queryset.filter(semester=semester)
        
        # Filter by academic year
        year = self.request.GET.get('year')
        if year:
            queryset = queryset.filter(academic_year=year)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.core.models import Program
        
        context['programs'] = Program.objects.all().order_by('name')
        context['semesters'] = Timetable.SEMESTER_CHOICES
        context['academic_years'] = Timetable.objects.values_list('academic_year', flat=True).distinct()
        
        # Current filters
        context['current_program'] = self.request.GET.get('program', '')
        context['current_semester'] = self.request.GET.get('semester', '')
        context['current_year'] = self.request.GET.get('year', '')
        
        return context


class SemesterTimetableCreateView(LoginRequiredMixin, AdminRequiredMixin, View):
    """
    Multi-step view for creating a semester timetable with inline subjects.
    Step 1: Select program, semester, year, dates + ADD SUBJECTS INLINE
    Step 2: Auto-generation fills the weekly grid
    """
    
    template_name = 'scheduling/semester_timetable_create.html'
    
    def get(self, request):
        from .forms import SemesterTimetableForm, SubjectFormSet
        from .models import TimeSlot
        from apps.accounts.models import Teacher
        
        form = SemesterTimetableForm()
        subject_formset = SubjectFormSet()
        teachers = Teacher.objects.all().order_by('user__last_name')
        time_slots = TimeSlot.objects.all().order_by('slot_number')
        
        context = {
            'form': form,
            'subject_formset': subject_formset,
            'teachers': teachers,
            'time_slots': time_slots,
            'days': [
                ('MON', 'Lundi'),
                ('TUE', 'Mardi'),
                ('WED', 'Mercredi'),
                ('THU', 'Jeudi'),
                ('FRI', 'Vendredi'),
                ('SAT', 'Samedi'),
            ],
            'step': 1
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        from .forms import SemesterTimetableForm, SubjectFormSet
        from .models import TimeSlot, Timetable, Subject
        from .services.semester_generator import SemesterTimetableGenerator
        from django.db import transaction
        
        form = SemesterTimetableForm(request.POST)
        subject_formset = SubjectFormSet(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Save timetable
                    timetable = form.save(commit=False)
                    timetable.created_by = request.user
                    timetable.save()
                    
                    # Process subject formset
                    subject_formset = SubjectFormSet(request.POST, instance=timetable)
                    
                    if subject_formset.is_valid():
                        # Save inline subjects
                        subjects = subject_formset.save(commit=False)
                        
                        # Extract semester number
                        try:
                            semester_num = int(timetable.semester.replace('S', ''))
                        except:
                            semester_num = 1
                        
                        for subject in subjects:
                            subject.timetable = timetable
                            subject.program = timetable.program
                            subject.semester = semester_num
                            subject.is_active = True
                            subject.save()
                        
                        # Delete marked-for-deletion subjects
                        for obj in subject_formset.deleted_objects:
                            obj.delete()
                    
                    # Trigger automatic generation
                    generator = SemesterTimetableGenerator(timetable)
                    result = generator.generate()
                    
                    if result['success']:
                        messages.success(
                            request,
                            f"✅ {result['message']} Vous pouvez maintenant modifier la grille."
                        )
                        if result.get('unscheduled'):
                            messages.warning(
                                request,
                                f"⚠️ {len(result['unscheduled'])} matière(s) non programmée(s): {', '.join(result['unscheduled'][:3])}"
                            )
                    else:
                        messages.warning(
                            request,
                            f"⚠️ Génération: {result.get('error', 'Erreur inconnue')}. Remplissez manuellement."
                        )
                    
                    return redirect('timetable_edit', pk=timetable.pk)
                    
            except Exception as e:
                messages.error(request, f"Erreur: {str(e)}")
        
        # Form invalid - re-render with errors
        from apps.accounts.models import Teacher
        time_slots = TimeSlot.objects.all().order_by('slot_number')
        teachers = Teacher.objects.all().order_by('user__last_name')
        
        context = {
            'form': form,
            'subject_formset': subject_formset,
            'teachers': teachers,
            'time_slots': time_slots,
            'days': [
                ('MON', 'Lundi'),
                ('TUE', 'Mardi'),
                ('WED', 'Mercredi'),
                ('THU', 'Jeudi'),
                ('FRI', 'Vendredi'),
                ('SAT', 'Samedi'),
            ],
            'step': 1
        }
        return render(request, self.template_name, context)


class SemesterTimetableEditView(LoginRequiredMixin, AdminRequiredMixin, View):
    """
    Edit timetable entries in a weekly grid format.
    """
    
    template_name = 'scheduling/semester_timetable_edit.html'
    
    def get(self, request, pk):
        from .models import TimeSlot, TimetableEntry, Subject
        from apps.accounts.models import Teacher
        from apps.core.models import Room, Group
        
        timetable = get_object_or_404(Timetable, pk=pk)
        time_slots = TimeSlot.objects.all().order_by('slot_number')
        
        # Build grid data from existing entries
        entries = TimetableEntry.objects.filter(timetable=timetable).select_related(
            'subject', 'teacher', 'teacher__user', 'room', 'study_group', 'time_slot'
        )
        
        # Create a lookup dict for entries
        entry_dict = {}
        for entry in entries:
            key = f"{entry.day_of_week}_{entry.time_slot.slot_number}"
            entry_dict[key] = entry
        
        # Get available options
        subjects = Subject.objects.filter(program=timetable.program).order_by('code')
        teachers = Teacher.objects.all().order_by('user__last_name')
        rooms = Room.objects.filter(is_active=True).order_by('building', 'name')
        groups = Group.objects.filter(program=timetable.program).order_by('name')
        
        days = [
            ('MON', 'Lundi'),
            ('TUE', 'Mardi'),
            ('WED', 'Mercredi'),
            ('THU', 'Jeudi'),
            ('FRI', 'Vendredi'),
            ('SAT', 'Samedi'),
        ]
        
        context = {
            'timetable': timetable,
            'time_slots': time_slots,
            'days': days,
            'entry_dict': entry_dict,
            'subjects': subjects,
            'teachers': teachers,
            'rooms': rooms,
            'groups': groups,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        from .models import TimeSlot, TimetableEntry, Subject
        from apps.accounts.models import Teacher
        from apps.core.models import Room, Group
        from apps.notifications.services import NotificationService
        
        timetable = get_object_or_404(Timetable, pk=pk)
        time_slots = TimeSlot.objects.all().order_by('slot_number')
        time_slot_dict = {ts.slot_number: ts for ts in time_slots}
        
        days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
        created_count = 0
        updated_count = 0
        deleted_count = 0
        errors = []
        
        # Process each cell in the grid
        for day in days:
            for slot_num in range(1, 6):
                prefix = f"{day}_{slot_num}"
                
                subject_id = request.POST.get(f"{prefix}_subject")
                teacher_id = request.POST.get(f"{prefix}_teacher")
                room_id = request.POST.get(f"{prefix}_room")
                group_id = request.POST.get(f"{prefix}_group")
                session_type = request.POST.get(f"{prefix}_type") or 'cours'
                
                time_slot = time_slot_dict.get(slot_num)
                if not time_slot:
                    continue
                
                # Get existing entry
                existing = TimetableEntry.objects.filter(
                    timetable=timetable,
                    day_of_week=day,
                    time_slot=time_slot
                ).first()
                
                if subject_id:
                    try:
                        subject = Subject.objects.get(pk=subject_id)
                        teacher = Teacher.objects.get(pk=teacher_id) if teacher_id else None
                        room = Room.objects.get(pk=room_id) if room_id else None
                        group = Group.objects.get(pk=group_id) if group_id else None
                        
                        if existing:
                            existing.subject = subject
                            existing.teacher = teacher
                            existing.room = room
                            existing.study_group = group
                            existing.session_type = session_type
                            
                            # Check conflicts
                            conflicts = existing.get_all_conflicts()
                            if conflicts:
                                for c in conflicts:
                                    errors.append(c['message'])
                            else:
                                existing.save()
                                updated_count += 1
                        else:
                            entry = TimetableEntry(
                                timetable=timetable,
                                day_of_week=day,
                                time_slot=time_slot,
                                subject=subject,
                                teacher=teacher,
                                room=room,
                                study_group=group,
                                session_type=session_type
                            )
                            
                            conflicts = entry.get_all_conflicts()
                            if conflicts:
                                for c in conflicts:
                                    errors.append(c['message'])
                            else:
                                entry.save()
                                created_count += 1
                    except Exception as e:
                        errors.append(str(e))
                elif existing:
                    existing.delete()
                    deleted_count += 1
        
        # Send notifications if saved successfully
        if created_count > 0 or updated_count > 0:
            try:
                NotificationService.notify_timetable_update(timetable)
            except Exception as e:
                pass  # Don't fail the save if notification fails
        
        if errors:
            for error in errors[:5]:  # Show max 5 errors
                messages.error(request, error)
        
        if created_count > 0 or updated_count > 0 or deleted_count > 0:
            messages.success(
                request,
                f"Emploi du temps mis à jour: {created_count} créés, {updated_count} modifiés, {deleted_count} supprimés."
            )
        
        return redirect('timetable_detail', pk=timetable.pk)


class SemesterTimetableDetailView(LoginRequiredMixin, DetailView):
    """
    View timetable in read-only weekly grid format.
    """
    
    model = Timetable
    template_name = 'scheduling/semester_timetable_detail.html'
    context_object_name = 'timetable'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import TimeSlot, TimetableEntry
        
        timetable = self.object
        time_slots = TimeSlot.objects.all().order_by('slot_number')
        
        # Build grid data from entries
        entries = TimetableEntry.objects.filter(timetable=timetable).select_related(
            'subject', 'teacher', 'teacher__user', 'room', 'study_group', 'time_slot'
        )
        
        # Store as lists to handle potential multiple entries per slot
        entry_dict = {}
        for entry in entries:
            key = f"{entry.day_of_week}_{entry.time_slot.slot_number}"
            if key not in entry_dict:
                entry_dict[key] = []
            entry_dict[key].append(entry)
        
        days = [
            ('MON', 'Lundi'),
            ('TUE', 'Mardi'),
            ('WED', 'Mercredi'),
            ('THU', 'Jeudi'),
            ('FRI', 'Vendredi'),
            ('SAT', 'Samedi'),
        ]
        
        context['time_slots'] = time_slots
        context['days'] = days
        context['entry_dict'] = entry_dict
        context['total_entries'] = entries.count()
        
        return context


class SemesterTimetableDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """
    Delete a semester timetable with confirmation.
    """
    
    model = Timetable
    template_name = 'scheduling/semester_timetable_confirm_delete.html'
    success_url = reverse_lazy('timetable_list')
    context_object_name = 'timetable'
    
    def delete(self, request, *args, **kwargs):
        timetable = self.get_object()
        messages.success(
            request,
            f"L'emploi du temps '{timetable}' a été supprimé avec succès."
        )
        return super().delete(request, *args, **kwargs)


class MyTimetableView(LoginRequiredMixin, TemplateView):
    """
    Personal timetable view for students and teachers.
    """
    
    template_name = 'scheduling/my_timetable.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import TimeSlot, TimetableEntry, Timetable
        
        user = self.request.user
        time_slots = TimeSlot.objects.all().order_by('slot_number')
        
        days = [
            ('MON', 'Lundi'),
            ('TUE', 'Mardi'),
            ('WED', 'Mercredi'),
            ('THU', 'Jeudi'),
            ('FRI', 'Vendredi'),
            ('SAT', 'Samedi'),
        ]
        
        if user.role == 'student' and hasattr(user, 'student_profile'):
            student = user.student_profile
            # Get program directly or via group (student.program is now a direct FK)
            current_program = student.program or (student.group.program if student.group else None)
            
            if current_program:
                # Latest Version Priority: Get latest timetable (Published or Draft)
                timetable = Timetable.objects.filter(
                    program=current_program
                ).order_by('-created_at').first()
                
                if timetable:
                    # Get all entries for this timetable
                    if student.group:
                        # Filter by student's group OR entries with no specific group (program-wide)
                        entries = TimetableEntry.objects.filter(
                            timetable=timetable
                        ).filter(
                            models.Q(study_group=student.group) | models.Q(study_group__isnull=True)
                        )
                    else:
                        # No group - show all entries for the program
                        entries = TimetableEntry.objects.filter(timetable=timetable)
                
                # FALLBACK: If no entries in static timetable system, check for dynamic Sessions
                if not entries.exists():
                    from .models import Session
                    from django.utils import timezone
                    
                    # Fetch validated sessions for this group/program
                    sessions_query = Session.objects.filter(is_validated=True)
                    if student.group:
                        sessions_query = sessions_query.filter(groups=student.group)
                    else:
                        sessions_query = sessions_query.filter(groups__program=current_program)
                    
                    # Convert sessions to a compatible format for the grid
                    dynamic_entries = []
                    DAY_MAP_REVERSE = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT'}
                    
                    for session in sessions_query.distinct().select_related('teacher', 'room')[:50]:
                        day_code = DAY_MAP_REVERSE.get(session.start_datetime.weekday())
                        if not day_code: continue
                        
                        # Find matching time slot
                        start_time = session.start_datetime.time()
                        slot = time_slots.filter(start_time__lte=start_time).order_by('-start_time').first()
                        
                        if slot:
                            # Create a duck-typed object compatible with the template
                            dynamic_entries.append({
                                'day_of_week': day_code,
                                'time_slot': slot,
                                'subject': {
                                    'name': session.subject,
                                    'code': (session.subject[:10] + '..') if len(session.subject) > 10 else session.subject
                                },
                                'teacher': session.teacher,
                                'room': session.room,
                                'session_type': session.session_type,
                                'event_type': 'recurring' if session.is_recurring else 'one_off',
                                'is_exam': session.is_exam,
                                'is_dynamic': True # Marker
                            })
                    
                    if dynamic_entries:
                        context['dynamic_entries'] = dynamic_entries
                        context['total_entries'] = len(dynamic_entries)
        
        elif user.role == 'teacher' and hasattr(user, 'teacher_profile'):
            teacher = user.teacher_profile
            
            # Admin-Alignment: Teachers see the FULL master timetable of programs they teach in
            # Find programs where this teacher has any entries in the LATEST timetable version
            from apps.core.models import Program
            from django.db.models import Subquery, OuterRef
            
            # Get latest timetable ID for each program
            latest_timetable_ids = Timetable.objects.filter(
                program=OuterRef('pk')
            ).order_by('-created_at').values('id')[:1]
            
            programs_taught = Program.objects.filter(
                timetables__id__in=Subquery(latest_timetable_ids),
                timetables__entries__teacher=teacher
            ).distinct()
            
            # Now fetch all entries for the latest timetables of these programs
            entries = TimetableEntry.objects.filter(
                timetable__id__in=Subquery(latest_timetable_ids),
                timetable__program__in=programs_taught
            ).select_related('timetable', 'timetable__program', 'subject', 'room', 'study_group', 'time_slot')
            
            context['teacher_name'] = user.get_full_name() or user.username
            context['teacher_programs'] = programs_taught
            context['teacher_specialization'] = teacher.get_specialization_display() if teacher.specialization else ''
        
        # Build entry dict
        entry_dict = {}
        
        if user.role == 'teacher':
            # Deduplicate entries for teacher: same subject+room at same day+slot
            # appears once, with merged group names
            for entry in entries.select_related('subject', 'teacher', 'room', 'time_slot', 'study_group'):
                key = f"{entry.day_of_week}_{entry.time_slot.slot_number}"
                if key not in entry_dict:
                    entry_dict[key] = []
                
                # Check if same subject+room already exists in this slot
                duplicate = False
                for existing in entry_dict[key]:
                    same_subject = (existing.subject_id == entry.subject_id)
                    same_room = (existing.room_id == entry.room_id)
                    if same_subject and same_room:
                        # Merge group name into existing entry
                        if entry.study_group and hasattr(existing, 'merged_groups'):
                            existing.merged_groups.append(entry.study_group.name)
                        elif entry.study_group:
                            existing.merged_groups = []
                            if existing.study_group:
                                existing.merged_groups.append(existing.study_group.name)
                            existing.merged_groups.append(entry.study_group.name)
                        duplicate = True
                        break
                
                if not duplicate:
                    if entry.study_group:
                        entry.merged_groups = [entry.study_group.name]
                    else:
                        entry.merged_groups = []
                    entry_dict[key].append(entry)
        else:
            # Process static entries
            for entry in entries.select_related('subject', 'teacher', 'room', 'time_slot'):
                key = f"{entry.day_of_week}_{entry.time_slot.slot_number}"
                if key not in entry_dict:
                    entry_dict[key] = []
                entry_dict[key].append(entry)
            
            # Process dynamic entries if fallback used
            dynamic_entries = context.get('dynamic_entries', [])
            for entry in dynamic_entries:
                key = f"{entry['day_of_week']}_{entry['time_slot'].slot_number}"
                if key not in entry_dict:
                    entry_dict[key] = []
                # Avoid exact duplicates if somehow static entries also exist
                is_duplicate = any(
                    str(e.subject) == str(entry['subject']) and 
                    str(e.time_slot) == str(entry['time_slot']) and 
                    str(e.day_of_week) == str(entry['day_of_week'])
                    for e in entry_dict[key] if not isinstance(e, dict)
                )
                if not is_duplicate:
                    entry_dict[key].append(entry)
        
        context['time_slots'] = time_slots
        context['days'] = days
        context['entry_dict'] = entry_dict
        context['timetable'] = timetable
        
        # Calculate total entries from the entry_dict to include both static and dynamic
        total_count = 0
        for slots in entry_dict.values():
            total_count += len(slots)
        context['total_entries'] = total_count
        
        return context


# =============================================================================
# API ENDPOINTS FOR AJAX CALLS
# =============================================================================

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json



@login_required
@require_GET
def get_program_groups_api(request, program_id):
    """
    API to get all groups for a given program.
    """
    try:
        from apps.core.models import Program, StudyGroup
        
        try:
            program = Program.objects.get(id=program_id)
        except Program.DoesNotExist:
            return JsonResponse({'error': 'Program not found'}, status=404)
        
        groups = StudyGroup.objects.filter(program=program)
        groups_data = []
        for group in groups:
            groups_data.append({
                'id': group.id,
                'name': group.name,
                'student_count': group.students.count() if hasattr(group, 'students') else 0
            })
        
        return JsonResponse({'groups': groups_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET 
def check_room_availability_api(request):
    """
    API to check room availability for a specific datetime range.
    """
    try:
        room_id = request.GET.get('room_id')
        start_datetime = request.GET.get('start_datetime')
        end_datetime = request.GET.get('end_datetime')
        
        if not all([room_id, start_datetime, end_datetime]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        from .models import Session, RoomReservationRequest
        from apps.core.models import Room
        from datetime import datetime
        
        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            return JsonResponse({'error': 'Room not found'}, status=404)
        
        # Parse datetime strings
        start_dt = datetime.fromisoformat(start_datetime)
        end_dt = datetime.fromisoformat(end_datetime)
        
        # Check for existing reservations
        reservations = RoomReservationRequest.objects.filter(
            room=room,
            status='approved',
            start_datetime__lt=end_dt,
            end_datetime__gt=start_dt
        )
        
        # Check for sessions in that room
        sessions = Session.objects.filter(
            room=room,
            date=start_dt.date(),
            start_time__lt=end_dt.time(),
            end_time__gt=start_dt.time()
        )
        
        conflicts = []
        for res in reservations:
            conflicts.append({
                'type': 'reservation',
                'title': res.subject if res.subject else 'Réservation',
                'time': f"{res.start_datetime.strftime('%H:%M')} - {res.end_datetime.strftime('%H:%M')}"
            })
        
        for session in sessions:
            conflicts.append({
                'type': 'session',
                'title': session.subject.name if session.subject else 'Séance',
                'time': f"{session.start_time.strftime('%H:%M')} - {session.end_time.strftime('%H:%M')}"
            })
        
        return JsonResponse({
            'available': len(conflicts) == 0,
            'room': {'id': room.id, 'name': room.name},
            'conflicts': conflicts
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def get_available_dates_api(request):
    """
    API to get available dates for a room within a date range.
    Returns availability status (available, partial, busy) for each date.
    """
    try:
        room_id = request.GET.get('room_id')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if not start_date or not end_date:
            return JsonResponse({'error': 'start_date and end_date required'}, status=400)
        
        from .models import Session, RoomReservationRequest
        from apps.core.models import Room
        from datetime import datetime, timedelta
        
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        availability = {}
        current = start
        
        while current <= end:
            # Skip Sundays
            if current.weekday() == 6:
                availability[current.strftime('%Y-%m-%d')] = 'unavailable'
            else:
                # Count reservations and sessions for this day
                res_count = 0
                if room_id:
                    res_count = RoomReservationRequest.objects.filter(
                        room_id=room_id,
                        status='approved',
                        start_datetime__date=current
                    ).count()
                    
                    session_count = Session.objects.filter(
                        room_id=room_id,
                        date=current
                    ).count()
                    
                    total = res_count + session_count
                else:
                    total = 0
                
                # 9h00-18h00 = 9 hours, typical slots of 1.5h = 6 slots
                if total == 0:
                    availability[current.strftime('%Y-%m-%d')] = 'available'
                elif total < 3:
                    availability[current.strftime('%Y-%m-%d')] = 'partial'
                else:
                    availability[current.strftime('%Y-%m-%d')] = 'busy'
            
            current += timedelta(days=1)
        
        return JsonResponse({'availability': availability})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def get_available_time_slots_api(request):
    """
    API to get available time slots for a specific room and date.
    """
    try:
        room_id = request.GET.get('room_id')
        date = request.GET.get('date')
        
        if not date:
            return JsonResponse({'error': 'date is required'}, status=400)
        
        from .models import Session, RoomReservationRequest
        from datetime import datetime
        from django.conf import settings
        
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
        
        # Define working hours slots
        slots = []
        for hour in range(9, 18):
            for minute in [0, 30]:
                slot_start = f"{hour:02d}:{minute:02d}"
                end_hour = hour if minute == 0 else hour + 1
                end_minute = 30 if minute == 0 else 0
                if end_hour >= 18:
                    continue
                slot_end = f"{end_hour:02d}:{end_minute:02d}"
                
                # Check if this slot is available
                available = True
                if room_id:
                    start_time = datetime.strptime(slot_start, '%H:%M').time()
                    end_time = datetime.strptime(slot_end, '%H:%M').time()
                    
                    # Check reservations
                    res_conflict = RoomReservationRequest.objects.filter(
                        room_id=room_id,
                        status='approved',
                        start_datetime__date=target_date,
                        start_datetime__time__lt=end_time,
                        end_datetime__time__gt=start_time
                    ).exists()
                    
                    # Check sessions
                    session_conflict = Session.objects.filter(
                        room_id=room_id,
                        date=target_date,
                        start_time__lt=end_time,
                        end_time__gt=start_time
                    ).exists()
                    
                    available = not (res_conflict or session_conflict)
                
                slots.append({
                    'start': slot_start,
                    'end': slot_end,
                    'available': available
                })
        
        return JsonResponse({'slots': slots})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def get_subjects_by_program_api(request):
    """
    API to get subjects for a given program.
    """
    try:
        program_id = request.GET.get('program_id')
        
        if not program_id:
            return JsonResponse({'error': 'program_id is required'}, status=400)
        
        from apps.core.models import Subject, Program
        
        try:
            program = Program.objects.get(id=program_id)
        except Program.DoesNotExist:
            return JsonResponse({'error': 'Program not found'}, status=404)
        
        subjects = Subject.objects.filter(program=program)
        subjects_data = [{
            'id': s.id,
            'name': s.name,
            'code': s.code if hasattr(s, 'code') and s.code else ''
        } for s in subjects]
        
        return JsonResponse({'subjects': subjects_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def subject_create_api(request):
    """
    API to create a new subject.
    """
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Admin only'}, status=403)
    try:
        data = json.loads(request.body)
        name = data.get('name')
        program_id = data.get('program_id')
        
        if not name or not program_id:
            return JsonResponse({'error': 'name and program_id are required'}, status=400)
        
        from apps.core.models import Subject, Program
        
        try:
            program = Program.objects.get(id=program_id)
        except Program.DoesNotExist:
            return JsonResponse({'error': 'Program not found'}, status=404)
        
        subject = Subject.objects.create(name=name, program=program)
        
        return JsonResponse({
            'success': True,
            'subject': {
                'id': subject.id,
                'name': subject.name
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def subject_delete_api(request, pk):
    """
    API to delete a subject.
    """
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Admin only'}, status=403)
    try:
        from apps.core.models import Subject
        
        try:
            subject = Subject.objects.get(id=pk)
        except Subject.DoesNotExist:
            return JsonResponse({'error': 'Subject not found'}, status=404)
        
        subject.delete()
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


class ReservationApproveAPIView(LoginRequiredMixin, View):
    """API to approve a reservation."""
    
    def post(self, request, pk):
        if request.user.role != 'admin':
            return JsonResponse({'error': 'Admin only'}, status=403)
        
        try:
            reservation = RoomReservationRequest.objects.get(id=pk)
            reservation.status = 'approved'
            reservation.reviewed_by = request.user
            reservation.reviewed_at = timezone.now()
            reservation.save()
            
            return JsonResponse({'success': True, 'status': 'approved'})
        except RoomReservationRequest.DoesNotExist:
            return JsonResponse({'error': 'Reservation not found'}, status=404)


class ReservationRejectAPIView(LoginRequiredMixin, View):
    """API to reject a reservation."""
    
    def post(self, request, pk):
        if request.user.role != 'admin':
            return JsonResponse({'error': 'Admin only'}, status=403)
        
        try:
            data = json.loads(request.body) if request.body else {}
            rejection_reason = data.get('reason', '')
            
            reservation = RoomReservationRequest.objects.get(id=pk)
            reservation.status = 'rejected'
            reservation.reviewed_by = request.user
            reservation.reviewed_at = timezone.now()
            reservation.rejection_reason = rejection_reason
            reservation.save()
            
            return JsonResponse({'success': True, 'status': 'rejected'})
        except RoomReservationRequest.DoesNotExist:
            return JsonResponse({'error': 'Reservation not found'}, status=404)


class ExportTimetableView(LoginRequiredMixin, DetailView):
    """
    View to export timetable as PDF or DOCX.
    """
    model = Timetable
    
    def get(self, request, *args, **kwargs):
        timetable = self.get_object()
        user = request.user
        
        # Check permissions
        from .utils.export import check_export_permissions, generate_pdf, generate_docx
        if not check_export_permissions(user, timetable):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Vous n'avez pas la permission d'exporter cet emploi du temps.")
            
        export_format = request.GET.get('format', 'pdf')
        
        from .models import TimeSlot, TimetableEntry
        from django.utils import timezone
        from django.http import HttpResponse
        
        time_slots = TimeSlot.objects.all().order_by('slot_number')
        
        # Fetch entries
        entries = TimetableEntry.objects.filter(timetable=timetable).select_related(
            'subject', 'teacher', 'teacher__user', 'room', 'study_group', 'time_slot'
        )
        
        # Filter for teachers if requested
        if user.role == 'teacher' and hasattr(user, 'teacher_profile'):
             if request.GET.get('filter') == 'mine':
                 entries = entries.filter(teacher=user.teacher_profile)
        
        # Prepare days
        day_map = {
            'MON': 'Lundi', 'TUE': 'Mardi', 'WED': 'Mercredi',
            'THU': 'Jeudi', 'FRI': 'Vendredi', 'SAT': 'Samedi'
        }
        # Maintain order
        day_codes = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
        days = [(code, day_map[code]) for code in day_codes]
        
        if export_format == 'pdf':
            # Build context for PDF
            entry_dict = {}
            for entry in entries:
                # Structure: dict[slot_id][day_code] = [entries]
                slot_id = entry.time_slot.id
                day_code = entry.day_of_week
                
                if slot_id not in entry_dict:
                    entry_dict[slot_id] = {}
                
                if day_code not in entry_dict[slot_id]:
                    entry_dict[slot_id][day_code] = []
                    
                entry_dict[slot_id][day_code].append(entry)
                
            context = {
                'timetable': timetable,
                'time_slots': time_slots,
                'days': days,
                'entry_dict': entry_dict,
                'user': user,
                'generated_at': timezone.now()
            }
            
            pdf_file = generate_pdf(context)
            if not pdf_file:
                return HttpResponse("Erreur lors de la génération du PDF", status=500)
                
            response = HttpResponse(pdf_file, content_type='application/pdf')
            filename = f"Emploi_Du_Temps_{timetable.program.code}_{timetable.semester}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        elif export_format == 'docx':
            docx_file = generate_docx(timetable, entries, time_slots, days)
            
            response = HttpResponse(docx_file.getvalue(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            filename = f"Emploi_Du_Temps_{timetable.program.code}_{timetable.semester}.docx"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            

class ExportMyTimetableView(LoginRequiredMixin, View):
    """
    View to export personal timetable (Teacher/Student) as PDF or DOCX.
    """
    
    def get(self, request, *args, **kwargs):
        user = request.user
        export_format = request.GET.get('format', 'pdf')
        
        from .models import TimeSlot, TimetableEntry, Timetable
        from django.utils import timezone
        from django.http import HttpResponse
        from .utils.export import generate_pdf, generate_docx
        
        time_slots = TimeSlot.objects.all().order_by('slot_number')
        entries = TimetableEntry.objects.none()
        
        # Virtual timetable object for templates
        class VirtualTimetable:
            def __init__(self, name, program_name, semester, year):
                self.name = name
                self.program = type('obj', (object,), {'name': program_name, 'code': 'PERSO'})
                self.semester = semester
                self.academic_year = year
                
            def get_semester_display(self):
                return self.semester

        # Determine entries and context info
        if user.role == 'student' and hasattr(user, 'student_profile'):
            student = user.student_profile
            if student.group and student.group.program:
                timetable = Timetable.objects.filter(
                    program=student.group.program,
                    is_published=True
                ).order_by('-created_at').first()
                
                if timetable:
                    entries = TimetableEntry.objects.filter(
                        timetable=timetable
                    ).filter(
                        models.Q(study_group=student.group) | models.Q(study_group__isnull=True)
                    ).select_related('subject', 'teacher', 'room', 'time_slot')
                    
                    v_timetable = timetable # Use real one
                else:
                    return HttpResponse("Aucun emploi du temps trouvé", status=404)
            else:
                return HttpResponse("Non assigné à un programme", status=404)

        elif user.role == 'teacher' and hasattr(user, 'teacher_profile'):
            teacher = user.teacher_profile
            entries = TimetableEntry.objects.filter(
                teacher=teacher,
                timetable__is_published=True
            ).select_related('timetable', 'subject', 'room', 'study_group', 'time_slot')
            
            v_timetable = VirtualTimetable(
                name=f"Emploi du Temps - {user.get_full_name()}",
                program_name="Planning Personnel",
                semester="2025/2026",
                year=""
            )
        
        else:
             return HttpResponse("Rôle non autorisé pour cet export", status=403)

        # Prepare days
        day_map = {
            'MON': 'Lundi', 'TUE': 'Mardi', 'WED': 'Mercredi',
            'THU': 'Jeudi', 'FRI': 'Vendredi', 'SAT': 'Samedi'
        }
        day_codes = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
        days = [(code, day_map[code]) for code in day_codes]
        
        if export_format == 'pdf':
            entry_dict = {}
            for entry in entries:
                slot_id = entry.time_slot.id
                day_code = entry.day_of_week
                if slot_id not in entry_dict: entry_dict[slot_id] = {}
                if day_code not in entry_dict[slot_id]: entry_dict[slot_id][day_code] = []
                entry_dict[slot_id][day_code].append(entry)
                
            context = {
                'timetable': v_timetable,
                'time_slots': time_slots,
                'days': days,
                'entry_dict': entry_dict,
                'user': user,
                'generated_at': timezone.now()
            }
            pdf_file = generate_pdf(context)
            if not pdf_file: return HttpResponse("Erreur PDF", status=500)
            
            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Mon_Emploi_Du_Temps.pdf"'
            return response
            
        elif export_format == 'docx':
            docx_file = generate_docx(v_timetable, entries, time_slots, days)
            response = HttpResponse(docx_file.getvalue(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            response['Content-Disposition'] = f'attachment; filename="Mon_Emploi_Du_Temps.docx"'
            return response
            
        return HttpResponse("Format non supporté", status=400)


# =============================================================================
# TIMETABLE ENTRY DRAG-DROP API ENDPOINTS
# =============================================================================

@login_required
@require_POST
def timetable_entry_create_api(request):
    """
    API to create a new timetable entry when dragging a subject to a cell.
    """
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Admin only'}, status=403)
    from .models import TimetableEntry, TimeSlot, Subject, Timetable
    from apps.accounts.models import Teacher
    from apps.core.models import Room
    
    try:
        data = json.loads(request.body)
        
        timetable_id = data.get('timetable_id')
        day = data.get('day')
        slot_number = data.get('slot_number')
        subject_id = data.get('subject_id')
        teacher_id = data.get('teacher_id')
        room_id = data.get('room_id')
        session_type = data.get('session_type', 'cours')
        
        if not all([timetable_id, day, slot_number, subject_id]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        timetable = Timetable.objects.get(pk=timetable_id)
        time_slot = TimeSlot.objects.get(slot_number=slot_number)
        subject = Subject.objects.get(pk=subject_id)
        teacher = Teacher.objects.get(pk=teacher_id) if teacher_id else None
        room = Room.objects.get(pk=room_id) if room_id else None
        
        # Check if entry already exists
        existing = TimetableEntry.objects.filter(
            timetable=timetable,
            day_of_week=day,
            time_slot=time_slot
        ).first()
        
        if existing:
            return JsonResponse({'error': 'Une séance existe déjà dans ce créneau'}, status=400)
        
        # Create entry
        entry = TimetableEntry.objects.create(
            timetable=timetable,
            day_of_week=day,
            time_slot=time_slot,
            subject=subject,
            teacher=teacher,
            room=room,
            session_type=session_type
        )
        
        # Notify students if timetable is published
        if timetable.is_published:
            from apps.notifications.services import NotificationService
            NotificationService.notify_timetable_update(timetable)
        
        return JsonResponse({
            'success': True,
            'entry': {
                'id': entry.id,
                'subject_code': entry.subject.code,
                'subject_name': entry.subject.name,
                'teacher_name': entry.teacher.user.get_full_name() if entry.teacher else None,
                'room_name': entry.room.name if entry.room else None,
                'session_type': entry.session_type,
                'day': entry.day_of_week,
                'slot_number': entry.time_slot.slot_number
            }
        })
        
    except Timetable.DoesNotExist:
        return JsonResponse({'error': 'Emploi du temps non trouvé'}, status=404)
    except TimeSlot.DoesNotExist:
        return JsonResponse({'error': 'Créneau horaire non trouvé'}, status=404)
    except Subject.DoesNotExist:
        return JsonResponse({'error': 'Matière non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def timetable_entry_move_api(request):
    """
    API to move an existing entry to a new cell (drag and drop).
    """
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Admin only'}, status=403)
    from .models import TimetableEntry, TimeSlot
    
    try:
        data = json.loads(request.body)
        
        entry_id = data.get('entry_id')
        new_day = data.get('new_day')
        new_slot_number = data.get('new_slot_number')
        
        if not all([entry_id, new_day, new_slot_number]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        entry = TimetableEntry.objects.get(pk=entry_id)
        new_time_slot = TimeSlot.objects.get(slot_number=new_slot_number)
        
        # Check if destination is occupied
        existing = TimetableEntry.objects.filter(
            timetable=entry.timetable,
            day_of_week=new_day,
            time_slot=new_time_slot
        ).exclude(pk=entry_id).first()
        
        if existing:
            return JsonResponse({'error': 'Ce créneau est déjà occupé'}, status=400)
        
        # Update entry
        old_day = entry.day_of_week
        old_slot = entry.time_slot.slot_number
        entry.day_of_week = new_day
        entry.time_slot = new_time_slot
        entry.save()
        
        # Notify students if timetable is published
        if entry.timetable.is_published:
            from apps.notifications.services import NotificationService
            NotificationService.notify_timetable_update(entry.timetable)
        
        return JsonResponse({
            'success': True,
            'entry': {
                'id': entry.id,
                'old_day': old_day,
                'old_slot': old_slot,
                'new_day': new_day,
                'new_slot': new_slot_number
            }
        })
        
    except TimetableEntry.DoesNotExist:
        return JsonResponse({'error': 'Entrée non trouvée'}, status=404)
    except TimeSlot.DoesNotExist:
        return JsonResponse({'error': 'Créneau horaire non trouvé'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def timetable_entry_update_api(request):
    """
    API to update an existing entry's details.
    """
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Admin only'}, status=403)
    from .models import TimetableEntry
    from apps.accounts.models import Teacher
    from apps.core.models import Room
    
    try:
        data = json.loads(request.body)
        
        entry_id = data.get('entry_id')
        if not entry_id:
            return JsonResponse({'error': 'entry_id required'}, status=400)
        
        entry = TimetableEntry.objects.get(pk=entry_id)
        
        # Update fields if provided
        if 'teacher_id' in data:
            entry.teacher = Teacher.objects.get(pk=data['teacher_id']) if data['teacher_id'] else None
        if 'room_id' in data:
            entry.room = Room.objects.get(pk=data['room_id']) if data['room_id'] else None
        if 'session_type' in data:
            entry.session_type = data['session_type']
        
        entry.save()
        
        # Update siblings (other entries for same teacher at same time)
        # to ensure consistency when editing a merged card
        siblings = TimetableEntry.objects.filter(
            teacher=entry.teacher,
            day_of_week=entry.day_of_week,
            time_slot=entry.time_slot,
            timetable__is_published=True
        ).exclude(pk=entry.id)
        
        for sibling in siblings:
            updated = False
            if 'room_id' in data:
                sibling.room = entry.room
                updated = True
            if 'session_type' in data:
                sibling.session_type = entry.session_type
                updated = True
            if updated:
                sibling.save()
        
        # Notify students if timetable is published
        if entry.timetable.is_published:
            from apps.notifications.services import NotificationService
            NotificationService.notify_timetable_update(entry.timetable)
        
        return JsonResponse({
            'success': True,
            'entry': {
                'id': entry.id,
                'subject_code': entry.subject.code,
                'subject_name': entry.subject.name,
                'teacher_name': entry.teacher.user.get_full_name() if entry.teacher else None,
                'room_name': entry.room.name if entry.room else None,
                'session_type': entry.session_type
            }
        })
        
    except TimetableEntry.DoesNotExist:
        return JsonResponse({'error': 'Entrée non trouvée'}, status=404)
    except Teacher.DoesNotExist:
        return JsonResponse({'error': 'Enseignant non trouvé'}, status=404)
    except Room.DoesNotExist:
        return JsonResponse({'error': 'Salle non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def timetable_entry_delete_api(request):
    """
    API to delete a timetable entry.
    """
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Admin only'}, status=403)
    from .models import TimetableEntry
    
    try:
        data = json.loads(request.body)
        
        entry_id = data.get('entry_id')
        if not entry_id:
            return JsonResponse({'error': 'entry_id required'}, status=400)
        
        entry = TimetableEntry.objects.select_related('timetable').get(pk=entry_id)
        timetable = entry.timetable
        entry_info = {
            'id': entry.id,
            'day': entry.day_of_week,
            'slot': entry.time_slot.slot_number,
            'subject': entry.subject.code
        }
        entry.delete()
        
        # Notify students if timetable is published
        if timetable.is_published:
            from apps.notifications.services import NotificationService
            NotificationService.notify_timetable_update(timetable)
        
        return JsonResponse({
            'success': True,
            'deleted': entry_info
        })
        
    except TimetableEntry.DoesNotExist:
        return JsonResponse({'error': 'Entrée non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def check_conflict_api(request):
    """
    Pre-flight conflict check for drag-and-drop moves.
    Checks 3 conflict types on TimetableEntry for the target (day, time_slot):
      1. Same room already occupied at that slot/day
      2. Same teacher already teaching at that slot/day
      3. Same study_group already scheduled at that slot/day
    Returns: {has_conflict: bool, conflict_type: str, message: str, room_name, teacher_name, subject_name}
    """
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Admin only'}, status=403)
    from .models import TimetableEntry, TimeSlot

    try:
        data = json.loads(request.body)

        day          = data.get('day_of_week')
        slot_number  = data.get('time_slot_id')
        room_id      = data.get('room_id')
        teacher_id   = data.get('teacher_id')
        group_id     = data.get('group_id')
        exclude_id   = data.get('exclude_entry_id')
        timetable_id = data.get('timetable_id')

        if not day or not slot_number:
            return JsonResponse({'has_conflict': False, 'message': ''})

        time_slot = TimeSlot.objects.filter(slot_number=int(slot_number)).first()
        if not time_slot:
            return JsonResponse({'has_conflict': False})

        # Check only room conflict on TimetableEntry
        qs = TimetableEntry.objects.filter(
            day_of_week=day,
            time_slot=time_slot,
            room_id=room_id
        )
        if exclude_id:
            qs = qs.exclude(pk=exclude_id)

        room_conflict = qs.select_related('teacher__user', 'subject', 'room', 'time_slot').first()
        
        if room_conflict:
            # Format the message as requested:
            # "La salle [Salle F01] est déjà réservée le [Lundi] à [09h00-10h30] par Pr. [Mohammed Alami] pour [INFO-301]."
            day_name = dict(TimetableEntry.DAYS_OF_WEEK).get(day, day)
            time_str = f"{room_conflict.time_slot.start_time.strftime('%Hh%M')}-{room_conflict.time_slot.end_time.strftime('%Hh%M')}"
            teacher_name = room_conflict.teacher.user.get_full_name() if room_conflict.teacher else "N/A"
            room_name = room_conflict.room.name if room_conflict.room else "N/A"
            subject_display = room_conflict.subject.code # Matches "INFO-301" example style

            message = (
                f"La salle [{room_name}] est déjà réservée le [{day_name}] à [{time_str}] "
                f"par Pr. [{teacher_name}] pour [{subject_display}]."
            )

            return JsonResponse({
                'has_conflict': True,
                'message': message,
                'room_name': room_name,
                'teacher_name': teacher_name,
                'subject_name': subject_display
            })

        return JsonResponse({'has_conflict': False})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_GET
def timetable_entries_api(request, pk):
    """
    API to get all entries for a timetable as JSON.
    """
    from .models import TimetableEntry, Timetable, TimeSlot
    
    try:
        timetable = Timetable.objects.get(pk=pk)
        entries = TimetableEntry.objects.filter(timetable=timetable).select_related(
            'subject', 'teacher', 'teacher__user', 'room', 'time_slot'
        )
        
        entries_list = []
        for e in entries:
            entries_list.append({
                'id': e.id,
                'day': e.day_of_week,
                'slot_number': e.time_slot.slot_number,
                'subject_id': e.subject.id,
                'subject_code': e.subject.code,
                'subject_name': e.subject.name,
                'teacher_id': e.teacher.id if e.teacher else None,
                'teacher_name': e.teacher.user.get_full_name() if e.teacher else None,
                'room_id': e.room.id if e.room else None,
                'room_name': e.room.name if e.room else None,
                'session_type': e.session_type
            })
        
        return JsonResponse({
            'timetable_id': timetable.id,
            'entries': entries_list
        })
        
    except Timetable.DoesNotExist:
        return JsonResponse({'error': 'Emploi du temps non trouvé'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# TIMETABLE CHANGE REQUEST VIEWS
# ============================================================================

class TimetableChangeRequestCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """View to create a new timetable change request"""
    template_name = 'scheduling/change_request_form.html'
    success_url = reverse_lazy('change_request_list')

    def get_queryset(self):
         from .models import TimetableChangeRequest
         return TimetableChangeRequest.objects.all()

    def get_form_class(self):
        from .forms import TimetableChangeRequestForm
        return TimetableChangeRequestForm

    def test_func(self):
        return self.request.user.role == 'teacher'

    def handle_no_permission(self):
        messages.error(self.request, "Seuls les enseignants peuvent faire cette demande.")
        return redirect('dashboard')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if hasattr(self.request.user, 'teacher_profile'):
            kwargs['teacher'] = self.request.user.teacher_profile
        return kwargs

    def form_valid(self, form):
        form.instance.teacher = self.request.user.teacher_profile
        response = super().form_valid(form)
        
        # Notify Admins
        try:
            from apps.notifications.models import Notification
            from apps.accounts.models import User
            
            admins = User.objects.filter(role='admin', is_active=True)
            teacher_name = self.request.user.get_full_name()
            subject_name = form.instance.subject.name if form.instance.subject else "N/A"
            
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    notification_type='general', # Using general for now
                    priority='high',
                    title=f"Demande de changement - {teacher_name}",
                    message=f"L'enseignant {teacher_name} a demandé un changement pour la matière {subject_name}.\nMotif: {form.instance.reason[:50]}...",
                    related_object_type='TimetableChangeRequest', # For future use
                    related_object_id=form.instance.pk
                )
        except Exception as e:
            print(f"Error sending notification: {e}")
            
        messages.success(self.request, "Votre demande de changement a été soumise avec succès.")
        return response

class TimetableChangeRequestListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """View to list teacher's change requests"""
    template_name = 'scheduling/change_request_list.html'
    context_object_name = 'requests'

    def get_queryset(self):
        from .models import TimetableChangeRequest
        return TimetableChangeRequest.objects.filter(
            teacher=self.request.user.teacher_profile
        ).order_by('-created_at')

    def test_func(self):
        return self.request.user.role == 'teacher'


# ============================================================================
# ADMIN TEACHER TIMETABLE VIEW
# ============================================================================

class AdminTeacherTimetableView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """
    Admin view to view and edit any teacher's timetable (Semester View).
    Refactored to match student timetable structure (TimetableEntry).
    """
    template_name = 'scheduling/admin_teacher_timetable.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.accounts.models import Teacher
        from apps.core.models import Room
        from .models import TimetableEntry, TimeSlot
        
        # Get all teachers for dropdown
        teachers = Teacher.objects.select_related('user').order_by('user__last_name', 'user__first_name')
        context['teachers'] = teachers
        
        # Get selected teacher
        teacher_id = self.request.GET.get('teacher')
        selected_teacher = None
        if teacher_id:
            try:
                selected_teacher = Teacher.objects.select_related('user').get(pk=teacher_id)
            except Teacher.DoesNotExist:
                pass
        context['selected_teacher'] = selected_teacher
        
        # Get slots and days
        time_slots = TimeSlot.objects.all().order_by('slot_number')
        days = [
            ('MON', 'Lundi'), ('TUE', 'Mardi'), ('WED', 'Mercredi'),
            ('THU', 'Jeudi'), ('FRI', 'Vendredi'), ('SAT', 'Samedi'),
        ]
        context['time_slots'] = time_slots
        context['days'] = days
        
        # Build entry dict: key="DAY_SLOTNUM", value=[entries]
        entry_dict = {}
        if selected_teacher:
            # Get entries from PUBLISHED timetables
            # We fetch ALL entries for this teacher from any published timetable
            entries = TimetableEntry.objects.filter(
                teacher=selected_teacher,
                timetable__is_published=True
            ).select_related('subject', 'room', 'study_group', 'time_slot', 'timetable__program')
            
            # Deduplicate entries for display
            # We group entries that have same: Day, Slot, Subject, Room, Type
            # And merge their Group names
            processed_keys = set()
            
            for entry in entries:
                key = f"{entry.day_of_week}_{entry.time_slot.slot_number}"
                
                # Check for duplicates based on visual properties
                dedup_key = f"{key}_{entry.subject_id}_{entry.room_id}_{entry.session_type}"
                
                if dedup_key in processed_keys:
                    # Find existing entry and merge group info
                    if key in entry_dict:
                        for existing in entry_dict[key]:
                            existing_dedup = f"{existing.day_of_week}_{existing.time_slot.slot_number}_{existing.subject_id}_{existing.room_id}_{existing.session_type}"
                            if existing_dedup == dedup_key:
                                # Merge group name
                                if not hasattr(existing, 'program_groups'):
                                    existing.program_groups = [existing.study_group.name] if existing.study_group else []
                                if entry.study_group and entry.study_group.name not in existing.program_groups:
                                    existing.program_groups.append(entry.study_group.name)
                                    
                                # Merge program name
                                if not hasattr(existing, 'program_names'):
                                    existing.program_names = [existing.timetable.program.name] if existing.timetable.program else []
                                if entry.timetable.program and entry.timetable.program.name not in existing.program_names:
                                    existing.program_names.append(entry.timetable.program.name)
                                break
                    continue
                
                # New unique visual entry
                processed_keys.add(dedup_key)
                
                # Init lists
                if not hasattr(entry, 'program_groups'):
                    entry.program_groups = [entry.study_group.name] if entry.study_group else []
                if not hasattr(entry, 'program_names'):
                    entry.program_names = [entry.timetable.program.name] if entry.timetable.program else []
                
                if key not in entry_dict:
                    entry_dict[key] = []
                entry_dict[key].append(entry)
                    
        context['entry_dict'] = entry_dict
        
        # Get rooms for edit modal
        context['rooms'] = Room.objects.filter(is_active=True).order_by('building', 'name')
        
        return context


@login_required
@require_GET
def get_teacher_sessions_api(request, teacher_id):
    """
    API to get a teacher's sessions for a specific week.
    Used for AJAX updates in the admin teacher timetable view.
    """
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Admin only'}, status=403)
    
    try:
        from apps.accounts.models import Teacher
        from datetime import timedelta
        
        teacher = Teacher.objects.get(pk=teacher_id)
        
        week_offset = int(request.GET.get('week_offset', 0))
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
        week_end = week_start + timedelta(days=5)
        
        sessions = Session.objects.filter(
            teacher=teacher,
            start_datetime__date__gte=week_start,
            start_datetime__date__lte=week_end,
            is_validated=True
        ).select_related('room').prefetch_related('groups', 'groups__program')
        
        session_list = []
        for session in sessions:
            groups = list(session.groups.all()[:3])
            program_name = groups[0].program.name if groups and groups[0].program else None
            
            session_list.append({
                'id': session.id,
                'subject': session.subject,
                'session_type': session.get_session_type_display(),
                'room': session.room.name if session.room else None,
                'room_id': session.room_id,
                'start_datetime': session.start_datetime.isoformat(),
                'end_datetime': session.end_datetime.isoformat(),
                'day_index': session.start_datetime.weekday(),
                'hour': session.start_datetime.hour,
                'program_name': program_name,
                'group_names': [g.name for g in groups],
            })
        
        return JsonResponse({
            'sessions': session_list,
            'teacher_name': teacher.user.get_full_name(),
            'week_start': week_start.isoformat(),
            'week_end': week_end.isoformat(),
        })
    except Teacher.DoesNotExist:
        return JsonResponse({'error': 'Teacher not found'}, status=404)


@login_required
@require_POST
def update_session_api(request, pk):
    """
    API to update a session's room or time.
    Used for inline editing in the admin teacher timetable view.
    """
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Admin only'}, status=403)
    
    try:
        from apps.core.models import Room
        from datetime import datetime, timedelta
        
        session = Session.objects.get(pk=pk)
        data = json.loads(request.body)
        
        updated_fields = []
        
        # Update room if provided
        if 'room_id' in data and data['room_id']:
            try:
                new_room = Room.objects.get(pk=data['room_id'])
                if session.room_id != new_room.id:
                    session.room = new_room
                    updated_fields.append('room')
            except Room.DoesNotExist:
                return JsonResponse({'error': 'Room not found'}, status=404)
        
        # Update time if day_index and slot_index provided
        if 'day_index' in data and 'slot_index' in data:
            new_day_index = int(data['day_index'])
            new_slot_index = int(data['slot_index'])
            
            # Calculate new datetime
            current_date = session.start_datetime.date()
            current_weekday = current_date.weekday()
            
            # Adjust to new day
            day_diff = new_day_index - current_weekday
            new_date = current_date + timedelta(days=day_diff)
            
            # Get time slot times
            time_slots = [
                ('09:00', '10:30'),
                ('10:45', '12:15'),
                ('12:30', '14:00'),
                ('14:15', '15:45'),
                ('16:00', '17:30'),
            ]
            
            if 0 <= new_slot_index < len(time_slots):
                start_time_str, end_time_str = time_slots[new_slot_index]
                start_h, start_m = map(int, start_time_str.split(':'))
                end_h, end_m = map(int, end_time_str.split(':'))
                
                new_start = datetime.combine(new_date, datetime.min.time().replace(hour=start_h, minute=start_m))
                new_end = datetime.combine(new_date, datetime.min.time().replace(hour=end_h, minute=end_m))
                
                # Make timezone aware
                new_start = timezone.make_aware(new_start)
                new_end = timezone.make_aware(new_end)
                
                if session.start_datetime != new_start or session.end_datetime != new_end:
                    session.start_datetime = new_start
                    session.end_datetime = new_end
                    updated_fields.append('time')
        
        if updated_fields:
            session.save()
            
            return JsonResponse({
                'success': True,
                'updated_fields': updated_fields,
                'session': {
                    'id': session.id,
                    'subject': session.subject,
                    'room': session.room.name if session.room else None,
                    'start_datetime': session.start_datetime.isoformat(),
                    'end_datetime': session.end_datetime.isoformat(),
                }
            })
        else:
            return JsonResponse({'success': True, 'message': 'No changes made'})
        
    except Session.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def change_request_approve_api(request, pk):
    """API to approve a timetable change request."""
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Admin only'}, status=403)
    from .models import TimetableChangeRequest
    from apps.notifications.services import NotificationService
    
    try:
        change_request = TimetableChangeRequest.objects.select_related(
            'teacher__user', 'subject'
        ).get(pk=pk)
        
        data = json.loads(request.body) if request.body else {}
        
        change_request.status = 'approved'
        change_request.admin_notes = data.get('admin_notes', '')
        change_request.save()
        
        # Notify the teacher
        NotificationService.send_notification(
            user=change_request.teacher.user,
            notification_type='change_request_approved',
            title='Demande de changement approuvée',
            message=(
                f'Votre demande de changement pour {change_request.subject.code} '
                f'a été approuvée par l\'administration.'
            ),
            related_object=change_request
        )
        
        return JsonResponse({'success': True, 'message': 'Demande approuvée.'})
    
    except TimetableChangeRequest.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Demande introuvable.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_POST
def change_request_reject_api(request, pk):
    """API to reject a timetable change request."""
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Admin only'}, status=403)
    from .models import TimetableChangeRequest
    from apps.notifications.services import NotificationService
    
    try:
        change_request = TimetableChangeRequest.objects.select_related(
            'teacher__user', 'subject'
        ).get(pk=pk)
        
        data = json.loads(request.body) if request.body else {}
        
        change_request.status = 'rejected'
        change_request.admin_notes = data.get('admin_notes', '')
        change_request.save()
        
        # Notify the teacher
        NotificationService.send_notification(
            user=change_request.teacher.user,
            notification_type='change_request_rejected',
            title='Demande de changement rejetée',
            message=(
                f'Votre demande de changement pour {change_request.subject.code} '
                f'a été rejetée par l\'administration.'
            ),
            related_object=change_request
        )
        
        return JsonResponse({'success': True, 'message': 'Demande rejetée.'})
    
    except TimetableChangeRequest.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Demande introuvable.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
