"""
Views for notifications API and pages.
"""

from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    """Full page notification list with filtering and pagination"""
    
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Notification.objects.filter(recipient=self.request.user)
        
        # Apply filter based on URL parameter
        filter_type = self.request.GET.get('filter', 'all')
        
        if filter_type == 'unread':
            queryset = queryset.filter(is_read=False)
        elif filter_type == 'reservation':
            queryset = queryset.filter(notification_type__in=[
                'reservation_pending', 'reservation_approved', 'reservation_rejected'
            ])
        elif filter_type == 'session':
            queryset = queryset.filter(notification_type__in=[
                'session_scheduled', 'session_modified', 'session_cancelled',
                'exam_scheduled', 'teacher_unavailable'
            ])
        elif filter_type == 'timetable':
            queryset = queryset.filter(notification_type__in=[
                'timetable_published', 'timetable_updated'
            ])
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.request.GET.get('filter', 'all')
        context['unread_count'] = Notification.objects.filter(
            recipient=self.request.user,
            is_read=False
        ).count()
        return context


class UnreadCountView(LoginRequiredMixin, View):
    """API endpoint to get unread notification count"""
    
    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        return JsonResponse({'count': count})


class RecentNotificationsView(LoginRequiredMixin, View):
    """API endpoint to get recent notifications for dropdown"""
    
    def get(self, request):
        notifications = Notification.objects.filter(
            recipient=request.user
        ).order_by('-created_at')[:10]
        
        notifications_data = [
            {
                'id': n.id,
                'type': n.notification_type,
                'priority': n.priority,
                'title': n.title,
                'message': n.message[:100] + '...' if len(n.message) > 100 else n.message,
                'is_read': n.is_read,
                'icon': n.get_icon(),
                'color': n.get_color(),
                'link_url': n.get_link_url(),
                'created_at': n.created_at.isoformat(),
            }
            for n in notifications
        ]
        
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        return JsonResponse({
            'notifications': notifications_data,
            'unread_count': unread_count
        })


@method_decorator(csrf_exempt, name='dispatch')
class MarkAsReadView(LoginRequiredMixin, View):
    """API endpoint to mark a notification as read"""
    
    def post(self, request, pk):
        try:
            notification = Notification.objects.get(
                pk=pk,
                recipient=request.user
            )
            notification.mark_as_read()
            return JsonResponse({'success': True})
        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)


@method_decorator(csrf_exempt, name='dispatch')
class MarkAllAsReadView(LoginRequiredMixin, View):
    """API endpoint to mark all notifications as read"""
    
    def post(self, request):
        Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True)
        
        # Redirect back to notification list if coming from there
        referer = request.META.get('HTTP_REFERER', '')
        if 'notifications' in referer:
            return redirect('notification_list')
        
        return JsonResponse({'success': True})


class NotificationDetailAPIView(LoginRequiredMixin, View):
    """API endpoint to get detailed info about a notification's related object"""
    
    def get(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, recipient=request.user)
        except Notification.DoesNotExist:
            return JsonResponse({'error': 'Notification introuvable'}, status=404)
        
        # Mark as read
        if not notification.is_read:
            notification.is_read = True
            notification.save()
        
        data = {
            'id': notification.id,
            'type': notification.notification_type,
            'title': notification.title,
            'message': notification.message,
            'priority': notification.priority,
            'created_at': notification.created_at.strftime('%d/%m/%Y à %H:%M'),
            'detail': None,
        }
        
        # Fetch related object details
        if notification.related_object_type and notification.related_object_id:
            try:
                if notification.related_object_type == 'TeacherUnavailability':
                    from apps.scheduling.models import TeacherUnavailability
                    obj = TeacherUnavailability.objects.select_related('teacher__user').get(
                        pk=notification.related_object_id
                    )
                    data['detail'] = {
                        'object_type': 'unavailability',
                        'teacher_name': obj.teacher.user.get_full_name(),
                        'start': obj.start_datetime.strftime('%d/%m/%Y %H:%M'),
                        'end': obj.end_datetime.strftime('%d/%m/%Y %H:%M'),
                        'reason': obj.reason,
                        'is_recurring': obj.is_recurring,
                        'created_at': obj.created_at.strftime('%d/%m/%Y %H:%M'),
                    }
                
                elif notification.related_object_type == 'TimetableChangeRequest':
                    from apps.scheduling.models import TimetableChangeRequest
                    obj = TimetableChangeRequest.objects.select_related(
                        'teacher__user', 'subject', 'current_entry'
                    ).get(pk=notification.related_object_id)
                    data['detail'] = {
                        'object_type': 'change_request',
                        'teacher_name': obj.teacher.user.get_full_name(),
                        'subject_code': obj.subject.code,
                        'subject_name': obj.subject.name,
                        'desired_change': obj.desired_change,
                        'reason': obj.reason,
                        'status': obj.status,
                        'status_display': obj.get_status_display(),
                        'admin_notes': obj.admin_notes,
                        'created_at': obj.created_at.strftime('%d/%m/%Y %H:%M'),
                        'current_entry': str(obj.current_entry) if obj.current_entry else None,
                        'change_request_id': obj.id,
                    }
                
                elif notification.related_object_type == 'RoomReservationRequest':
                    from apps.scheduling.models import RoomReservationRequest
                    obj = RoomReservationRequest.objects.select_related(
                        'teacher__user', 'association__user', 'room', 'program'
                    ).get(pk=notification.related_object_id)
                    start = obj.get_start_datetime()
                    end = obj.get_end_datetime()
                    data['detail'] = {
                        'object_type': 'reservation',
                        'requester_type': obj.requester_type,
                        'requester_name': obj.teacher.user.get_full_name() if obj.teacher else (obj.association.name if obj.association else ''),
                        'room_name': obj.room.name if obj.room else '',
                        'program_name': obj.program.name if obj.program else '',
                        'subject': obj.subject,
                        'reservation_type': obj.reservation_type,
                        'reservation_type_display': obj.get_reservation_type_display(),
                        'start': start.strftime('%d/%m/%Y %H:%M') if start else '',
                        'end': end.strftime('%d/%m/%Y %H:%M') if end else '',
                        'reason': obj.reason,
                        'status': obj.status,
                        'status_display': obj.get_status_display(),
                        'is_exam': obj.is_exam,
                        'admin_notes': obj.admin_notes,
                        'created_at': obj.created_at.strftime('%d/%m/%Y %H:%M'),
                    }
                    
            except Exception:
                data['detail'] = None
        
        return JsonResponse(data)
