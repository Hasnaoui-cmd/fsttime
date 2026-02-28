"""
Django signals for automatic notification triggers.
Signals listen for model save/delete events and trigger appropriate notifications.
"""

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from .services import NotificationService


# Store original values for comparison in pre_save
_original_values = {}


def get_original_value(instance, field_name):
    """Get the original value of a field before save"""
    key = f"{instance.__class__.__name__}_{instance.pk}_{field_name}"
    return _original_values.get(key)


def store_original_value(instance, field_name, value):
    """Store the original value of a field before save"""
    if instance.pk:
        key = f"{instance.__class__.__name__}_{instance.pk}_{field_name}"
        _original_values[key] = value


def clear_original_value(instance, field_name):
    """Clear stored original value after save"""
    if instance.pk:
        key = f"{instance.__class__.__name__}_{instance.pk}_{field_name}"
        _original_values.pop(key, None)


def format_datetime_french(dt):
    """Format datetime in French."""
    days = {0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'}
    day_name = days.get(dt.weekday(), '')
    return f"{day_name} {dt.strftime('%d/%m à %H:%M')}"


# ========== ROOM RESERVATION REQUEST SIGNALS ==========

@receiver(post_save, sender='scheduling.RoomReservationRequest')
def on_reservation_created(sender, instance, created, **kwargs):
    """
    Notify admins when a new room reservation request is submitted.
    """
    if created and instance.status == 'pending':
        NotificationService.notify_admins_new_reservation(instance)


@receiver(pre_save, sender='scheduling.RoomReservationRequest')
def store_reservation_status(sender, instance, **kwargs):
    """Store original status before save for comparison"""
    if instance.pk:
        try:
            from apps.scheduling.models import RoomReservationRequest
            original = RoomReservationRequest.objects.get(pk=instance.pk)
            store_original_value(instance, 'status', original.status)
        except RoomReservationRequest.DoesNotExist:
            pass


@receiver(post_save, sender='scheduling.RoomReservationRequest')
def on_reservation_status_changed(sender, instance, created, **kwargs):
    """
    Notify requester when reservation status changes.
    """
    if not created:
        original_status = get_original_value(instance, 'status')
        clear_original_value(instance, 'status')
        
        if original_status and original_status != instance.status:
            if instance.status == 'approved':
                if instance.teacher:
                    NotificationService.notify_teacher_reservation_approved(instance)
                elif instance.association:
                    NotificationService.notify_association_reservation_approved(instance)
            elif instance.status == 'rejected':
                reason = instance.admin_notes or ""
                if instance.teacher:
                    NotificationService.notify_teacher_reservation_rejected(instance, reason)
                elif instance.association:
                    NotificationService.notify_association_reservation_rejected(instance, reason)


# ========== TEACHER UNAVAILABILITY SIGNALS ==========

@receiver(post_save, sender='scheduling.TeacherUnavailability')
def on_unavailability_created(sender, instance, created, **kwargs):
    """
    Notify admins and affected students when a teacher marks unavailability.
    """
    if created:
        # Notify admins
        NotificationService.notify_admins_teacher_unavailability(instance)
        
        # Notify affected students
        NotificationService.notify_students_teacher_unavailable(instance)


# ========== SESSION SIGNALS ==========

@receiver(pre_save, sender='scheduling.Session')
def store_session_original_values(sender, instance, **kwargs):
    """Store original session values before save for comparison"""
    if instance.pk:
        try:
            from apps.scheduling.models import Session
            original = Session.objects.get(pk=instance.pk)
            store_original_value(instance, 'room_id', original.room_id)
            store_original_value(instance, 'teacher_id', original.teacher_id)
            store_original_value(instance, 'start_datetime', original.start_datetime)
            store_original_value(instance, 'end_datetime', original.end_datetime)
            store_original_value(instance, 'is_validated', original.is_validated)
        except Session.DoesNotExist:
            pass


@receiver(post_save, sender='scheduling.Session')
def on_session_modified(sender, instance, created, **kwargs):
    """
    Notify teacher and students when a session is modified.
    """
    if created:
        # New exam session - notify students
        if instance.is_exam:
            NotificationService.notify_students_exam_scheduled(instance)
        
        # Check for conflicts on new sessions
        conflicts = instance.check_conflicts()
        if conflicts:
            NotificationService.notify_admins_conflict_detected(instance, list(conflicts))
            NotificationService.notify_teacher_conflict_detected(instance, list(conflicts))
    else:
        # Existing session modified
        changes = []
        
        original_room = get_original_value(instance, 'room_id')
        original_teacher = get_original_value(instance, 'teacher_id')
        original_start = get_original_value(instance, 'start_datetime')
        original_end = get_original_value(instance, 'end_datetime')
        
        if original_room and original_room != instance.room_id:
            from apps.core.models import Room
            try:
                old_room = Room.objects.get(pk=original_room)
                new_room_name = instance.room.name if instance.room else "Non définie"
                changes.append(f"Salle: {old_room.name} → {new_room_name}")
            except Room.DoesNotExist:
                changes.append("Salle modifiée")
        
        if original_teacher and original_teacher != instance.teacher_id:
            changes.append("Enseignant modifié")
        
        if original_start and original_start != instance.start_datetime:
            changes.append(f"Horaire: {instance.start_datetime.strftime('%d/%m/%Y %H:%M')}")
        
        # Clear stored values
        clear_original_value(instance, 'room_id')
        clear_original_value(instance, 'teacher_id')
        clear_original_value(instance, 'start_datetime')
        clear_original_value(instance, 'end_datetime')
        clear_original_value(instance, 'is_validated')
        
        if changes:
            change_description = "\n".join(changes)
            
            # Notify teacher
            NotificationService.notify_teacher_session_modified(instance, change_description)
            
            # Notify students
            NotificationService.notify_students_session_modified(instance, change_description)


@receiver(post_delete, sender='scheduling.Session')
def on_session_deleted(sender, instance, **kwargs):
    """
    Notify teacher and students when a session is deleted.
    """
    if not instance.is_validated:
        return
    
    try:
        # Notify teacher
        if instance.teacher:
            formatted_time = format_datetime_french(instance.start_datetime)
            NotificationService.send_notification(
                user=instance.teacher.user,
                notification_type='session_cancelled',
                title=f'Séance annulée: {instance.subject}',
                message=f'Votre séance de {instance.subject} ({formatted_time}) a été supprimée.',
                related_object=None,
                priority='high'
            )
        
        # Student notification is handled via NotificationService or similar logic
        # For now, let's use the explicit logic from scheduling/signals.py
        from apps.accounts.models import Student
        programs = set()
        for group in instance.groups.all():
            if group.program:
                programs.add(group.program)
        
        formatted_time = format_datetime_french(instance.start_datetime)
        for program in programs:
            students = Student.objects.filter(program=program).select_related('user')
            for student in students:
                NotificationService.send_notification(
                    user=student.user,
                    notification_type='session_cancelled',
                    title=f'Séance annulée: {instance.subject}',
                    message=f'📚 {instance.subject}\n📅 {formatted_time}\n❌ Cette séance a été annulée.',
                    related_object=None,
                    priority='normal'
                )
    except Exception:
        pass


# ========== ROOM SIGNALS ==========

@receiver(pre_save, sender='core.Room')
def store_room_is_active(sender, instance, **kwargs):
    """Store original is_active value before save"""
    if instance.pk:
        try:
            from apps.core.models import Room
            original = Room.objects.get(pk=instance.pk)
            store_original_value(instance, 'is_active', original.is_active)
        except Room.DoesNotExist:
            pass


@receiver(post_save, sender='core.Room')
def on_room_deactivated(sender, instance, created, **kwargs):
    """
    Notify affected teachers and associations when a room is deactivated.
    """
    if not created:
        original_active = get_original_value(instance, 'is_active')
        clear_original_value(instance, 'is_active')
        
        if original_active is True and instance.is_active is False:
            # Room was deactivated - notify affected users
            from apps.scheduling.models import Session, RoomReservationRequest
            from apps.accounts.models import Teacher, Association
            from django.utils import timezone
            
            # Find teachers with future sessions in this room
            future_sessions = Session.objects.filter(
                room=instance,
                start_datetime__gte=timezone.now()
            ).values_list('teacher_id', flat=True).distinct()
            
            teachers = Teacher.objects.filter(id__in=future_sessions)
            NotificationService.notify_teacher_room_deactivated(instance, teachers)
            
            # Find associations with pending reservations in this room
            pending_reservations = RoomReservationRequest.objects.filter(
                room=instance,
                status='pending',
                association__isnull=False
            ).values_list('association_id', flat=True).distinct()
            
            associations = Association.objects.filter(id__in=pending_reservations)
            NotificationService.notify_association_room_deactivated(instance, associations)


# ========== TIMETABLE SIGNALS ==========

@receiver(pre_save, sender='scheduling.Timetable')
def store_timetable_is_published(sender, instance, **kwargs):
    """Store original is_published value before save"""
    if instance.pk:
        try:
            from apps.scheduling.models import Timetable
            original = Timetable.objects.get(pk=instance.pk)
            store_original_value(instance, 'is_published', original.is_published)
        except Timetable.DoesNotExist:
            pass


@receiver(post_save, sender='scheduling.Timetable')
def on_timetable_published(sender, instance, created, **kwargs):
    """
    Notify students and teachers when a timetable is published.
    """
    original_published = get_original_value(instance, 'is_published')
    clear_original_value(instance, 'is_published')
    
    # Check if just published (transitioned from unpublished to published)
    if instance.is_published and (created or original_published is False):
        from apps.scheduling.models import TimetableEntry
        from apps.accounts.models import Teacher
        
        # Notify students
        NotificationService.notify_students_timetable_published(instance)
        
        # Notify teachers involved in this timetable
        teacher_ids = TimetableEntry.objects.filter(
            timetable=instance,
            teacher__isnull=False
        ).values_list('teacher_id', flat=True).distinct()
        
        for teacher in Teacher.objects.filter(id__in=teacher_ids):
            NotificationService.notify_teacher_timetable_published(instance, teacher)
    elif not created and instance.is_published and original_published is True:
        # Timetable was already published but updated
        NotificationService.notify_timetable_update(instance)


# ========== ASSOCIATION APPROVAL SIGNALS ==========

@receiver(pre_save, sender='accounts.Association')
def store_association_is_approved(sender, instance, **kwargs):
    """Store original is_approved value before save"""
    if instance.pk:
        try:
            from apps.accounts.models import Association
            original = Association.objects.get(pk=instance.pk)
            store_original_value(instance, 'is_approved', original.is_approved)
        except Association.DoesNotExist:
            pass


@receiver(post_save, sender='accounts.Association')
def on_association_approved(sender, instance, created, **kwargs):
    """
    Notify association when their registration is approved.
    """
    if not created:
        original_approved = get_original_value(instance, 'is_approved')
        clear_original_value(instance, 'is_approved')
        
        if original_approved is False and instance.is_approved is True:
            NotificationService.notify_association_approved(instance)


# ========== CONTACT MESSAGE SIGNALS ==========

@receiver(post_save, sender='core.ContactMessage')
def on_contact_message_created(sender, instance, created, **kwargs):
    """
    Notify admins when a new contact message is received.
    """
    if created:
        NotificationService.notify_admins_contact_received(instance)


# ========== SUBJECT SIGNALS ==========

@receiver(post_save, sender='scheduling.Subject')
def on_subject_teacher_assigned(sender, instance, created, **kwargs):
    """
    Notify teacher when assigned to a Subject.
    """
    if instance.teacher:
        try:
            if created:
                # New subject - notify teacher of assignment
                NotificationService.send_notification(
                    user=instance.teacher.user,
                    notification_type='session_scheduled',
                    title=f'Nouvelle affectation: {instance.name}',
                    message=f'Vous avez été assigné à la matière "{instance.name}" ({instance.code}) pour le programme {instance.program.code if instance.program else "N/A"}.',
                    related_object=instance,
                    priority='normal'
                )
        except Exception:
            pass


# ========== PROGRAM SIGNALS ==========

@receiver(post_save, sender='core.Program')
def on_program_head_assigned(sender, instance, **kwargs):
    """
    Notify teacher when made 'Chef de Filière' (Head of Program).
    """
    if instance.program_head:
        try:
            NotificationService.send_notification(
                user=instance.program_head.user,
                notification_type='schedule_updated',
                title='Nomination: Chef de Filière',
                message=f'Vous avez été nommé Chef de Filière pour "{instance.name}" ({instance.code}).',
                related_object=instance,
                priority='high'
            )
        except Exception:
            pass


# ========== TIMETABLE ENTRY SIGNALS ==========

@receiver(post_save, sender='scheduling.TimetableEntry')
def on_timetable_entry_saved(sender, instance, created, **kwargs):
    """
    Notify all students when a TimetableEntry is created or modified
    in a published timetable.
    """
    # Only notify if timetable is published
    if not instance.timetable or not instance.timetable.is_published:
        return
    
    # Skip entries injected from reservations (they have their own notification)
    if instance.source_reservation_id:
        return
    
    try:
        action = 'added' if created else 'modified'
        NotificationService.notify_timetable_entry_change(instance, action=action)
    except Exception:
        pass


@receiver(post_delete, sender='scheduling.TimetableEntry')
def on_timetable_entry_deleted(sender, instance, **kwargs):
    """
    Notify all students when a TimetableEntry is deleted
    from a published timetable.
    """
    if not instance.timetable or not instance.timetable.is_published:
        return
    
    try:
        NotificationService.notify_timetable_entry_change(instance, action='deleted')
    except Exception:
        pass
