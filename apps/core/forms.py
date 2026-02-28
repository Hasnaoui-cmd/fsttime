"""
Forms for core app.
Includes bulk room creation, contact form, and group management.
"""

from django import forms
from django.forms import inlineformset_factory
from .models import Room, Equipment, ContactMessage, Program, Group


class BulkRoomCreateForm(forms.Form):
    """
    Form for creating multiple rooms in one operation.
    Example: B1 to B23 creates 23 rooms.
    """
    
    building = forms.CharField(
        max_length=50,
        label="Bâtiment",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: Bâtiment A'
        })
    )
    room_prefix = forms.CharField(
        max_length=10,
        label="Préfixe",
        help_text="Lettre ou code du bâtiment (ex: B)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: B'
        })
    )
    start_number = forms.IntegerField(
        label="Numéro de début",
        initial=1,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1
        })
    )
    end_number = forms.IntegerField(
        label="Numéro de fin",
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1
        })
    )
    room_type = forms.ChoiceField(
        choices=Room.ROOM_TYPE_CHOICES,
        label="Type de salle",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    capacity = forms.IntegerField(
        label="Capacité",
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1
        })
    )
    floor = forms.IntegerField(
        label="Étage",
        widget=forms.NumberInput(attrs={
            'class': 'form-control'
        })
    )
    equipment = forms.ModelMultipleChoiceField(
        queryset=Equipment.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Équipements disponibles"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_number')
        end = cleaned_data.get('end_number')
        
        if start and end and start > end:
            raise forms.ValidationError(
                "Le numéro de début doit être inférieur ou égal au numéro de fin."
            )
        
        if start and end and (end - start) > 100:
            raise forms.ValidationError(
                "Vous ne pouvez pas créer plus de 100 salles à la fois."
            )
        
        return cleaned_data


class ContactForm(forms.ModelForm):
    """
    Contact form for all users including guests.
    """
    
    class Meta:
        model = ContactMessage
        fields = ['sender_name', 'sender_email', 'subject', 'message']
        labels = {
            'sender_name': 'Votre nom',
            'sender_email': 'Votre email',
            'subject': 'Sujet',
            'message': 'Message',
        }
        widgets = {
            'sender_name': forms.TextInput(attrs={
                'placeholder': 'Nom complet'
            }),
            'sender_email': forms.EmailInput(attrs={
                'placeholder': 'email@exemple.com'
            }),
            'subject': forms.TextInput(attrs={
                'placeholder': 'Sujet de votre message'
            }),
            'message': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'Décrivez votre demande ou question...'
            }),
        }


class ContactResponseForm(forms.ModelForm):
    """
    Form for admin to respond to contact messages.
    """
    
    class Meta:
        model = ContactMessage
        fields = ['status', 'response']
        labels = {
            'status': 'Statut',
            'response': 'Réponse',
        }
        widgets = {
            'status': forms.Select(),
            'response': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'Rédigez votre réponse...'
            }),
        }


class RoomForm(forms.ModelForm):
    """
    Form for creating/editing a single room.
    """
    
    class Meta:
        model = Room
        fields = ['name', 'room_type', 'capacity', 'building', 'floor', 'equipment', 'is_active']
        labels = {
            'name': 'Nom de la salle',
            'room_type': 'Type',
            'capacity': 'Capacité',
            'building': 'Bâtiment',
            'floor': 'Étage',
            'equipment': 'Équipements',
            'is_active': 'Active',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'room_type': forms.Select(attrs={'class': 'form-select'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'building': forms.TextInput(attrs={'class': 'form-control'}),
            'floor': forms.NumberInput(attrs={'class': 'form-control'}),
            'equipment': forms.CheckboxSelectMultiple,
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class GroupForm(forms.ModelForm):
    """
    Form for creating/editing a single group within a program.
    """
    
    class Meta:
        model = Group
        fields = ['name', 'capacity', 'academic_year']
        labels = {
            'name': 'Nom du groupe',
            'capacity': 'Capacité',
            'academic_year': 'Année universitaire',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': 'Ex: TD 1, Groupe A'
            }),
            'capacity': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
                'min': 1,
                'placeholder': '30'
            }),
            'academic_year': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': '2025-2026'
            }),
        }


# Inline formset for managing groups within a program
GroupFormSet = inlineformset_factory(
    Program,
    Group,
    form=GroupForm,
    extra=0,  # We use JS template for adding new groups
    can_delete=True,
    min_num=0,
    validate_min=False,
)
