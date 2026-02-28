"""
Intelligent Timetable Generator Service.
Uses a greedy algorithm with conflict detection to automatically
generate conflict-free schedules for academic programs.
"""

import random
from collections import defaultdict
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone


class TimetableGenerator:
    """
    Intelligent timetable generator with conflict resolution.
    
    Algorithm:
    1. Get all subjects for the program
    2. For each subject, calculate required weekly slots
    3. Iterate through available time slots
    4. Check conflicts (room, teacher, group)
    5. Assign subject to conflict-free slots
    6. Create Session objects and link to Timetable
    7. Send notifications to teachers and students
    """
    
    def __init__(self, timetable):
        """
        Initialize generator with a Timetable instance.
        
        Args:
            timetable: Timetable model instance
        """
        self.timetable = timetable
        self.errors = []
        self.warnings = []
        
        # Tracking dictionaries for conflict detection
        self.room_usage = {}  # {(day, slot_order, room_id): subject_id}
        self.teacher_usage = {}  # {(day, slot_order, teacher_id): subject_id}
        self.group_usage = {}  # {(day, slot_order, group_id): subject_id}
        
        # Statistics
        self.stats = {
            'sessions_created': 0,
            'subjects_scheduled': 0,
            'conflicts_avoided': 0,
        }
    
    def generate(self):
        """
        Main generation method.
        
        Returns:
            tuple: (success: bool, message: str)
        """
        from apps.scheduling.models import Subject, TimeSlot, Session
        from apps.core.models import Room, Group
        
        try:
            with transaction.atomic():
                # Get subjects for this program
                subjects = Subject.objects.filter(program=self.timetable.program)
                
                if not subjects.exists():
                    return False, "Aucune matière trouvée pour cette filière. Ajoutez des matières d'abord."
                
                # Get time slots
                time_slots = list(TimeSlot.objects.all())
                if not time_slots:
                    return False, "Aucun créneau horaire défini. Exécutez 'python manage.py seed_timeslots'."
                
                # Get available rooms
                rooms = list(Room.objects.filter(is_active=True))
                if not rooms:
                    return False, "Aucune salle disponible."
                
                # Get study groups
                study_groups = list(self.timetable.study_groups.all())
                if not study_groups:
                    # Use all groups from the program
                    study_groups = list(Group.objects.filter(program=self.timetable.program))
                
                # Clear existing sessions for this timetable
                self.timetable.sessions.clear()
                
                # Schedule each subject
                for subject in subjects:
                    success = self._schedule_subject(
                        subject, time_slots, rooms, study_groups
                    )
                    if success:
                        self.stats['subjects_scheduled'] += 1
                    else:
                        self.warnings.append(f"Impossible de planifier complètement: {subject.name}")
                
                # Mark timetable as generated
                self.timetable.is_generated = True
                if not self.timetable.name:
                    self.timetable.name = f"{self.timetable.program.code} - {self.timetable.semester} - {self.timetable.academic_year}"
                self.timetable.save()
                
                # Send notifications
                self._send_notifications()
                
                # Build result message
                message = (
                    f"Emploi du temps généré avec succès!\n"
                    f"• {self.stats['subjects_scheduled']} matières planifiées\n"
                    f"• {self.stats['sessions_created']} séances créées\n"
                    f"• {self.stats['conflicts_avoided']} conflits évités"
                )
                
                if self.warnings:
                    message += f"\n\n⚠️ Avertissements:\n" + "\n".join(f"• {w}" for w in self.warnings)
                
                return True, message
                
        except Exception as e:
            return False, f"Erreur lors de la génération: {str(e)}"
    
    def _schedule_subject(self, subject, time_slots, rooms, study_groups):
        """
        Schedule a single subject across the week.
        
        Args:
            subject: Subject model instance
            time_slots: List of TimeSlot instances
            rooms: List of Room instances
            study_groups: List of Group instances
            
        Returns:
            bool: True if scheduled successfully
        """
        from apps.scheduling.models import Session
        
        # Calculate slots needed
        slots_needed = subject.get_required_slots()
        slots_scheduled = 0
        
        # Track hours per day for this subject
        hours_per_day = defaultdict(float)
        max_hours_per_day = float(subject.max_hours_per_day)
        
        # Group time slots by day
        slots_by_day = defaultdict(list)
        for slot in time_slots:
            slots_by_day[slot.day_of_week].append(slot)
        
        # Randomize day order to distribute subjects
        days = list(slots_by_day.keys())
        random.shuffle(days)
        
        for day in days:
            if slots_scheduled >= slots_needed:
                break
            
            day_slots = slots_by_day[day]
            
            for time_slot in day_slots:
                if slots_scheduled >= slots_needed:
                    break
                
                # Check max hours per day for this subject
                slot_hours = time_slot.get_duration_hours()
                if hours_per_day[day] + slot_hours > max_hours_per_day:
                    continue
                
                # Find available room
                room = self._find_available_room(day, time_slot, rooms, subject)
                if not room:
                    self.stats['conflicts_avoided'] += 1
                    continue
                
                # Check teacher availability
                if subject.teacher and not self._is_teacher_available(day, time_slot, subject.teacher):
                    self.stats['conflicts_avoided'] += 1
                    continue
                
                # Check group availability
                available_groups = []
                for group in study_groups:
                    if self._is_group_available(day, time_slot, group):
                        available_groups.append(group)
                
                if not available_groups:
                    self.stats['conflicts_avoided'] += 1
                    continue
                
                # Create session
                session = self._create_session(subject, time_slot, room, available_groups)
                
                # Mark as used
                self.room_usage[(day, time_slot.slot_order, room.id)] = subject.id
                if subject.teacher:
                    self.teacher_usage[(day, time_slot.slot_order, subject.teacher.id)] = subject.id
                for group in available_groups:
                    self.group_usage[(day, time_slot.slot_order, group.id)] = subject.id
                
                slots_scheduled += 1
                hours_per_day[day] += slot_hours
                self.stats['sessions_created'] += 1
        
        return slots_scheduled >= slots_needed
    
    def _find_available_room(self, day, time_slot, rooms, subject):
        """
        Find an available room for the given time slot.
        
        Args:
            day: Day of week code
            time_slot: TimeSlot instance
            rooms: List of Room instances
            subject: Subject instance
            
        Returns:
            Room instance or None
        """
        # Filter rooms based on requirements
        suitable_rooms = []
        for room in rooms:
            # Check if room is free
            if (day, time_slot.slot_order, room.id) in self.room_usage:
                continue
            
            # Check lab requirement
            if subject.requires_lab and room.room_type not in ['tp', 'laboratoire']:
                continue
            
            suitable_rooms.append(room)
        
        if not suitable_rooms:
            return None
        
        # Prefer rooms that match the session type
        preferred = []
        for room in suitable_rooms:
            if (subject.session_type == 'cours' and room.room_type in ['amphi', 'cours']) or \
               (subject.session_type == 'td' and room.room_type in ['td', 'cours']) or \
               (subject.session_type == 'tp' and room.room_type in ['tp', 'laboratoire']):
                preferred.append(room)
        
        if preferred:
            return random.choice(preferred)
        return random.choice(suitable_rooms)
    
    def _is_teacher_available(self, day, time_slot, teacher):
        """Check if teacher is available at this time slot."""
        return (day, time_slot.slot_order, teacher.id) not in self.teacher_usage
    
    def _is_group_available(self, day, time_slot, group):
        """Check if study group is available at this time slot."""
        return (day, time_slot.slot_order, group.id) not in self.group_usage
    
    def _create_session(self, subject, time_slot, room, groups):
        """
        Create a session and link it to the timetable.
        
        Args:
            subject: Subject instance
            time_slot: TimeSlot instance
            room: Room instance
            groups: List of Group instances
            
        Returns:
            Session instance
        """
        from apps.scheduling.models import Session
        
        # Calculate session datetime based on timetable start date
        start_date = self.timetable.start_date
        
        # Handle string dates - parse to date object
        if start_date is None:
            start_date = timezone.now().date()
        elif isinstance(start_date, str):
            from datetime import date as date_type
            try:
                # Parse ISO format date string (YYYY-MM-DD)
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                start_date = timezone.now().date()
        
        # Find the first occurrence of this day
        days_map = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5}
        target_day = days_map.get(time_slot.day_of_week, 0)
        current_day = start_date.weekday()
        days_ahead = (target_day - current_day) % 7
        session_date = start_date + timedelta(days=days_ahead)

        
        # Combine date and time
        start_datetime = datetime.combine(session_date, time_slot.start_time)
        end_datetime = datetime.combine(session_date, time_slot.end_time)
        
        # Make timezone aware
        start_datetime = timezone.make_aware(start_datetime)
        end_datetime = timezone.make_aware(end_datetime)
        
        # Create session
        session = Session.objects.create(
            session_type=subject.session_type,
            subject=subject.name,
            teacher=subject.teacher,
            room=room,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            is_exam=False,
            is_validated=True,
            is_recurring=True,
            notes=f"Généré automatiquement - {subject.code}"
        )
        
        # Link to groups
        session.groups.set(groups)
        
        # Link to timetable
        self.timetable.sessions.add(session)
        
        return session
    
    def _send_notifications(self):
        """Send notifications to teachers and students about the new timetable."""
        from apps.notifications.services import NotificationService
        from apps.accounts.models import Student
        
        # Get unique teachers
        teachers = set()
        for session in self.timetable.sessions.all():
            if session.teacher:
                teachers.add(session.teacher)
        
        # Notify teachers
        for teacher in teachers:
            NotificationService.send_notification(
                user=teacher.user,
                notification_type='timetable_updated',
                title="📅 Nouvel Emploi du Temps",
                message=(
                    f"Un nouvel emploi du temps a été généré pour {self.timetable.program.name}.\n"
                    f"Semestre: {self.timetable.get_semester_display()}\n"
                    f"Année: {self.timetable.academic_year}\n"
                    f"Consultez votre emploi du temps pour voir vos séances."
                ),
                related_object=self.timetable
            )
        
        # Get students
        study_groups = list(self.timetable.study_groups.all())
        if study_groups:
            students = Student.objects.filter(group__in=study_groups)
        else:
            students = Student.objects.filter(group__program=self.timetable.program)
        
        # Notify students
        for student in students:
            NotificationService.send_notification(
                user=student.user,
                notification_type='timetable_updated',
                title="📅 Nouvel Emploi du Temps",
                message=(
                    f"Votre emploi du temps pour {self.timetable.program.name} est maintenant disponible.\n"
                    f"Semestre: {self.timetable.get_semester_display()}\n"
                    f"Année: {self.timetable.academic_year}"
                ),
                related_object=self.timetable
            )
