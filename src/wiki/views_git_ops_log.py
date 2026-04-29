"""HTTP surface for the in-memory git operations log.

Read-only for the current user; the Debug panel calls this on demand to
render "what just happened" without grepping server logs.
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from . import git_ops_log


class GitOpsLogViewSet(ViewSet):
    """Per-user ring-buffer of git mutations (commit / push / PR / errors)."""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Return the most recent log entries for the current user.

        Query params:
          since (float, optional) — only entries with ts > since
          limit (int, optional, default 100) — clamp on the response size
        """
        try:
            since = float(request.query_params.get('since', '0') or 0)
        except ValueError:
            since = 0.0
        try:
            limit = int(request.query_params.get('limit', '100') or 100)
        except ValueError:
            limit = 100
        limit = max(1, min(limit, 500))
        entries = git_ops_log.fetch(request.user.id, since=since, limit=limit)
        return Response({'entries': entries})

    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Drop the entire log for the current user. Returns the count cleared."""
        cleared = git_ops_log.clear(request.user.id)
        return Response({'cleared': cleared}, status=status.HTTP_200_OK)
