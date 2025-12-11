"""
Supabase JWT Authentication Backend for Django REST Framework.

This module provides JWT authentication for validating Supabase access tokens.
It verifies the JWT signature using the Supabase JWT secret and syncs users
with the Django User model.
"""

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions
from .models import User


class SupabaseJWTAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication class for validating Supabase JWT tokens.

    This authenticator:
    1. Extracts the Bearer token from the Authorization header
    2. Verifies the JWT signature using the Supabase JWT secret
    3. Creates or updates a Django User based on the token claims
    4. Returns the authenticated user
    """

    keyword = 'Bearer'

    def authenticate(self, request):
        """
        Authenticate the request and return a tuple of (user, token) or None.
        """
        auth_header = authentication.get_authorization_header(request).decode('utf-8')

        if not auth_header:
            return None

        parts = auth_header.split()

        if parts[0].lower() != self.keyword.lower():
            return None

        if len(parts) == 1:
            raise exceptions.AuthenticationFailed('Invalid token header. No credentials provided.')

        if len(parts) > 2:
            raise exceptions.AuthenticationFailed('Invalid token header. Token string should not contain spaces.')

        token = parts[1]

        return self.authenticate_token(token)

    def authenticate_token(self, token):
        """
        Validate the JWT token and return the user.
        """
        jwt_secret = getattr(settings, 'SUPABASE_JWT_SECRET', None)

        if not jwt_secret:
            raise exceptions.AuthenticationFailed(
                'Supabase JWT secret not configured. Please set SUPABASE_JWT_SECRET in your settings.'
            )

        try:
            # Decode and verify the JWT token
            # Supabase uses HS256 algorithm by default
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=['HS256'],
                options={
                    'verify_aud': False,  # Supabase doesn't always set audience
                    'verify_exp': True,   # Verify token expiration
                }
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired.')
        except jwt.InvalidTokenError as e:
            raise exceptions.AuthenticationFailed(f'Invalid token: {str(e)}')

        # Extract user information from the token
        supabase_user_id = payload.get('sub')  # Supabase user ID
        email = payload.get('email')
        user_metadata = payload.get('user_metadata', {})
        name = user_metadata.get('name', email.split('@')[0] if email else 'User')

        if not supabase_user_id or not email:
            raise exceptions.AuthenticationFailed('Token missing required claims (sub, email).')

        # Check if email is verified (Supabase sets this after email confirmation)
        email_confirmed = payload.get('email_confirmed_at') is not None

        if not email_confirmed:
            raise exceptions.AuthenticationFailed('Email not verified. Please verify your email first.')

        # Get or create the Django user
        user = self.get_or_create_user(supabase_user_id, email, name)

        return (user, token)

    def get_or_create_user(self, supabase_user_id, email, name):
        """
        Get or create a Django User based on Supabase user information.

        This syncs the Supabase user with the Django User model.
        """
        try:
            # First, try to find user by supabase_id
            user = User.objects.filter(supabase_id=supabase_user_id).first()

            if user:
                # Update user info if changed
                if user.email != email or user.name != name:
                    user.email = email
                    user.name = name
                    user.save(update_fields=['email', 'name'])
                return user

            # If not found by supabase_id, try to find by email
            user = User.objects.filter(email=email).first()

            if user:
                # Link existing user to Supabase
                user.supabase_id = supabase_user_id
                user.name = name  # Update name from Supabase
                user.save(update_fields=['supabase_id', 'name'])
                return user

            # Create new user
            user = User.objects.create(
                email=email,
                name=name,
                supabase_id=supabase_user_id,
                # No password needed - authentication is handled by Supabase
            )
            return user

        except Exception as e:
            raise exceptions.AuthenticationFailed(f'Failed to sync user: {str(e)}')

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the WWW-Authenticate
        header in a 401 Unauthenticated response.
        """
        return self.keyword
