"""
Notification model for real-time notifications.
Enhanced with additional notification types and priority levels.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    """
    Notification model for real-time user notifications.
    Supports role-based notifications for Admin, Student, Teacher, and Association.
    """
    
    NOTIFICATION_TYPE_CHOICES = [
        # Reservation notifications
        ('reservation_pending', 'Nouvelle Demande de Réservation'),
        ('reservation_approved', 'Réservation Approuvée'),
        ('reservation_rejected', 'Réservation Rejetée'),
        # Session notifications
        ('session_scheduled', 'Séance Programmée'),
        ('session_modified', 'Séance Modifiée'),
        ('session_cancelled', 'Séance Annulée'),
        # Exam notifications
        ('exam_scheduled', 'Examen Programmé'),
        # Timetable notifications
        ('timetable_published', 'Emploi du Temps Publié'),
        ('timetable_updated', 'Emploi du Temps Modifié'),
        # Teacher notifications
        ('teacher_unavailable', 'Enseignant Indisponible'),
        # Room notifications
        ('room_changed', 'Salle Modifiée'),
        ('room_deactivated', 'Salle Désactivée'),
        # Conflict notifications
        ('conflict_detected', 'Conflit Détecté'),
        # Administrative notifications
        ('contact_received', 'Message Reçu'),
        ('association_approved', 'Association Approuvée'),
        # General
        ('general', 'Notification Générale'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Basse'),
        ('normal', 'Normale'),
        ('high', 'Haute'),
        ('urgent', 'Urgente'),
    ]
    
    recipient = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_("Destinataire")
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPE_CHOICES,
        verbose_name=_("Type")
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name=_("Priorité")
    )
    title = models.CharField(
        max_length=200,
        verbose_name=_("Titre")
    )
    message = models.TextField(
        verbose_name=_("Message")
    )
    related_object_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_("Type d'objet lié")
    )
    related_object_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("ID de l'objet lié")
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name=_("Lu")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date de création")
    )
    
    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        status = "✓" if self.is_read else "○"
        priority_icon = {"urgent": "🔴", "high": "🟠", "normal": "", "low": "⚪"}.get(self.priority, "")
        return f"{status} {priority_icon}{self.title} - {self.recipient.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.save()
    
    def to_dict(self):
        """Convert notification to dictionary for WebSocket"""
        return {
            'id': self.id,
            'type': self.notification_type,
            'priority': self.priority,
            'title': self.title,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
            'link_url': self.get_link_url(),
        }
    
    def get_link_url(self):
        """Get URL to redirect to when notification is clicked"""
        from django.urls import reverse
        from django.apps import apps
        
        # Check if recipient is a student or teacher (for timetable routing)
        is_admin = self.recipient.is_staff or self.recipient.is_superuser
        
        # Map notification types to URLs
        # For timetable notifications, route non-admins to my_timetable
        timetable_url = 'timetable_list' if is_admin else 'my_timetable'
        
        url_map = {
            'reservation_pending': ('reservation_list', {}),
            'reservation_approved': ('reservation_list', {}),
            'reservation_rejected': ('reservation_list', {}),
            'session_scheduled': ('dashboard', {}),
            'session_modified': ('dashboard', {}),
            'session_cancelled': ('dashboard', {}),
            'exam_scheduled': ('dashboard', {}),
            'timetable_published': (timetable_url, {}),
            'timetable_updated': (timetable_url, {}),
            'teacher_unavailable': ('dashboard', {}),
            'room_changed': ('dashboard', {}),
            'room_deactivated': ('room_list', {}),
            'conflict_detected': ('dashboard', {}),
            'contact_received': ('contact_list', {}),
            'association_approved': ('dashboard', {}),
            'general': ('dashboard', {}),
        }
        
        try:
            url_name, kwargs = url_map.get(self.notification_type, ('dashboard', {}))
            
            # If there's a related object, try to get more specific URL
            if self.related_object_type and self.related_object_id:
                try:
                    if self.related_object_type == 'RoomReservationRequest':
                        ReservationModel = apps.get_model('scheduling', 'RoomReservationRequest')
                        if ReservationModel.objects.filter(pk=self.related_object_id).exists():
                            return reverse('reservation_detail', kwargs={'pk': self.related_object_id})
                        else:
                            return reverse('reservation_list')
                    elif self.related_object_type == 'ContactMessage':
                        ContactModel = apps.get_model('accounts', 'ContactMessage')
                        if ContactModel.objects.filter(pk=self.related_object_id).exists():
                            return reverse('contact_detail', kwargs={'pk': self.related_object_id})
                        else:
                            return reverse('contact_list')
                    elif self.related_object_type == 'Timetable':
                        # For students/teachers, always go to my_timetable
                        if not is_admin:
                            return reverse('my_timetable')
                        # For admins, try detail view
                        TimetableModel = apps.get_model('scheduling', 'Timetable')
                        if TimetableModel.objects.filter(pk=self.related_object_id).exists():
                            return reverse('timetable_detail', kwargs={'pk': self.related_object_id})
                        else:
                            return reverse('timetable_list')
                except Exception:
                    pass
            
            return reverse(url_name, kwargs=kwargs)
        except Exception:
            return reverse('dashboard')
    
    def get_icon(self):
        """Get Font Awesome icon for notification type"""
        icon_map = {
            'reservation_pending': 'fas fa-clock',
            'reservation_approved': 'fas fa-check-circle',
            'reservation_rejected': 'fas fa-times-circle',
            'session_scheduled': 'fas fa-calendar-plus',
            'session_modified': 'fas fa-calendar-alt',
            'session_cancelled': 'fas fa-calendar-times',
            'exam_scheduled': 'fas fa-file-alt',
            'timetable_published': 'fas fa-calendar-check',
            'timetable_updated': 'fas fa-sync-alt',
            'teacher_unavailable': 'fas fa-user-slash',
            'room_changed': 'fas fa-exchange-alt',
            'room_deactivated': 'fas fa-door-closed',
            'conflict_detected': 'fas fa-exclamation-triangle',
            'contact_received': 'fas fa-envelope',
            'association_approved': 'fas fa-users',
            'general': 'fas fa-bell',
        }
        return icon_map.get(self.notification_type, 'fas fa-bell')
    
    def get_color(self):
        """Get color class based on priority and type"""
        if self.priority == 'urgent':
            return 'danger'
        elif self.priority == 'high':
            return 'warning'
        elif self.notification_type in ['reservation_approved', 'association_approved', 'timetable_published']:
            return 'success'
        elif self.notification_type in ['reservation_rejected', 'session_cancelled', 'room_deactivated']:
            return 'danger'
        elif self.notification_type == 'conflict_detected':
            return 'warning'
        return 'primary'
