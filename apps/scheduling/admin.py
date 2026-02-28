"""
Admin configuration for scheduling app.
"""

from django.contrib import admin
from .models import (
    Session, Timetable, RoomReservationRequest, TeacherUnavailability,
    TimeSlot, TimetableEntry, Subject, TimetableChangeRequest
)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('subject', 'session_type', 'teacher', 'room', 'start_datetime', 'is_validated')
    list_filter = ('session_type', 'is_exam', 'is_validated', 'start_datetime')
    search_fields = ('subject', 'teacher__user__first_name', 'teacher__user__last_name')
    filter_horizontal = ('groups',)
    date_hierarchy = 'start_datetime'


@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ('program', 'semester', 'academic_year', 'is_published', 'is_generated', 'created_at')
    list_filter = ('program', 'semester', 'is_published', 'is_generated')
    filter_horizontal = ('sessions', 'study_groups')
    search_fields = ('name', 'program__name', 'program__code')


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('slot_number', 'start_time', 'end_time', 'get_display_time')
    list_display_links = ('slot_number',)
    ordering = ('slot_number',)


@admin.register(TimetableEntry)
class TimetableEntryAdmin(admin.ModelAdmin):
    list_display = ('timetable', 'day_of_week', 'time_slot', 'subject', 'teacher', 'room', 'study_group')
    list_filter = ('timetable__program', 'day_of_week', 'session_type', 'timetable__semester')
    search_fields = ('subject__name', 'subject__code', 'teacher__user__first_name', 'room__name')
    raw_id_fields = ('timetable', 'subject', 'teacher', 'room', 'study_group')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'program', 'teacher', 'session_type', 'hours_per_week')
    list_filter = ('program', 'session_type', 'requires_lab')
    search_fields = ('code', 'name', 'teacher__user__first_name')


@admin.register(RoomReservationRequest)
class RoomReservationRequestAdmin(admin.ModelAdmin):
    list_display = ('room', 'requester_type', 'requested_datetime', 'status', 'created_at')
    list_filter = ('status', 'requester_type', 'is_exam')
    search_fields = ('room__name', 'reason')
    date_hierarchy = 'created_at'
    actions = ['approve_reservations', 'reject_reservations']
    
    @admin.action(description="Approuver les réservations sélectionnées")
    def approve_reservations(self, request, queryset):
        for reservation in queryset.filter(status='pending'):
            reservation.approve(request.user)
        self.message_user(request, f"Réservations approuvées.")
    
    @admin.action(description="Rejeter les réservations sélectionnées")
    def reject_reservations(self, request, queryset):
        for reservation in queryset.filter(status='pending'):
            reservation.reject(request.user, "Rejeté en masse par l'administrateur")
        self.message_user(request, f"Réservations rejetées.")


@admin.register(TeacherUnavailability)
class TeacherUnavailabilityAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'start_datetime', 'end_datetime', 'reason')
    list_filter = ('teacher', 'start_datetime')
    date_hierarchy = 'start_datetime'


@admin.register(TimetableChangeRequest)
class TimetableChangeRequestAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'subject', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('teacher__user__last_name', 'subject__name', 'desired_change')
    list_editable = ('status',)
    date_hierarchy = 'created_at'
