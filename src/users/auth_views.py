"""
Authentication views for login, logout, and SSO.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .serializers import LoginSerializer, UserInfoSerializer
from .models import ApiToken
import secrets


@extend_schema(
    operation_id='auth_login',
    summary='User login',
    description='Authenticate user with username and password. Creates a session cookie for UI and returns an API token for REST clients. Supports both session-based (UI) and token-based (API) authentication.',
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(
            description='Login successful',
            examples=[{
                'user': {
                    'id': 1,
                    'username': 'admin',
                    'email': 'admin@example.com',
                    'first_name': '',
                    'last_name': '',
                    'role': 'admin',
                    'settings': {}
                },
                'token': 'cwt_1234567890abcdef...'
            }]
        ),
        400: OpenApiResponse(description='Invalid credentials'),
    },
    tags=['auth'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Authenticate user and return token.
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    username = serializer.validated_data['username']
    password = serializer.validated_data['password']
    
    user = authenticate(request, username=username, password=password)
    
    if user is not None:
        # Create Django session for UI (session-based auth)
        login(request, user)
        
        # Create or get existing API token for REST clients (token-based auth)
        token, created = ApiToken.objects.get_or_create(
            user=user,
            name='web_session',
            defaults={'token': ApiToken.generate_token()}
        )
        
        # Update last used timestamp
        if not created:
            token.save()  # This updates last_used_at via auto_now
        
        user_serializer = UserInfoSerializer(user)
        return Response({
            'user': user_serializer.data,
            'token': token.token
        })
    else:
        return Response(
            {'error': 'Invalid credentials', 'code': 'INVALID_CREDENTIALS'},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    operation_id='auth_logout',
    summary='User logout',
    description='Logout current user and destroy session.',
    responses={
        200: OpenApiResponse(description='Successfully logged out'),
    },
    tags=['auth'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout user and destroy session.
    """
    logout(request)
    return Response({'message': 'Successfully logged out'})


@extend_schema(
    operation_id='auth_me',
    summary='Get current user info',
    description='Retrieve information about the currently authenticated user.',
    responses={
        200: UserInfoSerializer,
        401: OpenApiResponse(description='Not authenticated'),
    },
    tags=['auth'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """
    Get current user information.
    """
    serializer = UserInfoSerializer(request.user)
    return Response(serializer.data)


@extend_schema(
    operation_id='auth_sso_login',
    summary='SSO login redirect',
    description='Redirect to SSO provider for authentication (OIDC).',
    responses={
        302: OpenApiResponse(description='Redirect to SSO provider'),
        503: OpenApiResponse(description='SSO not configured'),
    },
    tags=['auth'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def sso_login_view(request):
    """
    Initiate SSO login flow.
    """
    # TODO: Implement OIDC flow with Authlib
    return Response(
        {'error': 'SSO not yet implemented', 'code': 'NOT_IMPLEMENTED'},
        status=status.HTTP_501_NOT_IMPLEMENTED
    )


@extend_schema(
    operation_id='auth_sso_callback',
    summary='SSO callback handler',
    description='Handle callback from SSO provider after authentication.',
    responses={
        200: UserInfoSerializer,
        400: OpenApiResponse(description='Invalid SSO response'),
    },
    tags=['auth'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def sso_callback_view(request):
    """
    Handle SSO callback.
    """
    # TODO: Implement OIDC callback handling
    return Response(
        {'error': 'SSO not yet implemented', 'code': 'NOT_IMPLEMENTED'},
        status=status.HTTP_501_NOT_IMPLEMENTED
    )
