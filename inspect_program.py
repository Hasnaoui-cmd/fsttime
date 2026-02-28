import os
import django
from django.conf import settings
from django.db.models import Count

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.core.models import Program, Group
from apps.scheduling.models import Session

def inspect():
    program = Program.objects.first()
    if not program:
        print("No program found.")
        return

    print(f"Program: {program.name}")
    groups = Group.objects.filter(program=program)
    print(f"Total groups in this program: {groups.count()}")

    for g in groups:
        sessions = Session.objects.filter(groups=g).count()
        print(f"  Group: {g.name} | Sessions: {sessions}")

    # Check for sessions that are for the program but maybe not linked to any group?
    # (Shouldn't happen based on previous check, but let's be sure)
    program_sessions = Session.objects.filter(groups__program=program).distinct().count()
    print(f"\nTotal unique sessions for this program (via groups): {program_sessions}")

if __name__ == "__main__":
    inspect()
