"""
Management command to seed time slots for timetable scheduling.
Creates 5 fixed time slots per day as per university schedule.
"""

from django.core.management.base import BaseCommand
from datetime import time


class Command(BaseCommand):
    help = 'Seed the 5 fixed time slots for semester timetables'

    def handle(self, *args, **kwargs):
        from apps.scheduling.models import TimeSlot
        
        # Clear existing time slots
        old_count = TimeSlot.objects.count()
        if old_count > 0:
            self.stdout.write(
                self.style.WARNING(f"[!] Suppression de {old_count} anciens creneaux...")
            )
            TimeSlot.objects.all().delete()
        
        # Define the 5 fixed time slots
        time_slots = [
            {'slot_number': 1, 'start': time(9, 0), 'end': time(10, 45)},   # 09:00 - 10:45
            {'slot_number': 2, 'start': time(10, 45), 'end': time(12, 15)}, # 10:45 - 12:15
            {'slot_number': 3, 'start': time(12, 30), 'end': time(14, 0)},  # 12:30 - 14:00
            {'slot_number': 4, 'start': time(14, 15), 'end': time(15, 45)}, # 14:15 - 15:45
            {'slot_number': 5, 'start': time(16, 0), 'end': time(17, 30)},  # 16:00 - 17:30
        ]
        
        created_count = 0
        
        for slot_data in time_slots:
            slot = TimeSlot.objects.create(
                slot_number=slot_data['slot_number'],
                start_time=slot_data['start'],
                end_time=slot_data['end']
            )
            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"[OK] Creneau {slot.slot_number}: "
                    f"{slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}"
                )
            )
        
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(
            self.style.SUCCESS(
                f"\n[SUCCESS] Creneaux horaires configures!\n"
                f"   - {created_count} creneaux crees\n"
                f"\n   Horaires:\n"
                f"   - Creneau 1: 09:00 - 10:45\n"
                f"   - Creneau 2: 10:45 - 12:15\n"
                f"   - Creneau 3: 12:30 - 14:00\n"
                f"   - Creneau 4: 14:15 - 15:45\n"
                f"   - Creneau 5: 16:00 - 17:30"
            )
        )
