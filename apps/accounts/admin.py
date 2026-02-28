"""
Admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, Teacher, Student, Association


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations supplémentaires', {'fields': ('role', 'phone')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informations supplémentaires', {'fields': ('role', 'phone')}),
    )


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'department', 'specialization')
    list_filter = ('department',)
    search_fields = ('user__first_name', 'user__last_name', 'employee_id')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id', 'group', 'enrollment_year')
    list_filter = ('enrollment_year', 'group__program')
    search_fields = ('user__first_name', 'user__last_name', 'student_id')


@admin.register(Association)
class AssociationAdmin(admin.ModelAdmin):
    list_display = ('name', 'president_name', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('name', 'president_name', 'email')
    actions = ['approve_associations']
    
    @admin.action(description="Approuver les associations sélectionnées")
    def approve_associations(self, request, queryset):
        for association in queryset:
            association.approve()
        self.message_user(request, f"{queryset.count()} association(s) approuvée(s).")
