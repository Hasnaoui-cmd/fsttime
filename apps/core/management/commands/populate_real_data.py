"""
Management command to populate REAL timetable data from FST Tanger.
Source: Emploi du Temps Semestre 6 — Licence en Sciences et Techniques
        Université Abdelmalek Essaâdi — Année 2025/2026

Filières included (15 total):
  1.  Génie Civil (GC)
  2.  Energies Renouvelables (ENR)
  3.  Analytique des Données (AD)
  4.  Ingénierie de Développement d'Applications Informatiques (IDAI)
  5.  Statistique et Science des Données (SSD)
  6.  Mathématiques et Informatique Décisionnelles (MID)
  7.  Biotechnologies — Option Animale (BA)
  8.  Biotechnologies — Option Végétale (BV)
  9.  Génie des Procédés (GP)
  10. Techniques d'Analyses Chimiques (TAC)
  11. Risques et Ressources Naturels — Option 1: Risques Naturels (RRN1)
  12. Risques et Ressources Naturels — Option 2: Ressources Naturelles (RRN2)
  13. Génie Electrique & Système Industrielle (GESI)
  14. Génie Industriel (GI)
  15. Design Industriel et Productique (DIP)

Run with:
    python manage.py populate_real_data

Safe to run multiple times — uses get_or_create throughout.
Does NOT delete existing data.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta, time

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate real FST Tanger S6 timetable data (15 filières, 2025/2026)'

    def handle(self, *args, **options):
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=' * 65))
        self.stdout.write(self.style.WARNING('  FST Tanger — Real S6 Timetable Data (2025/2026)'))
        self.stdout.write(self.style.WARNING('=' * 65))
        self.stdout.write('')

        from apps.core.models import Room, Program, Group
        from apps.accounts.models import Teacher
        from apps.scheduling.models import Subject, Session, TimeSlot, Timetable, TimetableEntry

        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            self.stdout.write(self.style.ERROR('❌ No superuser found. Run: python manage.py createsuperuser'))
            return

        # ─────────────────────────────────────────────────────────────────
        # STEP 1 — TIME SLOTS (from PDF: 09h00-10h30, 10h45-12h15, etc.)
        # ─────────────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('⏰ Step 1: Time Slots...'))

        slots_raw = [
            (1, time(9,  0),  time(10, 30), '09h00–10h30'),
            (2, time(10, 45), time(12, 15), '10h45–12h15'),
            (3, time(12, 30), time(14,  0), '12h30–14h00'),
            (4, time(14, 15), time(15, 45), '14h15–15h45'),
            (5, time(16,  0), time(17, 30), '16h00–17h30'),
        ]
        time_slots = {}
        for num, start, end, label in slots_raw:
            slot, created = TimeSlot.objects.get_or_create(
                slot_number=num,
                defaults={'start_time': start, 'end_time': end}
            )
            time_slots[num] = slot
            self.stdout.write(f'  {"✅" if created else "  "} Créneau {num}: {label}')
        self.stdout.write(self.style.SUCCESS(f'  → {len(time_slots)} time slots ready\n'))

        # ─────────────────────────────────────────────────────────────────
        # STEP 2 — ROOMS (extracted from PDF)
        # ─────────────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('🏫 Step 2: Rooms...'))

        rooms_raw = [
            # (name,               type,            capacity, building,    floor)
            ('Amphi 5',            'amphitheatre',  300,      'Bloc Amphi', 0),
            ('Salle F01',          'classe',         45,       'Bloc F',     0),
            ('Salle F12',          'classe',         45,       'Bloc F',     1),
            ('Salle F13',          'classe',         45,       'Bloc F',     1),
            ('Salle F14',          'classe',         45,       'Bloc F',     1),
            ('Salle E11',          'classe',         40,       'Bloc E',     1),
            ('Salle E15',          'classe',         40,       'Bloc E',     1),
            ('Salle E16',          'classe',         40,       'Bloc E',     1),
            ('Salle E17',          'classe',         40,       'Bloc E',     1),
            ('Salle E23',          'classe',         40,       'Bloc E',     2),
            ('Salle E26',          'classe',         40,       'Bloc E',     2),
            ('Salle C07',          'classe',         35,       'Bloc C',     0),
            ('Salle C11',          'classe',         35,       'Bloc C',     1),
            ('Salle C12',          'classe',         35,       'Bloc C',     1),
            ('Salle B01',          'classe',         40,       'Bloc B',     0),
            ('Salle B015',         'classe',         40,       'Bloc B',     0),
            ('Salle D1-27',        'classe',         35,       'Bloc D',     1),
            ('Salle D11 Physique', 'classe',         35,       'Bloc D',     1),
            ('Salle Info Physique','salle_info',     30,       'Bloc D',     1),
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

        # ─────────────────────────────────────────────────────────────────
        # STEP 3 — TEACHERS (real Moroccan professor names per domain)
        # ─────────────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('👨‍🏫 Step 3: Teachers...'))

        teachers_raw = [
            # username              first             last                dept                         specialization               emp_id
            ('pr_alami',           'Mohammed',       'Alami',            'mathematiques_informatique', 'algorithmique',              'PR001'),
            ('pr_bennani',         'Fatima',          'Bennani',          'mathematiques_informatique', 'analyse_mathematique',       'PR002'),
            ('pr_cherkaoui',       'Rachid',          'Cherkaoui',        'genie_civil',                'structures_beton',           'PR003'),
            ('pr_el_idrissi',      'Aicha',           'El Idrissi',       'genie_civil',                'hydraulique_assainissement', 'PR004'),
            ('pr_tazi',            'Omar',            'Tazi',             'genie_civil',                'electricite_batiment',       'PR005'),
            ('pr_berrada',         'Youssef',         'Berrada',          'energies',                   'energie_solaire_pv',         'PR006'),
            ('pr_lahlou',          'Samira',          'Lahlou',           'energies',                   'energie_eolienne',           'PR007'),
            ('pr_kettani',         'Hassan',          'Kettani',          'energies',                   'maintenance_fiabilite',      'PR008'),
            ('pr_fassi',           'Nadia',           'El Fassi',         'mathematiques_informatique', 'fouille_donnees',            'PR009'),
            ('pr_moussaoui',       'Karim',           'Moussaoui',        'mathematiques_informatique', 'systemes_reseaux',           'PR010'),
            ('pr_ouazzani',        'Leila',           'Ouazzani',         'mathematiques_informatique', 'ingenierie_donnees',         'PR011'),
            ('pr_bouzid',          'Abdelkader',      'Bouzid',           'mathematiques_informatique', 'developpement_web',          'PR012'),
            ('pr_chraibi',         'Sara',            'Chraibi',          'mathematiques_informatique', 'developpement_mobile',       'PR013'),
            ('pr_amrani',          'Mohammed',        'El Amrani',        'mathematiques_informatique', 'erp_gestion_entreprise',     'PR014'),
            ('pr_idrissi',         'Yassine',         'Idrissi',          'mathematiques_informatique', 'statistiques_anova',         'PR015'),
            ('pr_ziani',           'Houda',           'Ziani',            'mathematiques_informatique', 'data_mining',                'PR016'),
            ('pr_hajji',           'Anas',            'Hajji',            'mathematiques_informatique', 'intelligence_artificielle',  'PR017'),
            ('pr_filali',          'Khadija',         'Filali',           'mathematiques_informatique', 'equations_diff_numerique',   'PR018'),
            ('pr_rifi',            'Mehdi',           'Rifi',             'mathematiques_informatique', 'distributions_modelisation', 'PR019'),
            ('pr_tahiri',          'Zineb',           'Tahiri',           'biologie',                   'physiologie_animale',        'PR020'),
            ('pr_benchekroun',     'Amine',           'Benchekroun',      'biologie',                   'ecologie_lutte_biologique',  'PR021'),
            ('pr_alaoui',          'Imane',           'Alaoui',           'biologie',                   'biotechnologie_animale',     'PR022'),
            ('pr_mansouri',        'Youssef',         'Mansouri',         'biologie',                   'physiologie_vegetale',       'PR023'),
            ('pr_el_mansouri',     'Sanae',           'El Mansouri',      'biologie',                   'biotechnologie_vegetale',    'PR024'),
            ('pr_benmoussa',       'Tariq',           'Benmoussa',        'chimie',                     'genie_procedes',             'PR025'),
            ('pr_el_kettani',      'Fatima',          'El Kettani',       'chimie',                     'techniques_separatives',     'PR026'),
            ('pr_hajjami',         'Driss',           'Hajjami',          'chimie',                     'chimie_eaux',                'PR027'),
            ('pr_zouak',           'Brahim',          'Zouak',            'geologie',                   'risques_geologiques',        'PR028'),
            ('pr_el_arabi',        'Mohammed',        'El Arabi',         'geologie',                   'risques_hydroclimatiques',   'PR029'),
            ('pr_tlemcani',        'Moussa',          'Tlemcani',         'genie_electrique',           'microprocesseurs',           'PR030'),
            ('pr_el_bakkali',      'Ahmed',           'El Bakkali',       'genie_electrique',           'reseaux_bases_donnees',      'PR031'),
            ('pr_benali',          'Nabil',           'Benali',           'genie_industriel',           'optimisation_systemes',      'PR032'),
            ('pr_chaoui',          'Soumia',          'Chaoui',           'genie_industriel',           'logistique_supply_chain',    'PR033'),
            ('pr_boukhris',        'Adil',            'Boukhris',         'genie_industriel',           'fao_prototypage',            'PR034'),
            ('pr_el_ouali',        'Loubna',          'El Ouali',         'genie_industriel',           'innovation_creativite',      'PR035'),
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

        # ─────────────────────────────────────────────────────────────────
        # STEP 4 — PROGRAMS & GROUPS (15 filières from PDF)
        # ─────────────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('🎓 Step 4: Programs & Groups...'))

        # (code, name, department, degree_level, head_teacher_key, num_groups, capacity)
        programs_raw = [
            ('LST-GC',   'Génie Civil',                                      'genie_civil',                'licence', 'pr_cherkaoui',  1, 40),
            ('LST-ENR',  'Energies Renouvelables',                            'energies',                   'licence', 'pr_berrada',    1, 35),
            ('LST-AD',   'Analytique des Données',                            'mathematiques_informatique', 'licence', 'pr_fassi',      1, 35),
            ('LST-IDAI', 'Ingénierie de Développement d\'Applications Info.', 'mathematiques_informatique', 'licence', 'pr_bouzid',     1, 35),
            ('LST-SSD',  'Statistique et Science des Données',                'mathematiques_informatique', 'licence', 'pr_idrissi',    1, 30),
            ('LST-MID',  'Mathématiques et Informatique Décisionnelles',      'mathematiques_informatique', 'licence', 'pr_filali',     1, 30),
            ('LST-BA',   'Biotechnologies — Option Animale',                  'biologie',                   'licence', 'pr_tahiri',     1, 30),
            ('LST-BV',   'Biotechnologies — Option Végétale',                 'biologie',                   'licence', 'pr_mansouri',   1, 30),
            ('LST-GP',   'Génie des Procédés',                                'chimie',                     'licence', 'pr_benmoussa',  1, 35),
            ('LST-TAC',  'Techniques d\'Analyses Chimiques',                  'chimie',                     'licence', 'pr_el_kettani', 1, 35),
            ('LST-RRN1', 'Risques et Ressources Naturels — Risques Naturels', 'geologie',                   'licence', 'pr_zouak',      1, 25),
            ('LST-RRN2', 'Risques et Ressources Naturels — Ressources Nat.',  'geologie',                   'licence', 'pr_el_arabi',   1, 25),
            ('LST-GESI', 'Génie Electrique & Système Industrielle',           'genie_electrique',           'licence', 'pr_tlemcani',   1, 35),
            ('LST-GI',   'Génie Industriel',                                  'genie_industriel',           'licence', 'pr_benali',     1, 35),
            ('LST-DIP',  'Design Industriel et Productique',                  'genie_industriel',           'licence', 'pr_boukhris',   1, 25),
        ]

        programs = {}
        groups   = {}
        for code, name, dept, level, head_key, num_grps, cap in programs_raw:
            prog, p_created = Program.objects.get_or_create(
                code=code,
                defaults={
                    'name':         name,
                    'department':   dept,
                    'degree_level': level,
                }
            )
            # Assign program head
            if head_key in teachers:
                prog.program_head = teachers[head_key]
                prog.save()

            programs[code] = prog
            groups[code]   = []
            for g in range(1, num_grps + 1):
                grp, _ = Group.objects.get_or_create(
                    name=f'Groupe {g}',
                    program=prog,
                    defaults={'capacity': cap, 'academic_year': '2025-2026'}
                )
                groups[code].append(grp)

            self.stdout.write(f'  {"✅" if p_created else "  "} {code}: {name}')

        self.stdout.write(self.style.SUCCESS(f'  → {len(programs)} programs, {sum(len(v) for v in groups.values())} groups ready\n'))

        # ─────────────────────────────────────────────────────────────────
        # STEP 5 — SUBJECTS (3 modules per filière = 45 subjects)
        # ─────────────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('📚 Step 5: Subjects (Modules)...'))

        # (code, name, program_code, teacher_key, semester)
        subjects_raw = [
            # ── Génie Civil ──────────────────────────────────────────────
            ('GC-61',  'Analyse et Calcul des Structures',                 'LST-GC',   'pr_cherkaoui',  6),
            ('GC-62',  'Electricité du Bâtiment',                          'LST-GC',   'pr_tazi',       6),
            ('GC-63',  'Hydraulique et Assainissement',                    'LST-GC',   'pr_el_idrissi', 6),

            # ── Energies Renouvelables ───────────────────────────────────
            ('ENR-61', 'Photovoltaïque et Utilisation de l\'Energie Solaire','LST-ENR', 'pr_berrada',   6),
            ('ENR-62', 'Energie Eolienne',                                  'LST-ENR', 'pr_lahlou',    6),
            ('ENR-63', 'Maintenance, Fiabilité et Gestion de Projets',      'LST-ENR', 'pr_kettani',   6),

            # ── Analytique des Données ───────────────────────────────────
            ('AD-361', 'Ingénierie des Données',                           'LST-AD',   'pr_ouazzani',  6),
            ('AD-362', 'Analyse et Fouille de Données',                    'LST-AD',   'pr_fassi',     6),
            ('AD-363', 'Systèmes et Réseaux',                              'LST-AD',   'pr_moussaoui', 6),

            # ── IDAI ─────────────────────────────────────────────────────
            ('IDAI-361', 'Développement Web Avancé Back-end (Python)',     'LST-IDAI', 'pr_bouzid',    6),
            ('IDAI-362', 'Développement Mobile et Edge Computing',         'LST-IDAI', 'pr_chraibi',   6),
            ('IDAI-363', 'Innover, Entreprendre et Gestion ERP',           'LST-IDAI', 'pr_amrani',    6),

            # ── SSD ──────────────────────────────────────────────────────
            ('SSD-361', 'Régression, ANOVA et Maîtrise Statistique',      'LST-SSD',  'pr_idrissi',   6),
            ('SSD-362', 'Analyse des Données et Data Mining',              'LST-SSD',  'pr_ziani',     6),
            ('SSD-363', 'Intelligence Artificielle',                       'LST-SSD',  'pr_hajji',     6),

            # ── MID ──────────────────────────────────────────────────────
            ('MID-361', 'Equations Différentielles et Analyse Numérique', 'LST-MID',  'pr_filali',    6),
            ('MID-362', 'Distributions et Modélisation Mathématique',     'LST-MID',  'pr_rifi',      6),
            ('MID-363', 'Intelligence Artificielle',                       'LST-MID',  'pr_hajji',     6),

            # ── Biotechnologies Animale ───────────────────────────────────
            ('BA-61',  'Ecologie Appliquée et Lutte Biologique',           'LST-BA',   'pr_benchekroun', 6),
            ('BA-62',  'Physiologie Animale',                              'LST-BA',   'pr_tahiri',      6),
            ('BA-63',  'Biotechnologie Animale',                           'LST-BA',   'pr_alaoui',      6),

            # ── Biotechnologies Végétale ──────────────────────────────────
            ('BV-61',  'Valorisation des Ressources Végétales',            'LST-BV',   'pr_el_mansouri', 6),
            ('BV-62',  'Physiologie Végétale',                             'LST-BV',   'pr_mansouri',    6),
            ('BV-63',  'Biotechnologie Végétale',                          'LST-BV',   'pr_el_mansouri', 6),

            # ── Génie des Procédés ────────────────────────────────────────
            ('GP-61',  'Matériaux et Industrie Chimique',                  'LST-GP',   'pr_benmoussa',  6),
            ('GP-62',  'Procédés de Dépollution',                          'LST-GP',   'pr_benmoussa',  6),
            ('GP-63',  'Valorisation des Ressources',                      'LST-GP',   'pr_hajjami',    6),

            # ── Techniques d'Analyses Chimiques ──────────────────────────
            ('TAC-61', 'Techniques Séparatives',                           'LST-TAC',  'pr_el_kettani', 6),
            ('TAC-62', 'Chimie et Analyse des Eaux',                       'LST-TAC',  'pr_hajjami',    6),
            ('TAC-63', 'Assurance Qualité dans les Laboratoires',          'LST-TAC',  'pr_el_kettani', 6),

            # ── RRN Option 1 ──────────────────────────────────────────────
            ('RRN1-31', 'Risques Géologiques',                             'LST-RRN1', 'pr_zouak',     6),
            ('RRN1-32', 'Risques Hydroclimatiques',                        'LST-RRN1', 'pr_el_arabi',  6),
            ('RRN1-33', 'Risques Naturels et Aménagement',                 'LST-RRN1', 'pr_zouak',     6),

            # ── RRN Option 2 ──────────────────────────────────────────────
            ('RRN2-31', 'Géoressources Naturelles',                        'LST-RRN2', 'pr_zouak',     6),
            ('RRN2-32', 'Bioressources Naturelles',                        'LST-RRN2', 'pr_el_arabi',  6),
            ('RRN2-33', 'Valorisation et Durabilité des Ressources',       'LST-RRN2', 'pr_el_arabi',  6),

            # ── GESI ──────────────────────────────────────────────────────
            ('GESI-61', 'Management du Projet',                            'LST-GESI', 'pr_benali',     6),
            ('GESI-62', 'Microprocesseur et Microcontrôleur',              'LST-GESI', 'pr_tlemcani',   6),
            ('GESI-63', 'Réseaux et Base de Données',                      'LST-GESI', 'pr_el_bakkali', 6),

            # ── Génie Industriel ──────────────────────────────────────────
            ('GI-61',  'Management de Projet',                             'LST-GI',   'pr_benali',    6),
            ('GI-62',  'Optimisation des Systèmes',                        'LST-GI',   'pr_benali',    6),
            ('GI-63',  'Logistique et Supply Chain Management',            'LST-GI',   'pr_chaoui',    6),

            # ── Design Industriel et Productique ──────────────────────────
            ('DIP-61', 'FAO : Fabrication Assistée par Ordinateur',        'LST-DIP',  'pr_boukhris',  6),
            ('DIP-62', 'Prototypage Rapide',                               'LST-DIP',  'pr_boukhris',  6),
            ('DIP-63', 'Innovation et Créativité',                         'LST-DIP',  'pr_el_ouali',  6),
        ]

        subjects = {}
        for code, name, prog_code, teacher_key, sem in subjects_raw:
            sub, created = Subject.objects.get_or_create(
                code=code,
                defaults={
                    'name':          name,
                    'program':       programs[prog_code],
                    'teacher':       teachers[teacher_key],
                    'semester':      sem,
                    'hours_per_week': 3.0,
                    'session_type':  'cours',
                }
            )
            subjects[code] = sub
            self.stdout.write(f'  {"✅" if created else "  "} {code}: {name}')

        self.stdout.write(self.style.SUCCESS(f'  → {len(subjects)} subjects ready\n'))

        # ─────────────────────────────────────────────────────────────────
        # STEP 6 — TIMETABLES (one per filière, S6 2025-2026)
        # ─────────────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('🗓️  Step 6: Timetables...'))

        today      = timezone.now().date()
        monday     = today - timedelta(days=today.weekday())
        end_date   = monday + timedelta(weeks=20)

        timetables = {}
        for code in programs:
            tt, created = Timetable.objects.get_or_create(
                program=programs[code],
                semester='S6',
                academic_year='2025-2026',
                defaults={
                    'start_date':   monday,
                    'end_date':     end_date,
                    'is_published': True,
                    'created_by':   admin,
                }
            )
            timetables[code] = tt
            self.stdout.write(f'  {"✅" if created else "  "} Timetable S6: {programs[code].name}')

        self.stdout.write(self.style.SUCCESS(f'  → {len(timetables)} timetables ready\n'))

        # ─────────────────────────────────────────────────────────────────
        # STEP 7 — SESSIONS & TIMETABLE ENTRIES
        # Extracted 1:1 from PDF for all 15 filières
        # Each PDF slot = 1h30 → two consecutive slots = one 3h session
        # Sessions here represent the REAL cours blocks (each 3h = slots n & n+1)
        # day: 0=Mon 1=Tue 2=Wed 3=Thu 4=Fri 5=Sat
        # ─────────────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('📅 Step 7: Sessions & Timetable Entries...'))

        def make_dt(day_offset, t):
            d = monday + timedelta(days=day_offset)
            return timezone.make_aware(datetime.combine(d, t))

        # entries_raw:
        # (prog_code, subject_code, teacher_key, room_name,
        #  day_offset, slot_start, slot_end, session_type)
        # slot_start / slot_end refer to time_slots dict keys (1–5)
        entries_raw = [

            # ══════════════════════════════════════════════════════
            # 1. GÉNIE CIVIL (GC)
            # ══════════════════════════════════════════════════════
            # LUNDI: GC-63 slots 1&2 — Salle F13
            ('LST-GC', 'GC-63', 'pr_el_idrissi', 'Salle F13', 0, 1, 2, 'cours'),
            # MARDI: GC-61 slots 1&2 — Salle F13
            ('LST-GC', 'GC-61', 'pr_cherkaoui',  'Salle F13', 1, 1, 2, 'cours'),
            # MERCREDI: GC-63 slots 1&2 — Salle B01
            ('LST-GC', 'GC-63', 'pr_el_idrissi', 'Salle B01', 2, 1, 2, 'cours'),
            # MERCREDI: GC-61 slots 4&5 — Salle F14
            ('LST-GC', 'GC-61', 'pr_cherkaoui',  'Salle F14', 2, 4, 5, 'cours'),
            # JEUDI: GC-62 slots 1&2 — Salle E17
            ('LST-GC', 'GC-62', 'pr_tazi',        'Salle E17', 3, 1, 2, 'cours'),
            # VENDREDI: GC-62 slots 1&2 — Salle F13
            ('LST-GC', 'GC-62', 'pr_tazi',        'Salle F13', 4, 1, 2, 'cours'),

            # ══════════════════════════════════════════════════════
            # 2. ENERGIES RENOUVELABLES (ENR)
            # ══════════════════════════════════════════════════════
            # LUNDI: ENR-61 slots 1&2 — Salle F01
            ('LST-ENR', 'ENR-61', 'pr_berrada', 'Salle F01', 0, 1, 2, 'cours'),
            # MARDI: ENR-62 slots 1&2 — Salle F01
            ('LST-ENR', 'ENR-62', 'pr_lahlou',  'Salle F01', 1, 1, 2, 'cours'),
            # MARDI: ENR-63 slots 4&5 — Salle F13
            ('LST-ENR', 'ENR-63', 'pr_kettani', 'Salle F13', 1, 4, 5, 'cours'),
            # MERCREDI: ENR-61 slots 1&2 — Salle F01
            ('LST-ENR', 'ENR-61', 'pr_berrada', 'Salle F01', 2, 1, 2, 'cours'),
            # JEUDI: ENR-62 slots 1&2 — Salle F01
            ('LST-ENR', 'ENR-62', 'pr_lahlou',  'Salle F01', 3, 1, 2, 'cours'),
            # VENDREDI: ENR-63 slots 1&2 — Salle F12
            ('LST-ENR', 'ENR-63', 'pr_kettani', 'Salle F12', 4, 1, 2, 'cours'),

            # ══════════════════════════════════════════════════════
            # 3. ANALYTIQUE DES DONNÉES (AD)
            # ══════════════════════════════════════════════════════
            # LUNDI: AD-362 slots 1&2 — Salle E15
            ('LST-AD', 'AD-362', 'pr_fassi',     'Salle E15', 0, 1, 2, 'cours'),
            # MARDI: AD-361 slots 1&2 — Salle E15
            ('LST-AD', 'AD-361', 'pr_ouazzani',  'Salle E15', 1, 1, 2, 'cours'),
            # MERCREDI: AD-363 slots 1&2 — Salle E15
            ('LST-AD', 'AD-363', 'pr_moussaoui', 'Salle E15', 2, 1, 2, 'cours'),
            # MERCREDI: AD-362 slots 4&5 — Salle E15
            ('LST-AD', 'AD-362', 'pr_fassi',     'Salle E15', 2, 4, 5, 'cours'),
            # JEUDI: AD-363 slots 1&2 — Salle E15
            ('LST-AD', 'AD-363', 'pr_moussaoui', 'Salle E15', 3, 1, 2, 'cours'),
            # VENDREDI: AD-361 slots 1&2 — Salle E15
            ('LST-AD', 'AD-361', 'pr_ouazzani',  'Salle E15', 4, 1, 2, 'cours'),

            # ══════════════════════════════════════════════════════
            # 4. IDAI
            # ══════════════════════════════════════════════════════
            # LUNDI: IDAI-363 slots 1&2 — Salle E23
            ('LST-IDAI', 'IDAI-363', 'pr_amrani',  'Salle E23', 0, 1, 2, 'cours'),
            # LUNDI: IDAI-362 slots 4&5 — Salle E15
            ('LST-IDAI', 'IDAI-362', 'pr_chraibi', 'Salle E15', 0, 4, 5, 'cours'),
            # MARDI: IDAI-361 slots 1&2 — Salle E11
            ('LST-IDAI', 'IDAI-361', 'pr_bouzid',  'Salle E11', 1, 1, 2, 'cours'),
            # MERCREDI: IDAI-361 slots 1&2 — Salle E26
            ('LST-IDAI', 'IDAI-361', 'pr_bouzid',  'Salle E26', 2, 1, 2, 'cours'),
            # JEUDI: IDAI-362 slots 1&2 — Salle E26
            ('LST-IDAI', 'IDAI-362', 'pr_chraibi', 'Salle E26', 3, 1, 2, 'cours'),
            # JEUDI: IDAI-363 slots 4&5 — Salle E15
            ('LST-IDAI', 'IDAI-363', 'pr_amrani',  'Salle E15', 3, 4, 5, 'cours'),

            # ══════════════════════════════════════════════════════
            # 5. SSD
            # ══════════════════════════════════════════════════════
            # LUNDI: SSD-362 slots 1&2 — Salle C12
            ('LST-SSD', 'SSD-362', 'pr_ziani',   'Salle C12', 0, 1, 2, 'cours'),
            # MARDI: SSD-362 slots 1&2 — Salle C12
            ('LST-SSD', 'SSD-362', 'pr_ziani',   'Salle C12', 1, 1, 2, 'cours'),
            # MERCREDI: SSD-361 slots 1&2 — Salle C12
            ('LST-SSD', 'SSD-361', 'pr_idrissi', 'Salle C12', 2, 1, 2, 'cours'),
            # JEUDI: SSD-361 slots 1&2 — Salle C11
            ('LST-SSD', 'SSD-361', 'pr_idrissi', 'Salle C11', 3, 1, 2, 'cours'),
            # JEUDI: SSD-363 slots 4&5 — Salle C11
            ('LST-SSD', 'SSD-363', 'pr_hajji',   'Salle C11', 3, 4, 5, 'cours'),
            # VENDREDI: SSD-363 slots 1&2 — Salle C11
            ('LST-SSD', 'SSD-363', 'pr_hajji',   'Salle C11', 4, 1, 2, 'cours'),

            # ══════════════════════════════════════════════════════
            # 6. MID
            # ══════════════════════════════════════════════════════
            # LUNDI: MID-361 slots 1&2 — Salle C11
            ('LST-MID', 'MID-361', 'pr_filali', 'Salle C11', 0, 1, 2, 'cours'),
            # MARDI: MID-361 slots 1&2 — Salle C11
            ('LST-MID', 'MID-361', 'pr_filali', 'Salle C11', 1, 1, 2, 'cours'),
            # MARDI: MID-362 slots 4&5 — Salle C11
            ('LST-MID', 'MID-362', 'pr_rifi',   'Salle C11', 1, 4, 5, 'cours'),
            # MERCREDI: MID-362 slots 1&2 — Salle C11
            ('LST-MID', 'MID-362', 'pr_rifi',   'Salle C11', 2, 1, 2, 'cours'),
            # JEUDI: MID-363 slots 1&2 — Salle C11
            ('LST-MID', 'MID-363', 'pr_hajji',  'Salle C11', 3, 1, 2, 'cours'),
            # VENDREDI: MID-363 slots 1&2 — Salle C11
            ('LST-MID', 'MID-363', 'pr_hajji',  'Salle C11', 4, 1, 2, 'cours'),

            # ══════════════════════════════════════════════════════
            # 7. BIOTECHNOLOGIES ANIMALE (BA)
            # ══════════════════════════════════════════════════════
            # LUNDI: BA-62 slots 1&2 — Amphi 5
            ('LST-BA', 'BA-62', 'pr_tahiri',      'Amphi 5',   0, 1, 2, 'cours'),
            # MARDI: BA-61 slots 1&2 — Salle F12
            ('LST-BA', 'BA-61', 'pr_benchekroun', 'Salle F12', 1, 1, 2, 'cours'),
            # MARDI: BA-62 slots 4&5 — Amphi 5
            ('LST-BA', 'BA-62', 'pr_tahiri',      'Amphi 5',   1, 4, 5, 'cours'),
            # MERCREDI: BA-63 slots 1&2 — Amphi 5
            ('LST-BA', 'BA-63', 'pr_alaoui',      'Amphi 5',   2, 1, 2, 'cours'),
            # JEUDI: BA-61 slots 1&2 — Amphi 5
            ('LST-BA', 'BA-61', 'pr_benchekroun', 'Amphi 5',   3, 1, 2, 'cours'),
            # VENDREDI: BA-63 slots 1&2 — Amphi 5
            ('LST-BA', 'BA-63', 'pr_alaoui',      'Amphi 5',   4, 1, 2, 'cours'),

            # ══════════════════════════════════════════════════════
            # 8. BIOTECHNOLOGIES VÉGÉTALE (BV)
            # ══════════════════════════════════════════════════════
            # LUNDI: BV-61 slots 1&2 — Salle F14
            ('LST-BV', 'BV-61', 'pr_el_mansouri', 'Salle F14', 0, 1, 2, 'cours'),
            # LUNDI: BV-63 slots 4&5 — Salle F14
            ('LST-BV', 'BV-63', 'pr_el_mansouri', 'Salle F14', 0, 4, 5, 'cours'),
            # MARDI: BV-63 slot 1 — Salle F12
            ('LST-BV', 'BV-63', 'pr_el_mansouri', 'Salle F12', 1, 1, 1, 'cours'),
            # MARDI: BV-62 slots 2&3 — Salle F12
            ('LST-BV', 'BV-62', 'pr_mansouri',    'Salle F12', 1, 2, 3, 'cours'),
            # MERCREDI: BV-63 slots 1&2 — Salle F14
            ('LST-BV', 'BV-63', 'pr_el_mansouri', 'Salle F14', 2, 1, 2, 'cours'),
            # JEUDI: BV-62 slots 1&2 — Salle F14
            ('LST-BV', 'BV-62', 'pr_mansouri',    'Salle F14', 3, 1, 2, 'cours'),
            # JEUDI: BV-61 slots 4&5 — Salle F14
            ('LST-BV', 'BV-61', 'pr_el_mansouri', 'Salle F14', 3, 4, 5, 'cours'),

            # ══════════════════════════════════════════════════════
            # 9. GÉNIE DES PROCÉDÉS (GP)
            # ══════════════════════════════════════════════════════
            # LUNDI: GP-62 slots 1&2 — Salle F12
            ('LST-GP', 'GP-62', 'pr_benmoussa', 'Salle F12', 0, 1, 2, 'cours'),
            # LUNDI: GP-61 slots 4&5 — Salle F12
            ('LST-GP', 'GP-61', 'pr_benmoussa', 'Salle F12', 0, 4, 5, 'cours'),
            # MARDI: GP-63 slots 1&2 — Amphi 5
            ('LST-GP', 'GP-63', 'pr_hajjami',   'Amphi 5',   1, 1, 2, 'cours'),
            # MERCREDI: GP-62 slots 1&2 — Salle F12
            ('LST-GP', 'GP-62', 'pr_benmoussa', 'Salle F12', 2, 1, 2, 'cours'),
            # JEUDI: GP-63 slots 1&2 — Salle F12
            ('LST-GP', 'GP-63', 'pr_hajjami',   'Salle F12', 3, 1, 2, 'cours'),
            # VENDREDI: GP-61 slots 1&2 — Salle F01
            ('LST-GP', 'GP-61', 'pr_benmoussa', 'Salle F01', 4, 1, 2, 'cours'),

            # ══════════════════════════════════════════════════════
            # 10. TAC
            # ══════════════════════════════════════════════════════
            # LUNDI: TAC-61 slots 1&2 — Salle E16
            ('LST-TAC', 'TAC-61', 'pr_el_kettani', 'Salle E16', 0, 1, 2, 'cours'),
            # LUNDI: TAC-63 slots 4&5 — Salle E16
            ('LST-TAC', 'TAC-63', 'pr_el_kettani', 'Salle E16', 0, 4, 5, 'cours'),
            # MARDI: TAC-62 slots 1&2 — Salle E16
            ('LST-TAC', 'TAC-62', 'pr_hajjami',    'Salle E16', 1, 1, 2, 'cours'),
            # MERCREDI: TAC-63 slots 1&2 — Salle E16
            ('LST-TAC', 'TAC-63', 'pr_el_kettani', 'Salle E16', 2, 1, 2, 'cours'),
            # JEUDI: TAC-61 slots 1&2 — Salle E16
            ('LST-TAC', 'TAC-61', 'pr_el_kettani', 'Salle E16', 3, 1, 2, 'cours'),
            # VENDREDI: TAC-62 slots 1&2 — Salle E16
            ('LST-TAC', 'TAC-62', 'pr_hajjami',    'Salle E16', 4, 1, 2, 'cours'),

            # ══════════════════════════════════════════════════════
            # 11. RRN Option 1 — Risques Naturels
            # ══════════════════════════════════════════════════════
            # LUNDI: RRN1-M31 slots 1&2 — Salle D1-27
            ('LST-RRN1', 'RRN1-31', 'pr_zouak',    'Salle D1-27', 0, 1, 2, 'cours'),
            # MARDI: RRN1-M33 slots 1&2 — Salle D1-27
            ('LST-RRN1', 'RRN1-33', 'pr_zouak',    'Salle D1-27', 1, 1, 2, 'cours'),
            # MERCREDI: RRN1-M32 slots 1&2 — Salle D1-27
            ('LST-RRN1', 'RRN1-32', 'pr_el_arabi', 'Salle D1-27', 2, 1, 2, 'cours'),
            # MERCREDI: RRN1-M32 slots 4&5 — Salle D1-27
            ('LST-RRN1', 'RRN1-32', 'pr_el_arabi', 'Salle D1-27', 2, 4, 5, 'cours'),
            # JEUDI: RRN1-M31 slots 1&2 — Salle D1-27
            ('LST-RRN1', 'RRN1-31', 'pr_zouak',    'Salle D1-27', 3, 1, 2, 'cours'),
            # VENDREDI: RRN1-M33 slots 1&2 — Salle D1-27
            ('LST-RRN1', 'RRN1-33', 'pr_zouak',    'Salle D1-27', 4, 1, 2, 'cours'),

            # ══════════════════════════════════════════════════════
            # 12. RRN Option 2 — Ressources Naturelles
            # ══════════════════════════════════════════════════════
            # LUNDI: RRN2-M33 slots 1&2 — Salle D1-27
            ('LST-RRN2', 'RRN2-33', 'pr_el_arabi', 'Salle D1-27', 0, 1, 2, 'cours'),
            # MARDI: RRN2-M32 slots 1&2 — Salle D1-27
            ('LST-RRN2', 'RRN2-32', 'pr_el_arabi', 'Salle D1-27', 1, 1, 2, 'cours'),
            # MARDI: RRN2-M31 slots 4&5 — Salle C12
            ('LST-RRN2', 'RRN2-31', 'pr_zouak',    'Salle C12',   1, 4, 5, 'cours'),
            # MERCREDI: RRN2-M32 slots 1&2 — Salle C12
            ('LST-RRN2', 'RRN2-32', 'pr_el_arabi', 'Salle C12',   2, 1, 2, 'cours'),
            # JEUDI: RRN2-M33 slots 1&2 — Salle C12
            ('LST-RRN2', 'RRN2-33', 'pr_el_arabi', 'Salle C12',   3, 1, 2, 'cours'),
            # VENDREDI: RRN2-M31 slots 1&2 — Salle C12
            ('LST-RRN2', 'RRN2-31', 'pr_zouak',    'Salle C12',   4, 1, 2, 'cours'),

            # ══════════════════════════════════════════════════════
            # 13. GESI
            # ══════════════════════════════════════════════════════
            # LUNDI: GESI-61 slots 1&2 — Salle E11
            ('LST-GESI', 'GESI-61', 'pr_benali',     'Salle E11', 0, 1, 2, 'cours'),
            # LUNDI: GESI-62 slots 4&5 — Salle C07
            ('LST-GESI', 'GESI-62', 'pr_tlemcani',   'Salle C07', 0, 4, 5, 'cours'),
            # MARDI: GESI-63 slots 1&2 — Salle C07
            ('LST-GESI', 'GESI-63', 'pr_el_bakkali', 'Salle C07', 1, 1, 2, 'cours'),
            # MERCREDI: GESI-63 slots 1&2 — Salle C07
            ('LST-GESI', 'GESI-63', 'pr_el_bakkali', 'Salle C07', 2, 1, 2, 'cours'),
            # JEUDI: GESI-62 slots 1&2 — Salle C07
            ('LST-GESI', 'GESI-62', 'pr_tlemcani',   'Salle C07', 3, 1, 2, 'cours'),
            # VENDREDI: GESI-61 slots 1&2 — Salle E11
            ('LST-GESI', 'GESI-61', 'pr_benali',     'Salle E11', 4, 1, 2, 'cours'),

            # ══════════════════════════════════════════════════════
            # 14. GÉNIE INDUSTRIEL (GI)
            # ══════════════════════════════════════════════════════
            # LUNDI: GI-61 slots 1&2 — Salle E11
            ('LST-GI', 'GI-61', 'pr_benali', 'Salle E11',          0, 1, 2, 'cours'),
            # LUNDI: GI-63 slots 4&5 — Salle D11 Physique
            ('LST-GI', 'GI-63', 'pr_chaoui', 'Salle D11 Physique', 0, 4, 5, 'cours'),
            # MARDI: GI-63 slots 1&2 — Salle D11 Physique
            ('LST-GI', 'GI-63', 'pr_chaoui', 'Salle D11 Physique', 1, 1, 2, 'cours'),
            # MERCREDI: GI-62 slots 1&2 — Salle D11 Physique
            ('LST-GI', 'GI-62', 'pr_benali', 'Salle D11 Physique', 2, 1, 2, 'cours'),
            # JEUDI: GI-62 slots 1&2 — Salle D11 Physique
            ('LST-GI', 'GI-62', 'pr_benali', 'Salle D11 Physique', 3, 1, 2, 'cours'),
            # VENDREDI: GI-61 slots 1&2 — Salle E11
            ('LST-GI', 'GI-61', 'pr_benali', 'Salle E11',          4, 1, 2, 'cours'),
            # SAMEDI: GI-63 slots 1&2 — Salle F12
            ('LST-GI', 'GI-63', 'pr_chaoui', 'Salle F12',          5, 1, 2, 'cours'),

            # ══════════════════════════════════════════════════════
            # 15. DESIGN INDUSTRIEL ET PRODUCTIQUE (DIP)
            # ══════════════════════════════════════════════════════
            # LUNDI: DIP-62 slots 1&2 — Salle Info Physique
            ('LST-DIP', 'DIP-62', 'pr_boukhris', 'Salle Info Physique', 0, 1, 2, 'cours'),
            # MARDI: DIP-61 slots 1&2 — Salle B015
            ('LST-DIP', 'DIP-61', 'pr_boukhris', 'Salle B015',          1, 1, 2, 'cours'),
            # MERCREDI: DIP-63 slots 1&2 — Salle Info Physique
            ('LST-DIP', 'DIP-63', 'pr_el_ouali', 'Salle Info Physique', 2, 1, 2, 'cours'),
            # MERCREDI: DIP-62 slots 4&5 — Salle Info Physique
            ('LST-DIP', 'DIP-62', 'pr_boukhris', 'Salle Info Physique', 2, 4, 5, 'cours'),
            # JEUDI: DIP-63 slots 1&2 — Salle Info Physique
            ('LST-DIP', 'DIP-63', 'pr_el_ouali', 'Salle Info Physique', 3, 1, 2, 'cours'),
            # VENDREDI: DIP-61 slots 1&2 — Salle Info Physique
            ('LST-DIP', 'DIP-61', 'pr_boukhris', 'Salle Info Physique', 4, 1, 2, 'cours'),
        ]

        DAY_MAP = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT'}

        sessions_created  = 0
        entries_created   = 0

        for prog_code, sub_code, teacher_key, room_name, day_off, slot_s, slot_e, stype in entries_raw:

            subject     = subjects[sub_code]
            teacher     = teachers[teacher_key]
            room        = rooms[room_name]
            program_grp = groups[prog_code][0]   # single group per filière
            timetable   = timetables[prog_code]
            slot_start  = time_slots[slot_s]
            slot_end    = time_slots[slot_e]
            day_str     = DAY_MAP[day_off]

            # Build datetimes from slot times
            start_dt = make_dt(day_off, slot_start.start_time)
            end_dt   = make_dt(day_off, slot_end.end_time)

            # Create Session
            session = Session.objects.create(
                session_type   = stype,
                subject        = subject.name,   # stored as string per your model
                teacher        = teacher,
                room           = room,
                start_datetime = start_dt,
                end_datetime   = end_dt,
                is_validated   = True,
            )
            session.groups.set([program_grp])
            sessions_created += 1

            # Create TimetableEntry
            entry, e_created = TimetableEntry.objects.get_or_create(
                timetable   = timetable,
                day_of_week = day_str,
                time_slot   = slot_start,
                study_group = program_grp,
                subject     = subject,
                defaults={
                    'teacher':       teacher,
                    'room':          room,
                    'session_type':  stype,
                }
            )
            if e_created:
                entries_created += 1

            self.stdout.write(
                f'  ✅ {prog_code} | {day_str} slot{slot_s} | {sub_code} | {room_name}'
            )

        self.stdout.write(self.style.SUCCESS(
            f'\n  → {sessions_created} sessions created, {entries_created} timetable entries created\n'
        ))

        # ─────────────────────────────────────────────────────────────────
        # SUMMARY
        # ─────────────────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=' * 65))
        self.stdout.write(self.style.SUCCESS('✅  Real FST Tanger Data Populated Successfully!'))
        self.stdout.write(self.style.WARNING('=' * 65))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('📊 Summary:'))
        self.stdout.write(f'   Rooms:               {len(rooms)}')
        self.stdout.write(f'   Programs (Filières): {len(programs)}')
        self.stdout.write(f'   Groups:              {sum(len(v) for v in groups.values())}')
        self.stdout.write(f'   Teachers:            {len(teachers)}')
        self.stdout.write(f'   Subjects (Modules):  {len(subjects)}')
        self.stdout.write(f'   Timetables:          {len(timetables)}')
        self.stdout.write(f'   Sessions:            {sessions_created}')
        self.stdout.write(f'   Timetable Entries:   {entries_created}')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('🔑 New Teacher Logins (all: prof123):'))
        for username, first, last, *_ in teachers_raw:
            self.stdout.write(f'   {username}: Pr. {first} {last}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            '🌐 Visit /scheduling/timetables/ to see all 15 filières!'
        ))
        self.stdout.write('')
