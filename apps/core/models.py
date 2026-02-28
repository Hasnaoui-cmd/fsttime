"""
Core models for FSTTIME application.
Includes academic programs, groups, rooms, and equipment.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Equipment(models.Model):
    """
    Equipment model representing room equipment.
    """
    
    name = models.CharField(
        max_length=100,
        verbose_name=_("Nom")
    )
    icon = models.CharField(
        max_length=50,
        default='fas fa-tools',
        verbose_name=_("Icône")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )
    
    class Meta:
        verbose_name = _("Équipement")
        verbose_name_plural = _("Équipements")
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Room(models.Model):
    """
    Room model with availability checking functionality.
    """
    
    ROOM_TYPE_CHOICES = [
        ('classe', 'Salle de classe'),
        ('amphitheatre', 'Amphithéâtre'),
        ('labo', 'Laboratoire'),
        ('salle_info', 'Salle informatique'),
    ]
    
    name = models.CharField(
        max_length=50,
        verbose_name=_("Nom")
    )
    room_type = models.CharField(
        max_length=20,
        choices=ROOM_TYPE_CHOICES,
        verbose_name=_("Type")
    )
    capacity = models.IntegerField(
        verbose_name=_("Capacité")
    )
    building = models.CharField(
        max_length=50,
        verbose_name=_("Bâtiment")
    )
    floor = models.IntegerField(
        verbose_name=_("Étage")
    )
    equipment = models.ManyToManyField(
        Equipment,
        blank=True,
        related_name='rooms',
        verbose_name=_("Équipements")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active")
    )
    
    class Meta:
        verbose_name = _("Salle")
        verbose_name_plural = _("Salles")
        ordering = ['building', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_room_type_display()})"
    
    def check_availability(self, start_time, end_time):
        """
        Check if room is available in the given time range.
        Returns True if available, False if there are conflicts.
        Checks both Session and approved RoomReservationRequest conflicts.
        """
        from apps.scheduling.models import Session, RoomReservationRequest
        from datetime import timedelta
        
        # Check session conflicts
        session_conflicts = Session.objects.filter(
            room=self,
            start_datetime__lt=end_time,
            end_datetime__gt=start_time
        ).exists()
        
        if session_conflicts:
            return False
        
        # Check approved reservation conflicts
        approved_reservations = RoomReservationRequest.objects.filter(
            room=self,
            status='approved',
        )
        
        for reservation in approved_reservations:
            res_start = reservation.get_start_datetime()
            res_end = reservation.get_end_datetime()
            
            if res_start and res_end:
                if res_start < end_time and res_end > start_time:
                    return False
        
        return True
    
    def get_equipment_list(self):
        """Get comma-separated list of equipment"""
        return ", ".join(eq.name for eq in self.equipment.all())


class Program(models.Model):
    """
    Academic program model (Filière).
    """
    
    DEGREE_LEVEL_CHOICES = [
        ('licence', 'Licence'),
        ('master', 'Master'),
        ('doctorat', 'Doctorat'),
    ]
    
    DEPARTMENT_CHOICES = [
        ('mathematiques_informatique', 'Département de Mathématiques et Informatique'),
        ('physique', 'Département de Physique'),
        ('chimie', 'Département de Chimie'),
        ('biologie', 'Département de Biologie'),
        ('geologie', 'Département de Géologie'),
        ('sciences_terre', 'Département de Sciences de la Terre'),
    ]
    
    name = models.CharField(
        max_length=200,
        verbose_name=_("Nom")
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("Code")
    )
    department = models.CharField(
        max_length=100,
        choices=DEPARTMENT_CHOICES,
        verbose_name=_("Département")
    )
    degree_level = models.CharField(
        max_length=50,
        choices=DEGREE_LEVEL_CHOICES,
        verbose_name=_("Niveau")
    )
    capacity = models.PositiveIntegerField(
        default=100,
        verbose_name=_("Capacité"),
        help_text=_("Nombre maximum d'étudiants")
    )
    program_head = models.ForeignKey(
        'accounts.Teacher',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_programs',
        verbose_name=_("Chef de Filière")
    )
    
    class Meta:
        verbose_name = _("Filière")
        verbose_name_plural = _("Filières")
        ordering = ['department', 'name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"



class Group(models.Model):
    """
    Student group model within a program.
    """
    
    name = models.CharField(
        max_length=100,
        verbose_name=_("Nom du groupe")
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='groups',
        verbose_name=_("Filière")
    )
    academic_year = models.CharField(
        max_length=10,
        verbose_name=_("Année universitaire")
    )
    capacity = models.IntegerField(
        verbose_name=_("Capacité")
    )
    
    class Meta:
        verbose_name = _("Groupe")
        verbose_name_plural = _("Groupes")
        ordering = ['program', 'name']
    
    def __str__(self):
        return f"{self.program.code} - {self.name}"
    
    def get_student_count(self):
        """Get the number of students in this group"""
        return self.students.count()


class ContactMessage(models.Model):
    """
    Contact message model for user inquiries.
    """
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('in_progress', 'En cours'),
        ('resolved', 'Résolu'),
    ]
    
    sender_name = models.CharField(
        max_length=100,
        verbose_name=_("Nom")
    )
    sender_email = models.EmailField(
        verbose_name=_("Email")
    )
    user = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Utilisateur")
    )
    subject = models.CharField(
        max_length=200,
        verbose_name=_("Sujet")
    )
    message = models.TextField(
        verbose_name=_("Message")
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_("Statut")
    )
    response = models.TextField(
        blank=True,
        verbose_name=_("Réponse")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date de création")
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date de réponse")
    )
    
    class Meta:
        verbose_name = _("Message de Contact")
        verbose_name_plural = _("Messages de Contact")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subject} - {self.sender_name}"
