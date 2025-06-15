from django.test import TestCase
from django.contrib.auth import get_user_model
from ..serializers import UserProfileSerializer, RegisterSerializer

User = get_user_model()

class UserSerializerTest(TestCase):
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'password2': 'TestPass123!',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'patient'
        }
    
    def test_register_serializer_valid(self):
        serializer = RegisterSerializer(data=self.user_data)
        self.assertTrue(serializer.is_valid())
    
    def test_register_serializer_password_mismatch(self):
        self.user_data['password2'] = 'DifferentPass123!'
        serializer = RegisterSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)
    
    def test_user_profile_serializer(self):
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        serializer = UserProfileSerializer(user)
        data = serializer.data
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['email'], 'test@example.com')
        self.assertNotIn('password', data)