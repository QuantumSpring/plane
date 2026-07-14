# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db.models import Prefetch

from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers.agent_run import AgentRunAppSerializer
from plane.db.models import AgentRun, AgentRunActivity

from .. import BaseAPIView


class IssueAgentRunsEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id, issue_id):
        # TODO: paginate / since-cursor if this outlives the PoC
        runs = (
            AgentRun.objects.filter(workspace__slug=slug, project_id=project_id, issue_id=issue_id)
            .prefetch_related(
                Prefetch("activities", queryset=AgentRunActivity.objects.order_by("created_at"))
            )
            .order_by("-created_at")
        )
        return Response(AgentRunAppSerializer(runs, many=True).data, status=status.HTTP_200_OK)
