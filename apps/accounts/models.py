"""
User models for FSTTIME application.
Implements 5 user roles with OOP principles.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom User model with role-based access control.
    Supports 5 roles: Admin, Teacher, Student, Association, Guest
    """
    
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('teacher', 'Enseignant'),
        ('student', 'Étudiant'),
        ('association', 'Association'),
        ('guest', 'Invité'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='guest',
        verbose_name=_("Rôle")
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Téléphone")
    )
    
    class Meta:
        verbose_name = _("Utilisateur")
        verbose_name_plural = _("Utilisateurs")
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_teacher(self):
        return self.role == 'teacher'
    
    @property
    def is_student(self):
        return self.role == 'student'
    
    @property
    def is_association(self):
        return self.role == 'association'
    
    @property
    def can_reserve_room(self):
        """Teachers and associations can reserve rooms"""
        return self.role in ['teacher', 'association']


class Teacher(models.Model):
    """
    Teacher profile model linked to User.
    Stores teaching-specific information.
    """
    
    DEPARTMENT_CHOICES = [
        ('informatique', 'Département Informatique'),
        ('mathematiques', 'Département Mathématiques'),
        ('physique', 'Département Physique'),
        ('chimie', 'Département Chimie'),
        ('biologie', 'Département Biologie'),
        ('genie_civil', 'Département Génie Civil'),
        ('genie_electrique', 'Département Génie Électrique'),
        ('genie_mecanique', 'Département Génie Mécanique'),
        ('economie', 'Département Économie et Gestion'),
        ('langues', 'Département Langues et Communication'),
        ('sciences_juridiques', 'Département Sciences Juridiques'),
        ('sciences_terre', 'Département Sciences de la Terre'),
    ]
    
    SPECIALIZATION_CHOICES = [
        # Informatique
        ('informatique_generale', 'Informatique Générale'),
        ('intelligence_artificielle', 'Intelligence Artificielle'),
        ('reseaux_securite', 'Réseaux et Sécurité'),
        ('genie_logiciel', 'Génie Logiciel'),
        ('systemes_information', 'Systèmes d\'Information'),
        ('science_donnees', 'Science des Données'),
        # Mathématiques
        ('mathematiques_appliquees', 'Mathématiques Appliquées'),
        ('mathematiques_pures', 'Mathématiques Pures'),
        ('statistiques', 'Statistiques'),
        ('recherche_operationnelle', 'Recherche Opérationnelle'),
        # Physique
        ('physique_generale', 'Physique Générale'),
        ('physique_nucleaire', 'Physique Nucléaire'),
        ('physique_theorique', 'Physique Théorique'),
        ('electronique', 'Électronique'),
        ('optique', 'Optique'),
        # Chimie
        ('chimie_organique', 'Chimie Organique'),
        ('chimie_inorganique', 'Chimie Inorganique'),
        ('chimie_analytique', 'Chimie Analytique'),
        ('chimie_industrielle', 'Chimie Industrielle'),
        # Biologie
        ('biologie_moleculaire', 'Biologie Moléculaire'),
        ('genetique', 'Génétique'),
        ('ecologie', 'Écologie'),
        ('microbiologie', 'Microbiologie'),
        # Ingénierie
        ('genie_civil', 'Génie Civil'),
        ('genie_electrique', 'Génie Électrique'),
        ('genie_mecanique', 'Génie Mécanique'),
        ('automatique', 'Automatique'),
        # Sciences économiques
        ('economie', 'Économie'),
        ('finance', 'Finance'),
        ('management', 'Management'),
        ('comptabilite', 'Comptabilité'),
        # Langues
        ('francais', 'Français'),
        ('anglais', 'Anglais'),
        ('arabe', 'Arabe'),
        # Autre
        ('autre', 'Autre'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
        verbose_name=_("Utilisateur")
    )
    specialization = models.CharField(
        max_length=100,
        choices=SPECIALIZATION_CHOICES,
        verbose_name=_("Spécialité")
    )
    department = models.CharField(
        max_length=100,
        choices=DEPARTMENT_CHOICES,
        verbose_name=_("Département")
    )
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("Matricule")
    )
    
    class Meta:
        verbose_name = _("Enseignant")
        verbose_name_plural = _("Enseignants")
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.department}"
    
    def get_weekly_hours(self):
        """Calculate total weekly teaching hours"""
        from apps.scheduling.models import Session
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        sessions = Session.objects.filter(
            teacher=self,
            start_datetime__date__gte=start_of_week,
            start_datetime__date__lte=end_of_week
        )
        
        total_hours = 0
        for session in sessions:
            duration = (session.end_datetime - session.start_datetime).seconds / 3600
            total_hours += duration
        
        return total_hours


class Student(models.Model):
    """
    Student profile model linked to User.
    Stores academic information.
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
        verbose_name=_("Utilisateur")
    )
    student_id = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("Numéro d'étudiant")
    )
    student_email = models.EmailField(
        blank=True,
        null=True,
        verbose_name=_("Email Étudiant"),
        help_text=_("Email institutionnel de l'étudiant")
    )
    enrollment_year = models.IntegerField(
        verbose_name=_("Année d'inscription")
    )
    # Direct link to Program (required for timetable access)
    program = models.ForeignKey(
        'core.Program',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        verbose_name=_("Filière")
    )
    group = models.ForeignKey(
        'core.Group',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='group_students',
        verbose_name=_("Groupe")
    )
    
    class Meta:
        verbose_name = _("Étudiant")
        verbose_name_plural = _("Étudiants")
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.student_id}"
    
    def get_timetable(self):
        """Get student's timetable based on their program"""
        current_program = self.program or (self.group.program if self.group else None)
        if current_program:
            from apps.scheduling.models import Timetable
            # Get the most recent published timetable for the student's program
            return Timetable.objects.filter(
                program=current_program,
                is_published=True
            ).order_by('-created_at').first()
        return None
    
    def get_program(self):
        """Get student's program (direct or through group)"""
        return self.program or (self.group.program if self.group else None)


class Association(models.Model):
    """
    Association/Club profile model linked to User.
    Requires admin approval to activate.
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='association_profile',
        verbose_name=_("Utilisateur")
    )
    name = models.CharField(
        max_length=200,
        verbose_name=_("Nom de l'association")
    )
    description = models.TextField(
        verbose_name=_("Description")
    )
    president_name = models.CharField(
        max_length=100,
        verbose_name=_("Nom du président")
    )
    email = models.EmailField(
        verbose_name=_("Email")
    )
    phone = models.CharField(
        max_length=20,
        verbose_name=_("Téléphone")
    )
    is_approved = models.BooleanField(
        default=False,
        verbose_name=_("Approuvée")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date de création")
    )
    
    class Meta:
        verbose_name = _("Association")
        verbose_name_plural = _("Associations")
    
    def __str__(self):
        status = "✓" if self.is_approved else "⏳"
        return f"{self.name} {status}"
    
    def approve(self):
        """Approve the association and activate the user account"""
        self.is_approved = True
        self.user.is_active = True
        self.save()
        self.user.save()
