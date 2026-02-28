"""
Forms for user registration and authentication.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils import timezone

from .models import User, Student, Association, Teacher
from apps.core.models import Program, Group


class LoginForm(AuthenticationForm):
    """Custom login form with French labels"""
    
    username = forms.CharField(
        label="Nom d'utilisateur",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Nom d'utilisateur"
        })
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe'
        })
    )


class StudentRegistrationForm(UserCreationForm):
    """
    Registration form for students.
    Dynamic group selection based on program.
    """
    
    first_name = forms.CharField(
        max_length=100,
        required=True,
        label="Prénom",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=100,
        required=True,
        label="Nom",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        label="Email universitaire",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'prenom.nom@university.ma'
        })
    )
    student_id = forms.CharField(
        max_length=20,
        required=True,
        label="Numéro d'étudiant",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: S12345'
        })
    )
    program = forms.ModelChoiceField(
        queryset=Program.objects.all(),
        required=True,
        label="Filière",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.none(),
        required=False,
        label="Groupe d'étude",
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Optionnel - vous pouvez sélectionner un groupe plus tard"
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Style password fields
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': "Nom d'utilisateur"
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Mot de passe'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirmer le mot de passe'
        })
        
        # Dynamic group loading based on program
        if 'program' in self.data:
            try:
                program_id = int(self.data.get('program'))
                self.fields['group'].queryset = Group.objects.filter(program_id=program_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['group'].queryset = Group.objects.all()
    
    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id')
        if Student.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError("Ce numéro d'étudiant existe déjà.")
        return student_id
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'student'
        
        if commit:
            user.save()
            Student.objects.create(
                user=user,
                student_id=self.cleaned_data['student_id'],
                student_email=self.cleaned_data.get('email'),
                enrollment_year=timezone.now().year,
                program=self.cleaned_data.get('program'),  # Save program directly
                group=self.cleaned_data.get('group')  # Optional - can be None
            )
        
        return user


class AssociationRegistrationForm(UserCreationForm):
    """
    Registration form for associations.
    Requires admin approval after submission.
    """
    
    association_name = forms.CharField(
        max_length=200,
        required=True,
        label="Nom de l'association",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: Club Informatique'
        })
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': "Description de l'association et ses activités"
        }),
        required=True,
        label="Description de l'association"
    )
    president_name = forms.CharField(
        max_length=100,
        required=True,
        label="Nom du président",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        label="Email de l'association",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'contact@association.ma'
        })
    )
    phone = forms.CharField(
        max_length=20,
        required=True,
        label="Téléphone",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+212 6XX XXX XXX'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': "Identifiant de l'association"
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Email de connexion'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Mot de passe'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirmer le mot de passe'
        })
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'association'
        # Association users can now access immediately without admin approval
        
        if commit:
            user.save()
            Association.objects.create(
                user=user,
                name=self.cleaned_data['association_name'],
                description=self.cleaned_data['description'],
                president_name=self.cleaned_data['president_name'],
                email=self.cleaned_data['email'],
                phone=self.cleaned_data['phone'],
                is_approved=True  # Auto-approved
            )
        
        return user


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'email': 'Email',
            'phone': 'Téléphone',
        }


class TeacherRegistrationForm(UserCreationForm):
    """
    Registration form for teachers.
    Creates user account and teacher profile.
    """
    
    first_name = forms.CharField(
        max_length=100,
        required=True,
        label="Prénom",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=100,
        required=True,
        label="Nom",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        label="Email professionnel",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'prenom.nom@university.ma'
        })
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        label="Téléphone",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+212 6XX XXX XXX'
        })
    )
    employee_id = forms.CharField(
        max_length=20,
        required=True,
        label="Matricule",
        help_text="Votre identifiant unique d'enseignant",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: ENS12345'
        })
    )
    specialization = forms.ChoiceField(
        choices=[('', '-- Sélectionnez une spécialité --')] + list(Teacher.SPECIALIZATION_CHOICES),
        required=True,
        label="Spécialité",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    department = forms.ChoiceField(
        choices=[('', '-- Sélectionnez un département --')] + list(Teacher.DEPARTMENT_CHOICES),
        required=True,
        label="Département",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': "Nom d'utilisateur"
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Mot de passe'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirmer le mot de passe'
        })
    
    def clean_employee_id(self):
        employee_id = self.cleaned_data.get('employee_id')
        if Teacher.objects.filter(employee_id=employee_id).exists():
            raise forms.ValidationError("Ce matricule existe déjà.")
        return employee_id
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Cet email est déjà utilisé.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'teacher'
        user.phone = self.cleaned_data.get('phone', '')
        
        if commit:
            user.save()
            Teacher.objects.create(
                user=user,
                employee_id=self.cleaned_data['employee_id'],
                specialization=self.cleaned_data['specialization'],
                department=self.cleaned_data['department']
            )
        
        return user
