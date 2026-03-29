from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.home_view, name='home'),
    path('reserve/', views.make_reservation, name='make_reservation'),
    path('reservation/<int:pk>/', views.reservation_detail, name='reservation_detail'),
    path('cancel/<int:pk>/', views.cancel_reservation, name='cancel_reservation'),
    path('my-reservations/', views.my_reservations, name='my_reservations'),
    path('profile/', views.profile_view, name='profile'),
    path('protected/', views.protected_view, name='protected'),
]