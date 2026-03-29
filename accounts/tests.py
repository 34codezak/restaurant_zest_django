from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Table, Reservation, Profile
from datetime import datetime, timedelta


class UserModelTestCase(TestCase):
    """Test cases for User and Profile models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_profile_creation(self):
        """Test that profile is automatically created with user"""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertEqual(self.user.profile.user, self.user)
    
    def test_profile_string_representation(self):
        """Test profile __str__ method"""
        self.assertEqual(str(self.user.profile), 'testuser Profile')


class TableModelTestCase(TestCase):
    """Test cases for Table model"""
    
    def setUp(self):
        self.table = Table.objects.create(
            table_number='T1',
            capacity=4,
            location='Main Dining'
        )
    
    def test_table_creation(self):
        """Test table creation"""
        self.assertEqual(self.table.table_number, 'T1')
        self.assertEqual(self.table.capacity, 4)
        self.assertEqual(self.table.status, 'available')
    
    def test_table_string_representation(self):
        """Test table __str__ method"""
        self.assertEqual(str(self.table), 'Table T1 (4 seats)')
    
    def test_table_ordering(self):
        """Test table ordering by table_number"""
        Table.objects.create(table_number='T2', capacity=2)
        tables = list(Table.objects.all())
        self.assertEqual(tables[0].table_number, 'T1')
        self.assertEqual(tables[1].table_number, 'T2')


class ReservationModelTestCase(TestCase):
    """Test cases for Reservation model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.table = Table.objects.create(table_number='T1', capacity=4)
        self.reservation = Reservation.objects.create(
            user=self.user,
            table=self.table,
            reservation_date=datetime.now().date() + timedelta(days=1),
            reservation_time=datetime.now().time(),
            number_of_guests=2,
            phone_number='1234567890',
            email='test@example.com'
        )
    
    def test_reservation_creation(self):
        """Test reservation creation"""
        self.assertEqual(self.reservation.user, self.user)
        self.assertEqual(self.reservation.table, self.table)
        self.assertEqual(self.reservation.status, 'pending')
    
    def test_reservation_string_representation(self):
        """Test reservation __str__ method"""
        self.assertIn('testuser', str(self.reservation))
        self.assertIn('T1', str(self.reservation))
    
    def test_is_upcoming_method(self):
        """Test is_upcoming method"""
        self.assertTrue(self.reservation.is_upcoming())


class AuthenticationViewsTestCase(TestCase):
    """Test cases for authentication views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_register_view_get(self):
        """Test registration page loads"""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')
    
    def test_register_view_post(self):
        """Test user registration"""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'newpass123',
            'password2': 'newpass123',
        })
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertTrue(User.objects.filter(username='newuser').exists())
    
    def test_login_view_get(self):
        """Test login page loads"""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
    
    def test_login_view_post(self):
        """Test user login"""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)  # Redirect to home
    
    def test_logout_view(self):
        """Test user logout"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)


class ProtectedViewsTestCase(TestCase):
    """Test cases for protected views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_home_view_requires_login(self):
        """Test home view requires authentication"""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_home_view_authenticated(self):
        """Test home view for authenticated users"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/home.html')
    
    def test_make_reservation_requires_login(self):
        """Test reservation view requires authentication"""
        response = self.client.get(reverse('make_reservation'))
        self.assertEqual(response.status_code, 302)
    
    def test_protected_view_requires_login(self):
        """Test protected view requires authentication"""
        response = self.client.get(reverse('protected'))
        self.assertEqual(response.status_code, 302)


class ReservationViewsTestCase(TestCase):
    """Test cases for reservation views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.table = Table.objects.create(table_number='T1', capacity=4)
        self.client.login(username='testuser', password='testpass123')
    
    def test_make_reservation_get(self):
        """Test reservation form loads"""
        response = self.client.get(reverse('make_reservation'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/reservation_form.html')
    
    def test_make_reservation_post(self):
        """Test creating a reservation"""
        response = self.client.post(reverse('make_reservation'), {
            'table': self.table.pk,
            'reservation_date': (datetime.now().date() + timedelta(days=1)).isoformat(),
            'reservation_time': '19:00',
            'number_of_guests': 2,
            'phone_number': '1234567890',
            'email': 'test@example.com',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reservation.objects.count(), 1)
    
    def test_cancel_reservation(self):
        """Test cancelling a reservation"""
        reservation = Reservation.objects.create(
            user=self.user,
            table=self.table,
            reservation_date=datetime.now().date() + timedelta(days=1),
            reservation_time=datetime.now().time(),
            number_of_guests=2,
            phone_number='1234567890',
            email='test@example.com',
            status='confirmed'
        )
        response = self.client.get(reverse('cancel_reservation', args=[reservation.pk]))
        self.assertEqual(response.status_code, 302)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'cancelled')