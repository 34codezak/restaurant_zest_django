from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

class Profile(models.Model):
    """Extended user profile with additional information"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True)
    # profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f'{self.user.username} Profile'

# Auto-create profile when user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


class Table(models.Model):
    """Restaurant tables for reservations"""
    
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Maintenance'),
    ]
    
    table_number = models.CharField(max_length=10, unique=True)
    capacity = models.PositiveIntegerField(default=2)
    location = models.CharField(max_length=50, default='Main Dining')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['table_number']
        verbose_name = 'Table'
        verbose_name_plural = 'Tables'
    
    def __str__(self):
        return f'Table {self.table_number} ({self.capacity} seats)'
    
    @classmethod
    def get_occupancy_stats(cls, date=None):
        """Get table occupancy statistics for a given date"""
        if date is None:
            date = timezone.now().date()
        
        total_tables = cls.objects.filter(is_active=True).count()
        reserved_count = Reservation.objects.filter(
            reservation_date=date,
            table__is_active=True,
            status__in=['pending', 'confirmed']
        ).values('table').distinct().count()
        
        return {
            'total_tables': total_tables,
            'reserved': reserved_count,
            'available': total_tables - reserved_count,
            'occupancy_rate': round((reserved_count / total_tables * 100), 1) if total_tables > 0 else 0
        }


class Reservation(models.Model):
    """Table reservations made by users"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='reservations')
    reservation_date = models.DateField()
    reservation_time = models.TimeField()
    number_of_guests = models.PositiveIntegerField()
    special_requests = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    phone_number = models.CharField(max_length=15)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-reservation_date', '-reservation_time']
        verbose_name = 'Reservation'
        verbose_name_plural = 'Reservations'
        indexes = [
            models.Index(fields=['reservation_date', 'reservation_time']),
        ]
    
    def __str__(self):
        return f'{self.user.username} - Table {self.table.table_number} ({self.reservation_date})'
    
    def is_upcoming(self):
        return timezone.now().date() <= self.reservation_date