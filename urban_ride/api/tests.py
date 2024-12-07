from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Slot, SlotParticipant, Auto, AutoQueue
''' AI GENERATED TEST CASES '''

class BaseTestCase(TestCase):
    def setUp(self):
        # Create test client
        self.client = APIClient()

        # Create test users
        self.customer_user = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='testpass123',
            user_type='CUSTOMER',
            phone='1234567890'
        )
        self.driver_user = User.objects.create_user(
            username='driver',
            email='driver@test.com',
            password='testpass123',
            user_type='DRIVER',
            phone='0987654321'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )

        # Generate tokens for each user
        self.customer_token = str(RefreshToken.for_user(self.customer_user).access_token)
        self.driver_token = str(RefreshToken.for_user(self.driver_user).access_token)
        self.admin_token = str(RefreshToken.for_user(self.admin_user).access_token)

class UserAPITestCase(BaseTestCase):
    def test_user_registration(self):
        """
        Test user registration API
        """
        url = reverse('user-list')
        data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'testpass123',
            'user_type': 'CUSTOMER',
            'phone': '1122334455'
        }
        
        # Authenticate as admin
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('id' in response.data)
        self.assertEqual(response.data['username'], 'newuser')
        self.assertEqual(response.data['email'], 'newuser@test.com')

    def test_user_authentication(self):
        """
        Test JWT token generation
        """
        url = reverse('token_obtain_pair')
        data = {
            'username': 'customer',
            'password': 'testpass123'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('access' in response.data)
        self.assertTrue('refresh' in response.data)

class SlotAPITestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        # Create a test slot
        self.slot = Slot.objects.create(
            creator=self.customer_user,
            max_capacity=4,
            current_capacity=0,
            fare=50.00,
            status='OPEN',
            ride_time='2024-02-15 10:00:00'
        )

    def test_create_slot(self):
        """
        Test creating a new slot
        """
        url = reverse('slot-list')
        data = {
            'creator': self.customer_user.id,
            'max_capacity': 5,
            'fare': 60.00,
            'ride_time': '2024-03-15T10:00:00Z'
        }
        
        # Authenticate as customer
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['max_capacity'], 5)
        self.assertEqual(float(response.data['fare']), 60.00)

    def test_join_slot(self):
        """
        Test joining an existing slot
        """
        url = reverse('slot-join', kwargs={'pk': self.slot.id})
        data = {
            'convenience_fee': 10.00
        }
        
        # Authenticate as another customer
        another_customer = User.objects.create_user(
            username='another_customer',
            email='another@test.com',
            password='testpass123',
            user_type='CUSTOMER',
            phone='5566778899'
        )
        self.client.force_authenticate(user=another_customer)
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data['convenience_fee']), 10.00)

    def test_finalize_slot(self):
        """
        Test finalizing a slot
        """
        url = reverse('slot-finalize', kwargs={'pk': self.slot.id})
        
        # Authenticate as slot creator
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'FINALIZED')

class AutoQueueAPITestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        # Create a test auto and add to queue
        self.auto = Auto.objects.create(
            driver=self.driver_user,
            license_plate='TEST123',
            status='AVAILABLE'
        )
        self.auto_queue = AutoQueue.objects.create(
            auto=self.auto,
            position=1
        )
        
        # Create a test slot to book
        self.slot = Slot.objects.create(
            creator=self.customer_user,
            max_capacity=4,
            current_capacity=0,
            fare=50.00,
            status='FINALIZED',
            ride_time='2024-02-15 10:00:00'
        )

    def test_get_auto_queue(self):
        """
        Test retrieving auto queue
        """
        url = reverse('autoqueue-list')
        
        # Authenticate as customer
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)

    def test_book_auto(self):
        """
        Test booking an auto from queue
        """
        url = reverse('autoqueue-book')
        data = {
            'slot_id': self.slot.id
        }
        
        # Authenticate as customer
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'BOOKED')

class PaymentAPITestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        # Create a test slot participant
        self.slot = Slot.objects.create(
            creator=self.customer_user,
            max_capacity=4,
            current_capacity=1,
            fare=50.00,
            status='OPEN',
            ride_time='2024-02-15 10:00:00'
        )
        self.slot_participant = SlotParticipant.objects.create(
            slot=self.slot,
            user=self.customer_user,
            status='JOINED',
            convenience_fee=10.00,
            paid=False
        )

    def test_pay_convenience_fee(self):
        """
        Test paying convenience fee
        """
        url = reverse('payments-convenience-fee')
        data = {
            'participant_id': self.slot_participant.id,
            'amount': 10.00
        }
        
        # Authenticate as customer
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'SUCCESS')

        # Verify participant is marked as paid
        updated_participant = SlotParticipant.objects.get(id=self.slot_participant.id)
        self.assertTrue(updated_participant.paid)
