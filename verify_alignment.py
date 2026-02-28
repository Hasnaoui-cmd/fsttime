import os
import django
from django.test import RequestFactory

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import User
from apps.scheduling.views import MyTimetableView

def verify_alignment():
    print("--- Verifying Master Timetable Alignment (Including Drafts) ---")
    try:
        # Check manar1
        user = User.objects.get(username='manar1')
        factory = RequestFactory()
        request = factory.get('/scheduling/my-timetable/')
        request.user = user
        
        view = MyTimetableView()
        view.request = request
        context = view.get_context_data()
        
        total_entries = context.get('total_entries', 0)
        entry_dict = context.get('entry_dict', {})
        timetable = context.get('timetable')
        
        print(f"User: {user.username}")
        print(f"Timetable Found: {timetable.id if timetable else 'None'} (Published: {timetable.is_published if timetable else 'N/A'})")
        print(f"Total Entries: {total_entries}")
        
        if timetable and timetable.id == 31: # We know draft 31 is the master
            print("✅ SUCCESS: Student is now seeing the Master Draft (ID 31).")
        elif total_entries > 0:
            print("✅ SUCCESS: Student is seeing entries.")
        else:
            print("❌ FAILURE: Timetable is empty.")
            
        # Sample entry check
        if entry_dict:
            for key, items in entry_dict.items():
                for item in items:
                    subj = item['subject'] if isinstance(item, dict) else item.subject
                    name = subj['name'] if isinstance(subj, dict) else subj.name
                    print(f"  - Sample Entry: {name} at {key}")
                break
                
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    verify_alignment()
