"""
Forms for scheduling app.
"""

from django import forms
from datetime import timedelta, time, datetime
from django.conf import settings
from django.utils import timezone

from .models import Session, RoomReservationRequest, TeacherUnavailability, TimetableEntry
from apps.core.models import Room, Group


class RoomReservationForm(forms.ModelForm):
    """
    Form for room reservation requests.
    Used by teachers and associations.
    Validates working hours (9:00-18:00, Mon-Sat).
    """
    
    class Meta:
        model = RoomReservationRequest
        fields = ['room', 'requested_datetime', 'duration', 'reason', 'is_exam']
        labels = {
            'room': 'Salle souhaitée',
            'requested_datetime': 'Date et heure',
            'duration': 'Durée (en heures)',
            'reason': 'Motif de la demande',
            'is_exam': 'Réservation pour un examen',
        }
        help_texts = {
            'reason': 'Veuillez préciser le motif de votre réservation',
            'is_exam': 'Cocher si cette réservation concerne un examen (les étudiants seront notifiés)',
        }
        widgets = {
            'requested_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'duration': forms.NumberInput(attrs={
                'min': 1,
                'max': 8,
                'class': 'form-control'
            }),
            'reason': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Ex: Séance de rattrapage pour le groupe X'
            }),
            'room': forms.Select(attrs={'class': 'form-select'}),
            'is_exam': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active rooms
        self.fields['room'].queryset = Room.objects.filter(is_active=True).order_by('building', 'name')
    
    def clean_requested_datetime(self):
        """Validate requested datetime is within working hours"""
        dt = self.cleaned_data.get('requested_datetime')
        
        if not dt:
            raise forms.ValidationError("La date et l'heure sont requises.")
        
        # Make timezone aware if needed
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt)
        
        # Check if in the past
        if dt < timezone.now():
            raise forms.ValidationError("Vous ne pouvez pas réserver dans le passé.")
        
        # Check if Sunday (isoweekday: Monday=1, Sunday=7)
        if dt.isoweekday() == 7:
            raise forms.ValidationError(
                "Les réservations ne sont pas autorisées le dimanche."
            )
        
        # Check if within allowed weekdays
        if dt.isoweekday() not in settings.WORKING_DAYS:
            raise forms.ValidationError(
                "Les réservations sont autorisées uniquement du lundi au samedi."
            )
        
        # Check if within working hours (9:00 - 18:00)
        start_time = time(settings.WORKING_HOURS_START, 0)
        end_time = time(settings.WORKING_HOURS_END, 0)
        
        if not (start_time <= dt.time() < end_time):
            raise forms.ValidationError(
                f"Les réservations sont autorisées uniquement entre "
                f"{settings.WORKING_HOURS_START}h00 et {settings.WORKING_HOURS_END}h00."
            )
        
        return dt
    
    def clean(self):
        cleaned_data = super().clean()
        room = cleaned_data.get('room')
        requested_datetime = cleaned_data.get('requested_datetime')
        duration = cleaned_data.get('duration')
        
        if room and requested_datetime and duration:
            end_time_dt = requested_datetime + timedelta(hours=duration)
            
            # Check end time doesn't exceed 18:00
            closing_time = time(settings.WORKING_HOURS_END, 0)
            if end_time_dt.time() > closing_time:
                raise forms.ValidationError(
                    f"La réservation se termine à {end_time_dt.strftime('%H:%M')}, "
                    f"ce qui dépasse l'heure de fermeture ({settings.WORKING_HOURS_END}h00). "
                    f"Veuillez réduire la durée ou choisir une heure de début plus tôt."
                )
            
            # Check room availability
            if not room.check_availability(requested_datetime, end_time_dt):
                raise forms.ValidationError(
                    "La salle est déjà réservée pour ce créneau horaire."
                )
        
        return cleaned_data


class SessionForm(forms.ModelForm):
    """
    Form for creating/editing sessions.
    """
    
    class Meta:
        model = Session
        fields = ['session_type', 'subject', 'teacher', 'room', 'groups', 
                  'start_datetime', 'end_datetime', 'notes']
        labels = {
            'session_type': 'Type de séance',
            'subject': 'Matière',
            'teacher': 'Enseignant',
            'room': 'Salle',
            'groups': 'Groupes',
            'start_datetime': 'Date et heure de début',
            'end_datetime': 'Date et heure de fin',
            'notes': 'Notes',
        }
        widgets = {
            'session_type': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'teacher': forms.Select(attrs={'class': 'form-select'}),
            'room': forms.Select(attrs={'class': 'form-select'}),
            'groups': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'start_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'end_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_datetime')
        end = cleaned_data.get('end_datetime')
        
        if start and end and start >= end:
            raise forms.ValidationError(
                "La date de fin doit être après la date de début."
            )
        
        return cleaned_data


class ReservationApprovalForm(forms.Form):
    """
    Form for admin to approve/reject reservations.
    """
    
    ACTION_CHOICES = [
        ('approve', 'Approuver'),
        ('reject', 'Rejeter'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        label="Action",
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    admin_notes = forms.CharField(
        label="Notes (obligatoire en cas de rejet)",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Raison du rejet ou notes supplémentaires'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        admin_notes = cleaned_data.get('admin_notes')
        
        if action == 'reject' and not admin_notes:
            raise forms.ValidationError(
                "Veuillez fournir une raison pour le rejet."
            )
        
        return cleaned_data


class TeacherUnavailabilityForm(forms.ModelForm):
    """
    Form for teachers to declare unavailability periods.
    """
    
    class Meta:
        model = TeacherUnavailability
        fields = ['start_datetime', 'end_datetime', 'reason']
        labels = {
            'start_datetime': 'Date et heure de début',
            'end_datetime': 'Date et heure de fin',
            'reason': 'Raison',
        }
        widgets = {
            'start_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'end_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ex: Conférence, Formation, Congé...'
            }),
        }


class TeacherRoomReservationForm(forms.ModelForm):
    """
    Enhanced reservation form for teachers with program selection,
    reservation type choice, and date range selection.
    """
    
    class Meta:
        model = RoomReservationRequest
        fields = [
            'program', 'reservation_type', 'subject', 'room',
            'start_datetime', 'end_datetime', 'reason', 'is_exam'
        ]
        labels = {
            'program': 'Filière concernée',
            'reservation_type': 'Type de réservation',
            'subject': 'Matière/Sujet du cours',
            'room': 'Salle souhaitée',
            'start_datetime': 'Date et heure de début',
            'end_datetime': 'Date et heure de fin',
            'reason': 'Motif/Description',
            'is_exam': 'Cette séance est un examen'
        }
        widgets = {
            'program': forms.Select(attrs={'class': 'form-select'}),
            'reservation_type': forms.RadioSelect(),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Algèbre Linéaire, Révision Chimie'
            }),
            'room': forms.Select(attrs={'class': 'form-select'}),
            'start_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'end_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Décrivez brièvement le contenu ou la raison de cette séance'
            }),
            'is_exam': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        help_texts = {
            'program': 'Sélectionnez la filière dont les étudiants assisteront',
            'start_datetime': 'Lundi à Samedi, entre 9h00 et 18h00',
            'end_datetime': 'Doit être le même jour et avant 18h00',
        }
    
    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        
        # Filter programs optionally by teacher's department
        from apps.core.models import Program
        self.fields['program'].queryset = Program.objects.all().order_by('name')
        
        # Only show active rooms
        self.fields['room'].queryset = Room.objects.filter(is_active=True).order_by('building', 'name')
        
        # Make key fields required
        self.fields['program'].required = False  # Optional for one-time sessions
        self.fields['subject'].required = True
        self.fields['start_datetime'].required = True
        self.fields['end_datetime'].required = True
    
    def clean_start_datetime(self):
        """Validate start datetime is within working hours"""
        start_dt = self.cleaned_data.get('start_datetime')
        
        if not start_dt:
            raise forms.ValidationError("La date de début est requise.")
        
        # Make timezone aware if needed
        if timezone.is_naive(start_dt):
            start_dt = timezone.make_aware(start_dt)
        
        # Check if in the past
        if start_dt < timezone.now():
            raise forms.ValidationError("Vous ne pouvez pas réserver dans le passé.")
        
        # Check if Sunday
        if start_dt.isoweekday() == 7:
            raise forms.ValidationError("Les réservations ne sont pas autorisées le dimanche.")
        
        # Check working hours
        start_time_limit = time(settings.WORKING_HOURS_START, 0)
        end_time_limit = time(settings.WORKING_HOURS_END, 0)
        
        if not (start_time_limit <= start_dt.time() < end_time_limit):
            raise forms.ValidationError(
                f"L'heure de début doit être entre {settings.WORKING_HOURS_START}h00 et {settings.WORKING_HOURS_END}h00."
            )
        
        return start_dt
    
    def clean_end_datetime(self):
        """Validate end datetime is within working hours"""
        end_dt = self.cleaned_data.get('end_datetime')
        
        if not end_dt:
            raise forms.ValidationError("La date de fin est requise.")
        
        # Make timezone aware if needed
        if timezone.is_naive(end_dt):
            end_dt = timezone.make_aware(end_dt)
        
        # Check if Sunday
        if end_dt.isoweekday() == 7:
            raise forms.ValidationError("Les réservations ne sont pas autorisées le dimanche.")
        
        # Check working hours (end can be exactly at 18:00)
        end_time_limit = time(settings.WORKING_HOURS_END, 0)
        
        if end_dt.time() > end_time_limit:
            raise forms.ValidationError(
                f"L'heure de fin ne peut pas dépasser {settings.WORKING_HOURS_END}h00."
            )
        
        return end_dt
    
    def clean(self):
        """Cross-field validation including program conflicts"""
        cleaned_data = super().clean()
        start_dt = cleaned_data.get('start_datetime')
        end_dt = cleaned_data.get('end_datetime')
        room = cleaned_data.get('room')
        program = cleaned_data.get('program')
        reservation_type = cleaned_data.get('reservation_type')
        
        # Validate date range
        if start_dt and end_dt:
            if end_dt <= start_dt:
                raise forms.ValidationError({
                    'end_datetime': "L'heure de fin doit être après l'heure de début."
                })
            
            # Check same day
            if start_dt.date() != end_dt.date():
                raise forms.ValidationError(
                    "Les réservations doivent être dans la même journée."
                )
            
            # Check room availability
            if room and not room.check_availability(start_dt, end_dt):
                raise forms.ValidationError({
                    'room': f"La salle {room.name} est déjà occupée pendant ce créneau."
                })
        
        # Check conflicts (Teacher availability and Program availability)
        if start_dt and end_dt:
            # Create temp reservation for checking conflicts
            temp_reservation = RoomReservationRequest(
                program=program,
                teacher=self.teacher,
                room=room,
                start_datetime=start_dt,
                end_datetime=end_dt
            )
            
            # 1. Check Teacher Conflicts (Prevent double-booking the teacher)
            if self.teacher:
                teacher_conflicts = temp_reservation.check_teacher_conflicts()
                if teacher_conflicts.exists():
                    conflict = teacher_conflicts.first()
                    raise forms.ValidationError({
                        'start_datetime': f"Vous enseignez déjà '{conflict.subject}' ce jour-là de {conflict.start_datetime.strftime('%H:%M')} à {conflict.end_datetime.strftime('%H:%M')}."
                    })
                
                # Check for conflicts in published timetable
                if hasattr(temp_reservation, '_teacher_timetable_conflicts'):
                    tt_conflict = temp_reservation._teacher_timetable_conflicts.first()
                    day_name = dict(TimetableEntry.DAY_CHOICES).get(tt_conflict.day_of_week, tt_conflict.day_of_week) if hasattr(TimetableEntry, 'DAY_CHOICES') else tt_conflict.day_of_week
                    raise forms.ValidationError({
                        'start_datetime': f"Vous avez déjà un cours prévu dans votre emploi du temps : {day_name} ({tt_conflict.time_slot} - {tt_conflict.subject or 'Cours'})."
                    })

            # 2. Check Program Conflicts (Prevent overlapping sessions for students)
            if program:
                conflicts = temp_reservation.check_program_conflicts()
                if conflicts.exists():
                    conflict_info = ", ".join([
                        f"{c.subject} ({c.start_datetime.strftime('%H:%M')})"
                        for c in conflicts[:3]
                    ])
                    raise forms.ValidationError({
                        'program': f"Conflit détecté: La filière {program.name} a déjà des séances à cet horaire: {conflict_info}"
                    })
                
                # Also check TimetableEntry-level conflicts
                if hasattr(temp_reservation, '_timetable_conflicts') and temp_reservation._timetable_conflicts.exists():
                    tt_conflicts = temp_reservation._timetable_conflicts
                    conflict_info = ", ".join([
                        f"{c.subject.name if c.subject else 'Séance'} ({c.time_slot.get_display_time() if c.time_slot else ''})"
                        for c in tt_conflicts[:3]
                    ])
                    raise forms.ValidationError({
                        'program': f"Conflit détecté: La filière {program.name} a déjà des cours programmés à cet horaire: {conflict_info}"
                    })
        
        # Recurring sessions must have a program
        if reservation_type == 'recurring' and not program:
            raise forms.ValidationError({
                'program': "Une filière est obligatoire pour les séances hebdomadaires."
            })
        
        return cleaned_data


class AssociationRoomReservationForm(forms.ModelForm):
    """
    Simplified reservation form for associations.
    No program/groups/subject - focused on event information.
    """
    
    class Meta:
        model = RoomReservationRequest
        fields = [
            'room', 'start_datetime', 'end_datetime', 'reason'
        ]
        labels = {
            'room': 'Salle souhaitée',
            'start_datetime': 'Date et heure de début',
            'end_datetime': 'Date et heure de fin',
            'reason': 'Description de l\'événement'
        }
        widgets = {
            'room': forms.Select(attrs={
                'class': 'form-select form-select-lg'
            }),
            'start_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control form-control-lg'
            }),
            'end_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control form-control-lg'
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Décrivez votre événement: réunion, conférence, atelier, etc.'
            })
        }
        help_texts = {
            'start_datetime': 'Lundi à Samedi, entre 9h00 et 18h00',
            'end_datetime': 'Doit être le même jour, avant 18h00',
        }
    
    def __init__(self, *args, **kwargs):
        # Remove teacher kwarg if passed
        kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        
        # Only show active rooms
        self.fields['room'].queryset = Room.objects.filter(is_active=True).order_by('building', 'name')
        
        # All fields required
        self.fields['room'].required = True
        self.fields['start_datetime'].required = True
        self.fields['end_datetime'].required = True
        self.fields['reason'].required = True
    
    def clean_start_datetime(self):
        """Validate start datetime is within working hours"""
        start_dt = self.cleaned_data.get('start_datetime')
        
        if not start_dt:
            raise forms.ValidationError("La date de début est requise.")
        
        # Make timezone aware if needed
        if timezone.is_naive(start_dt):
            start_dt = timezone.make_aware(start_dt)
        
        # Check if in the past
        if start_dt < timezone.now():
            raise forms.ValidationError("Vous ne pouvez pas réserver dans le passé.")
        
        # Check if Sunday
        if start_dt.isoweekday() == 7:
            raise forms.ValidationError("Les réservations ne sont pas autorisées le dimanche.")
        
        # Check working hours
        start_time_limit = time(settings.WORKING_HOURS_START, 0)
        end_time_limit = time(settings.WORKING_HOURS_END, 0)
        
        if not (start_time_limit <= start_dt.time() < end_time_limit):
            raise forms.ValidationError(
                f"L'heure de début doit être entre {settings.WORKING_HOURS_START}h00 et {settings.WORKING_HOURS_END}h00."
            )
        
        return start_dt
    
    def clean_end_datetime(self):
        """Validate end datetime is within working hours"""
        end_dt = self.cleaned_data.get('end_datetime')
        
        if not end_dt:
            raise forms.ValidationError("La date de fin est requise.")
        
        # Make timezone aware if needed
        if timezone.is_naive(end_dt):
            end_dt = timezone.make_aware(end_dt)
        
        # Check if Sunday
        if end_dt.isoweekday() == 7:
            raise forms.ValidationError("Les réservations ne sont pas autorisées le dimanche.")
        
        # Check working hours
        end_time_limit = time(settings.WORKING_HOURS_END, 0)
        
        if end_dt.time() > end_time_limit:
            raise forms.ValidationError(
                f"L'heure de fin ne peut pas dépasser {settings.WORKING_HOURS_END}h00."
            )
        
        return end_dt
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        start_dt = cleaned_data.get('start_datetime')
        end_dt = cleaned_data.get('end_datetime')
        room = cleaned_data.get('room')
        
        # Validate date range
        if start_dt and end_dt:
            if end_dt <= start_dt:
                raise forms.ValidationError({
                    'end_datetime': "L'heure de fin doit être après l'heure de début."
                })
            
            # Check same day
            if start_dt.date() != end_dt.date():
                raise forms.ValidationError(
                    "Les réservations doivent être dans la même journée."
                )
            
            # Check room availability
            if room and not room.check_availability(start_dt, end_dt):
                raise forms.ValidationError({
                    'room': f"La salle {room.name} est déjà occupée pendant ce créneau."
                })
        
        return cleaned_data


# ============================================================================
# SEMESTER TIMETABLE FORMS
# ============================================================================

class SemesterTimetableForm(forms.ModelForm):
    """
    Form for creating/editing semester timetables.
    Step 1: Select program, semester, academic year, and dates.
    """
    
    class Meta:
        from .models import Timetable
        model = Timetable
        fields = ['name', 'program', 'semester', 'academic_year', 'start_date', 'end_date']
        labels = {
            'name': 'Nom de l\'emploi du temps',
            'program': 'Filière',
            'semester': 'Semestre',
            'academic_year': 'Année universitaire',
            'start_date': 'Date de début du semestre',
            'end_date': 'Date de fin du semestre',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Emploi du temps S1 - SMI'
            }),
            'program': forms.Select(attrs={'class': 'form-select'}),
            'semester': forms.Select(attrs={'class': 'form-select'}),
            'academic_year': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '2025-2026'
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.core.models import Program
        self.fields['program'].queryset = Program.objects.all().order_by('department', 'name')
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        program = cleaned_data.get('program')
        semester = cleaned_data.get('semester')
        academic_year = cleaned_data.get('academic_year')
        
        # Validate date range
        if start_date and end_date:
            if end_date <= start_date:
                raise forms.ValidationError({
                    'end_date': "La date de fin doit être après la date de début."
                })
        
        # Check for duplicate timetable
        from .models import Timetable
        existing = Timetable.objects.filter(
            program=program,
            semester=semester,
            academic_year=academic_year
        )
        
        # Exclude current instance if editing
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        
        if existing.exists():
            raise forms.ValidationError(
                f"Un emploi du temps existe déjà pour {program} - {semester} ({academic_year})."
            )
        
        return cleaned_data


class TimetableEntryForm(forms.ModelForm):
    """
    Form for a single timetable entry (one cell in the weekly grid).
    """
    
    class Meta:
        from .models import TimetableEntry
        model = TimetableEntry
        fields = ['subject', 'teacher', 'room', 'study_group', 'session_type']
        labels = {
            'subject': 'Matière',
            'teacher': 'Enseignant',
            'room': 'Salle',
            'study_group': 'Groupe',
            'session_type': 'Type',
        }
        widgets = {
            'subject': forms.Select(attrs={
                'class': 'form-select form-select-sm'
            }),
            'teacher': forms.Select(attrs={
                'class': 'form-select form-select-sm'
            }),
            'room': forms.Select(attrs={
                'class': 'form-select form-select-sm'
            }),
            'study_group': forms.Select(attrs={
                'class': 'form-select form-select-sm'
            }),
            'session_type': forms.Select(attrs={
                'class': 'form-select form-select-sm'
            }),
        }
    
    def __init__(self, *args, program=None, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Subject
        from apps.accounts.models import Teacher
        from apps.core.models import Room, Group
        
        # Filter subjects by program if provided
        if program:
            self.fields['subject'].queryset = Subject.objects.filter(program=program).order_by('code')
            self.fields['study_group'].queryset = Group.objects.filter(program=program).order_by('name')
        else:
            self.fields['subject'].queryset = Subject.objects.all().order_by('code')
            self.fields['study_group'].queryset = Group.objects.all().order_by('program', 'name')
        
        self.fields['teacher'].queryset = Teacher.objects.all().order_by('user__last_name')
        self.fields['room'].queryset = Room.objects.filter(is_active=True).order_by('building', 'name')
        
        # All fields optional except subject
        self.fields['teacher'].required = False
        self.fields['room'].required = False
        self.fields['study_group'].required = False


class BulkTimetableEntryForm(forms.Form):
    """
    Form for bulk creating/updating timetable entries.
    Handles the full weekly grid (6 days × 5 slots = 30 cells).
    """
    
    DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
    DAY_NAMES = {
        'MON': 'Lundi', 
        'TUE': 'Mardi', 
        'WED': 'Mercredi', 
        'THU': 'Jeudi', 
        'FRI': 'Vendredi', 
        'SAT': 'Samedi'
    }
    
    def __init__(self, *args, timetable=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.timetable = timetable
        
        from .models import Subject, TimeSlot
        from apps.accounts.models import Teacher
        from apps.core.models import Room, Group
        
        # Get data from database
        time_slots = TimeSlot.objects.all().order_by('slot_number')
        
        if timetable:
            subjects = Subject.objects.filter(program=timetable.program).order_by('code')
            groups = Group.objects.filter(program=timetable.program).order_by('name')
        else:
            subjects = Subject.objects.none()
            groups = Group.objects.none()
        
        teachers = Teacher.objects.all().order_by('user__last_name')
        rooms = Room.objects.filter(is_active=True).order_by('building', 'name')
        
        # Create fields for each cell in the grid
        for day in self.DAYS:
            for slot in time_slots:
                prefix = f"{day}_{slot.slot_number}"
                
                # Subject field
                self.fields[f"{prefix}_subject"] = forms.ModelChoiceField(
                    queryset=subjects,
                    required=False,
                    label=f"{self.DAY_NAMES[day]} - {slot.get_display_time()} - Matière",
                    widget=forms.Select(attrs={
                        'class': 'form-select form-select-sm cell-subject',
                        'data-day': day,
                        'data-slot': slot.slot_number
                    })
                )
                
                # Teacher field
                self.fields[f"{prefix}_teacher"] = forms.ModelChoiceField(
                    queryset=teachers,
                    required=False,
                    label=f"{self.DAY_NAMES[day]} - {slot.get_display_time()} - Enseignant",
                    widget=forms.Select(attrs={
                        'class': 'form-select form-select-sm cell-teacher',
                        'data-day': day,
                        'data-slot': slot.slot_number
                    })
                )
                
                # Room field
                self.fields[f"{prefix}_room"] = forms.ModelChoiceField(
                    queryset=rooms,
                    required=False,
                    label=f"{self.DAY_NAMES[day]} - {slot.get_display_time()} - Salle",
                    widget=forms.Select(attrs={
                        'class': 'form-select form-select-sm cell-room',
                        'data-day': day,
                        'data-slot': slot.slot_number
                    })
                )
                
                # Study group field
                self.fields[f"{prefix}_group"] = forms.ModelChoiceField(
                    queryset=groups,
                    required=False,
                    label=f"{self.DAY_NAMES[day]} - {slot.get_display_time()} - Groupe",
                    widget=forms.Select(attrs={
                        'class': 'form-select form-select-sm cell-group',
                        'data-day': day,
                        'data-slot': slot.slot_number
                    })
                )
                
                
                # Session type field
                self.fields[f"{prefix}_type"] = forms.ChoiceField(
                    choices=[('', '---'), ('cours', 'CM'), ('td', 'TD'), ('tp', 'TP')],
                    required=False,
                    label=f"{self.DAY_NAMES[day]} - {slot.get_display_time()} - Type",
                    widget=forms.Select(attrs={
                        'class': 'form-select form-select-sm cell-type',
                        'data-day': day,
                        'data-slot': slot.slot_number
                    })
                )


class TimetableChangeRequestForm(forms.ModelForm):
    """
    Form for teachers to request timetable changes.
    """
    class Meta:
        from .models import TimetableChangeRequest
        model = TimetableChangeRequest
        fields = ['subject', 'current_entry', 'desired_change', 'reason']
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'current_entry': forms.Select(attrs={'class': 'form-select'}),
            'desired_change': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ex: Je souhaite déplacer le cours du Lundi 8h30 au Mercredi 14h'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ex: Conflit avec une réunion départementale'}),
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher:
            from .models import Subject, TimetableEntry
            # Filter subjects where teacher is assigned OR all subjects if lenient
            # Ideally only their subjects
            self.fields['subject'].queryset = Subject.objects.filter(teacher=teacher).order_by('code')
            
            # Filter entries for this teacher
            self.fields['current_entry'].queryset = TimetableEntry.objects.filter(teacher=teacher).order_by('day_of_week')
            self.fields['current_entry'].label_from_instance = lambda obj: f"{obj.subject.code} - {obj.get_day_of_week_display()} {obj.time_slot}"


# =============================================================================
# SEMESTER TIMETABLE FORMS WITH INLINE SUBJECTS
# =============================================================================

class SemesterTimetableForm(forms.ModelForm):
    """
    Form for creating/editing semester timetables.
    """
    
    class Meta:
        from apps.scheduling.models import Timetable
        model = Timetable
        fields = ['name', 'program', 'semester', 'academic_year', 'start_date', 'end_date']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Ex: Emploi du temps S1 - SMI'
            }),
            'program': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500'
            }),
            'semester': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500'
            }),
            'academic_year': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500',
                'placeholder': '2025-2026'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500',
                'type': 'date'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.core.models import Program
        self.fields['program'].queryset = Program.objects.all().order_by('name')
        self.fields['program'].empty_label = "Sélectionner une filière"


class SubjectInlineForm(forms.ModelForm):
    """
    Form for each subject in the inline formset.
    """
    
    class Meta:
        from apps.scheduling.models import Subject
        model = Subject
        fields = [
            'code', 
            'name', 
            'hours_per_week',
            'sessions_cours',
            'sessions_td',
            'sessions_tp',
            'teacher'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-200 rounded-lg text-sm',
                'placeholder': 'AD_51'
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-200 rounded-lg text-sm',
                'placeholder': 'Nom de la matière'
            }),
            'hours_per_week': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-200 rounded-lg text-sm',
                'step': '0.5',
                'min': '0.5',
                'placeholder': '4.5'
            }),
            'sessions_cours': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-200 rounded-lg text-sm',
                'min': '0',
                'placeholder': '2'
            }),
            'sessions_td': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-200 rounded-lg text-sm',
                'min': '0',
                'placeholder': '1'
            }),
            'sessions_tp': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-200 rounded-lg text-sm',
                'min': '0',
                'placeholder': '0'
            }),
            'teacher': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-200 rounded-lg text-sm'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.models import Teacher
        self.fields['teacher'].queryset = Teacher.objects.all().order_by('user__last_name')
        self.fields['teacher'].empty_label = "Sélectionner un professeur"
        self.fields['teacher'].required = False
        self.fields['code'].required = True
        self.fields['name'].required = True


def get_subject_formset(extra=2):
    """
    Factory function to create the inline formset for subjects.
    """
    from django.forms import inlineformset_factory
    from .models import Timetable, Subject
    
    return inlineformset_factory(
        Timetable,
        Subject,
        form=SubjectInlineForm,
        fk_name='timetable',
        extra=extra,
        can_delete=True,
        min_num=0,
        validate_min=False
    )


# Default formset with 2 extra forms
SubjectFormSet = get_subject_formset(extra=2)
