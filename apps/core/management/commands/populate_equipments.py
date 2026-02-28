"""
Management command to seed equipment data.
Run with: python manage.py seed_equipments
"""

from django.core.management.base import BaseCommand
from apps.core.models import Equipment


class Command(BaseCommand):
    help = 'Seed equipment data with icons'

    def handle(self, *args, **kwargs):
        equipments = [
            {'name': 'Projecteur', 'icon': 'fas fa-video', 'description': 'Projecteur multimédia'},
            {'name': 'Ordinateurs', 'icon': 'fas fa-desktop', 'description': 'Postes informatiques'},
            {'name': 'Tableau interactif', 'icon': 'fas fa-chalkboard', 'description': 'Tableau blanc interactif'},
            {'name': 'Système audio', 'icon': 'fas fa-volume-up', 'description': 'Système de sonorisation'},
            {'name': 'Microphones', 'icon': 'fas fa-microphone', 'description': 'Microphones sans fil'},
            {'name': 'WiFi', 'icon': 'fas fa-wifi', 'description': 'Connexion WiFi haut débit'},
            {'name': 'Climatisation', 'icon': 'fas fa-snowflake', 'description': 'Climatisation centrale'},
            {'name': 'Caméras', 'icon': 'fas fa-camera', 'description': 'Caméras de surveillance/visioconférence'},
            {'name': 'Écran LED', 'icon': 'fas fa-tv', 'description': 'Grand écran LED'},
            {'name': 'Prises électriques', 'icon': 'fas fa-plug', 'description': 'Prises multiples pour étudiants'},
            {'name': 'Tableau blanc', 'icon': 'fas fa-square', 'description': 'Tableau blanc classique'},
            {'name': 'Vidéoconférence', 'icon': 'fas fa-video', 'description': 'Équipement de visioconférence'},
        ]
        
        created_count = 0
        updated_count = 0
        
        for eq_data in equipments:
            equipment, created = Equipment.objects.update_or_create(
                name=eq_data['name'],
                defaults={
                    'icon': eq_data['icon'],
                    'description': eq_data['description']
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f"  ✅ Created: {equipment.name}")
            else:
                updated_count += 1
                self.stdout.write(f"  🔄 Updated: {equipment.name}")
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Equipment seeded successfully! Created: {created_count}, Updated: {updated_count}'
        ))
