"""
Management command to populate REAL Master S2 timetable data from FST Tanger.
Source: Emploi du Temps Semestre 2 — 1ère Année Cycle Master
        Université Abdelmalek Essaâdi — Année 2025/2026

Masters included (7 total):
  1. Génie Civil (Master-GC)
  2. Bases Cellulaires et Moléculaires en Biotechnologies (Master-BCMB)
  3. Intelligence Artificielle et Sciences de Données (Master-IASD)
  4. Sécurité IT et BIG DATA (Master-SIBD)
  5. Génie des Matériaux pour Plasturgie et Métallurgie (Master-GMPM)
  6. Modélisation Mathématique et Science de Données (Master-MMSD)
  7. Génie Energétique (Master-GE)

Run with:
    python manage.py populate_masters_s2

Safe to run multiple times — uses get_or_create throughout.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta, time

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate real FST Tanger Master S2 timetable data (7 masters, 2025/2026)'

    def handle(self, *args, **options):
        from apps.core.models import Room, Program, Group
        from apps.accounts.models import Teacher
        from apps.scheduling.models import Subject, Session, TimeSlot, Timetable, TimetableEntry

        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=' * 65))
        self.stdout.write(self.style.WARNING('  FST Tanger — Master S2 Timetable Data (2025/2026)'))
        self.stdout.write(self.style.WARNING('=' * 65))
        self.stdout.write('')

        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            self.stdout.write(self.style.ERROR('❌ No superuser found. Run: python manage.py createsuperuser'))
            return

        # ─────────────────────────────────────────────────────────
        # STEP 1 — TIME SLOTS (same as S6: 09h00-10h30 etc.)
        # ─────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('⏰ Step 1: Time Slots...'))
        slots_raw = [
            (1, time(9,  0),  time(10, 30)),
            (2, time(10, 45), time(12, 15)),
            (3, time(12, 30), time(14,  0)),
            (4, time(14, 15), time(15, 45)),
            (5, time(16,  0), time(17, 30)),
        ]
        time_slots = {}
        for num, start, end in slots_raw:
            slot, created = TimeSlot.objects.get_or_create(
                slot_number=num,
                defaults={'start_time': start, 'end_time': end}
            )
            time_slots[num] = slot
            self.stdout.write(f'  {"✅" if created else "  "} Créneau {num}: {start}–{end}')
        self.stdout.write(self.style.SUCCESS(f'  → {len(time_slots)} time slots ready\n'))

        # ─────────────────────────────────────────────────────────
        # STEP 2 — ROOMS (new rooms from this PDF)
        # ─────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('🏫 Step 2: Rooms...'))
        rooms_raw = [
            # (name,                  type,         capacity, building, floor)
            ('Salle Info (Bat_B)',    'salle_info',  30, 'Bloc B', 1),
            ('Salle F01',             'classe',      45, 'Bloc F', 0),
            ('Salle F13',             'classe',      45, 'Bloc F', 1),
            ('Salle F14',             'classe',      45, 'Bloc F', 1),
            ('Salle E11',             'classe',      40, 'Bloc E', 1),
            ('Salle E23',             'classe',      40, 'Bloc E', 2),
            ('Salle E24',             'classe',      40, 'Bloc E', 2),
            ('Salle A24',             'classe',      35, 'Bloc A', 2),
            ('Salle A34',             'classe',      35, 'Bloc A', 3),
            ('Salle C05',             'classe',      35, 'Bloc C', 0),
            ('Salle G01',             'classe',      40, 'Bloc G', 0),
            ('Salle G02',             'classe',      40, 'Bloc G', 0),
            ('Salle G03',             'classe',      40, 'Bloc G', 0),
        ]
        rooms = {}
        for name, rtype, cap, building, floor in rooms_raw:
            room, created = Room.objects.get_or_create(
                name=name,
                defaults={
                    'room_type': rtype,
                    'capacity':  cap,
                    'building':  building,
                    'floor':     floor,
                    'is_active': True,
                }
            )
            rooms[name] = room
            self.stdout.write(f'  {"✅" if created else "  "} {name}')
        self.stdout.write(self.style.SUCCESS(f'  → {len(rooms)} rooms ready\n'))

        # ─────────────────────────────────────────────────────────
        # STEP 3 — TEACHERS (one responsible per master + modules)
        # ─────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('👨‍🏫 Step 3: Teachers...'))
        teachers_raw = [
            # username               first           last               dept                          specialization                  emp_id
            ('pr_m_cherkaoui',      'Noureddine',   'Cherkaoui',       'genie_civil',                'beton_arme_precontraint',      'PM001'),
            ('pr_m_el_idrissi',     'Fatima',        'El Idrissi',      'genie_civil',                'routes_parasismique',          'PM002'),
            ('pr_m_benali',         'Hicham',        'Benali',          'genie_civil',                'transferts_thermiques',        'PM003'),
            ('pr_m_tahiri',         'Soumia',        'Tahiri',          'biologie',                   'microbiologie_appliquee',      'PM004'),
            ('pr_m_alaoui',         'Reda',          'Alaoui',          'biologie',                   'genomique_proteomique',        'PM005'),
            ('pr_m_el_ouali',       'Nadia',         'El Ouali',        'biologie',                   'biotechnologie_valorisation',  'PM006'),
            ('pr_m_hajji',          'Khalid',        'Hajji',           'mathematiques_informatique', 'bigdata_systemes_distribues',  'PM007'),
            ('pr_m_chraibi',        'Imane',         'Chraibi',         'mathematiques_informatique', 'iot_ia',                       'PM008'),
            ('pr_m_bouzid',         'Yassine',       'Bouzid',          'mathematiques_informatique', 'metaheuristiques_nlp',         'PM009'),
            ('pr_m_moussaoui',      'Sanae',         'Moussaoui',       'mathematiques_informatique', 'securite_it_cloud',            'PM010'),
            ('pr_m_el_bakkali',     'Abderrahim',   'El Bakkali',       'mathematiques_informatique', 'cryptographie_bigdata',        'PM011'),
            ('pr_m_benmoussa',      'Loubna',        'Benmoussa',       'chimie',                     'materiaux_metallurgie',        'PM012'),
            ('pr_m_zouak',          'Driss',         'Zouak',           'chimie',                     'plasturgie_surfaces',          'PM013'),
            ('pr_m_filali',         'Mohammed',      'Filali',          'mathematiques_informatique', 'analyse_numerique_edp',        'PM014'),
            ('pr_m_rifi',           'Hanane',        'Rifi',            'mathematiques_informatique', 'statistiques_modelisation',    'PM015'),
            ('pr_m_kettani',        'Aziz',          'Kettani',         'energies',                   'genie_energetique_eolien',     'PM016'),
            ('pr_m_lahlou',         'Meryem',        'Lahlou',          'energies',                   'procedes_automatique',         'PM017'),
        ]

        teachers = {}
        for username, first, last, dept, spec, emp_id in teachers_raw:
            user, u_created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email':      f'{username}@fst-tanger.ac.ma',
                    'first_name': first,
                    'last_name':  last,
                    'role':       'teacher',
                }
            )
            if u_created:
                user.set_password('prof123')
                user.save()
            teacher, _ = Teacher.objects.get_or_create(
                user=user,
                defaults={
                    'department':     dept,
                    'specialization': spec,
                    'employee_id':    emp_id,
                }
            )
            teachers[username] = teacher
            self.stdout.write(f'  {"✅" if u_created else "  "} Pr. {first} {last}')
        self.stdout.write(self.style.SUCCESS(f'  → {len(teachers)} teachers ready\n'))

        # ─────────────────────────────────────────────────────────
        # STEP 4 — PROGRAMS & GROUPS
        # ─────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('🎓 Step 4: Programs & Groups...'))
        programs_raw = [
            # (code,          name,                                               dept,                         head_key,          cap)
            ('MST-GC',   'Master Génie Civil',                                    'genie_civil',                'pr_m_cherkaoui',  20),
            ('MST-BCMB', 'Master Bases Cellulaires et Moléculaires Biotechnologies','biologie',                 'pr_m_tahiri',     20),
            ('MST-IASD', 'Master Intelligence Artificielle et Sciences de Données','mathematiques_informatique','pr_m_hajji',      25),
            ('MST-SIBD', 'Master Sécurité IT et BIG DATA',                        'mathematiques_informatique', 'pr_m_moussaoui',  25),
            ('MST-GMPM', 'Master Génie des Matériaux Plasturgie et Métallurgie',  'chimie',                     'pr_m_benmoussa',  20),
            ('MST-MMSD', 'Master Modélisation Mathématique et Science de Données','mathematiques_informatique', 'pr_m_filali',     20),
            ('MST-GE',   'Master Génie Energétique',                              'energies',                   'pr_m_kettani',    20),
        ]

        programs = {}
        groups   = {}
        for code, name, dept, head_key, cap in programs_raw:
            prog, p_created = Program.objects.get_or_create(
                code=code,
                defaults={
                    'name':         name,
                    'department':   dept,
                    'degree_level': 'master',
                }
            )
            if head_key in teachers:
                prog.program_head = teachers[head_key]
                prog.save()
            programs[code] = prog
            grp, _ = Group.objects.get_or_create(
                name='Groupe 1',
                program=prog,
                defaults={'capacity': cap, 'academic_year': '2025-2026'}
            )
            groups[code] = [grp]
            self.stdout.write(f'  {"✅" if p_created else "  "} {code}: {name}')
        self.stdout.write(self.style.SUCCESS(f'  → {len(programs)} programs ready\n'))

        # ─────────────────────────────────────────────────────────
        # STEP 5 — SUBJECTS (6 modules per master = 42 subjects)
        # ─────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('📚 Step 5: Subjects...'))
        subjects_raw = [
            # ── Master Génie Civil ────────────────────────────────
            ('MST-GC-M21', 'Béton Armé',                               'MST-GC',   'pr_m_cherkaoui', 2),
            ('MST-GC-M22', 'Béton Précontraint',                       'MST-GC',   'pr_m_cherkaoui', 2),
            ('MST-GC-M23', 'Routes',                                   'MST-GC',   'pr_m_el_idrissi',2),
            ('MST-GC-M24', 'Procédés Généraux de Construction',        'MST-GC',   'pr_m_el_idrissi',2),
            ('MST-GC-M25', 'Dynamique et Calcul Parasismique',         'MST-GC',   'pr_m_benali',    2),
            ('MST-GC-M26', 'Transferts Thermiques et Acoustique',      'MST-GC',   'pr_m_benali',    2),

            # ── Master BCMB ───────────────────────────────────────
            ('MST-BCMB-M21', 'Microbiologie Appliquée',                'MST-BCMB', 'pr_m_tahiri',    2),
            ('MST-BCMB-M22', 'Génomique',                              'MST-BCMB', 'pr_m_alaoui',    2),
            ('MST-BCMB-M23', 'Concepts de Base en Génétique Quantitative','MST-BCMB','pr_m_alaoui',  2),
            ('MST-BCMB-M24', 'Système de Management Intégré QSE',      'MST-BCMB', 'pr_m_el_ouali',  2),
            ('MST-BCMB-M25', 'Technologie de Transformation Bio-ressources','MST-BCMB','pr_m_el_ouali',2),
            ('MST-BCMB-M26', 'Protéomique',                            'MST-BCMB', 'pr_m_alaoui',    2),

            # ── Master IASD ───────────────────────────────────────
            ('MST-IASD-M121', 'Infrastructure et Architecture Systèmes Distribués & BigData','MST-IASD','pr_m_hajji',    2),
            ('MST-IASD-M122', 'Plateformes IoT Core : Technologies, Data et IA',             'MST-IASD','pr_m_chraibi',  2),
            ('MST-IASD-M123', 'Métaheuristiques & Algorithmes de Recherche Stochastique',    'MST-IASD','pr_m_bouzid',   2),
            ('MST-IASD-M124', 'DataMining & BI',                                             'MST-IASD','pr_m_hajji',    2),
            ('MST-IASD-M125', 'Soft Skills : Développement Personnel et Intelligence Émotionnelle','MST-IASD','pr_m_bouzid',2),
            ('MST-IASD-M126', 'SMA & NLP',                                                   'MST-IASD','pr_m_chraibi',  2),

            # ── Master SIBD ───────────────────────────────────────
            ('MST-SIBD-M121', 'Virtualisation, Cloud et Edge Computing',                     'MST-SIBD','pr_m_moussaoui', 2),
            ('MST-SIBD-M122', 'IA Distribuée (SMA) & Apprentissage Automatique (ML)',        'MST-SIBD','pr_m_moussaoui', 2),
            ('MST-SIBD-M123', 'Cryptographie et Sécurité des Services',                      'MST-SIBD','pr_m_el_bakkali',2),
            ('MST-SIBD-M124', 'Architecture et Technologies Big Data',                       'MST-SIBD','pr_m_el_bakkali',2),
            ('MST-SIBD-M125', 'Gestion de l\'Innovation et Management de Projet Informatique','MST-SIBD','pr_m_moussaoui',2),
            ('MST-SIBD-M126', 'Technologies IoT : Architectures, Protocoles et Applications','MST-SIBD','pr_m_el_bakkali',2),

            # ── Master GMPM ───────────────────────────────────────
            ('MST-GMPM-M21', 'Propriétés Physiques et Mécaniques des Matériaux',            'MST-GMPM','pr_m_benmoussa', 2),
            ('MST-GMPM-M22', 'Métallurgie des Poudres et Fiabilité Mécaniques',             'MST-GMPM','pr_m_benmoussa', 2),
            ('MST-GMPM-M23', 'Conception et Elaboration des Thermodurcissables',            'MST-GMPM','pr_m_zouak',     2),
            ('MST-GMPM-M24', 'Fonctionnalisation, Revêtement et Traitement des Surfaces',   'MST-GMPM','pr_m_zouak',     2),
            ('MST-GMPM-M25', 'Matériaux Catalytiques',                                      'MST-GMPM','pr_m_benmoussa', 2),
            ('MST-GMPM-M26', 'Gestion de Projets et Propriété Industrielle',                'MST-GMPM','pr_m_zouak',     2),

            # ── Master MMSD ───────────────────────────────────────
            ('MST-MMSD-M07', 'Data Warehouse et Sécurité Informatique',                     'MST-MMSD','pr_m_filali',    2),
            ('MST-MMSD-M08', 'Analyse Numérique des EDPs',                                  'MST-MMSD','pr_m_filali',    2),
            ('MST-MMSD-M09', 'Séminaire / Initiation à la Recherche',                       'MST-MMSD','pr_m_rifi',      2),
            ('MST-MMSD-M10', 'Analyse de Données, Réseau et BIG DATA',                      'MST-MMSD','pr_m_rifi',      2),
            ('MST-MMSD-M11', 'Statistiques des Valeurs Extrêmes',                           'MST-MMSD','pr_m_filali',    2),
            ('MST-MMSD-M12', 'Analyse Asymptotique et Modélisation',                        'MST-MMSD','pr_m_rifi',      2),

            # ── Master Génie Energétique ──────────────────────────
            ('MST-GE-M07', 'Métrologie Thermique et Echangeurs Thermiques',                 'MST-GE',  'pr_m_kettani',   2),
            ('MST-GE-M08', 'Production et Stockage de l\'Energie',                          'MST-GE',  'pr_m_kettani',   2),
            ('MST-GE-M09', 'Automatique et Régulation',                                     'MST-GE',  'pr_m_lahlou',    2),
            ('MST-GE-M10', 'Ingénierie des Procédés',                                       'MST-GE',  'pr_m_lahlou',    2),
            ('MST-GE-M11', 'Energie Eolienne',                                              'MST-GE',  'pr_m_kettani',   2),
            ('MST-GE-M12', 'Langues et Techniques de Communication',                        'MST-GE',  'pr_m_lahlou',    2),
        ]

        subjects = {}
        for code, name, prog_code, teacher_key, sem in subjects_raw:
            sub, created = Subject.objects.get_or_create(
                code=code,
                defaults={
                    'name':           name,
                    'program':        programs[prog_code],
                    'teacher':        teachers[teacher_key],
                    'semester':       sem,
                    'hours_per_week': 3.0,
                    'session_type':   'cours',
                }
            )
            subjects[code] = sub
            self.stdout.write(f'  {"✅" if created else "  "} {code}: {name}')
        self.stdout.write(self.style.SUCCESS(f'  → {len(subjects)} subjects ready\n'))

        # ─────────────────────────────────────────────────────────
        # STEP 6 — TIMETABLES
        # ─────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('🗓️  Step 6: Timetables...'))
        today    = timezone.now().date()
        monday   = today - timedelta(days=today.weekday())
        end_date = monday + timedelta(weeks=20)

        timetables = {}
        for code in programs:
            tt, created = Timetable.objects.get_or_create(
                program=programs[code],
                semester='S2',
                academic_year='2025-2026',
                defaults={
                    'start_date':   monday,
                    'end_date':     end_date,
                    'is_published': True,
                    'created_by':   admin,
                }
            )
            timetables[code] = tt
            self.stdout.write(f'  {"✅" if created else "  "} Timetable S2: {programs[code].name}')
        self.stdout.write(self.style.SUCCESS(f'  → {len(timetables)} timetables ready\n'))

        # ─────────────────────────────────────────────────────────
        # STEP 7 — SESSIONS & TIMETABLE ENTRIES
        # Extracted 1:1 from PDF — each row = one 3h block (2 slots)
        # day: 0=Mon 1=Tue 2=Wed 3=Thu 4=Fri 5=Sat
        # ─────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('📅 Step 7: Sessions & Timetable Entries...'))

        def make_dt(day_offset, t):
            d = monday + timedelta(days=day_offset)
            return timezone.make_aware(datetime.combine(d, t))

        DAY_MAP = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT'}

        # (prog_code, subject_code, teacher_key, room_name, day, slot_s, slot_e, stype)
        entries_raw = [

            # ══ Master Génie Civil ════════════════════════════════
            # MARDI: M22 slots 1&2 — Salle Info (Bat_B)
            ('MST-GC', 'MST-GC-M22', 'pr_m_cherkaoui', 'Salle Info (Bat_B)', 1, 1, 2, 'cours'),
            # MARDI: M25 slots 4&5 — Salle F01
            ('MST-GC', 'MST-GC-M25', 'pr_m_benali',    'Salle F01',          1, 4, 5, 'cours'),
            # MERCREDI: M24 slots 1&2 — Salle F13
            ('MST-GC', 'MST-GC-M24', 'pr_m_el_idrissi','Salle F13',          2, 1, 2, 'cours'),
            # MERCREDI: M26 slots 4&5 — Salle F01
            ('MST-GC', 'MST-GC-M26', 'pr_m_benali',    'Salle F01',          2, 4, 5, 'cours'),
            # JEUDI: M21 slots 1&2 — Salle F01
            ('MST-GC', 'MST-GC-M21', 'pr_m_cherkaoui', 'Salle F01',          3, 1, 2, 'cours'),
            # VENDREDI: M23 slots 1&2 — Salle F14
            ('MST-GC', 'MST-GC-M23', 'pr_m_el_idrissi','Salle F14',          4, 1, 2, 'cours'),

            # ══ Master BCMB ═══════════════════════════════════════
            # LUNDI: M21 slots 1&2 — Salle A34
            ('MST-BCMB', 'MST-BCMB-M21', 'pr_m_tahiri',   'Salle A34', 0, 1, 2, 'cours'),
            # MARDI: M25 slots 1&2 — Salle A34
            ('MST-BCMB', 'MST-BCMB-M25', 'pr_m_el_ouali', 'Salle A34', 1, 1, 2, 'cours'),
            # MERCREDI: M22 slots 1&2 — Salle A34
            ('MST-BCMB', 'MST-BCMB-M22', 'pr_m_alaoui',   'Salle A34', 2, 1, 2, 'cours'),
            # MERCREDI: M24 slots 4&5 — Salle A34
            ('MST-BCMB', 'MST-BCMB-M24', 'pr_m_el_ouali', 'Salle A34', 2, 4, 5, 'cours'),
            # JEUDI: M26 slots 1&2 — Salle A34
            ('MST-BCMB', 'MST-BCMB-M26', 'pr_m_alaoui',   'Salle A34', 3, 1, 2, 'cours'),
            # VENDREDI: M23 slots 1&2 — Salle A34
            ('MST-BCMB', 'MST-BCMB-M23', 'pr_m_alaoui',   'Salle A34', 4, 1, 2, 'cours'),

            # ══ Master IASD ═══════════════════════════════════════
            # LUNDI: M121 slots 1&2 — Salle E24
            ('MST-IASD', 'MST-IASD-M121', 'pr_m_hajji',   'Salle E24', 0, 1, 2, 'cours'),
            # MARDI: M122 slots 1&2 — Salle E24
            ('MST-IASD', 'MST-IASD-M122', 'pr_m_chraibi', 'Salle E24', 1, 1, 2, 'cours'),
            # MERCREDI: M123 slots 1&2 — Salle E24
            ('MST-IASD', 'MST-IASD-M123', 'pr_m_bouzid',  'Salle E24', 2, 1, 2, 'cours'),
            # JEUDI: M126 slots 1&2 — Salle E24
            ('MST-IASD', 'MST-IASD-M126', 'pr_m_chraibi', 'Salle E24', 3, 1, 2, 'cours'),
            # VENDREDI: M124 slots 1&2 — Salle E24
            ('MST-IASD', 'MST-IASD-M124', 'pr_m_hajji',   'Salle E24', 4, 1, 2, 'cours'),
            # VENDREDI: M125 slots 4&5 — Salle E11
            ('MST-IASD', 'MST-IASD-M125', 'pr_m_bouzid',  'Salle E11', 4, 4, 5, 'cours'),

            # ══ Master SIBD ═══════════════════════════════════════
            # LUNDI: M122 slots 1&2 — Salle E23
            ('MST-SIBD', 'MST-SIBD-M122', 'pr_m_moussaoui',  'Salle E23', 0, 1, 2, 'cours'),
            # MARDI: M126 slots 1&2 — Salle E23
            ('MST-SIBD', 'MST-SIBD-M126', 'pr_m_el_bakkali', 'Salle E23', 1, 1, 2, 'cours'),
            # MERCREDI: M121 slots 1&2 — Salle E23
            ('MST-SIBD', 'MST-SIBD-M121', 'pr_m_moussaoui',  'Salle E23', 2, 1, 2, 'cours'),
            # JEUDI: M123 slots 1&2 — Salle E23
            ('MST-SIBD', 'MST-SIBD-M123', 'pr_m_el_bakkali', 'Salle E23', 3, 1, 2, 'cours'),
            # VENDREDI: M124 slots 1&2 — Salle E23
            ('MST-SIBD', 'MST-SIBD-M124', 'pr_m_el_bakkali', 'Salle E23', 4, 1, 2, 'cours'),
            # VENDREDI: M125 slots 4&5 — Salle E11
            ('MST-SIBD', 'MST-SIBD-M125', 'pr_m_moussaoui',  'Salle E11', 4, 4, 5, 'cours'),

            # ══ Master GMPM ═══════════════════════════════════════
            # LUNDI: M26 slots 1&2 — Salle A24
            ('MST-GMPM', 'MST-GMPM-M26', 'pr_m_zouak',     'Salle A24', 0, 1, 2, 'cours'),
            # MARDI: M25 slots 1&2 — Salle A24
            ('MST-GMPM', 'MST-GMPM-M25', 'pr_m_benmoussa', 'Salle A24', 1, 1, 2, 'cours'),
            # MARDI: M22 slots 4&5 — Salle A24
            ('MST-GMPM', 'MST-GMPM-M22', 'pr_m_benmoussa', 'Salle A24', 1, 4, 5, 'cours'),
            # MERCREDI: M23 slots 1&2 — Salle A24
            ('MST-GMPM', 'MST-GMPM-M23', 'pr_m_zouak',     'Salle A24', 2, 1, 2, 'cours'),
            # JEUDI: M24 slots 1&2 — Salle A24
            ('MST-GMPM', 'MST-GMPM-M24', 'pr_m_zouak',     'Salle A24', 3, 1, 2, 'cours'),
            # VENDREDI: M21 slots 1&2 — Salle A24
            ('MST-GMPM', 'MST-GMPM-M21', 'pr_m_benmoussa', 'Salle A24', 4, 1, 2, 'cours'),

            # ══ Master MMSD ═══════════════════════════════════════
            # LUNDI: M07 slots 1&2 — Salle C05
            ('MST-MMSD', 'MST-MMSD-M07', 'pr_m_filali', 'Salle C05', 0, 1, 2, 'cours'),
            # MARDI: M10 slots 1&2 — Salle C05
            ('MST-MMSD', 'MST-MMSD-M10', 'pr_m_rifi',   'Salle C05', 1, 1, 2, 'cours'),
            # MERCREDI: M08 slots 1&2 — Salle C05
            ('MST-MMSD', 'MST-MMSD-M08', 'pr_m_filali', 'Salle C05', 2, 1, 2, 'cours'),
            # MERCREDI: M11 slots 4&5 — Salle C05
            ('MST-MMSD', 'MST-MMSD-M11', 'pr_m_filali', 'Salle C05', 2, 4, 5, 'cours'),
            # JEUDI: M09 slots 1&2 — Salle C05
            ('MST-MMSD', 'MST-MMSD-M09', 'pr_m_rifi',   'Salle C05', 3, 1, 2, 'cours'),
            # VENDREDI: M12 slots 1&2 — Salle C05
            ('MST-MMSD', 'MST-MMSD-M12', 'pr_m_rifi',   'Salle C05', 4, 1, 2, 'cours'),

            # ══ Master Génie Energétique ══════════════════════════
            # LUNDI: M11 slots 1&2 — Salle G01
            ('MST-GE', 'MST-GE-M11', 'pr_m_kettani', 'Salle G01', 0, 1, 2, 'cours'),
            # MARDI: M08 slots 1&2 — Salle G03
            ('MST-GE', 'MST-GE-M08', 'pr_m_kettani', 'Salle G03', 1, 1, 2, 'cours'),
            # MERCREDI: M12 slots 1&2 — Salle G02
            ('MST-GE', 'MST-GE-M12', 'pr_m_lahlou',  'Salle G02', 2, 1, 2, 'cours'),
            # JEUDI: M10 slots 1&2 — Salle G01
            ('MST-GE', 'MST-GE-M10', 'pr_m_lahlou',  'Salle G01', 3, 1, 2, 'cours'),
            # VENDREDI: M09 slots 1&2 — Salle G01
            ('MST-GE', 'MST-GE-M09', 'pr_m_lahlou',  'Salle G01', 4, 1, 2, 'cours'),
            # VENDREDI: M07 slots 4&5 — Salle G01
            ('MST-GE', 'MST-GE-M07', 'pr_m_kettani', 'Salle G01', 4, 4, 5, 'cours'),
        ]

        sessions_created = 0
        entries_created  = 0

        for prog_code, sub_code, teacher_key, room_name, day_off, slot_s, slot_e, stype in entries_raw:
            subject     = subjects[sub_code]
            teacher     = teachers[teacher_key]
            room        = rooms[room_name]
            program_grp = groups[prog_code][0]
            timetable   = timetables[prog_code]
            slot_start  = time_slots[slot_s]
            slot_end    = time_slots[slot_e]
            day_str     = DAY_MAP[day_off]

            start_dt = make_dt(day_off, slot_start.start_time)
            end_dt   = make_dt(day_off, slot_end.end_time)

            session = Session.objects.create(
                session_type   = stype,
                subject        = subject.name,
                teacher        = teacher,
                room           = room,
                start_datetime = start_dt,
                end_datetime   = end_dt,
                is_validated   = True,
            )
            session.groups.set([program_grp])
            sessions_created += 1

            entry, e_created = TimetableEntry.objects.get_or_create(
                timetable   = timetable,
                day_of_week = day_str,
                time_slot   = slot_start,
                study_group = program_grp,
                subject     = subject,
                defaults={
                    'teacher':      teacher,
                    'room':         room,
                    'session_type': stype,
                }
            )
            if e_created:
                entries_created += 1

            self.stdout.write(
                f'  ✅ {prog_code} | {day_str} slot{slot_s} | {sub_code} | {room_name}'
            )

        self.stdout.write(self.style.SUCCESS(
            f'\n  → {sessions_created} sessions, {entries_created} timetable entries created\n'
        ))

        # ─────────────────────────────────────────────────────────
        # SUMMARY
        # ─────────────────────────────────────────────────────────
        self.stdout.write(self.style.WARNING('=' * 65))
        self.stdout.write(self.style.SUCCESS('✅  Master S2 Data Populated Successfully!'))
        self.stdout.write(self.style.WARNING('=' * 65))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('📊 Summary:'))
        self.stdout.write(f'   Rooms:      {len(rooms)}')
        self.stdout.write(f'   Programs:   {len(programs)}')
        self.stdout.write(f'   Teachers:   {len(teachers)}')
        self.stdout.write(f'   Subjects:   {len(subjects)}')
        self.stdout.write(f'   Timetables: {len(timetables)}')
        self.stdout.write(f'   Sessions:   {sessions_created}')
        self.stdout.write(f'   Entries:    {entries_created}')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('🔑 New Teacher Logins (password: prof123):'))
        for username, first, last, *_ in teachers_raw:
            self.stdout.write(f'   {username}: Pr. {first} {last}')
        self.stdout.write('')