from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Reservation, Profile, Table
from datetime import datetime


class UserRegistrationForm(UserCreationForm):
    """Custom registration form with email field"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )
    
    phone = forms.CharField(
        required=False,
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone number (optional)'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
            'password1': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter password'
            }),
            'password2': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Confirm password'
            }),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Save phone to profile
            if hasattr(user, 'profile'):
                user.profile.phone = self.cleaned_data.get('phone', '')
                user.profile.save()
        return user


class LoginForm(AuthenticationForm):
    """Custom login form with better styling"""
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )


class ReservationForm(forms.ModelForm):
    """Form for creating table reservations with guest capacity validation"""
    
    class Meta:
        model = Reservation
        fields = ['table', 'reservation_date', 'reservation_time', 
                  'number_of_guests', 'special_requests', 'phone_number', 'email']
        widgets = {
            'table': forms.Select(attrs={'class': 'form-control'}),
            'reservation_date': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date'
            }),
            'reservation_time': forms.TimeInput(attrs={
                'class': 'form-control', 
                'type': 'time'
            }),
            'number_of_guests': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': 1, 
                'max': 20,
                'id': 'id_number_of_guests'  # Add ID for JavaScript
            }),
            'special_requests': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3
            }),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter available tables
        available_tables = Table.objects.filter(
            status='available', 
            is_active=True
        )
        self.fields['table'].queryset = available_tables
        
        # Set minimum date to today
        self.fields['reservation_date'].widget.attrs['min'] = datetime.now().date().isoformat()
        
        # Add data attributes for JavaScript validation
        if available_tables.exists():
            table_capacities = {t.pk: t.capacity for t in available_tables}
            self.fields['table'].widget.attrs['data-capacities'] = str(table_capacities)
    
    def clean_number_of_guests(self):
        """Validate number of guests against table capacity"""
        number_of_guests = self.cleaned_data.get('number_of_guests')
        table = self.cleaned_data.get('table')
        
        if number_of_guests and table:
            if number_of_guests > table.capacity:
                raise ValidationError(
                    f"Table {table.table_number} can only accommodate up to {table.capacity} guests. "
                    f"You selected {number_of_guests} guests."
                )
            if number_of_guests < 1:
                raise ValidationError("Number of guests must be at least 1.")
        
        return number_of_guests
    
    def clean(self):
        """Additional cross-field validation"""
        cleaned_data = super().clean()
        reservation_date = cleaned_data.get('reservation_date')
        reservation_time = cleaned_data.get('reservation_time')
        table = cleaned_data.get('table')
        number_of_guests = cleaned_data.get('number_of_guests')
        
        # Check for conflicting reservations
        if reservation_date and reservation_time and table:
            conflicting = Reservation.objects.filter(
                table=table,
                reservation_date=reservation_date,
                reservation_time=reservation_time,
                status__in=['pending', 'confirmed']
            ).exists()
            
            if conflicting:
                raise ValidationError(
                    "This table is already reserved for the selected date and time."
                )
        
        # Double-check capacity validation (in case clean_number_of_guests wasn't called)
        if table and number_of_guests and number_of_guests > table.capacity:
            raise ValidationError(
                f"Cannot reserve for {number_of_guests} guests. "
                f"Table {table.table_number} maximum capacity is {table.capacity}."
            )
        
        return cleaned_data
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter available tables
        available_tables = Table.objects.filter(
            status='available', 
            is_active=True
        )
        
        # Set queryset
        self.fields['table'].queryset = available_tables
        
        # Add helpful message if no tables available
        if not available_tables.exists():
            self.fields['table'].help_text = "No tables currently available. Please try another date or contact us."
            self.fields['table'].widget.attrs['disabled'] = True
        else:
            self.fields['table'].help_text = f"{available_tables.count()} table(s) available"
        
        # Set minimum date to today
        self.fields['reservation_date'].widget.attrs['min'] = datetime.now().date().isoformat()


class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile"""
    
    class Meta:
        model = Profile
        fields = ['phone', 'date_of_birth']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            # 'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date'
            }),
        }