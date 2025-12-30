"""
Views for user authentication and management.

Views:
- RegisterView: User registration endpoint
- LoginView: User login endpoint
- LogoutView: User logout endpoint
- UserListCreateView: List and create users (admin only)
- UserDetailView: Retrieve, update, delete user
- ChangePasswordView: Change user password
- ProfileView: User profile management
"""

from rest_framework import status, viewsets, generics, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken  # type: ignore
from rest_framework_simplejwt.views import TokenObtainPairView  # type: ignore
from django.contrib.auth import authenticate
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from apps.users.models import User, Role, UserProfile
from apps.users.serializers import (
    UserSerializer, UserDetailSerializer, UserRegistrationSerializer,
    ChangePasswordSerializer, RoleSerializer
)
from apps.users.permissions import IsAdmin, IsOwnerOrAdmin
import logging

logger = logging.getLogger(__name__)


class UserRegistrationView(generics.CreateAPIView):
    """
    User registration endpoint.
    
    POST /api/v1/users/register/
    
    Parameters:
    - email (required): User's email address
    - username (required): Unique username
    - first_name (required): User's first name
    - last_name (required): User's last name
    - password (required): User's password (min 8 chars)
    - password_confirm (required): Confirm password
    - phone_number (optional): User's phone number
    - role (required): User's role ID
    """
    
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        """Handle user registration."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info(f"New user registered: {user.email}")
        
        return Response({
            'message': 'User registered successfully. Please log in.',
            'user': UserSerializer(user).data,
            'status': 'success'
        }, status=status.HTTP_201_CREATED)


class UserLoginView(views.APIView):
    """
    User login endpoint.
    
    POST /api/v1/users/login/
    
    Parameters:
    - email (required): User's email
    - password (required): User's password
    
    Returns:
    - access_token: JWT access token
    - refresh_token: JWT refresh token
    - user: User information
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Handle user login."""
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response({
                'message': 'Email and password are required.',
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            
            # Check if account is locked
            if user.is_account_locked():
                return Response({
                    'message': 'Account is temporarily locked. Try again later.',
                    'status': 'error'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Verify password
            if not user.check_password(password):
                user.increment_login_attempts()
                return Response({
                    'message': 'Invalid email or password.',
                    'status': 'error'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Check if user is active
            if not user.is_active:
                return Response({
                    'message': 'User account is inactive.',
                    'status': 'error'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Reset login attempts on successful login
            user.reset_login_attempts()
            user.last_login_ip = self._get_client_ip(request)
            user.save()
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            logger.info(f"User logged in: {user.email}")
            
            return Response({
                'message': 'Login successful.',
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'user': UserSerializer(user).data,
                'status': 'success'
            }, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            return Response({
                'message': 'Invalid email or password.',
                'status': 'error'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    @staticmethod
    def _get_client_ip(request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserLogoutView(views.APIView):
    """
    User logout endpoint.
    
    POST /api/v1/users/logout/
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Handle user logout."""
        logger.info(f"User logged out: {request.user.email}")
        return Response({
            'message': 'Logout successful.',
            'status': 'success'
        }, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    """
    User management ViewSet.
    
    Provides CRUD operations for user management.
    Only accessible to admin users.
    """
    
    queryset = User.objects.select_related('role').all()
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ['role', 'is_active']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'email', 'last_login']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['GET'])
    def me(self, request):
        """
        Get current authenticated user's information.
        
        GET /api/v1/users/me/
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['POST'], permission_classes=[IsAuthenticated])
    def change_password(self, request, pk=None):
        """
        Change user password.
        
        POST /api/v1/users/{id}/change_password/
        
        Parameters:
        - old_password (required): Current password
        - new_password (required): New password
        - new_password_confirm (required): Confirm new password
        """
        user = self.get_object()
        
        # Check if user is changing their own password or is admin
        if user != request.user and not request.user.role.name == 'admin':
            return Response({
                'message': 'You can only change your own password.',
                'status': 'error'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        logger.info(f"Password changed for user: {user.email}")
        
        return Response({
            'message': 'Password changed successfully.',
            'status': 'success'
        }, status=status.HTTP_200_OK)


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Role management ViewSet (Read-only).
    
    Provides READ operations for role information.
    """
    
    queryset = Role.objects.filter(is_active=True)
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active']
    ordering = ['name']


# Web Views (Django Templates)

class LoginPageView(DjangoLoginView):
    """Login page for web interface."""
    template_name = 'users/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        """Redirect to dashboard after successful login."""
        return '/dashboard/'


class LogoutPageView(DjangoLogoutView):
    """Logout view for web interface."""
    next_page = 'login'


class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view - accessible to authenticated users."""
    template_name = 'users/dashboard.html'
    login_url = 'login'
    
    def get_context_data(self, **kwargs):
        """Add context data for dashboard."""
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context


class RegisterPageView(TemplateView):
    """Registration page for web interface."""
    template_name = 'users/register.html'
    
    def get_context_data(self, **kwargs):
        """Add roles to context."""
        context = super().get_context_data(**kwargs)
        context['roles'] = Role.objects.filter(is_active=True)
        return context


def page_not_found(request, exception=None):
    """Handle 404 errors."""
    return render(request, 'errors/404.html', status=404)


def server_error(request, exception=None):
    """Handle 500 errors."""
    return render(request, 'errors/500.html', status=500)
