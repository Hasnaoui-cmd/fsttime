"""
Scheduling models for FSTTIME application.
Includes sessions, timetables, and room reservations.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Session(models.Model):
    """
    Session model representing a class/lecture.
    Triggers notifications when exam sessions are created.
    """
    
    SESSION_TYPE_CHOICES = [
        ('cours', 'Cours'),
        ('td', 'TD'),
        ('tp', 'TP'),
        ('examen', 'Examen'),
    ]
    
    session_type = models.CharField(
        max_length=20,
        choices=SESSION_TYPE_CHOICES,
        verbose_name=_("Type")
    )
    subject = models.CharField(
        max_length=200,
        verbose_name=_("Matière")
    )
    teacher = models.ForeignKey(
        'accounts.Teacher',
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name=_("Enseignant")
    )
    room = models.ForeignKey(
        'core.Room',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions',
        verbose_name=_("Salle")
    )
    groups = models.ManyToManyField(
        'core.Group',
        related_name='sessions',
        verbose_name=_("Groupes")
    )
    start_datetime = models.DateTimeField(
        verbose_name=_("Début")
    )
    end_datetime = models.DateTimeField(
        verbose_name=_("Fin")
    )
    is_exam = models.BooleanField(
        default=False,
        verbose_name=_("Est un examen")
    )
    is_validated = models.BooleanField(
        default=False,
        verbose_name=_("Validée")
    )
    is_recurring = models.BooleanField(
        default=False,
        verbose_name=_("Séance récurrente")
    )
    parent_reservation = models.ForeignKey(
        'RoomReservationRequest',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='generated_sessions',
        verbose_name=_("Réservation d'origine")
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date de création")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Date de modification")
    )
    
    class Meta:
        verbose_name = _("Séance")
        verbose_name_plural = _("Séances")
        ordering = ['start_datetime']
    
    def __str__(self):
        return f"{self.subject} - {self.get_session_type_display()} ({self.start_datetime.strftime('%d/%m/%Y %H:%M')})"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # Set is_exam based on session_type
        if self.session_type == 'examen':
            self.is_exam = True
        
        super().save(*args, **kwargs)
        
        # Trigger notifications if new exam session
        if is_new and self.is_exam:
            from apps.notifications.services import NotificationService
            NotificationService.notify_students_exam_scheduled(self)
    
    def get_duration_hours(self):
        """Get session duration in hours"""
        delta = self.end_datetime - self.start_datetime
        return delta.seconds / 3600
    
    def check_conflicts(self):
        """Check for scheduling conflicts"""
        conflicts = []
        
        # Check room conflicts
        if self.room:
            room_conflicts = Session.objects.filter(
                room=self.room,
                start_datetime__lt=self.end_datetime,
                end_datetime__gt=self.start_datetime
            ).exclude(pk=self.pk)
            conflicts.extend(room_conflicts)
        
        # Check teacher conflicts
        teacher_conflicts = Session.objects.filter(
            teacher=self.teacher,
            start_datetime__lt=self.end_datetime,
            end_datetime__gt=self.start_datetime
        ).exclude(pk=self.pk)
        conflicts.extend(teacher_conflicts)
        
        return conflicts


class Timetable(models.Model):
    """
    Timetable model representing a program's schedule.
    Enhanced with automatic generation support.
    """
    
    SEMESTER_CHOICES = [
        ('S1', 'Semestre 1'),
        ('S2', 'Semestre 2'),
    ]
    
    name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Nom")
    )
    program = models.ForeignKey(
        'core.Program',
        on_delete=models.CASCADE,
        related_name='timetables',
        verbose_name=_("Filière")
    )
    study_groups = models.ManyToManyField(
        'core.Group',
        blank=True,
        related_name='timetables',
        verbose_name=_("Groupes d'étude")
    )
    academic_year = models.CharField(
        max_length=10,
        verbose_name=_("Année universitaire")
    )
    semester = models.CharField(
        max_length=20,
        choices=SEMESTER_CHOICES,
        verbose_name=_("Semestre")
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date de début")
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date de fin")
    )
    sessions = models.ManyToManyField(
        Session,
        blank=True,
        related_name='timetables',
        verbose_name=_("Séances")
    )
    is_generated = models.BooleanField(
        default=False,
        verbose_name=_("Généré automatiquement")
    )
    is_published = models.BooleanField(
        default=False,
        verbose_name=_("Publié")
    )
    created_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_timetables',
        verbose_name=_("Créé par")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date de création")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Date de modification")
    )
    
    class Meta:
        verbose_name = _("Emploi du Temps")
        verbose_name_plural = _("Emplois du Temps")
        unique_together = ['program', 'academic_year', 'semester']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.program.code} - {self.semester} ({self.academic_year})"
    
    def get_total_hours(self):
        """Calculate total weekly hours"""
        total = 0
        for session in self.sessions.all():
            total += session.get_duration_hours()
        return total


class TimeSlot(models.Model):
    """
    Time slot model for timetable scheduling.
    Defines 5 fixed time slots per day:
    - Slot 1: 09:00 - 10:45
    - Slot 2: 10:45 - 12:15  
    - Slot 3: 12:30 - 14:00
    - Slot 4: 14:15 - 15:45
    - Slot 5: 16:00 - 17:30
    """
    
    slot_number = models.IntegerField(
        unique=True,
        verbose_name=_("Numéro du créneau")
    )
    start_time = models.TimeField(
        verbose_name=_("Heure de début")
    )
    end_time = models.TimeField(
        verbose_name=_("Heure de fin")
    )
    
    class Meta:
        verbose_name = _("Créneau Horaire")
        verbose_name_plural = _("Créneaux Horaires")
        ordering = ['slot_number']
    
    def __str__(self):
        return f"Créneau {self.slot_number}: {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"
    
    def get_display_time(self):
        """Get formatted display time"""
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"
    
    def get_duration_hours(self):
        """Get slot duration in hours"""
        from datetime import datetime
        start = datetime.combine(datetime.today(), self.start_time)
        end = datetime.combine(datetime.today(), self.end_time)
        delta = end - start
        return delta.seconds / 3600



class Subject(models.Model):
    """
    Subject/Course model for automatic timetable generation.
    Links subjects to programs, teachers, and scheduling requirements.
    Can be linked to a specific timetable when created inline.
    """
    
    SESSION_TYPE_CHOICES = [
        ('cours', 'Cours Magistral'),
        ('td', 'Travaux Dirigés'),
        ('tp', 'Travaux Pratiques'),
    ]
    
    SEMESTER_CHOICES = [
        (1, 'Semestre 1'),
        (2, 'Semestre 2'),
    ]
    
    name = models.CharField(
        max_length=200,
        verbose_name=_("Nom de la matière")
    )
    code = models.CharField(
        max_length=20,
        verbose_name=_("Code")
    )
    program = models.ForeignKey(
        'core.Program',
        on_delete=models.CASCADE,
        related_name='subjects',
        verbose_name=_("Filière"),
        null=True,
        blank=True
    )
    # Link to timetable for inline-created subjects
    timetable = models.ForeignKey(
        'Timetable',
        on_delete=models.CASCADE,
        related_name='inline_subjects',
        verbose_name=_("Emploi du temps"),
        null=True,
        blank=True
    )
    semester = models.IntegerField(
        choices=SEMESTER_CHOICES,
        default=1,
        verbose_name=_("Semestre")
    )
    teacher = models.ForeignKey(
        'accounts.Teacher',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subjects',
        verbose_name=_("Enseignant")
    )
    session_type = models.CharField(
        max_length=20,
        choices=SESSION_TYPE_CHOICES,
        default='cours',
        verbose_name=_("Type de séance")
    )
    hours_per_week = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=3.0,
        verbose_name=_("Heures par semaine")
    )
    # Session counts per week
    sessions_cours = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Séances COURS"),
        help_text=_("Nombre de séances de cours par semaine")
    )
    sessions_td = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Séances TD"),
        help_text=_("Nombre de séances de TD par semaine")
    )
    sessions_tp = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Séances TP"),
        help_text=_("Nombre de séances de TP par semaine")
    )
    max_hours_per_day = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=3.0,
        verbose_name=_("Max heures par jour")
    )
    requires_lab = models.BooleanField(
        default=False,
        verbose_name=_("Nécessite un laboratoire")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Actif")
    )
    color = models.CharField(
        max_length=7,
        default='#8b5cf6',
        verbose_name=_("Couleur d'affichage")
    )
    
    class Meta:
        verbose_name = _("Matière")
        verbose_name_plural = _("Matières")
        ordering = ['program', 'semester', 'code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_required_slots(self):

        """Calculate number of slots needed per week (1.5h per slot)"""
        return max(1, int(float(self.hours_per_week) / 1.5))


class RoomReservationRequest(models.Model):
    """
    Room reservation request model.
    Can be submitted by teachers or associations.
    Supports recurring weekly sessions and one-time sessions.
    """
    
    REQUESTER_TYPE_CHOICES = [
        ('teacher', 'Enseignant'),
        ('association', 'Association'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvée'),
        ('rejected', 'Rejetée'),
    ]
    
    RESERVATION_TYPE_CHOICES = [
        ('recurring', 'Séance Hebdomadaire (Modifie l\'emploi du temps)'),
        ('one_time', 'Séance Ponctuelle (Rattrapage/Révision)'),
    ]
    
    requester_type = models.CharField(
        max_length=20,
        choices=REQUESTER_TYPE_CHOICES,
        verbose_name=_("Type de demandeur")
    )
    teacher = models.ForeignKey(
        'accounts.Teacher',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='reservation_requests',
        verbose_name=_("Enseignant")
    )
    association = models.ForeignKey(
        'accounts.Association',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='reservation_requests',
        verbose_name=_("Association")
    )
    # NEW: Program for conflict detection
    program = models.ForeignKey(
        'core.Program',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reservation_requests',
        verbose_name=_("Filière concernée"),
        help_text=_("Sélectionnez la filière pour cette réservation")
    )
    # NEW: Reservation type (recurring or one-time)
    reservation_type = models.CharField(
        max_length=20,
        choices=RESERVATION_TYPE_CHOICES,
        default='one_time',
        verbose_name=_("Type de réservation")
    )
    # NEW: Subject field
    subject = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Matière/Sujet"),
        help_text=_("Ex: Algèbre Linéaire, Révision Chimie")
    )
    room = models.ForeignKey(
        'core.Room',
        on_delete=models.CASCADE,
        related_name='reservation_requests',
        verbose_name=_("Salle")
    )
    # CHANGED: Date range instead of duration
    start_datetime = models.DateTimeField(
        verbose_name=_("Date et heure de début"),
        null=True,
        blank=True
    )
    end_datetime = models.DateTimeField(
        verbose_name=_("Date et heure de fin"),
        null=True,
        blank=True
    )
    # DEPRECATED: Keep for backwards compatibility
    requested_datetime = models.DateTimeField(
        verbose_name=_("Date et heure (ancien)"),
        null=True,
        blank=True
    )
    duration = models.IntegerField(
        verbose_name=_("Durée (heures) (ancien)"),
        null=True,
        blank=True
    )
    reason = models.TextField(
        verbose_name=_("Motif")
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_("Statut")
    )
    is_exam = models.BooleanField(
        default=False,
        verbose_name=_("Pour un examen")
    )
    admin_notes = models.TextField(
        blank=True,
        verbose_name=_("Notes de l'administrateur")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date de création")
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date de traitement")
    )
    processed_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='processed_reservations',
        verbose_name=_("Traité par")
    )
    
    class Meta:
        verbose_name = _("Demande de Réservation")
        verbose_name_plural = _("Demandes de Réservation")
        ordering = ['-created_at']
    
    def __str__(self):
        requester = self.teacher.user.get_full_name() if self.teacher else self.association.name
        start = self.start_datetime or self.requested_datetime
        return f"{self.room.name} - {requester} ({start.strftime('%d/%m/%Y')})"
    
    def get_end_datetime(self):
        """Calculate end datetime - use new fields or legacy fields"""
        if self.end_datetime:
            return self.end_datetime
        elif self.requested_datetime and self.duration:
            from datetime import timedelta
            return self.requested_datetime + timedelta(hours=self.duration)
        return None
    
    def get_start_datetime(self):
        """Get start datetime - use new fields or legacy fields"""
        return self.start_datetime or self.requested_datetime
    
    def get_duration_hours(self):
        """Calculate duration in hours"""
        start = self.get_start_datetime()
        end = self.get_end_datetime()
        if start and end:
            delta = end - start
            return delta.total_seconds() / 3600
        return self.duration or 0
    
    def check_program_conflicts(self):
        """
        Check if any group in the selected program has a session or timetable entry
        at the requested time. Returns conflicting Session queryset for display.
        Also checks TimetableEntry (the published timetable grid).
        """
        if not self.program:
            return Session.objects.none()
        
        from apps.core.models import Group
        
        start = self.get_start_datetime()
        end = self.get_end_datetime()
        
        if not start or not end:
            return Session.objects.none()
        
        # Get all groups in this program
        groups = Group.objects.filter(program=self.program)
        
        # 1. Find conflicting sessions
        conflicts = Session.objects.filter(
            groups__in=groups,
            start_datetime__lt=end,
            end_datetime__gt=start,
            is_validated=True
        ).distinct()
        
        if conflicts.exists():
            return conflicts
        
        # 2. Also check TimetableEntry (the actual weekly schedule)
        DAY_MAP = {
            0: 'MON', 1: 'TUE', 2: 'WED',
            3: 'THU', 4: 'FRI', 5: 'SAT',
        }
        day_code = DAY_MAP.get(start.weekday())
        if not day_code:
            return Session.objects.none()
        
        # Find which time slot(s) overlap
        start_time = start.time()
        end_time = end.time()
        
        overlapping_slots = TimeSlot.objects.filter(
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        
        if not overlapping_slots.exists():
            return Session.objects.none()
        
        # Check published timetable for this program
        timetable = Timetable.objects.filter(
            program=self.program,
            is_published=True
        ).order_by('-created_at').first()
        
        if not timetable:
            return Session.objects.none()
        
        # Check if any TimetableEntry exists at this day/slot for any group
        timetable_conflicts = TimetableEntry.objects.filter(
            timetable=timetable,
            day_of_week=day_code,
            time_slot__in=overlapping_slots
        )
        
        if groups.exists():
            timetable_conflicts = timetable_conflicts.filter(
                models.Q(study_group__in=groups) | models.Q(study_group__isnull=True)
            )
        
        if timetable_conflicts.exists():
            # Return as a "fake" Session queryset for display compatibility
            # Create queryset that shows timetable conflicts via annotation
            conflict_info = timetable_conflicts.first()
            # We can't return TimetableEntry as Session, so raise via a different mechanism
            # Store the conflict details for the form to read
            self._timetable_conflicts = timetable_conflicts
            # Return empty session queryset — the form will check _timetable_conflicts
            return Session.objects.none()
        
        return Session.objects.none()

    def check_teacher_conflicts(self):
        """
        Check if the requesting teacher has a session or timetable entry
        at the requested time (prevent double-booking).
        """
        if not self.teacher:
            return Session.objects.none()
        
        start = self.get_start_datetime()
        end = self.get_end_datetime()
        
        if not start or not end:
            return Session.objects.none()
            
        # 1. Find conflicting sessions where this teacher is teaching
        conflicts = Session.objects.filter(
            teacher=self.teacher,
            start_datetime__lt=end,
            end_datetime__gt=start,
            is_validated=True
        ).distinct()
        
        if conflicts.exists():
            return conflicts
            
        # 2. Also check TimetableEntry (published timetables)
        DAY_MAP = {
            0: 'MON', 1: 'TUE', 2: 'WED',
            3: 'THU', 4: 'FRI', 5: 'SAT',
        }
        day_code = DAY_MAP.get(start.weekday())
        if not day_code:
            return Session.objects.none()
            
        start_time = start.time()
        end_time = end.time()
        
        overlapping_slots = TimeSlot.objects.filter(
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        
        if not overlapping_slots.exists():
            return Session.objects.none()
            
        # Check any published timetable entry for this teacher
        timetable_conflicts = TimetableEntry.objects.filter(
            teacher=self.teacher,
            timetable__is_published=True,
            day_of_week=day_code,
            time_slot__in=overlapping_slots
        )
        
        if timetable_conflicts.exists():
            # Store the conflict details for the form to read
            self._teacher_timetable_conflicts = timetable_conflicts
            return Session.objects.none()
            
        return Session.objects.none()

    
    def approve(self, admin_user):
        """Approve reservation, create sessions, and send notifications"""
        from django.utils import timezone
        from apps.notifications.services import NotificationService
        
        self.status = 'approved'
        self.processed_at = timezone.now()
        self.processed_by = admin_user
        self.save()
        
        # Create session(s) based on reservation type
        if self.teacher:
            if self.reservation_type == 'recurring':
                self._create_recurring_sessions()
            else:
                self._create_single_session()
        
        # Inject into the student timetable grid
        if self.program:
            self._inject_timetable_entry()
        
        # Notify requester
        requester = self.teacher.user if self.teacher else self.association.user
        start = self.get_start_datetime()
        NotificationService.send_notification(
            user=requester,
            notification_type='reservation_approved',
            title='Réservation approuvée',
            message=f'Votre réservation de la salle {self.room.name} pour le {start.strftime("%d/%m/%Y à %H:%M")} a été approuvée.',
            related_object=self
        )
        
        # Notify students if teacher reservation
        if self.teacher and self.program:
            self._notify_students()
    
    def _create_single_session(self):
        """Create a single one-time session"""
        from apps.core.models import Group
        
        session = Session.objects.create(
            session_type='cours',
            subject=self.subject or self.reason[:100],
            teacher=self.teacher,
            room=self.room,
            start_datetime=self.get_start_datetime(),
            end_datetime=self.get_end_datetime(),
            is_exam=self.is_exam,
            is_validated=True,
            is_recurring=False,
            parent_reservation=self
        )
        
        # Link to groups in the program
        if self.program:
            groups = Group.objects.filter(program=self.program)
            session.groups.set(groups)
    
    def _create_recurring_sessions(self):
        """Create recurring weekly sessions for the semester"""
        from apps.core.models import Group
        from datetime import timedelta
        
        # Create sessions for 16 weeks (typical semester)
        semester_weeks = 16
        
        start = self.get_start_datetime()
        end = self.get_end_datetime()
        
        if not start or not end:
            return
        
        groups = Group.objects.filter(program=self.program)
        
        for week in range(semester_weeks):
            session_start = start + timedelta(weeks=week)
            session_end = end + timedelta(weeks=week)
            
            # Skip if falls on Sunday
            if session_start.isoweekday() == 7:
                continue
            
            session = Session.objects.create(
                session_type='cours',
                subject=self.subject or self.reason[:100],
                teacher=self.teacher,
                room=self.room,
                start_datetime=session_start,
                end_datetime=session_end,
                is_exam=False,
                is_validated=True,
                is_recurring=True,
                parent_reservation=self
            )
            
            session.groups.set(groups)
    
    def _notify_students(self):
        """Notify all students in the program about the session"""
        from apps.notifications.services import NotificationService
        from apps.accounts.models import Student
        
        students = Student.objects.filter(group__program=self.program)
        
        start = self.get_start_datetime()
        end = self.get_end_datetime()
        
        if self.reservation_type == 'recurring':
            title = f"Nouvel emploi du temps - {self.subject}"
            message = (
                f"Nouvelle séance hebdomadaire ajoutée:\n"
                f"📚 Matière: {self.subject}\n"
                f"👨‍🏫 Enseignant: {self.teacher.user.get_full_name()}\n"
                f"📍 Salle: {self.room.name}\n"
                f"🕐 {start.strftime('%A')} {start.strftime('%H:%M')}-{end.strftime('%H:%M')}"
            )
        else:
            title = f"Séance ponctuelle - {self.subject}"
            message = (
                f"Séance programmée:\n"
                f"📚 {self.subject}\n"
                f"📅 {start.strftime('%d/%m/%Y')}\n"
                f"🕐 {start.strftime('%H:%M')}-{end.strftime('%H:%M')}\n"
                f"📍 Salle: {self.room.name}"
            )
        
        for student in students:
            NotificationService.send_notification(
                user=student.user,
                notification_type='session_scheduled',
                title=title,
                message=message,
                related_object=self
            )
    
    def _inject_timetable_entry(self):
        """Inject an entry into the student timetable grid when reservation is approved."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            start = self.get_start_datetime()
            if not start:
                return
            
            # Map weekday to day_of_week code
            weekday_map = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT'}
            day_code = weekday_map.get(start.weekday())
            if not day_code:
                return
            
            # Find matching TimeSlot — reservation time may not exactly match slot start
            start_time = start.time()
            time_slot = TimeSlot.objects.filter(
                start_time__lte=start_time,
                end_time__gt=start_time
            ).first()
            if not time_slot:
                # Fallback: find closest slot by start_time
                time_slot = TimeSlot.objects.filter(start_time__gte=start_time).order_by('start_time').first()
                if not time_slot:
                    time_slot = TimeSlot.objects.order_by('start_time').first()
                    if not time_slot:
                        return
            
            # Get the program's published timetable
            timetable = Timetable.objects.filter(
                program=self.program,
                is_published=True
            ).order_by('-created_at').first()
            
            if not timetable:
                logger.info(f"No published timetable found for program {self.program}")
                return
            
            # Determine session type and event type
            session_type = 'exam' if self.is_exam else 'cours'
            # Map reservation_type ('one_time') to TimetableEntry event_type ('one_off')
            event_type = 'one_off' if self.reservation_type != 'recurring' else 'recurring'
            
            # Find or create a Subject for this reservation
            from apps.scheduling.models import Subject as SubjectModel
            from django.db.models import Q
            subject_obj = None
            if self.subject:
                # 1. Try exact code match
                subject_obj = SubjectModel.objects.filter(
                    code__iexact=self.subject,
                    program=self.program
                ).first()
                
                if not subject_obj:
                    # 2. Try exact name match
                    subject_obj = SubjectModel.objects.filter(
                        name__iexact=self.subject,
                        program=self.program
                    ).first()
                
                if not subject_obj:
                    # 3. Try partial name match (starts with)
                    subject_obj = SubjectModel.objects.filter(
                        name__istartswith=self.subject,
                        program=self.program
                    ).first()
            
            if not subject_obj:
                # Create a stable placeholder subject for this name
                # Instead of appending reservation ID, use the name itself to make it reusable
                subject_code = self.subject[:15].upper().strip().replace(' ', '-') if self.subject else 'RES'
                subject_obj = SubjectModel.objects.filter(code=subject_code, program=self.program).first()
                
                if not subject_obj:
                    subject_obj = SubjectModel.objects.create(
                        code=subject_code,
                        name=self.subject or self.reason[:100],
                        program=self.program,
                        teacher=self.teacher,
                        session_type=session_type if session_type != 'exam' else 'cours',
                    )
            
            # Get groups for the program
            from apps.core.models import Group
            groups = Group.objects.filter(program=self.program)
            
            if groups.exists():
                # Create one entry per group (or one with no group if none exist)
                for group in groups:
                    TimetableEntry.objects.get_or_create(
                        timetable=timetable,
                        day_of_week=day_code,
                        time_slot=time_slot,
                        study_group=group,
                        defaults={
                            'subject': subject_obj,
                            'teacher': self.teacher,
                            'room': self.room,
                            'session_type': session_type,
                            'event_type': event_type,
                            'is_exam': self.is_exam,
                            'source_reservation': self,
                            'notes': f"Auto-injecté depuis réservation #{self.pk}",
                        }
                    )
            else:
                TimetableEntry.objects.get_or_create(
                    timetable=timetable,
                    day_of_week=day_code,
                    time_slot=time_slot,
                    study_group=None,
                    defaults={
                        'subject': subject_obj,
                        'teacher': self.teacher,
                        'room': self.room,
                        'session_type': session_type,
                        'event_type': event_type,
                        'is_exam': self.is_exam,
                        'source_reservation': self,
                        'notes': f"Auto-injecté depuis réservation #{self.pk}",
                    }
                )
        except Exception as e:
            logger.error(f"Error injecting timetable entry for reservation #{self.pk}: {e}")
    
    def reject(self, admin_user, reason=''):
        """Reject reservation and notify requester"""
        from django.utils import timezone
        from apps.notifications.services import NotificationService
        
        self.status = 'rejected'
        self.admin_notes = reason
        self.processed_at = timezone.now()
        self.processed_by = admin_user
        self.save()
        
        # Notify requester
        requester = self.teacher.user if self.teacher else self.association.user
        start = self.get_start_datetime()
        NotificationService.send_notification(
            user=requester,
            notification_type='reservation_rejected',
            title='Réservation refusée',
            message=f'Votre réservation de la salle {self.room.name} a été refusée. Raison: {reason or "Non spécifiée"}',
            related_object=self
        )


class TeacherUnavailability(models.Model):
    """
    Model to track teacher unavailability periods.
    """
    
    teacher = models.ForeignKey(
        'accounts.Teacher',
        on_delete=models.CASCADE,
        related_name='unavailabilities',
        verbose_name=_("Enseignant")
    )
    start_datetime = models.DateTimeField(
        verbose_name=_("Début")
    )
    end_datetime = models.DateTimeField(
        verbose_name=_("Fin")
    )
    reason = models.TextField(
        verbose_name=_("Raison")
    )
    is_recurring = models.BooleanField(
        default=False,
        verbose_name=_("Récurrent")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date de création")
    )
    
    class Meta:
        verbose_name = _("Indisponibilité Enseignant")
        verbose_name_plural = _("Indisponibilités Enseignants")
        ordering = ['start_datetime']
    
    def __str__(self):
        return f"{self.teacher.user.get_full_name()} - {self.start_datetime.strftime('%d/%m/%Y')}"


class TimetableEntry(models.Model):
    """
    Individual entry in a semester timetable.
    Represents one cell in the weekly grid (day + time slot).
    """
    
    DAYS_OF_WEEK = [
        ('MON', 'Lundi'),
        ('TUE', 'Mardi'),
        ('WED', 'Mercredi'),
        ('THU', 'Jeudi'),
        ('FRI', 'Vendredi'),
        ('SAT', 'Samedi'),
    ]
    
    DAY_ORDER = {'MON': 1, 'TUE': 2, 'WED': 3, 'THU': 4, 'FRI': 5, 'SAT': 6}
    
    timetable = models.ForeignKey(
        Timetable,
        on_delete=models.CASCADE,
        related_name='entries',
        verbose_name=_("Emploi du temps")
    )
    day_of_week = models.CharField(
        max_length=3,
        choices=DAYS_OF_WEEK,
        verbose_name=_("Jour")
    )
    time_slot = models.ForeignKey(
        TimeSlot,
        on_delete=models.CASCADE,
        related_name='entries',
        verbose_name=_("Créneau horaire")
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='timetable_entries',
        verbose_name=_("Matière")
    )
    teacher = models.ForeignKey(
        'accounts.Teacher',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timetable_entries',
        verbose_name=_("Enseignant")
    )
    room = models.ForeignKey(
        'core.Room',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timetable_entries',
        verbose_name=_("Salle")
    )
    study_group = models.ForeignKey(
        'core.Group',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timetable_entries',
        verbose_name=_("Groupe")
    )
    session_type = models.CharField(
        max_length=20,
        choices=[
            ('cours', 'Cours'),
            ('td', 'TD'),
            ('tp', 'TP'),
            ('exam', 'Examen'),
        ],
        default='cours',
        verbose_name=_("Type de séance")
    )
    
    # Event type: recurring (standard weekly) or one-off (catch-up, exam, etc.)
    EVENT_TYPE_CHOICES = [
        ('recurring', 'Séance Récurrente'),
        ('one_off', 'Séance Ponctuelle'),
    ]
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
        default='recurring',
        verbose_name=_("Type d'événement")
    )
    is_exam = models.BooleanField(
        default=False,
        verbose_name=_("Examen")
    )
    source_reservation = models.ForeignKey(
        'scheduling.RoomReservationRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timetable_entries',
        verbose_name=_("Réservation source")
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date de création")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Date de modification")
    )
    
    class Meta:
        verbose_name = _("Entrée d'emploi du temps")
        verbose_name_plural = _("Entrées d'emploi du temps")
        ordering = ['day_of_week', 'time_slot__slot_number']
        # Prevent duplicate entries (same timetable, day, slot)
        unique_together = ['timetable', 'day_of_week', 'time_slot', 'study_group']
    
    def __str__(self):
        return f"{self.get_day_of_week_display()} {self.time_slot}: {self.subject.code}"
    
    def get_day_order(self):
        """Get day order number for sorting"""
        return self.DAY_ORDER.get(self.day_of_week, 0)
    
    def check_teacher_conflict(self):
        """
        Check if teacher has another class at same day/slot in same academic year.
        Returns conflicting entry or None.
        """
        if not self.teacher:
            return None
        
        conflicts = TimetableEntry.objects.filter(
            teacher=self.teacher,
            day_of_week=self.day_of_week,
            time_slot=self.time_slot,
            timetable__academic_year=self.timetable.academic_year,
            timetable__semester=self.timetable.semester
        ).exclude(pk=self.pk)
        
        return conflicts.first()
    
    def check_room_conflict(self):
        """
        Check if room is booked at same day/slot in same academic year/semester.
        Returns conflicting entry or None.
        """
        if not self.room:
            return None
        
        conflicts = TimetableEntry.objects.filter(
            room=self.room,
            day_of_week=self.day_of_week,
            time_slot=self.time_slot,
            timetable__academic_year=self.timetable.academic_year,
            timetable__semester=self.timetable.semester
        ).exclude(pk=self.pk)
        
        return conflicts.first()
    
    def check_group_conflict(self):
        """
        Check if study group has another class at same day/slot.
        Returns conflicting entry or None.
        """
        if not self.study_group:
            return None
        
        conflicts = TimetableEntry.objects.filter(
            study_group=self.study_group,
            day_of_week=self.day_of_week,
            time_slot=self.time_slot,
            timetable__academic_year=self.timetable.academic_year,
            timetable__semester=self.timetable.semester
        ).exclude(pk=self.pk)
        
        return conflicts.first()
    
    def get_all_conflicts(self):
        """Get all conflicts for this entry"""
        conflicts = []
        
        teacher_conflict = self.check_teacher_conflict()
        if teacher_conflict:
            conflicts.append({
                'type': 'teacher',
                'message': f"Enseignant {self.teacher} déjà assigné à {teacher_conflict.subject.code}",
                'entry': teacher_conflict
            })
        
        room_conflict = self.check_room_conflict()
        if room_conflict:
            conflicts.append({
                'type': 'room',
                'message': f"Salle {self.room} déjà réservée pour {room_conflict.subject.code}",
                'entry': room_conflict
            })
        
        group_conflict = self.check_group_conflict()
        if group_conflict:
            conflicts.append({
                'type': 'group',
                'message': f"Groupe {self.study_group} déjà assigné à {group_conflict.subject.code}",
                'entry': group_conflict
            })
        
        return conflicts


class TimetableChangeRequest(models.Model):
    """
    Model for teachers to request changes to their timetable.
    """
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvée'),
        ('rejected', 'Rejetée'),
        ('completed', 'Traitée'),
    ]

    teacher = models.ForeignKey(
        'accounts.Teacher',
        on_delete=models.CASCADE,
        related_name='timetable_change_requests',
        verbose_name=_("Enseignant")
    )
    subject = models.ForeignKey(
        'Subject',
        on_delete=models.CASCADE,
        verbose_name=_("Matière concernée")
    )
    # Optional: link to existing entry if they selected one
    current_entry = models.ForeignKey(
        'TimetableEntry', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Séance actuelle"),
        help_text=_("Si la demande concerne une séance précise")
    )
    
    desired_change = models.TextField(
        verbose_name=_("Changement souhaité"),
        help_text=_("Décrivez le changement souhaité (ex: Déplacer le cours du Lundi 8h au Mardi 10h)")
    )
    reason = models.TextField(
        verbose_name=_("Justification"),
        blank=True
    )
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name=_("Statut")
    )
    admin_notes = models.TextField(
        blank=True, 
        verbose_name=_("Notes de l'administration")
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Date de modification"))

    class Meta:
        verbose_name = _("Demande de changement")
        verbose_name_plural = _("Demandes de changement")
        ordering = ['-created_at']

    def __str__(self):
        return f"Demande de {self.teacher.user.last_name} - {self.subject.code}"
