"""
Debug command to check timetable generation prerequisites.
Run: python manage.py debug_timetable
"""

from django.core.management.base import BaseCommand
from apps.scheduling.models import TimeSlot, Subject, TimetableEntry, Timetable
from apps.core.models import Room, Program
from apps.accounts.models import Teacher


class Command(BaseCommand):
    help = 'Debug timetable generation prerequisites'

    def add_arguments(self, parser):
        parser.add_argument(
            '--timetable',
            type=int,
            help='Check specific timetable by ID',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('\n=== TIMETABLE GENERATION DEBUG ===\n'))
        
        # Check TimeSlots
        slots = TimeSlot.objects.all()
        self.stdout.write(f'📅 TimeSlots: {slots.count()}')
        if not slots.exists():
            self.stdout.write(self.style.ERROR('   ❌ NO TimeSlots! Run: python manage.py seed_timeslots'))
        else:
            for slot in slots:
                self.stdout.write(f'   - Slot {slot.slot_number}: {slot.start_time} - {slot.end_time}')
        
        # Check Rooms
        rooms = Room.objects.filter(is_active=True)
        self.stdout.write(f'\n🏠 Active Rooms: {rooms.count()}')
        if not rooms.exists():
            self.stdout.write(self.style.ERROR('   ❌ NO Rooms! Create rooms in admin'))
        else:
            for room in rooms[:5]:
                self.stdout.write(f'   - {room.name} ({getattr(room, "room_type", "N/A")})')
        
        # Check Teachers
        teachers = Teacher.objects.all()
        self.stdout.write(f'\n👨‍🏫 Teachers: {teachers.count()}')
        if not teachers.exists():
            self.stdout.write(self.style.ERROR('   ❌ NO Teachers!'))
        else:
            for teacher in teachers[:3]:
                self.stdout.write(f'   - {teacher.user.get_full_name() or teacher.user.username}')
        
        # Check Programs
        programs = Program.objects.all()
        self.stdout.write(f'\n🎓 Programs: {programs.count()}')
        for program in programs:
            self.stdout.write(f'   - {program.code}: {program.name}')
        
        # Check Subjects
        subjects = Subject.objects.all()
        self.stdout.write(f'\n📚 Total Subjects: {subjects.count()}')
        
        # By program
        for program in programs:
            prog_subjects = Subject.objects.filter(program=program)
            self.stdout.write(f'\n   {program.code} Subjects: {prog_subjects.count()}')
            for subj in prog_subjects[:3]:
                self.stdout.write(f'      - {subj.code}: {subj.name}')
                self.stdout.write(f'        Teacher: {subj.teacher}')
                self.stdout.write(f'        Sessions: COURS={getattr(subj, "sessions_cours", "N/A")}, TD={getattr(subj, "sessions_td", "N/A")}, TP={getattr(subj, "sessions_tp", "N/A")}')
        
        # Check specific timetable
        if options['timetable']:
            self.stdout.write(f'\n\n=== TIMETABLE {options["timetable"]} ===\n')
            try:
                tt = Timetable.objects.get(pk=options['timetable'])
                self.stdout.write(f'Name: {tt.name}')
                self.stdout.write(f'Program: {tt.program}')
                self.stdout.write(f'Semester: {tt.semester}')
                
                # Inline subjects
                inline = Subject.objects.filter(timetable=tt)
                self.stdout.write(f'\nInline Subjects: {inline.count()}')
                for subj in inline:
                    self.stdout.write(f'   - {subj.code}: {subj.name}')
                    self.stdout.write(f'     Teacher: {subj.teacher}')
                    self.stdout.write(f'     COURS: {subj.sessions_cours}, TD: {subj.sessions_td}, TP: {subj.sessions_tp}')
                
                # Entries
                entries = TimetableEntry.objects.filter(timetable=tt)
                self.stdout.write(f'\nTimetableEntries: {entries.count()}')
                for entry in entries:
                    self.stdout.write(f'   - {entry.day_of_week} {entry.time_slot.start_time}: {entry.subject.code} ({entry.session_type})')
                    
            except Timetable.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Timetable {options["timetable"]} not found'))
        
        # List all timetables
        self.stdout.write(f'\n\n=== ALL TIMETABLES ===\n')
        timetables = Timetable.objects.all().order_by('-created_at')[:5]
        for tt in timetables:
            entries_count = TimetableEntry.objects.filter(timetable=tt).count()
            inline_count = Subject.objects.filter(timetable=tt).count()
            self.stdout.write(f'ID {tt.pk}: {tt.name}')
            self.stdout.write(f'   Entries: {entries_count}, Inline Subjects: {inline_count}')
        
        self.stdout.write(self.style.SUCCESS('\n=== DEBUG COMPLETE ===\n'))
