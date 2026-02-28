"""
Notification service for sending real-time notifications.
Enhanced with role-based notification methods for all user types.
"""

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Notification

User = get_user_model()


class NotificationService:
    """
    Service class for handling notifications with OOP principles.
    Provides static methods for sending various types of notifications.
    Supports role-based notifications for Admin, Student, Teacher, and Association.
    """
    
    @staticmethod
    def send_notification(user, notification_type, title, message, related_object=None, priority='normal'):
        """
        Create and send notification via WebSocket.
        
        Args:
            user: The recipient User object
            notification_type: Type of notification (from NOTIFICATION_TYPE_CHOICES)
            title: Notification title
            message: Notification message
            related_object: Optional related model instance
            priority: Notification priority ('low', 'normal', 'high', 'urgent')
        
        Returns:
            The created Notification object
        """
        # Create notification in database
        notification = Notification.objects.create(
            recipient=user,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            related_object_type=related_object.__class__.__name__ if related_object else None,
            related_object_id=related_object.id if related_object else None
        )
        
        # Send via WebSocket
        NotificationService._send_websocket(user, notification)
        
        return notification
    
    @staticmethod
    def _send_websocket(user, notification):
        """Send notification via WebSocket channel"""
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{user.id}",
                {
                    "type": "notification_message",
                    "notification": {
                        "id": notification.id,
                        "type": notification.notification_type,
                        "priority": notification.priority,
                        "title": notification.title,
                        "message": notification.message,
                        "icon": notification.get_icon(),
                        "color": notification.get_color(),
                        "created_at": notification.created_at.isoformat(),
                        "is_read": False
                    }
                }
            )
        except Exception as e:
            # Log error but don't fail - notification is saved in DB
            print(f"WebSocket notification error: {e}")
    
    # ========== ADMIN NOTIFICATIONS ==========
    
    @staticmethod
    def notify_admins_new_reservation(reservation_request):
        """
        Notify all administrators when a new room reservation request is submitted.
        
        Args:
            reservation_request: The RoomReservationRequest object
        """
        admins = User.objects.filter(role='admin')
        
        requester_name = (
            reservation_request.teacher.user.get_full_name() 
            if reservation_request.teacher 
            else reservation_request.association.name
        )
        requester_type = "l'enseignant" if reservation_request.teacher else "l'association"
        
        start = reservation_request.get_start_datetime()
        start_str = start.strftime('%d/%m/%Y à %H:%M') if start else 'Date non spécifiée'
        
        for admin in admins:
            NotificationService.send_notification(
                user=admin,
                notification_type='reservation_pending',
                title=f"Nouvelle demande de réservation",
                message=(
                    f"{requester_type.capitalize()} {requester_name} demande la salle "
                    f"{reservation_request.room.name} pour le {start_str}.\n"
                    f"Motif: {reservation_request.reason[:100]}..."
                ),
                related_object=reservation_request,
                priority='high'
            )

    @staticmethod
    def _get_affected_programs(unavailability):
        """
        Identify programs affected by a teacher's unavailability.
        Checks both recurring TimetableEntries and scheduled Sessions.
        
        Args:
            unavailability: The TeacherUnavailability object
            
        Returns:
            Set of Program names
        """
        from apps.scheduling.models import Session, TimetableEntry
        from datetime import timedelta
        
        affected_programs = set()
        
        # 1. Check scheduled Sessions (Specific dates)
        sessions = Session.objects.filter(
            teacher=unavailability.teacher,
            start_datetime__gte=unavailability.start_datetime,
            start_datetime__lte=unavailability.end_datetime
        ).prefetch_related('groups__program')
        
        for session in sessions:
            # Check groups for program info
            for group in session.groups.all():
                if group.program:
                    affected_programs.add(group.program.name)
                
        # 2. Check TimetableEntries (Recurring schedule)
        # Iterate through each day of the unavailability
        current_date = unavailability.start_datetime.date()
        end_date = unavailability.end_datetime.date()
        
        # Map python weekday to model day code
        WEEKDA_MAP = {
            0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 
            4: 'FRI', 5: 'SAT', 6: 'SUN'
        }
        
        while current_date <= end_date:
            day_code = WEEKDA_MAP.get(current_date.weekday())
            if day_code:
                # Find entries for this teacher on this day
                entries = TimetableEntry.objects.filter(
                    teacher=unavailability.teacher,
                    day_of_week=day_code,
                    timetable__is_published=True  # Only count published timetables
                ).select_related('timetable__program', 'time_slot')
                
                for entry in entries:
                    # Simple check: assumes entry is affected if it's on the day
                    # Ideally we should check time overlap if unavailability is partial day
                    # But for now, listing it as "potentially affected" is safer
                    if entry.timetable and entry.timetable.program:
                        affected_programs.add(entry.timetable.program.name)
            
            current_date += timedelta(days=1)
            
        return affected_programs

    @staticmethod
    def notify_admins_teacher_unavailability(unavailability):
        """
        Notify administrators when a teacher marks unavailability.
        
        Args:
            unavailability: The TeacherUnavailability object
        """
        admins = User.objects.filter(role='admin')
        
        teacher_name = unavailability.teacher.user.get_full_name()
        start = unavailability.start_datetime.strftime('%d/%m/%Y %H:%M')
        end = unavailability.end_datetime.strftime('%d/%m/%Y %H:%M')
        
        # Get affected programs
        affected_programs = NotificationService._get_affected_programs(unavailability)
        programs_str = ", ".join(affected_programs) if affected_programs else "Aucune filière détectée"
        
        for admin in admins:
            NotificationService.send_notification(
                user=admin,
                notification_type='teacher_unavailable',
                title=f"Indisponibilité enseignant: {teacher_name}",
                message=(
                    f"L'enseignant {teacher_name} sera indisponible du {start} au {end}.\n"
                    f"Raison: {unavailability.reason}\n"
                    f"⚠️ Filières impactées: {programs_str}"
                ),
                related_object=unavailability,
                priority='high'
            )
    
    @staticmethod
    def notify_admins_conflict_detected(session, conflicts):
        """
        Notify administrators when a scheduling conflict is detected.
        
        Args:
            session: The Session that has conflicts
            conflicts: List of conflicting sessions
        """
        admins = User.objects.filter(role='admin')
        
        conflict_details = ", ".join([
            f"{c.subject} ({c.start_datetime.strftime('%H:%M')})" 
            for c in conflicts[:3]
        ])
        
        for admin in admins:
            NotificationService.send_notification(
                user=admin,
                notification_type='conflict_detected',
                title=f"⚠️ Conflit détecté: {session.subject}",
                message=(
                    f"La séance {session.subject} du {session.start_datetime.strftime('%d/%m/%Y')} "
                    f"est en conflit avec: {conflict_details}.\n"
                    f"Enseignant: {session.teacher.user.get_full_name()}\n"
                    f"Salle: {session.room.name if session.room else 'Non définie'}"
                ),
                related_object=session,
                priority='urgent'
            )
    
    @staticmethod
    def notify_admins_contact_received(contact_message):
        """
        Notify administrators of a new contact message.
        
        Args:
            contact_message: The ContactMessage object
        """
        admins = User.objects.filter(role='admin')
        
        for admin in admins:
            NotificationService.send_notification(
                user=admin,
                notification_type='contact_received',
                title=f"Nouveau message: {contact_message.subject}",
                message=f"De: {contact_message.sender_name} ({contact_message.sender_email})",
                related_object=contact_message
            )
    
    # ========== STUDENT NOTIFICATIONS ==========
    
    @staticmethod
    def notify_students_exam_scheduled(session):
        """
        Notify all students when an exam is scheduled.
        
        Args:
            session: The Session object representing the exam
        """
        if not session.is_exam:
            return
        
        for group in session.groups.all():
            students = group.students.all()
            for student in students:
                NotificationService.send_notification(
                    user=student.user,
                    notification_type='exam_scheduled',
                    title=f"📝 Examen programmé: {session.subject}",
                    message=(
                        f"Un examen de {session.subject} a été programmé le "
                        f"{session.start_datetime.strftime('%d/%m/%Y à %H:%M')} "
                        f"dans la salle {session.room.name if session.room else 'À définir'}."
                    ),
                    related_object=session,
                    priority='high'
                )
    
    @staticmethod
    def notify_students_session_modified(session, change_description=""):
        """
        Notify students when a session is modified (time, room, teacher).
        
        Args:
            session: The modified Session object
            change_description: Description of what changed
        """
        for group in session.groups.all():
            for student in group.students.all():
                NotificationService.send_notification(
                    user=student.user,
                    notification_type='session_modified',
                    title=f"Séance modifiée: {session.subject}",
                    message=(
                        f"La séance de {session.subject} du "
                        f"{session.start_datetime.strftime('%d/%m/%Y à %H:%M')} a été modifiée.\n"
                        f"{change_description or 'Consultez votre emploi du temps pour les détails.'}"
                    ),
                    related_object=session
                )
    
    @staticmethod
    def notify_students_session_cancelled(session):
        """
        Notify students when a session is cancelled.
        
        Args:
            session: The cancelled Session object
        """
        for group in session.groups.all():
            for student in group.students.all():
                NotificationService.send_notification(
                    user=student.user,
                    notification_type='session_cancelled',
                    title=f"❌ Séance annulée: {session.subject}",
                    message=(
                        f"La séance de {session.subject} prévue le "
                        f"{session.start_datetime.strftime('%d/%m/%Y à %H:%M')} a été annulée."
                    ),
                    related_object=session,
                    priority='high'
                )
    
    @staticmethod
    def notify_students_teacher_unavailable(unavailability):
        """
        Notify affected students when their teacher is unavailable.
        
        Args:
            unavailability: The TeacherUnavailability object
        """
        from apps.scheduling.models import Session
        
        # Find sessions in the unavailability period
        affected_sessions = Session.objects.filter(
            teacher=unavailability.teacher,
            start_datetime__gte=unavailability.start_datetime,
            start_datetime__lte=unavailability.end_datetime
        )
        
        # Get unique students from affected sessions
        notified_students = set()
        
        for session in affected_sessions:
            for group in session.groups.all():
                for student in group.students.all():
                    if student.user.id not in notified_students:
                        notified_students.add(student.user.id)
                        NotificationService.send_notification(
                            user=student.user,
                            notification_type='teacher_unavailable',
                            title=f"Enseignant absent: {unavailability.teacher.user.get_full_name()}",
                            message=(
                                f"L'enseignant {unavailability.teacher.user.get_full_name()} "
                                f"sera absent du {unavailability.start_datetime.strftime('%d/%m')} "
                                f"au {unavailability.end_datetime.strftime('%d/%m')}.\n"
                                f"Raison: {unavailability.reason}\n"
                                f"Vos séances peuvent être affectées."
                            ),
                            related_object=unavailability
                        )
    
    @staticmethod
    def notify_students_timetable_published(timetable):
        """
        Notify students when a new timetable is published for their program.
        
        Args:
            timetable: The Timetable object
        """
        from apps.accounts.models import Student
        
        # Get students in the program's groups
        students = Student.objects.filter(group__program=timetable.program).distinct()
        
        for student in students:
            NotificationService.send_notification(
                user=student.user,
                notification_type='timetable_published',
                title=f"📅 Nouvel emploi du temps publié",
                message=(
                    f"L'emploi du temps pour {timetable.program.name} - "
                    f"{timetable.get_semester_display()} ({timetable.academic_year}) "
                    f"a été publié. Consultez-le dès maintenant!"
                ),
                related_object=timetable,
                priority='high'
            )
    
    # ========== TEACHER NOTIFICATIONS ==========
    
    @staticmethod
    def notify_teacher_session_modified(session, change_description=""):
        """
        Notify a teacher when their assigned session is modified.
        
        Args:
            session: The modified Session object
            change_description: Description of what changed
        """
        NotificationService.send_notification(
            user=session.teacher.user,
            notification_type='session_modified',
            title=f"Votre séance modifiée: {session.subject}",
            message=(
                f"Votre séance de {session.subject} du "
                f"{session.start_datetime.strftime('%d/%m/%Y à %H:%M')} a été modifiée.\n"
                f"{change_description or 'Consultez votre emploi du temps.'}"
            ),
            related_object=session
        )
    
    @staticmethod
    def notify_teacher_session_assigned(session):
        """
        Notify a teacher when they are assigned to a session.
        Message: "Vous avez été assigné à [Subject] le [Day] à [Time]"
        
        Args:
            session: The Session object the teacher is assigned to
        """
        if not session.teacher:
            return
        
        day_name = session.start_datetime.strftime('%A')
        # French day names
        day_names_fr = {
            'Monday': 'Lundi',
            'Tuesday': 'Mardi',
            'Wednesday': 'Mercredi',
            'Thursday': 'Jeudi',
            'Friday': 'Vendredi',
            'Saturday': 'Samedi',
            'Sunday': 'Dimanche'
        }
        day_fr = day_names_fr.get(day_name, day_name)
        
        NotificationService.send_notification(
            user=session.teacher.user,
            notification_type='session_scheduled',
            title=f"📚 Nouvelle assignation: {session.subject}",
            message=(
                f"Vous avez été assigné à {session.subject} le {day_fr} "
                f"{session.start_datetime.strftime('%d/%m/%Y')} à {session.start_datetime.strftime('%H:%M')}.\n"
                f"Salle: {session.room.name if session.room else 'À définir'}"
            ),
            related_object=session,
            priority='normal'
        )
    
    @staticmethod
    def notify_students_new_session(session):
        """
        Notify all students in the session's groups about a new session.
        Message: "Nouvelle séance ajoutée: [Subject] avec Prof. [Name]"
        
        Args:
            session: The new Session object
        """
        teacher_name = session.teacher.user.get_full_name() if session.teacher else "Non assigné"
        
        for group in session.groups.all():
            for student in group.students.all():
                NotificationService.send_notification(
                    user=student.user,
                    notification_type='session_scheduled',
                    title=f"📅 Nouvelle séance: {session.subject}",
                    message=(
                        f"Nouvelle séance ajoutée: {session.subject} avec Prof. {teacher_name}.\n"
                        f"Date: {session.start_datetime.strftime('%d/%m/%Y à %H:%M')}\n"
                        f"Salle: {session.room.name if session.room else 'À définir'}"
                    ),
                    related_object=session
                )
    
    @staticmethod
    def notify_teacher_room_deactivated(room, teachers):
        """
        Notify teachers when a room they use is deactivated.
        
        Args:
            room: The Room object that was deactivated
            teachers: List of Teacher objects to notify
        """
        for teacher in teachers:
            NotificationService.send_notification(
                user=teacher.user,
                notification_type='room_deactivated',
                title=f"⚠️ Salle désactivée: {room.name}",
                message=(
                    f"La salle {room.name} ({room.get_room_type_display()}) "
                    f"a été désactivée. Vérifiez vos séances programmées dans cette salle."
                ),
                related_object=room,
                priority='high'
            )
    
    @staticmethod
    def notify_teacher_reservation_approved(reservation_request):
        """
        Notify a teacher when their room reservation is approved.
        
        Args:
            reservation_request: The RoomReservationRequest object
        """
        if not reservation_request.teacher:
            return
        
        start = reservation_request.get_start_datetime()
        NotificationService.send_notification(
            user=reservation_request.teacher.user,
            notification_type='reservation_approved',
            title=f"✅ Réservation approuvée: {reservation_request.room.name}",
            message=(
                f"Votre réservation de la salle {reservation_request.room.name} "
                f"pour le {start.strftime('%d/%m/%Y à %H:%M')} a été approuvée."
            ),
            related_object=reservation_request,
            priority='high'
        )
    
    @staticmethod
    def notify_teacher_reservation_rejected(reservation_request, reason=""):
        """
        Notify a teacher when their room reservation is rejected.
        
        Args:
            reservation_request: The RoomReservationRequest object
            reason: Reason for rejection
        """
        if not reservation_request.teacher:
            return
        
        start = reservation_request.get_start_datetime()
        NotificationService.send_notification(
            user=reservation_request.teacher.user,
            notification_type='reservation_rejected',
            title=f"❌ Réservation refusée: {reservation_request.room.name}",
            message=(
                f"Votre réservation de la salle {reservation_request.room.name} "
                f"pour le {start.strftime('%d/%m/%Y à %H:%M')} a été refusée.\n"
                f"Raison: {reason or 'Non spécifiée'}"
            ),
            related_object=reservation_request,
            priority='high'
        )
    
    @staticmethod
    def notify_teacher_timetable_published(timetable, teacher):
        """
        Notify a teacher when a timetable including their subjects is published.
        
        Args:
            timetable: The Timetable object
            teacher: The Teacher object
        """
        NotificationService.send_notification(
            user=teacher.user,
            notification_type='timetable_published',
            title=f"📅 Emploi du temps publié: {timetable.program.code}",
            message=(
                f"L'emploi du temps de {timetable.program.name} - "
                f"{timetable.get_semester_display()} ({timetable.academic_year}) "
                f"incluant vos matières a été publié."
            ),
            related_object=timetable
        )
    
    @staticmethod
    def notify_teacher_conflict_detected(session, conflicts):
        """
        Notify a teacher when a scheduling conflict is detected.
        
        Args:
            session: The Session that has conflicts
            conflicts: List of conflicting sessions
        """
        conflict_details = ", ".join([
            f"{c.subject} ({c.start_datetime.strftime('%H:%M')})" 
            for c in conflicts[:3]
        ])
        
        NotificationService.send_notification(
            user=session.teacher.user,
            notification_type='conflict_detected',
            title=f"⚠️ Conflit de séance: {session.subject}",
            message=(
                f"Votre séance {session.subject} du "
                f"{session.start_datetime.strftime('%d/%m/%Y à %H:%M')} "
                f"est en conflit avec: {conflict_details}."
            ),
            related_object=session,
            priority='urgent'
        )
    
    # ========== ASSOCIATION NOTIFICATIONS ==========
    
    @staticmethod
    def notify_association_reservation_approved(reservation_request):
        """
        Notify an association when their room reservation is approved.
        
        Args:
            reservation_request: The RoomReservationRequest object
        """
        if not reservation_request.association:
            return
        
        start = reservation_request.get_start_datetime()
        NotificationService.send_notification(
            user=reservation_request.association.user,
            notification_type='reservation_approved',
            title=f"✅ Réservation approuvée: {reservation_request.room.name}",
            message=(
                f"La réservation de la salle {reservation_request.room.name} "
                f"pour le {start.strftime('%d/%m/%Y à %H:%M')} a été approuvée pour "
                f"{reservation_request.association.name}."
            ),
            related_object=reservation_request,
            priority='high'
        )
    
    @staticmethod
    def notify_association_reservation_rejected(reservation_request, reason=""):
        """
        Notify an association when their room reservation is rejected.
        
        Args:
            reservation_request: The RoomReservationRequest object
            reason: Reason for rejection
        """
        if not reservation_request.association:
            return
        
        NotificationService.send_notification(
            user=reservation_request.association.user,
            notification_type='reservation_rejected',
            title=f"❌ Réservation refusée: {reservation_request.room.name}",
            message=(
                f"La réservation de la salle {reservation_request.room.name} "
                f"a été refusée pour {reservation_request.association.name}.\n"
                f"Raison: {reason or 'Non spécifiée'}"
            ),
            related_object=reservation_request,
            priority='high'
        )
    
    @staticmethod
    def notify_association_room_deactivated(room, associations):
        """
        Notify associations when a room they use for events is deactivated.
        
        Args:
            room: The Room object that was deactivated
            associations: List of Association objects to notify
        """
        for association in associations:
            NotificationService.send_notification(
                user=association.user,
                notification_type='room_deactivated',
                title=f"⚠️ Salle désactivée: {room.name}",
                message=(
                    f"La salle {room.name} utilisée pour vos événements "
                    f"a été désactivée. Vérifiez vos réservations."
                ),
                related_object=room,
                priority='high'
            )
    
    @staticmethod
    def notify_association_approved(association):
        """
        Notify association when their registration is approved.
        
        Args:
            association: The Association object
        """
        NotificationService.send_notification(
            user=association.user,
            notification_type='association_approved',
            title="🎉 Association approuvée!",
            message=(
                f"Félicitations! Votre association '{association.name}' a été approuvée. "
                f"Vous pouvez maintenant réserver des salles et organiser des événements."
            ),
            related_object=association,
            priority='high'
        )
    
    # ========== BULK NOTIFICATION HELPERS ==========
    
    @staticmethod
    def notify_timetable_update(timetable):
        """
        Notify all affected users when a timetable is updated.
        
        Args:
            timetable: The Timetable object
        """
        from apps.accounts.models import Student, Teacher
        from apps.scheduling.models import TimetableEntry
        
        # Notify students
        students = Student.objects.filter(group__program=timetable.program).distinct()
        
        for student in students:
            NotificationService.send_notification(
                user=student.user,
                notification_type='timetable_updated',
                title=f"Emploi du temps mis à jour",
                message=(
                    f"L'emploi du temps pour {timetable.program.name} - "
                    f"{timetable.get_semester_display()} ({timetable.academic_year}) a été mis à jour."
                ),
                related_object=timetable
            )
        
        # Get unique teachers from timetable entries
        teacher_ids = TimetableEntry.objects.filter(
            timetable=timetable,
            teacher__isnull=False
        ).values_list('teacher_id', flat=True).distinct()
        
        teachers = Teacher.objects.filter(id__in=teacher_ids)
        
        for teacher in teachers:
            NotificationService.send_notification(
                user=teacher.user,
                notification_type='timetable_updated',
                title=f"Emploi du temps mis à jour",
                message=(
                    f"Votre emploi du temps pour {timetable.program.name} - "
                    f"{timetable.get_semester_display()} ({timetable.academic_year}) a été mis à jour."
                ),
                related_object=timetable
            )
    
    @staticmethod
    def notify_session_cancelled(session):
        """
        Notify all affected users when a session is cancelled.
        
        Args:
            session: The cancelled Session object
        """
        # Notify students
        NotificationService.notify_students_session_cancelled(session)
        
        # Notify teacher
        NotificationService.send_notification(
            user=session.teacher.user,
            notification_type='session_cancelled',
            title=f"Séance annulée: {session.subject}",
            message=(
                f"Votre séance de {session.subject} prévue le "
                f"{session.start_datetime.strftime('%d/%m/%Y à %H:%M')} a été annulée."
            ),
            related_object=session
        )
    
    @staticmethod
    def notify_timetable_update(timetable, action='modified', entry=None):
        """
        Notify all students when a timetable is modified.
        Called when admin adds/moves/deletes entries in the timetable editor.
        
        Args:
            timetable: The Timetable object
            action: 'added', 'modified', 'deleted'
            entry: Optional TimetableEntry for context
        """
        from apps.accounts.models import Student
        
        if not timetable.is_published or not timetable.program:
            return
        
        students = Student.objects.filter(
            Q(program=timetable.program) | 
            Q(group__program=timetable.program)
        ).distinct().select_related('user')
        
        if entry:
            title = f"📅 Emploi du temps mis à jour"
            subject_info = entry.subject.name if hasattr(entry, 'subject') and entry.subject else "une séance"
            if action == 'added':
                message = f"Nouvelle séance ajoutée: {subject_info}"
            elif action == 'deleted':
                message = f"Séance supprimée: {subject_info}"
            else:
                message = f"Séance modifiée: {subject_info}"
        else:
            title = "📅 Emploi du temps mis à jour"
            message = f"L'emploi du temps de {timetable.program.name} a été modifié."
        
        for student in students:
            NotificationService.send_notification(
                user=student.user,
                notification_type='schedule_updated',
                title=title,
                message=message,
                related_object=timetable,
                priority='normal'
            )
    
    @staticmethod
    def notify_timetable_entry_change(entry, action='added'):
        """
        Notify students about a specific timetable entry change.
        Used by TimetableEntry signals.
        
        Args:
            entry: The TimetableEntry object
            action: 'added', 'modified', 'deleted'
        """
        from apps.accounts.models import Student
        
        if not entry.timetable or not entry.timetable.is_published:
            return
        
        program = entry.timetable.program
        if not program:
            return
        
        students = Student.objects.filter(
            Q(program=program) | 
            Q(group__program=program)
        ).distinct().select_related('user')
        
        day_names = {'MON': 'Lundi', 'TUE': 'Mardi', 'WED': 'Mercredi', 
                     'THU': 'Jeudi', 'FRI': 'Vendredi', 'SAT': 'Samedi'}
        day_name = day_names.get(entry.day_of_week, entry.day_of_week)
        time_str = entry.time_slot.get_display_time() if entry.time_slot else ''
        
        subject_name = entry.subject.name if entry.subject else 'Séance'
        room_name = entry.room.name if entry.room else ''
        
        event_label = ""
        if entry.is_exam:
            event_label = "🔴 EXAMEN - "
        elif entry.event_type == 'one_off':
            event_label = "⚡ Ponctuelle - "
        
        if action == 'added':
            title = f"📚 Nouvelle séance: {subject_name}"
            message = (
                f"{event_label}{subject_name}\n"
                f"📅 {day_name} {time_str}\n"
                f"📍 {room_name}" if room_name else f"{event_label}{subject_name}\n📅 {day_name} {time_str}"
            )
        elif action == 'deleted':
            title = f"❌ Séance supprimée: {subject_name}"
            message = f"{subject_name} - {day_name} {time_str} a été supprimée."
        else:
            title = f"✏️ Séance modifiée: {subject_name}"
            message = (
                f"{event_label}{subject_name}\n"
                f"📅 {day_name} {time_str}\n"
                f"📍 {room_name}" if room_name else f"{event_label}{subject_name}\n📅 {day_name} {time_str}"
            )
        
        for student in students:
            NotificationService.send_notification(
                user=student.user,
                notification_type='schedule_updated',
                title=title,
                message=message,
                related_object=entry.timetable,
                priority='high' if entry.is_exam else 'normal'
            )
