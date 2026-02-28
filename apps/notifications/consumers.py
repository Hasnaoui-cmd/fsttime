"""
WebSocket consumer for real-time notifications.
"""

from channels.generic.websocket import AsyncWebsocketConsumer
import json


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for handling real-time notifications.
    Each authenticated user joins their own notification group.
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope["user"]
        
        if self.user.is_authenticated:
            # Create a unique group name for this user
            self.group_name = f"user_{self.user.id}"
            
            # Add to the user's notification group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            
            await self.accept()
        else:
            # Reject connection for unauthenticated users
            await self.close()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages.
        Currently supports marking notifications as read.
        """
        try:
            data = json.loads(text_data)
            
            if data.get('action') == 'mark_read':
                notification_id = data.get('notification_id')
                if notification_id:
                    # Mark notification as read (handled via HTTP API)
                    await self.send(text_data=json.dumps({
                        'type': 'acknowledgement',
                        'notification_id': notification_id,
                        'status': 'received'
                    }))
            
            elif data.get('action') == 'ping':
                # Keep-alive ping
                await self.send(text_data=json.dumps({
                    'type': 'pong'
                }))
                
        except json.JSONDecodeError:
            pass
    
    async def notification_message(self, event):
        """
        Send notification to WebSocket.
        Called when a notification is sent to the user's group.
        """
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))
