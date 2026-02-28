"""
Admin configuration for core app.
"""

from django.contrib import admin
from .models import Equipment, Room, Program, Group, ContactMessage


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'room_type', 'building', 'floor', 'capacity', 'is_active')
    list_filter = ('room_type', 'building', 'is_active')
    search_fields = ('name', 'building')
    filter_horizontal = ('equipment',)


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'department', 'degree_level')
    list_filter = ('department', 'degree_level')
    search_fields = ('code', 'name')


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'program', 'academic_year', 'capacity')
    list_filter = ('program', 'academic_year')
    search_fields = ('name', 'program__name')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'sender_name', 'sender_email', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('subject', 'sender_name', 'sender_email')
    readonly_fields = ('sender_name', 'sender_email', 'subject', 'message', 'user', 'created_at')
