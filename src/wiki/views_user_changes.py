"""
Views for user changes and approval workflow.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from .models import UserChange
from .serializers import UserChangeSerializer
from users.permissions import IsEditorOrAbove, IsAdmin


class UserChangeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing pending user changes.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserChangeSerializer
    
    def get_queryset(self):
        if self.request.user.userprofile.role in ['admin', 'editor']:
            return UserChange.objects.all().select_related('user', 'approved_by')
        return UserChange.objects.filter(user=self.request.user).select_related('user', 'approved_by')
    
    @extend_schema(
        operation_id='wiki_changes_list',
        summary='List user changes',
        description='List all pending changes for the current user or all users (admin/editor).',
        responses={200: UserChangeSerializer(many=True)},
        tags=['changes'],
    )
    def list(self, request):
        queryset = self.get_queryset()
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='wiki_changes_create',
        summary='Create a pending change',
        description='Create a new pending change for approval.',
        request=UserChangeSerializer,
        responses={201: UserChangeSerializer},
        tags=['changes'],
    )
    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        change = serializer.save(user=request.user, status='pending')
        response_serializer = self.serializer_class(change)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        operation_id='wiki_changes_approve',
        summary='Approve a change',
        description='Approve a pending change (editor/admin only).',
        responses={200: UserChangeSerializer},
        tags=['changes'],
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsEditorOrAbove])
    def approve(self, request, pk=None):
        change = self.get_object()
        change.status = 'approved'
        change.approved_by = request.user
        change.save()
        serializer = self.serializer_class(change)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='wiki_changes_reject',
        summary='Reject a change',
        description='Reject a pending change (editor/admin only).',
        responses={200: UserChangeSerializer},
        tags=['changes'],
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsEditorOrAbove])
    def reject(self, request, pk=None):
        change = self.get_object()
        change.status = 'rejected'
        change.approved_by = request.user
        change.save()
        serializer = self.serializer_class(change)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='wiki_changes_commit',
        summary='Commit approved changes',
        description='Commit approved changes to Git (admin only).',
        responses={200: {'description': 'Changes committed successfully'}},
        tags=['changes'],
    )
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def commit_batch(self, request):
        # Get all approved changes
        approved_changes = UserChange.objects.filter(status='approved')
        
        # TODO: Implement Git commit logic
        # For now, just mark as committed
        approved_changes.update(status='committed')
        
        return Response({'message': f'{approved_changes.count()} changes committed'})
