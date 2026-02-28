"""
Views for public pages accessible without authentication.
"""

from django.views.generic import TemplateView, ListView
from django.db.models import Count

from apps.core.models import Program, Room


class LandingPageView(TemplateView):
    """
    Public landing page view.
    Accessible without authentication.
    """
    
    template_name = 'public/landing.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get statistics
        from apps.core.models import ContactMessage
        from apps.scheduling.models import RoomReservationRequest, Timetable
        from apps.accounts.models import Association
        
        context['departments'] = Program.objects.values_list('department', flat=True).distinct()
        context['total_rooms'] = Room.objects.filter(is_active=True).count()
        context['total_programs'] = Program.objects.count()
        context['total_timetables'] = Timetable.objects.filter(is_generated=True).count()
        
        # New real-time stats
        context['pending_reservations'] = RoomReservationRequest.objects.filter(status='pending').count()
        context['pending_messages'] = ContactMessage.objects.filter(status='unread').count()
        context['pending_associations'] = Association.objects.filter(is_approved=False).count()
        
        # Get featured programs
        context['featured_programs'] = Program.objects.all()[:6]
        
        return context


class PublicRoomSearchView(ListView):
    """
    Public room search view.
    Accessible without authentication.
    """
    
    model = Room
    template_name = 'public/room_search.html'
    context_object_name = 'rooms'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Room.objects.filter(is_active=True)
        
        # Filter by building
        building = self.request.GET.get('building')
        if building:
            queryset = queryset.filter(building__icontains=building)
        
        # Filter by type
        room_type = self.request.GET.get('type')
        if room_type:
            queryset = queryset.filter(room_type=room_type)
        
        # Filter by minimum capacity
        min_capacity = self.request.GET.get('min_capacity')
        if min_capacity:
            try:
                queryset = queryset.filter(capacity__gte=int(min_capacity))
            except ValueError:
                pass
        
        return queryset.order_by('building', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['room_types'] = Room.ROOM_TYPE_CHOICES
        context['buildings'] = Room.objects.values_list('building', flat=True).distinct()
        context['current_building'] = self.request.GET.get('building', '')
        context['current_type'] = self.request.GET.get('type', '')
        context['current_capacity'] = self.request.GET.get('min_capacity', '')
        
        # Calculate status for each room in the current page
        from django.utils import timezone
        from apps.scheduling.models import Session
        
        now = timezone.now()
        
        # Get the actual list of rooms (works with pagination)
        rooms = context.get('object_list', context.get('rooms', []))
        
        for room in rooms:
            # Find current session
            current_session = Session.objects.filter(
                room=room,
                start_datetime__lte=now,
                end_datetime__gt=now,
                is_validated=True
            ).select_related('teacher__user').prefetch_related('groups').first()
            
            # Find next session today
            next_session = Session.objects.filter(
                room=room,
                start_datetime__gt=now,
                start_datetime__date=now.date(),
                is_validated=True
            ).select_related('teacher__user').prefetch_related('groups').order_by('start_datetime').first()
            
            # Set simple attributes directly on room object
            room.status_available = not current_session
            room.status_current = current_session
            room.status_next = next_session
            room.status_minutes = 0
            
            if current_session:
                time_remaining = current_session.end_datetime - now
                room.status_minutes = int(time_remaining.total_seconds() / 60)
        
        context['current_time'] = now
        return context



class PublicProgramListView(ListView):
    """
    Public program list view with filtering.
    """
    
    model = Program
    template_name = 'public/program_list.html'
    context_object_name = 'programs'
    
    def get_queryset(self):
        queryset = Program.objects.all()
        
        # Search filter
        search = self.request.GET.get('q', '')
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(code__icontains=search)
            )
        
        # Department filter
        dept = self.request.GET.get('dept', '')
        if dept:
            queryset = queryset.filter(department=dept)
        
        # Level filter
        level = self.request.GET.get('level', '')
        if level:
            queryset = queryset.filter(degree_level=level)
        
        return queryset.order_by('department', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Program.objects.values_list('department', flat=True).distinct()
        return context


class AboutView(TemplateView):
    """About page view"""
    
    template_name = 'public/about.html'
