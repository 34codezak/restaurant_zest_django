from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html, mark_safe
from django.utils.safestring import SafeString
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta, datetime
import json

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
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']


# Re-register User Admin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# Profile Admin
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'is_verified', 'created_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone']
    readonly_fields = ['created_at', 'updated_at']


# Table Admin with occupancy indicator - ✅ FIXED
@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['table_number', 'capacity', 'location', 'status', 'is_active', 'occupancy_indicator']
    list_filter = ['status', 'is_active', 'location', 'capacity']
    search_fields = ['table_number', 'location']
    ordering = ['table_number']
    list_editable = ['status', 'is_active']
    
    def occupancy_indicator(self, obj):
        """Show visual indicator of table occupancy today - ✅ FIXED"""
        today = timezone.now().date()
        reserved = Reservation.objects.filter(
            table=obj,
            reservation_date=today,
            status__in=['pending', 'confirmed']
        ).exists()
        
        # ✅ FIX: Use mark_safe() for static HTML, or format_html() with placeholders
        if reserved:
            return mark_safe('<span style="color: #e74c3c; font-weight: bold;">● Reserved</span>')
        elif obj.status == 'available' and obj.is_active:
            return mark_safe('<span style="color: #27ae60; font-weight: bold;">● Available</span>')
        return mark_safe('<span style="color: #95a5a6;">○ Inactive</span>')
    
    occupancy_indicator.short_description = "Today's Status"
    
    # Optional: Make the column sortable by status
    def get_ordering(self, request):
        return super().get_ordering(request) or ['table_number']


# Reservation Admin
@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'table', 'reservation_date', 'reservation_time', 
                    'number_of_guests', 'status', 'created_at']
    list_filter = ['status', 'reservation_date', 'table', 'number_of_guests']
    search_fields = ['user__username', 'user__email', 'table__table_number']
    ordering = ['-reservation_date', '-reservation_time']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'reservation_date'
    list_per_page = 25
    
    fieldsets = (
        ('Reservation Details', {'fields': ('user', 'table', 'status')}),
        ('Date & Time', {'fields': ('reservation_date', 'reservation_time', 'number_of_guests')}),
        ('Contact Information', {'fields': ('phone_number', 'email')}),
        ('Additional Info', {'fields': ('special_requests',), 'classes': ('collapse',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    
    actions = ['confirm_reservations', 'cancel_reservations', 'export_selected']
    
    def confirm_reservations(self, request, queryset):
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'{updated} reservations confirmed.')
    confirm_reservations.short_description = 'Confirm selected reservations'
    
    def cancel_reservations(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} reservations cancelled.')
    cancel_reservations.short_description = 'Cancel selected reservations'
    
    def export_selected(self, request, queryset):
        """Export selected reservations to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="reservations.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'User', 'Table', 'Date', 'Time', 'Guests', 'Status', 'Phone', 'Email'])
        
        for obj in queryset:
            writer.writerow([
                obj.id, obj.user.username, obj.table.table_number,
                obj.reservation_date, obj.reservation_time,
                obj.number_of_guests, obj.status,
                obj.phone_number, obj.email
            ])
        
        return response
    export_selected.short_description = 'Export selected reservations'


# ✅ Custom Admin Site with Dashboard - Compatible Version
class ZestAdminSite(admin.AdminSite):
    site_header = "🍽️ Zest Restaurant Admin"
    site_title = "Zest Restaurant"
    index_title = "Dashboard"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name='admin_dashboard'),
            path('api/metrics/', self.admin_view(self.metrics_api), name='admin_metrics_api'),
            path('api/realtime/', self.admin_view(self.realtime_api), name='admin_realtime_api'),
        ]
        return custom_urls + urls
    
    def dashboard_view(self, request):
        """Custom dashboard view with charts"""
        context = self.each_context(request)
        
        # Get metrics with error handling
        try:
            metrics = Reservation.get_dashboard_metrics(days=30)
            occupancy = Table.get_occupancy_stats()
            realtime = Reservation.get_realtime_data()
        except Exception as e:
            # Fallback to empty data if metrics fail
            metrics = {'today_reservations': 0, 'confirmed': 0, 'cancelled': 0, 
                      'cancellation_rate': 0, 'today_guests': 0, 'popular_times': [],
                      'daily_trend': [], 'party_sizes': [], 'date_range': {}}
            occupancy = {'total_tables': 0, 'reserved': 0, 'available': 0, 'occupancy_rate': 0}
            realtime = {'active_count': 0, 'next_reservation': None, 'tables_in_use': []}
        
        # Recent activity
        recent_reservations = Reservation.objects.select_related('user', 'table').order_by('-created_at')[:10]
        recent_users = User.objects.filter(date_joined__gte=timezone.now()-timedelta(days=7)).order_by('-date_joined')[:5]
        
        context.update({
            # Pass API URLs to template
            'metrics_api_url': reverse('zest_admin:admin_metrics_api'),
            'realtime_api_url': reverse('zest_admin:admin_realtime_api'),
            # 'metrics': metrics,
            'occupancy': occupancy,
            # 'realtime': realtime,
            'recent_reservations': recent_reservations,
            'recent_users': recent_users,
            'title': 'Dashboard',
        })
        
        return render(request, 'admin/dashboard.html', context)
    
    def metrics_api(self, request):
        """API endpoint for chart data"""
        from django.http import JsonResponse
        
        try:
            days = int(request.GET.get('days', 30))
            data = Reservation.get_dashboard_metrics(days=days)
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def realtime_api(self, request):
        """API endpoint for real-time updates"""
        from django.http import JsonResponse
        
        try:
            data = Reservation.get_realtime_data()
            data['occupancy'] = Table.get_occupancy_stats()
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ✅ Register custom admin site
admin_site = ZestAdminSite(name='zest_admin')

# Register models with custom admin site
admin_site.register(User, UserAdmin)
admin_site.register(Profile, ProfileAdmin)
admin_site.register(Table, TableAdmin)
admin_site.register(Reservation, ReservationAdmin)

# ✅ Replace default admin site
admin.site = admin_site