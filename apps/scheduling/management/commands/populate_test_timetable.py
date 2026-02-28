"""
Management command to populate test timetable entries.
Usage: python manage.py populate_test_timetable
"""

from django.core.management.base import BaseCommand
from apps.scheduling.models import Timetable, TimetableEntry, TimeSlot, Subject
from apps.accounts.models import Teacher
from apps.core.models import Room
import random


class Command(BaseCommand):
    help = 'Populate test timetable entries for visual verification'

    def handle(self, *args, **options):
        # Get or create test data
        timetable = Timetable.objects.first()
        if not timetable:
            self.stdout.write(self.style.ERROR('No timetable found. Create one first.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Using timetable: {timetable} (ID: {timetable.id})'))

        # Get available resources
        time_slots = list(TimeSlot.objects.all().order_by('slot_number'))
        subjects = list(Subject.objects.filter(program=timetable.program))
        teachers = list(Teacher.objects.all())
        rooms = list(Room.objects.filter(is_active=True))

        self.stdout.write(f'Resources: {len(subjects)} subjects, {len(teachers)} teachers, {len(rooms)} rooms')

        if not subjects:
            self.stdout.write(self.style.ERROR('No subjects found for this program.'))
            return

        if not teachers:
            self.stdout.write(self.style.WARNING('No teachers found. Entries will be created without teachers.'))
            teachers = [None]

        if not rooms:
            self.stdout.write(self.style.WARNING('No rooms found. Entries will be created without rooms.'))
            rooms = [None]

        # Days of the week
        days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
        session_types = ['cours', 'td', 'tp']

        # Clear existing entries for this timetable
        deleted_count = TimetableEntry.objects.filter(timetable=timetable).delete()[0]
        self.stdout.write(f'Cleared {deleted_count} existing entries')

        # Create sample entries (about 50% filled grid)
        created_count = 0

        for day in days:
            for slot in time_slots:
                # Randomly populate about 50% of cells
                if random.random() < 0.5:
                    subject = random.choice(subjects)
                    teacher = random.choice(teachers) if teachers[0] else None
                    room = random.choice(rooms) if rooms[0] else None
                    session_type = random.choice(session_types)
                    
                    try:
                        entry = TimetableEntry.objects.create(
                            timetable=timetable,
                            day_of_week=day,
                            time_slot=slot,
                            subject=subject,
                            teacher=teacher,
                            room=room,
                            session_type=session_type
                        )
                        created_count += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Created {created_count} timetable entries'))
        self.stdout.write(f'View at: /scheduling/timetables/{timetable.id}/')
