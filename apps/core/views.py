"""
Views for core app.
Includes bulk room creation, contact form, and room management.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import (
    CreateView, ListView, DetailView, UpdateView, 
    DeleteView, FormView, TemplateView
)
from django.urls import reverse_lazy
from django import forms
from django.db import models

from .models import Room, Equipment, Program, Group, ContactMessage
from .forms import BulkRoomCreateForm, ContactForm, ContactResponseForm, RoomForm


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require admin role"""
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'admin'


class BulkRoomCreateView(LoginRequiredMixin, AdminRequiredMixin, FormView):
    """
    View for creating multiple rooms at once.
    Admin only.
    """
    
    form_class = BulkRoomCreateForm
    template_name = 'core/bulk_room_create.html'
    success_url = reverse_lazy('room_list')
    
    def form_valid(self, form):
        prefix = form.cleaned_data['room_prefix']
        start = form.cleaned_data['start_number']
        end = form.cleaned_data['end_number']
        building = form.cleaned_data['building']
        room_type = form.cleaned_data['room_type']
        capacity = form.cleaned_data['capacity']
        floor = form.cleaned_data['floor']
        equipment_list = form.cleaned_data['equipment']
        
        # Create rooms in bulk
        rooms_to_create = []
        for num in range(start, end + 1):
            rooms_to_create.append(Room(
                name=f"{prefix}{num}",
                building=building,
                room_type=room_type,
                capacity=capacity,
                floor=floor,
                is_active=True
            ))
        
        # Use Django's bulk_create for efficiency
        created_rooms = Room.objects.bulk_create(rooms_to_create)
        
        # Add equipment to all created rooms
        for room in created_rooms:
            room.equipment.set(equipment_list)
        
        messages.success(
            self.request,
            f"{len(created_rooms)} salles créées avec succès ({prefix}{start} à {prefix}{end})"
        )
        
        return super().form_valid(form)


class RoomListView(ListView):
    """List all rooms with real-time availability status"""
    
    model = Room
    template_name = 'core/room_list.html'
    context_object_name = 'rooms'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Room.objects.filter(is_active=True).prefetch_related('equipment')
        
        # Filter by building
        building = self.request.GET.get('building')
        if building:
            queryset = queryset.filter(building__icontains=building)
        
        # Filter by type
        room_type = self.request.GET.get('type')
        if room_type:
            queryset = queryset.filter(room_type=room_type)
        
        # Filter by capacity
        min_capacity = self.request.GET.get('min_capacity')
        if min_capacity:
            queryset = queryset.filter(capacity__gte=min_capacity)
        
        # Filter by equipment (multiple checkboxes - AND logic)
        equipment_ids = self.request.GET.getlist('equipment')
        if equipment_ids:
            for equipment_id in equipment_ids:
                queryset = queryset.filter(equipment__id=equipment_id)
        
        return queryset.distinct().order_by('building', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['room_types'] = Room.ROOM_TYPE_CHOICES
        context['buildings'] = Room.objects.values_list('building', flat=True).distinct()
        
        # Add equipment list for checkbox filter
        context['equipments'] = Equipment.objects.all()
        
        # Get selected equipment IDs for maintaining checkbox state
        equipment_ids = self.request.GET.getlist('equipment')
        context['selected_equipments'] = [int(e) for e in equipment_ids if e.isdigit()]
        
        # Calculate status for each room in the current page
        from django.utils import timezone
        from apps.scheduling.models import Session
        
        now = timezone.now()
        
        # Get the actual list of rooms (works with pagination)
        rooms = context.get('object_list', context.get('rooms', []))
        
        for room in rooms:
            # Find current session
            current_session = Session.objects.filter(
                room=room,
                start_datetime__lte=now,
                end_datetime__gt=now,
                is_validated=True
            ).select_related('teacher__user').prefetch_related('groups').first()
            
            # Find next session today
            next_session = Session.objects.filter(
                room=room,
                start_datetime__gt=now,
                start_datetime__date=now.date(),
                is_validated=True
            ).select_related('teacher__user').prefetch_related('groups').order_by('start_datetime').first()
            
            # Set simple attributes directly on room object
            room.status_available = not current_session
            room.status_current = current_session
            room.status_next = next_session
            room.status_minutes = 0
            
            if current_session:
                time_remaining = current_session.end_datetime - now
                room.status_minutes = int(time_remaining.total_seconds() / 60)
        
        context['current_time'] = now
        return context



class RoomDetailView(DetailView):
    """View room details with real-time availability timeline"""
    
    model = Room
    template_name = 'core/room_detail.html'
    context_object_name = 'room'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        room = self.object
        user = self.request.user
        
        from datetime import datetime, timedelta, time, date
        from django.utils import timezone
        from apps.scheduling.models import Session
        
        # Get selected date (admin can pick any date, others see today)
        if user.is_authenticated and user.role == 'admin':
            selected_date_str = self.request.GET.get('date')
            if selected_date_str:
                try:
                    selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
                except ValueError:
                    selected_date = timezone.now().date()
            else:
                selected_date = timezone.now().date()
        else:
            selected_date = timezone.now().date()
        
        context['selected_date'] = selected_date
        context['today'] = timezone.now().date()
        context['current_time'] = timezone.now()
        
        # Generate hourly timeline (9:00 - 18:00)
        time_slots = []
        current_hour = timezone.now().hour
        current_minute = timezone.now().minute
        
        for hour in range(9, 18):
            slot_start = datetime.combine(selected_date, time(hour, 0))
            slot_end = datetime.combine(selected_date, time(hour + 1, 0))
            
            # Find session at this hour
            session = Session.objects.filter(
                room=room,
                start_datetime__date=selected_date,
                start_datetime__hour__lte=hour,
                end_datetime__hour__gt=hour,
                is_validated=True
            ).first()
            
            # Check pending reservations
            from apps.scheduling.models import RoomReservationRequest
            pending = RoomReservationRequest.objects.filter(
                room=room,
                start_datetime__date=selected_date,
                start_datetime__hour__lte=hour,
                status='pending'
            ).first()
            
            # Determine status
            is_current = (selected_date == timezone.now().date() and hour == current_hour)
            is_past = (selected_date == timezone.now().date() and hour < current_hour)
            
            if session:
                status = 'exam' if session.session_type == 'exam' else 'occupied'
                status_class = 'bg-danger' if session.session_type == 'exam' else 'bg-warning'
            elif pending:
                status = 'pending'
                status_class = 'bg-info'
            else:
                status = 'available'
                status_class = 'bg-success'
            
            time_slots.append({
                'hour': hour,
                'start_time': f'{hour:02d}:00',
                'end_time': f'{hour + 1:02d}:00',
                'is_available': status == 'available',
                'is_current': is_current,
                'is_past': is_past,
                'session': session,
                'pending': pending,
                'status': status,
                'status_class': status_class,
                'course_name': session.subject if session else None,
                'teacher_name': session.teacher.user.get_full_name() if session and session.teacher else None,
                'groups': ', '.join([g.name for g in session.groups.all()]) if session else None,
            })
        
        context['time_slots'] = time_slots
        
        # Calculate current status
        now = timezone.now()
        if selected_date == now.date() and 9 <= now.hour < 18:
            current_slot = next((s for s in time_slots if s['hour'] == now.hour), None)
            if current_slot:
                context['current_status'] = current_slot
        
        # Calculate position for current time line (pixels from top)
        # 60px per hour slot
        if selected_date == now.date() and 9 <= now.hour < 18:
            hour_offset = now.hour - 9
            minute_fraction = now.minute / 60
            context['current_time_position'] = (hour_offset + minute_fraction) * 63
        else:
            context['current_time_position'] = -1

        # Additional stats for redesigned template
        # 1. Upcoming reservations
        context['upcoming_reservations'] = RoomReservationRequest.objects.filter(
            room=room,
            start_datetime__gte=now,
            status='approved'
        ).order_by('start_datetime')[:5]
        
        # 2. Weekly reservations count
        start_of_week = now.date() - timedelta(days=now.weekday())
        context['weekly_reservations'] = Session.objects.filter(
            room=room,
            start_datetime__date__gte=start_of_week,
            is_validated=True
        ).count() + RoomReservationRequest.objects.filter(
            room=room,
            start_datetime__date__gte=start_of_week,
            status='approved'
        ).count()
        
        # 3. Monthly hours
        start_of_month = now.date().replace(day=1)
        sessions = Session.objects.filter(
            room=room,
            start_datetime__date__gte=start_of_month,
            is_validated=True
        )
        total_seconds = sum([(s.end_datetime - s.start_datetime).total_seconds() for s in sessions])
        reservations = RoomReservationRequest.objects.filter(
            room=room,
            start_datetime__date__gte=start_of_month,
            status='approved'
        )
        total_seconds += sum([(r.end_datetime - r.start_datetime).total_seconds() for r in reservations])
        context['monthly_hours'] = int(total_seconds // 3600)
        
        # 4. Occupancy Rate (approximate based on 9h-18h slots for 5 days a week = 45h)
        # We'll use the last 30 days as a baseline
        month_hours_capacity = 45 * 4 # roughly 4 weeks
        context['occupancy_rate'] = min(100, int((context['monthly_hours'] / month_hours_capacity) * 100)) if month_hours_capacity > 0 else 0
        
        context['current_date'] = selected_date
        context['previous_date'] = selected_date - timedelta(days=1)
        context['next_date'] = selected_date + timedelta(days=1)
        context['now'] = now
        
        # For admin: generate month calendar data
        if user.is_authenticated and user.role == 'admin':
            context['show_month_view'] = True
            # Get sessions for the month
            month_start = selected_date.replace(day=1)
            if selected_date.month == 12:
                month_end = selected_date.replace(year=selected_date.year + 1, month=1, day=1)
            else:
                month_end = selected_date.replace(month=selected_date.month + 1, day=1)
            
            month_sessions = Session.objects.filter(
                room=room,
                start_datetime__date__gte=month_start,
                start_datetime__date__lt=month_end,
                is_validated=True
            ).values('start_datetime__date').distinct()
            
            context['dates_with_sessions'] = [s['start_datetime__date'] for s in month_sessions]
        
        return context



class RoomCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Create a single room"""
    
    model = Room
    form_class = RoomForm
    template_name = 'core/room_form.html'
    success_url = reverse_lazy('room_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Salle créée avec succès.")
        return super().form_valid(form)


class RoomUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Update a room"""
    
    model = Room
    form_class = RoomForm
    template_name = 'core/room_form.html'
    success_url = reverse_lazy('room_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Salle modifiée avec succès.")
        return super().form_valid(form)


class RoomDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """Delete a room"""
    
    model = Room
    template_name = 'core/room_confirm_delete.html'
    success_url = reverse_lazy('room_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Salle supprimée avec succès.")
        return super().form_valid(form)


class ContactSubmitView(CreateView):
    """
    Contact form submission view.
    Accessible by all users including guests.
    """
    
    model = ContactMessage
    form_class = ContactForm
    template_name = 'core/contact.html'
    success_url = reverse_lazy('contact_success')
    
    def get_form(self, form_class=None):
        """Make sender fields optional for authenticated users"""
        form = super().get_form(form_class)
        
        if self.request.user.is_authenticated:
            # For authenticated users, these fields are auto-filled
            form.fields['sender_name'].required = False
            form.fields['sender_email'].required = False
            # Also hide them
            form.fields['sender_name'].widget = forms.HiddenInput()
            form.fields['sender_email'].widget = forms.HiddenInput()
        
        return form
    
    def form_valid(self, form):
        # Link to user if authenticated
        if self.request.user.is_authenticated:
            form.instance.user = self.request.user
            form.instance.sender_name = self.request.user.get_full_name() or self.request.user.username
            form.instance.sender_email = self.request.user.email
        
        response = super().form_valid(form)
        
        # Notify administrators
        try:
            from apps.notifications.services import NotificationService
            NotificationService.notify_admins_contact_received(self.object)
        except Exception:
            pass  # Don't fail if notification fails
        
        messages.success(
            self.request,
            "Votre message a été envoyé avec succès. Nous vous répondrons dans les plus brefs délais."
        )
        
        return response
    
    def get_initial(self):
        initial = super().get_initial()
        if self.request.user.is_authenticated:
            initial['sender_name'] = self.request.user.get_full_name()
            initial['sender_email'] = self.request.user.email
        return initial


class ContactSuccessView(TemplateView):
    """View shown after successful contact form submission"""
    
    template_name = 'core/contact_success.html'


class ContactListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """List all contact messages (admin only)"""
    
    model = ContactMessage
    template_name = 'core/contact_list.html'
    context_object_name = 'contacts'  # Fixed: template uses 'contacts', not 'messages'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = ContactMessage.objects.all()
        
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Search by sender name or email
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                models.Q(sender_name__icontains=q) |
                models.Q(sender_email__icontains=q) |
                models.Q(subject__icontains=q)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = ContactMessage.STATUS_CHOICES
        # Add pending count for display in header
        context['pending_count'] = ContactMessage.objects.filter(status='pending').count()
        return context


class ContactDetailView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """View and respond to a contact message"""
    
    model = ContactMessage
    form_class = ContactResponseForm
    template_name = 'core/contact_detail.html'
    success_url = reverse_lazy('contact_list')
    
    def form_valid(self, form):
        from django.utils import timezone
        
        if form.cleaned_data['response']:
            form.instance.responded_at = timezone.now()
        
        messages.success(self.request, "Réponse enregistrée avec succès.")
        return super().form_valid(form)


class ProgramListView(ListView):
    """List all programs with filtering"""
    
    model = Program
    template_name = 'core/program_list.html'
    context_object_name = 'programs'
    
    def get_queryset(self):
        queryset = Program.objects.all()
        
        # Search filter
        search = self.request.GET.get('q', '')
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(code__icontains=search)
            )
        
        # Department filter
        department = self.request.GET.get('department', '')
        if department:
            queryset = queryset.filter(department=department)
        
        # Level filter
        level = self.request.GET.get('level', '')
        if level:
            queryset = queryset.filter(degree_level=level)
        
        return queryset.order_by('department', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Program.DEPARTMENT_CHOICES
        return context


class ProgramCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Create a new program/filière"""
    
    model = Program
    fields = ['name', 'code', 'department', 'degree_level', 'capacity', 'program_head']
    template_name = 'core/program_form.html'
    success_url = reverse_lazy('program_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field_name, field in form.fields.items():
            if field_name in ['degree_level', 'program_head']:
                field.widget.attrs['class'] = 'form-select form-select-lg'
            else:
                field.widget.attrs['class'] = 'form-control form-control-lg'
        
        # Make program_head optional
        form.fields['program_head'].required = False
        form.fields['program_head'].empty_label = "-- Aucun chef de filière (Optionnel) --"
        return form
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Create groups if specified
        num_groups = self.request.POST.get('num_groups', 0)
        group_capacity = self.request.POST.get('group_capacity', 30)
        group_label = self.request.POST.get('group_label', 'Groupe').strip()
        
        # Default to "Groupe" if empty
        if not group_label:
            group_label = 'Groupe'
        
        try:
            num_groups = int(num_groups)
            group_capacity = int(group_capacity)
        except (ValueError, TypeError):
            num_groups = 0
            group_capacity = 30
        
        if num_groups > 0:
            from datetime import datetime
            current_year = datetime.now().year
            academic_year = f"{current_year}-{current_year + 1}"
            
            groups_created = []
            for i in range(1, num_groups + 1):
                group = Group.objects.create(
                    name=f"{group_label} {i}",
                    program=self.object,
                    academic_year=academic_year,
                    capacity=group_capacity
                )
                groups_created.append(group.name)
            
            messages.success(
                self.request, 
                f"Filière '{form.instance.name}' créée avec {num_groups} groupe(s): {', '.join(groups_created)}"
            )
        else:
            messages.success(self.request, f"Filière '{form.instance.name}' créée avec succès!")
        
        return response


class ProgramDetailView(DetailView):
    """View program details"""
    
    model = Program
    template_name = 'core/program_detail.html'
    context_object_name = 'program'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['groups'] = self.object.groups.all()
        return context


class ProgramUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Update a program/filière with group management"""
    
    model = Program
    fields = ['name', 'code', 'department', 'degree_level', 'capacity', 'program_head']
    template_name = 'core/program_update.html'
    success_url = reverse_lazy('program_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field_name, field in form.fields.items():
            if field_name in ['degree_level', 'program_head']:
                field.widget.attrs['class'] = 'form-select form-select-lg'
            else:
                field.widget.attrs['class'] = 'form-control form-control-lg'
        form.fields['program_head'].required = False
        form.fields['program_head'].empty_label = "-- Aucun chef de filière (Optionnel) --"
        return form
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .forms import GroupFormSet
        
        if self.request.POST:
            context['group_formset'] = GroupFormSet(
                self.request.POST, 
                instance=self.object,
                prefix='groups'
            )
        else:
            context['group_formset'] = GroupFormSet(
                instance=self.object,
                prefix='groups'
            )
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        group_formset = context['group_formset']
        
        if group_formset.is_valid():
            self.object = form.save()
            group_formset.instance = self.object
            group_formset.save()
            messages.success(self.request, f"Filière '{form.instance.name}' mise à jour avec succès!")
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))



class EquipmentListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """List all equipment (admin only)"""
    
    model = Equipment
    template_name = 'core/equipment_list.html'
    context_object_name = 'equipment'


# =============================================================================
# API Views for AJAX operations
# =============================================================================

from django.http import JsonResponse
from django.views import View

class ProgramDeleteAPIView(LoginRequiredMixin, AdminRequiredMixin, View):
    """API endpoint to delete a program"""
    
    def post(self, request, program_id):
        try:
            program = Program.objects.get(id=program_id)
            program_name = program.name
            groups_count = program.groups.count()
            
            program.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Filière "{program_name}" supprimée avec succès (incluant {groups_count} groupe(s))'
            })
            
        except Program.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Filière introuvable'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)


class RoomDeleteAPIView(LoginRequiredMixin, AdminRequiredMixin, View):
    """API endpoint to delete a room"""
    
    def post(self, request, room_id):
        try:
            room = Room.objects.get(id=room_id)
            room_name = room.name
            
            room.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Salle "{room_name}" supprimée avec succès'
            })
            
        except Room.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Salle introuvable'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)


class ContactMarkReadAPIView(LoginRequiredMixin, AdminRequiredMixin, View):
    """API endpoint to mark a contact message as read"""
    
    def post(self, request, message_id):
        try:
            message = ContactMessage.objects.get(id=message_id)
            message.status = 'in_progress'
            message.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Message marqué comme lu'
            })
        except ContactMessage.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Message introuvable'
            }, status=404)


class ContactDeleteAPIView(LoginRequiredMixin, AdminRequiredMixin, View):
    """API endpoint to delete a contact message"""
    
    def post(self, request, message_id):
        try:
            message = ContactMessage.objects.get(id=message_id)
            message.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Message supprimé'
            })
        except ContactMessage.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Message introuvable'
            }, status=404)


class ContactMarkAllReadAPIView(LoginRequiredMixin, AdminRequiredMixin, View):
    """API endpoint to mark all contact messages as read"""
    
    def post(self, request):
        updated = ContactMessage.objects.filter(status='pending').update(status='in_progress')
        
        return JsonResponse({
            'success': True,
            'message': f'{updated} message(s) marqué(s) comme lu(s)'
        })
