"""
Management command to seed sample subjects for timetable generation testing.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.scheduling.models import Subject
from apps.core.models import Program
from apps.accounts.models import Teacher


class Command(BaseCommand):
    help = 'Seed sample subjects for all programs to enable timetable auto-generation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing subjects before seeding',
        )
        parser.add_argument(
            '--program',
            type=str,
            help='Only seed subjects for a specific program code (e.g., MDS, SMI)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('🎓 Seeding subjects for timetable generation...'))
        
        if options['clear']:
            Subject.objects.all().delete()
            self.stdout.write(self.style.WARNING('⚠ Cleared all existing subjects'))
        
        # Get first available teacher (required for scheduling)
        teacher = Teacher.objects.first()
        if not teacher:
            self.stdout.write(self.style.ERROR(
                '❌ No teachers found. Please create at least one teacher first:\n'
                '   python manage.py createsuperuser (then add teacher profile)'
            ))
            return
        
        self.stdout.write(f'   Using teacher: {teacher.user.get_full_name() or teacher.user.username}')
        
        # Sample subjects data for different programs
        subjects_by_program = {
            # Master Data Science
            'MDS': [
                {'code': 'MDS_M1', 'name': 'Mathématiques pour la Data Science', 'semester': 1, 'hours': 4.5, 'type': 'cours'},
                {'code': 'MDS_SD1', 'name': 'Structures de Données Avancées', 'semester': 1, 'hours': 4.5, 'type': 'td'},
                {'code': 'MDS_BD1', 'name': 'Fondamentaux des Bases de Données', 'semester': 1, 'hours': 3.0, 'type': 'cours'},
                {'code': 'MDS_AA1', 'name': 'Algorithmique Avancée', 'semester': 1, 'hours': 4.5, 'type': 'td'},
                {'code': 'MDS_WEB1', 'name': 'Développement Web', 'semester': 1, 'hours': 3.0, 'type': 'tp', 'lab': True},
                {'code': 'MDS_SS1', 'name': 'Soft Skills & Communication', 'semester': 1, 'hours': 3.0, 'type': 'cours'},
                {'code': 'MDS_ML2', 'name': 'Machine Learning', 'semester': 2, 'hours': 4.5, 'type': 'cours'},
                {'code': 'MDS_DL2', 'name': 'Deep Learning', 'semester': 2, 'hours': 3.0, 'type': 'tp', 'lab': True},
                {'code': 'MDS_BD2', 'name': 'Big Data & Hadoop', 'semester': 2, 'hours': 4.5, 'type': 'tp', 'lab': True},
            ],
            # SMI - Sciences Mathématiques et Informatique
            'SMI': [
                {'code': 'SMI_ANAL1', 'name': 'Analyse Mathématique', 'semester': 1, 'hours': 4.5, 'type': 'cours'},
                {'code': 'SMI_ALG1', 'name': 'Algèbre Linéaire', 'semester': 1, 'hours': 4.5, 'type': 'td'},
                {'code': 'SMI_PROG1', 'name': 'Programmation C', 'semester': 1, 'hours': 3.0, 'type': 'tp', 'lab': True},
                {'code': 'SMI_PHYS1', 'name': 'Physique Générale', 'semester': 1, 'hours': 3.0, 'type': 'cours'},
                {'code': 'SMI_LANG1', 'name': 'Langues & Communication', 'semester': 1, 'hours': 1.5, 'type': 'td'},
                {'code': 'SMI_ANAL2', 'name': 'Analyse Fonctionnelle', 'semester': 2, 'hours': 4.5, 'type': 'cours'},
                {'code': 'SMI_JAVA2', 'name': 'Programmation Java', 'semester': 2, 'hours': 3.0, 'type': 'tp', 'lab': True},
                {'code': 'SMI_BD2', 'name': 'Bases de Données', 'semester': 2, 'hours': 3.0, 'type': 'td'},
            ],
            # Generic for any unlisted program
            'GENERIC': [
                {'code': 'GEN_M1', 'name': 'Mathématiques', 'semester': 1, 'hours': 4.5, 'type': 'cours'},
                {'code': 'GEN_INFO1', 'name': 'Informatique', 'semester': 1, 'hours': 3.0, 'type': 'tp', 'lab': True},
                {'code': 'GEN_PHYS1', 'name': 'Physique', 'semester': 1, 'hours': 3.0, 'type': 'td'},
                {'code': 'GEN_LANG1', 'name': 'Langues', 'semester': 1, 'hours': 1.5, 'type': 'cours'},
                {'code': 'GEN_M2', 'name': 'Statistiques', 'semester': 2, 'hours': 4.5, 'type': 'cours'},
                {'code': 'GEN_INFO2', 'name': 'Programmation Avancée', 'semester': 2, 'hours': 3.0, 'type': 'tp', 'lab': True},
            ],
        }
        
        # Get programs to seed
        if options['program']:
            programs = Program.objects.filter(code__iexact=options['program'])
            if not programs.exists():
                self.stdout.write(self.style.ERROR(f'❌ Program "{options["program"]}" not found'))
                return
        else:
            programs = Program.objects.all()
        
        if not programs.exists():
            self.stdout.write(self.style.ERROR(
                '❌ No programs found. Please create programs first via Django admin.'
            ))
            return
        
        total_created = 0
        
        with transaction.atomic():
            for program in programs:
                self.stdout.write(f'\n📚 Program: {program.code} - {program.name}')
                
                # Get subjects for this program code, or use GENERIC
                program_subjects = subjects_by_program.get(
                    program.code.upper(),
                    subjects_by_program['GENERIC']
                )
                
                for subj_data in program_subjects:
                    # Generate unique code for this program
                    code = subj_data['code']
                    if program.code.upper() not in code:
                        code = f"{program.code}_{code}"
                    
                    subject, created = Subject.objects.get_or_create(
                        code=code,
                        program=program,
                        semester=subj_data['semester'],
                        defaults={
                            'name': subj_data['name'],
                            'teacher': teacher,
                            'hours_per_week': subj_data['hours'],
                            'session_type': subj_data['type'],
                            'requires_lab': subj_data.get('lab', False),
                            'is_active': True,
                        }
                    )
                    
                    if created:
                        self.stdout.write(self.style.SUCCESS(
                            f'   ✓ {code}: {subj_data["name"]} (S{subj_data["semester"]}, {subj_data["hours"]}h)'
                        ))
                        total_created += 1
                    else:
                        self.stdout.write(
                            f'   ⚠ {code}: Already exists'
                        )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✅ Created {total_created} new subjects'))
        self.stdout.write(self.style.SUCCESS(f'   Total subjects in system: {Subject.objects.count()}'))
        self.stdout.write('')
        self.stdout.write('📝 Next steps:')
        self.stdout.write('   1. Go to /scheduling/timetables/create/')
        self.stdout.write('   2. Select a program with seeded subjects')
        self.stdout.write('   3. Click "Générer" to auto-fill the timetable')
