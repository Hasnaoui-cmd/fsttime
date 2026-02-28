"""
Management command to seed the database with test data for the reservation system.
Run with: python manage.py seed_test_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.core.models import Room, Program, Group
from apps.accounts.models import Teacher, Association, Student
from apps.scheduling.models import RoomReservationRequest
from django.utils import timezone
from datetime import timedelta
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds the database with test data for the reservation system'

    def handle(self, *args, **options):
        self.stdout.write('🌱 Starting database seeding...\n')

        # 1. Create Programs
        self.stdout.write('🎓 Creating programs...')
        programs = []
        program_data = [
            ('MIA', 'Master Intelligence Artificielle', 'master', 'mathematiques_informatique'),
            ('LAD', 'Licence Analytique de Données', 'licence', 'mathematiques_informatique'),
            ('SMI', 'Sciences Mathématiques et Informatique', 'licence', 'mathematiques_informatique'),
            ('SMP', 'Sciences de la Matière Physique', 'licence', 'physique'),
        ]
        for code, name, level, dept in program_data:
            program, created = Program.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'degree_level': level,
                    'department': dept,
                    'capacity': 100
                }
            )
            programs.append(program)
            if created:
                self.stdout.write(f'  ✓ Created: {code} - {name}')

        # 2. Create Groups for each program
        self.stdout.write('\n👥 Creating groups...')
        for program in programs:
            for i in range(1, 4):  # 3 groups per program
                group_name = f'Groupe {i}'
                group, created = Group.objects.get_or_create(
                    name=group_name,
                    program=program,
                    defaults={
                        'academic_year': '2025-2026',
                        'capacity': 30
                    }
                )
                if created:
                    self.stdout.write(f'  ✓ Created: {program.code} - {group_name}')

        # 3. Create Rooms
        self.stdout.write('\n🚪 Creating rooms...')
        room_data = [
            ('Amphi A', 'amphitheatre', 200, 'Bâtiment A', 0),
            ('Amphi B', 'amphitheatre', 150, 'Bâtiment A', 0),
            ('Salle 101', 'classe', 40, 'Bâtiment B', 1),
            ('Salle 102', 'classe', 35, 'Bâtiment B', 1),
            ('Salle 103', 'classe', 30, 'Bâtiment B', 1),
            ('Labo Info 1', 'salle_info', 25, 'Bâtiment C', 2),
            ('Labo Info 2', 'salle_info', 25, 'Bâtiment C', 2),
            ('Labo Physique', 'labo', 20, 'Bâtiment D', 1),
        ]
        rooms = []
        for name, room_type, capacity, building, floor in room_data:
            room, created = Room.objects.get_or_create(
                name=name,
                defaults={
                    'room_type': room_type,
                    'capacity': capacity,
                    'building': building,
                    'floor': floor,
                    'is_active': True
                }
            )
            rooms.append(room)
            if created:
                self.stdout.write(f'  ✓ Created: {name} ({capacity} places)')

        # 4. Create Admin User
        self.stdout.write('\n👤 Creating admin user...')
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@fst.ma',
                'first_name': 'Admin',
                'last_name': 'System',
                'is_staff': True,
                'is_superuser': True,
                'role': 'admin'
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write('  ✓ Created: admin (password: admin123)')

        # 5. Create Teacher Users
        self.stdout.write('\n👨‍🏫 Creating teachers...')
        teacher_data = [
            ('teacher1', 'Mohamed', 'Benali', 'Informatique'),
            ('teacher2', 'Fatima', 'Zahra', 'Mathématiques'),
            ('teacher3', 'Ahmed', 'Khalid', 'Physique'),
        ]
        teachers = []
        for username, first, last, specialty in teacher_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@fst.ma',
                    'first_name': first,
                    'last_name': last,
                    'role': 'teacher'
                }
            )
            if created:
                user.set_password('teacher123')
                user.save()

            teacher, t_created = Teacher.objects.get_or_create(
                user=user,
                defaults={'specialty': specialty}
            )
            teachers.append(teacher)
            if created:
                self.stdout.write(f'  ✓ Created: {first} {last} ({username}/teacher123)')

        # 6. Create Association Users
        self.stdout.write('\n🏛️ Creating associations...')
        assoc_data = [
            ('assoc1', 'Club Informatique FST', 'Association étudiante informatique'),
            ('assoc2', 'Club Scientifique', 'Association de vulgarisation scientifique'),
        ]
        associations = []
        for username, name, desc in assoc_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@fst.ma',
                    'first_name': name,
                    'last_name': '',
                    'role': 'association'
                }
            )
            if created:
                user.set_password('assoc123')
                user.save()

            assoc, a_created = Association.objects.get_or_create(
                user=user,
                defaults={
                    'name': name,
                    'description': desc
                }
            )
            associations.append(assoc)
            if created:
                self.stdout.write(f'  ✓ Created: {name} ({username}/assoc123)')

        # 7. Create Student Users
        self.stdout.write('\n🧑‍🎓 Creating students...')
        groups = list(Group.objects.all())
        for i in range(1, 6):
            username = f'student{i}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@fst.ma',
                    'first_name': f'Étudiant',
                    'last_name': f'{i}',
                    'role': 'student'
                }
            )
            if created:
                user.set_password('student123')
                user.save()

            Student.objects.get_or_create(
                user=user,
                defaults={
                    'group': random.choice(groups) if groups else None,
                    'student_id': f'STU{2024}{i:04d}'
                }
            )
            if created:
                self.stdout.write(f'  ✓ Created: student{i} (student123)')

        # 8. Create Sample Reservations
        self.stdout.write('\n📅 Creating sample reservations...')
        now = timezone.now()
        statuses = ['pending', 'pending', 'approved', 'rejected']
        
        for i, teacher in enumerate(teachers):
            for j in range(2):  # 2 reservations per teacher
                start_dt = now + timedelta(days=i+j+1, hours=9)
                end_dt = start_dt + timedelta(hours=2)
                
                reservation, created = RoomReservationRequest.objects.get_or_create(
                    teacher=teacher,
                    room=random.choice(rooms),
                    start_datetime=start_dt,
                    defaults={
                        'end_datetime': end_dt,
                        'program': random.choice(programs),
                        'reason': f'Cours de rattrapage - Semaine {i+1}',
                        'status': random.choice(statuses),
                        'reservation_type': 'one_time'
                    }
                )
                if created:
                    self.stdout.write(f'  ✓ Created reservation for {teacher.user.get_full_name()}')

        # 9. Create Association Reservations
        for assoc in associations:
            start_dt = now + timedelta(days=5, hours=14)
            end_dt = start_dt + timedelta(hours=3)
            
            reservation, created = RoomReservationRequest.objects.get_or_create(
                association=assoc,
                room=rooms[0],  # Amphi A
                start_datetime=start_dt,
                defaults={
                    'end_datetime': end_dt,
                    'reason': f'Événement {assoc.name}',
                    'status': 'pending',
                    'reservation_type': 'one_time'
                }
            )
            if created:
                self.stdout.write(f'  ✓ Created reservation for {assoc.name}')

        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('✅ Database seeded successfully!'))
        self.stdout.write('='*50)
        self.stdout.write('\n📋 Test Credentials:')
        self.stdout.write('  • Admin: admin / admin123')
        self.stdout.write('  • Teacher: teacher1 / teacher123')
        self.stdout.write('  • Association: assoc1 / assoc123')
        self.stdout.write('  • Student: student1 / student123')
        self.stdout.write('\n🔗 URLs:')
        self.stdout.write('  • Admin Dashboard: /dashboard/')
        self.stdout.write('  • Teacher Reservation: /scheduling/teacher/reservation/')
        self.stdout.write('  • Reservation List: /scheduling/reservations/')
        self.stdout.write('')
