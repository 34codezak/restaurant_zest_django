from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile, Table, Reservation


# Inline Profile Admin
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    readonly_fields = ['created_at', 'updated_at']


# Extended User Admin
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'groups']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['username']


# Re-register User Admin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# Profile Admin (standalone)
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'is_verified', 'created_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone']
    readonly_fields = ['created_at', 'updated_at']


# Table Admin
@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['table_number', 'capacity', 'location', 'status', 'is_active']
    list_filter = ['status', 'is_active', 'location']
    search_fields = ['table_number', 'location']
    ordering = ['table_number']
    list_editable = ['status', 'is_active']


# Reservation Admin
@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'table', 'reservation_date', 
        'reservation_time', 'number_of_guests', 'status'
    ]
    list_filter = ['status', 'reservation_date', 'table']
    search_fields = ['user__username', 'user__email', 'table__table_number']
    ordering = ['-reservation_date', '-reservation_time']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'reservation_date'
    
    fieldsets = (
        ('Reservation Details', {
            'fields': ('user', 'table', 'status')
        }),
        ('Date & Time', {
            'fields': ('reservation_date', 'reservation_time', 'number_of_guests')
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'email')
        }),
        ('Additional Info', {
            'fields': ('special_requests',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['confirm_reservations', 'cancel_reservations']
    
    def confirm_reservations(self, request, queryset):
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'{updated} reservations confirmed.')
    confirm_reservations.short_description = 'Confirm selected reservations'
    
    def cancel_reservations(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} reservations cancelled.')
    cancel_reservations.short_description = 'Cancel selected reservations'