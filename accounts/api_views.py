from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login
from .serializers import (
    UserProfileSerializer,
    LoginSerializer,
    RegisterSerializer,
    ChangePasswordSerializer,
    DoctorProfileSerializer,
    PatientProfileSerializer,
    AdminUserSerializer
)
from .models import UserProfile

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Vue de connexion API"""
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    user = serializer.validated_data['user']
    refresh = RefreshToken.for_user(user)
    
    # Sélectionner le bon serializer selon le rôle
    if user.role == 'doctor':
        user_serializer = DoctorProfileSerializer(user)
    elif user.role == 'patient':
        user_serializer = PatientProfileSerializer(user)
    elif user.role == 'admin':
        user_serializer = AdminUserSerializer(user, context={'request': request})
    else:
        user_serializer = UserProfileSerializer(user)
    
    return Response({
        'user': user_serializer.data,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Vue d'inscription API"""
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    user = serializer.save()
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'user': UserProfileSerializer(user).data,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """Vue pour changer le mot de passe"""
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    
    user = request.user
    user.set_password(serializer.validated_data['new_password'])
    user.save()
    
    return Response({'detail': 'Mot de passe modifié avec succès.'})

class UserProfileView(generics.RetrieveUpdateAPIView):
    """Vue pour voir et modifier son profil"""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon le rôle"""
        user = self.request.user
        if user.role == 'doctor':
            return DoctorProfileSerializer
        elif user.role == 'patient':
            return PatientProfileSerializer
        elif user.role == 'admin':
            return AdminUserSerializer
        return UserProfileSerializer