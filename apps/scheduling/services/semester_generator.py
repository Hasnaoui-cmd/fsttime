"""
Semester Timetable Auto-Generation Service.
Intelligently fills weekly grid with scheduled sessions,
avoiding conflicts and respecting room/subject type requirements.
Uses session counts (COURS, TD, TP) from inline subjects.
"""

import random
import logging
from collections import defaultdict
from django.db import transaction

from apps.scheduling.models import TimetableEntry, TimeSlot, Subject
from apps.core.models import Room, Group
from apps.accounts.models import Teacher

logger = logging.getLogger(__name__)


class SemesterTimetableGenerator:
    """
    Generates optimized semester timetables automatically.
    
    Algorithm:
    1. Load inline subjects from timetable OR program subjects
    2. For each subject, use sessions_cours, sessions_td, sessions_tp counts
    3. For each session:
       - Select random day (prefer Mon-Fri over Saturday)
       - Select appropriate time slot (morning for COURS, afternoon for TD/TP)
       - Validate: no teacher, room, or program conflicts
       - Find suitable room based on session type
       - Create TimetableEntry
    """
    
    def __init__(self, timetable):
        """Initialize generator with a Timetable instance."""
        self.timetable = timetable
        self.program = timetable.program
        
        # Extract semester number from timetable (S1 -> 1, S2 -> 2)
        self.semester_num = self._extract_semester_number(timetable.semester)
        
        # Days configuration
        self.days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
        self.preferred_days = ['MON', 'TUE', 'WED', 'THU', 'FRI']
        
        # Tracking conflicts
        self.teacher_schedule = defaultdict(set)
        self.room_schedule = defaultdict(set)
        self.program_schedule = defaultdict(set)
        
        # Statistics
        self.entries_created = 0
        self.unscheduled = []
        
        logger.info(f"=== Generator initialized for {timetable.name} ===")
        logger.info(f"Program: {self.program.name if self.program else 'None'}")
        logger.info(f"Semester: {self.semester_num}")
    
    def _extract_semester_number(self, semester_str):
        """Extract semester number from string like 'S1', 'S2', 'Semestre 1', etc."""
        import re
        if not semester_str:
            return 1
        match = re.search(r'(\d+)', str(semester_str))
        if match:
            return int(match.group(1))
        return 1
    
    def generate(self):
        """Main generation method."""
        try:
            with transaction.atomic():
                # Clear existing entries for this timetable
                deleted = TimetableEntry.objects.filter(timetable=self.timetable).delete()
                logger.info(f"Deleted {deleted[0]} existing entries")
                
                # Load time slots
                time_slots = list(TimeSlot.objects.all().order_by('slot_number'))
                if not time_slots:
                    return {
                        'success': False,
                        'error': "Aucun créneau horaire. Exécutez: python manage.py seed_timeslots"
                    }
                
                logger.info(f"Found {len(time_slots)} time slots")
                
                # Morning slots (1-2) and Afternoon slots (3-5)
                self.morning_slots = [ts for ts in time_slots if ts.slot_number <= 2]
                self.afternoon_slots = [ts for ts in time_slots if ts.slot_number >= 3]
                self.all_slots = time_slots
                
                # PRIORITY 1: Load inline subjects created with this timetable
                subjects = list(Subject.objects.filter(
                    timetable=self.timetable,
                    is_active=True
                ).select_related('teacher', 'teacher__user'))
                
                logger.info(f"Found {len(subjects)} inline subjects for this timetable")
                
                # PRIORITY 2: If no inline subjects, load from program
                if not subjects and self.program:
                    subjects = list(Subject.objects.filter(
                        program=self.program,
                        semester=self.semester_num,
                        is_active=True
                    ).select_related('teacher', 'teacher__user'))
                    logger.info(f"Found {len(subjects)} program subjects for semester {self.semester_num}")
                
                # PRIORITY 3: All program subjects
                if not subjects and self.program:
                    subjects = list(Subject.objects.filter(
                        program=self.program,
                        is_active=True
                    ).select_related('teacher', 'teacher__user'))
                    logger.info(f"Found {len(subjects)} all program subjects")
                
                if not subjects:
                    return {
                        'success': False,
                        'error': f"Aucune matière trouvée. Ajoutez des matières dans le formulaire ou via Admin."
                    }
                
                # Log subjects found
                for subj in subjects:
                    logger.info(f"  Subject: {subj.code} - {subj.name}")
                    logger.info(f"    Teacher: {subj.teacher}")
                    logger.info(f"    Sessions: COURS={getattr(subj, 'sessions_cours', 0)}, TD={getattr(subj, 'sessions_td', 0)}, TP={getattr(subj, 'sessions_tp', 0)}")
                
                # Load rooms
                self.rooms = list(Room.objects.filter(is_active=True))
                if not self.rooms:
                    return {
                        'success': False,
                        'error': "Aucune salle active trouvée."
                    }
                
                logger.info(f"Found {len(self.rooms)} active rooms")
                
                # Categorize rooms
                self.amphi_rooms = [r for r in self.rooms if getattr(r, 'room_type', '') == 'AMPHI' or getattr(r, 'capacity', 0) >= 100]
                self.lab_rooms = [r for r in self.rooms if getattr(r, 'room_type', '') == 'LABO']
                self.normal_rooms = [r for r in self.rooms if getattr(r, 'room_type', '') not in ['AMPHI', 'LABO']]
                
                # Fallback if no categorized rooms
                if not self.amphi_rooms:
                    self.amphi_rooms = self.rooms
                if not self.lab_rooms:
                    self.lab_rooms = self.rooms
                if not self.normal_rooms:
                    self.normal_rooms = self.rooms
                
                # Schedule each subject using session counts
                for subject in subjects:
                    sessions_created = self._schedule_subject_with_counts(subject)
                    if sessions_created > 0:
                        self.entries_created += sessions_created
                        logger.info(f"✓ Created {sessions_created} entries for {subject.code}")
                    else:
                        self.unscheduled.append(subject.code)
                        logger.warning(f"✗ Failed to schedule {subject.code}")
                
                # Verify entries were created
                final_count = TimetableEntry.objects.filter(timetable=self.timetable).count()
                logger.info(f"=== FINAL COUNT: {final_count} entries in database ===")
                
                # Update timetable status
                self.timetable.is_generated = True
                self.timetable.save()
                
                # Send notifications
                self._send_notifications()
                
                if self.entries_created == 0:
                    return {
                        'success': False,
                        'error': "Aucune séance créée. Vérifiez que les matières ont des professeurs assignés et des séances définies."
                    }
                
                return {
                    'success': True,
                    'entries_created': self.entries_created,
                    'unscheduled': self.unscheduled,
                    'message': f"✅ {self.entries_created} séances créées pour {len(subjects)} matières."
                }
                
        except Exception as e:
            import traceback
            logger.error(f"GENERATION FAILED: {str(e)}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def _schedule_subject_with_counts(self, subject):
        """
        Schedule sessions based on sessions_cours, sessions_td, sessions_tp counts.
        """
        sessions_created = 0
        
        # Get session counts (use lowercase for session_type - matches model choices)
        cours_count = getattr(subject, 'sessions_cours', 0) or 0
        td_count = getattr(subject, 'sessions_td', 0) or 0
        tp_count = getattr(subject, 'sessions_tp', 0) or 0
        
        logger.info(f"Scheduling {subject.code}: COURS={cours_count}, TD={td_count}, TP={tp_count}")
        
        # Schedule COURS sessions (morning preferred)
        for i in range(cours_count):
            if self._create_single_session(subject, 'cours', prefer_morning=True):
                sessions_created += 1
        
        # Schedule TD sessions (any time)
        for i in range(td_count):
            if self._create_single_session(subject, 'td', prefer_morning=False):
                sessions_created += 1
        
        # Schedule TP sessions (afternoon preferred, needs lab)
        for i in range(tp_count):
            if self._create_single_session(subject, 'tp', prefer_morning=False):
                sessions_created += 1
        
        # Fallback: If no session counts defined, use hours_per_week
        if cours_count == 0 and td_count == 0 and tp_count == 0:
            hours = float(subject.hours_per_week) if subject.hours_per_week else 3.0
            sessions_needed = max(1, int(hours / 1.5))
            session_type = getattr(subject, 'session_type', 'cours') or 'cours'
            
            logger.info(f"Fallback: Creating {sessions_needed} sessions of type {session_type}")
            
            for _ in range(sessions_needed):
                if self._create_single_session(subject, session_type, prefer_morning=(session_type == 'cours')):
                    sessions_created += 1
        
        return sessions_created
    
    def _create_single_session(self, subject, session_type, prefer_morning=False, max_attempts=50):
        """Create a single session for a subject."""
        
        # Check if subject has a teacher
        if not subject.teacher:
            logger.warning(f"No teacher for {subject.code} - skipping")
            return False
        
        for attempt in range(max_attempts):
            # Select day (90% prefer Mon-Fri)
            if random.random() < 0.9:
                day = random.choice(self.preferred_days)
            else:
                day = random.choice(self.days)
            
            # Select time slot
            if session_type == 'cours' and prefer_morning:
                if self.morning_slots and random.random() < 0.7:
                    time_slot = random.choice(self.morning_slots)
                else:
                    time_slot = random.choice(self.all_slots)
            elif session_type == 'tp':
                # Afternoon for TP
                if self.afternoon_slots and random.random() < 0.7:
                    time_slot = random.choice(self.afternoon_slots)
                else:
                    time_slot = random.choice(self.all_slots)
            else:
                # TD - any slot
                time_slot = random.choice(self.all_slots)
            
            # Check conflicts
            if self._has_conflict(day, time_slot, subject.teacher):
                continue
            
            # Find suitable room
            room = self._find_suitable_room(day, time_slot, session_type, subject)
            if not room:
                continue
            
            # Create entry (use lowercase session_type to match model choices!)
            try:
                entry = TimetableEntry.objects.create(
                    timetable=self.timetable,
                    day_of_week=day,
                    time_slot=time_slot,
                    subject=subject,
                    teacher=subject.teacher,
                    room=room,
                    session_type=session_type.lower()  # IMPORTANT: lowercase!
                )
                
                # Mark as used
                self._mark_used(day, time_slot, subject.teacher, room)
                
                logger.info(f"  ✓ Created: {subject.code} {session_type} on {day} at {time_slot.start_time} in {room.name}")
                return True
                
            except Exception as e:
                logger.error(f"  ✗ Error creating entry: {str(e)}")
                continue
        
        logger.warning(f"  ✗ Failed after {max_attempts} attempts for {subject.code} {session_type}")
        return False
    
    def _has_conflict(self, day, time_slot, teacher):
        """Check for scheduling conflicts."""
        key = (day, time_slot.id)
        
        # Teacher conflict
        if teacher and teacher.id in self.teacher_schedule.get(key, set()):
            return True
        
        # Program conflict
        if self.program and self.program.id in self.program_schedule.get(key, set()):
            return True
        
        return False
    
    def _find_suitable_room(self, day, time_slot, session_type, subject):
        """Find appropriate room based on session type."""
        key = (day, time_slot.id)
        used_rooms = self.room_schedule.get(key, set())
        
        # Select room pool based on session type
        if session_type == 'cours':
            room_pool = self.amphi_rooms
        elif session_type == 'tp' or getattr(subject, 'requires_lab', False):
            room_pool = self.lab_rooms
        else:
            room_pool = self.normal_rooms
        
        available = [r for r in room_pool if r.id not in used_rooms]
        
        if not available:
            available = [r for r in self.rooms if r.id not in used_rooms]
        
        return random.choice(available) if available else None
    
    def _mark_used(self, day, time_slot, teacher, room):
        """Mark resources as used."""
        key = (day, time_slot.id)
        
        if teacher:
            self.teacher_schedule[key].add(teacher.id)
        
        self.room_schedule[key].add(room.id)
        
        if self.program:
            self.program_schedule[key].add(self.program.id)
    
    def _send_notifications(self):
        """Send notifications to students and teachers."""
        try:
            from apps.notifications.services import NotificationService
            NotificationService.notify_timetable_update(self.timetable)
        except Exception as e:
            logger.error(f"Notification error: {str(e)}")
