# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.api.serializers import AgentRunCreateSerializer, AgentRunSerializer
from plane.app.permissions import WorkspaceEntityPermission
from plane.db.models import AgentRun, User, Workspace

from .base import BaseAPIView


class AgentRunListCreateAPIEndpoint(BaseAPIView):
    """Agent Run List and Create Endpoint"""

    serializer_class = AgentRunSerializer
    model = AgentRun
    permission_classes = [WorkspaceEntityPermission]

    def get_queryset(self):
        return AgentRun.objects.filter(workspace__slug=self.kwargs.get("slug"))

    def get(self, request, slug):
        """List agent runs

        Retrieve all agent runs for a workspace.
        """
        return self.paginate(
            request=request,
            queryset=self.get_queryset(),
            on_results=lambda runs: AgentRunSerializer(runs, many=True).data,
        )

    def post(self, request, slug):
        """Create agent run

        Create a new agent run for the agent identified by `agent_slug`.
        """
        serializer = AgentRunCreateSerializer(data=request.data, context={"slug": slug})
        serializer.is_valid(raise_exception=True)
        agent_slug = serializer.validated_data.pop("agent_slug")
        agent_user = User.objects.get(
            agent_slug=agent_slug,
            is_bot=True,
            member_workspace__workspace__slug=slug,
            member_workspace__is_active=True,
        )
        workspace = Workspace.objects.get(slug=slug)
        run = serializer.save(
            agent_user=agent_user,
            workspace_id=workspace.id,
            created_by=request.user,
        )
        return Response(AgentRunSerializer(run).data, status=status.HTTP_201_CREATED)


class AgentRunDetailAPIEndpoint(BaseAPIView):
    """Agent Run Detail Endpoint"""

    serializer_class = AgentRunSerializer
    model = AgentRun
    permission_classes = [WorkspaceEntityPermission]

    def get_queryset(self):
        return AgentRun.objects.filter(workspace__slug=self.kwargs.get("slug"))

    def get(self, request, slug, run_id):
        """Retrieve agent run

        Retrieve details of a specific agent run.
        """
        run = self.get_queryset().get(pk=run_id)
        return Response(AgentRunSerializer(run).data, status=status.HTTP_200_OK)
