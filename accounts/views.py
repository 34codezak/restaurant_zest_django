from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from .forms import (
    UserRegistrationForm, 
    LoginForm, 
    ReservationForm, 
    ProfileUpdateForm
)
from .models import Reservation, Table, Profile
import json


def register(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request, 
                f'Welcome to Zest Restaurant, {user.username}! Your account has been created.'
            )
            return redirect('home')
        else:
            messages.error(request, 'Registration failed. Please correct the errors below.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Redirect to next page if exists
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    """User logout view"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')


@login_required
def home_view(request):
    """Home dashboard for authenticated users"""
    # Get user's upcoming reservations
    upcoming = Reservation.objects.filter(
        user=request.user, 
        reservation_date__gte=timezone.now().date()
    ).order_by('reservation_date', 'reservation_time')[:5]
    
    # Get user's past reservations
    past = Reservation.objects.filter(
        user=request.user, 
        reservation_date__lt=timezone.now().date()
    ).order_by('-reservation_date', '-reservation_time')[:5]
    
    # Get available tables count
    available_tables = Table.objects.filter(
        status='available', 
        is_active=True
    ).count()
    
    context = {
        'upcoming_reservations': upcoming,
        'past_reservations': past,
        'available_tables': available_tables,
        'user_profile': getattr(request.user, 'profile', None),
    }
    
    return render(request, 'accounts/home.html', context)


@login_required
def make_reservation(request):
    available_tables = Table.objects.filter(status='available', is_active=True)
    table_capacities = {str(t.pk): t.capacity for t in available_tables}
    
    """Create a new table reservation"""
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.user = request.user
            reservation.status = 'confirmed'
            reservation.save()
            
            messages.success(
                request, 
                f'Reservation confirmed for Table {reservation.table.table_number} '
                f'on {reservation.reservation_date} at {reservation.reservation_time}!'
            )
            return redirect('reservation_detail', pk=reservation.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ReservationForm()

        # Pass table capacities as JSON string to template
    context = {
        'form': form,
        'table_capacities_json': json.dumps(table_capacities),  # <-- Add this
    }
    
    return render(request, 'accounts/reservation_form.html', {'form': form})


@login_required
def reservation_detail(request, pk):
    """View reservation details"""
    reservation = get_object_or_404(Reservation, pk=pk, user=request.user)
    return render(request, 'accounts/reservation_detail.html', {'reservation': reservation})


@login_required
def cancel_reservation(request, pk):
    """Cancel a reservation"""
    reservation = get_object_or_404(Reservation, pk=pk, user=request.user)
    
    if reservation.reservation_date >= timezone.now().date():
        reservation.status = 'cancelled'
        reservation.save()
        messages.success(request, 'Reservation has been cancelled.')
    else:
        messages.error(request, 'Cannot cancel past reservations.')
    
    return redirect('home')


@login_required
def my_reservations(request):
    """View all user reservations with pagination"""
    reservations = Reservation.objects.filter(
        user=request.user
    ).order_by('-reservation_date', '-reservation_time')
    
    paginator = Paginator(reservations, 10)  # 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'accounts/my_reservations.html', {'page_obj': page_obj})


@login_required
def profile_view(request):
    """View and edit user profile"""
    profile = getattr(request.user, 'profile', None)
    
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=profile)
    
    return render(request, 'accounts/profile.html', {'form': form, 'profile': profile})


@login_required
def protected_view(request):
    """Example protected view - only accessible to authenticated users"""
    return render(request, 'accounts/protected.html')