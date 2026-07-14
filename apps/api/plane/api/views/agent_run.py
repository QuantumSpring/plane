# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import transaction
from django.utils import timezone

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.api.serializers import (
    AgentRunActivityCreateSerializer,
    AgentRunActivitySerializer,
    AgentRunCreateSerializer,
    AgentRunSerializer,
)
from plane.app.permissions import WorkspaceEntityPermission
from plane.db.models import AgentRun, AgentRunActivity, User, Workspace

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


TERMINAL_STATUSES = [
    s.value for s in AgentRun.StatusEnum if s not in AgentRun.NON_TERMINAL_STATUSES
]


def apply_activity_lifecycle(run, activity):
    """Signal-driven run lifecycle (spec: Cloud has no stop/update endpoint)."""
    update_fields = []
    if activity.type == "error":
        run.status = "failed"
        run.ended_at = timezone.now()
        run.error_metadata = activity.content
        update_fields += ["status", "ended_at", "error_metadata"]
    elif activity.signal == "stop":
        run.status = "completed"
        run.ended_at = timezone.now()
        update_fields += ["status", "ended_at"]
    elif activity.type == "elicitation":
        run.status = "awaiting"
        update_fields += ["status"]
    elif activity.type == "prompt" and run.status == "awaiting":
        run.status = "in_progress"
        update_fields += ["status"]
    elif run.status == "created":
        run.status = "in_progress"
        update_fields += ["status"]
    if update_fields:
        run.save(update_fields=update_fields + ["updated_at"])


class AgentRunActivityListCreateAPIEndpoint(BaseAPIView):
    """Agent Run Activity List and Create Endpoint"""

    permission_classes = [WorkspaceEntityPermission]
    serializer_class = AgentRunActivitySerializer
    model = AgentRunActivity

    def get(self, request, slug, run_id):
        """List agent run activities

        Retrieve all activities for a specific agent run.
        """
        activities = AgentRunActivity.objects.filter(
            agent_run_id=run_id, workspace__slug=slug
        ).order_by("created_at")
        return self.paginate(
            request=request,
            queryset=activities,
            on_results=lambda results: AgentRunActivitySerializer(results, many=True).data,
        )

    def post(self, request, slug, run_id):
        """Create agent run activity

        Post a new activity for the agent run; drives the run's lifecycle
        (status transitions) and supersedes any prior ephemeral activities.
        """
        with transaction.atomic():
            # Lock the run row so retried/concurrent posts can't defeat the
            # terminal guard or duplicate the final activity.
            run = AgentRun.objects.select_for_update().get(
                workspace__slug=slug, id=run_id
            )
            if run.status in TERMINAL_STATUSES:
                return Response(
                    {"error": f"agent run is {run.status}; no further activities accepted"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = AgentRunActivityCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            # New activity supersedes prior ephemeral ones (thoughts/actions replace each other)
            AgentRunActivity.objects.filter(agent_run=run, ephemeral=True).delete()
            activity = serializer.save(
                agent_run=run,
                workspace_id=run.workspace_id,
                project_id=run.project_id,
                actor=request.user,
            )
            apply_activity_lifecycle(run, activity)
        return Response(AgentRunActivitySerializer(activity).data, status=status.HTTP_201_CREATED)


class AgentRunActivityDetailAPIEndpoint(BaseAPIView):
    """Agent Run Activity Detail Endpoint"""

    permission_classes = [WorkspaceEntityPermission]
    serializer_class = AgentRunActivitySerializer
    model = AgentRunActivity

    def get(self, request, slug, run_id, activity_id):
        """Retrieve agent run activity

        Retrieve details of a specific agent run activity.
        """
        activity = AgentRunActivity.objects.get(
            workspace__slug=slug, agent_run_id=run_id, id=activity_id
        )
        return Response(AgentRunActivitySerializer(activity).data, status=status.HTTP_200_OK)
