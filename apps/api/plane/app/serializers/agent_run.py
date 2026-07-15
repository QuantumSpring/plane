# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.db.models import AgentRun, AgentRunActivity

from .base import BaseSerializer


class AgentRunActivityAppSerializer(BaseSerializer):
    class Meta:
        model = AgentRunActivity
        fields = [
            "id",
            "agent_run",
            "type",
            "content",
            "ephemeral",
            "signal",
            "actor",
            "created_at",
        ]
        read_only_fields = fields


class AgentRunAppSerializer(BaseSerializer):
    activities = AgentRunActivityAppSerializer(many=True, read_only=True)

    class Meta:
        model = AgentRun
        fields = [
            "id",
            "agent_user",
            "issue",
            "project",
            "status",
            "type",
            "started_at",
            "ended_at",
            "external_link",
            "created_at",
            "activities",
        ]
        read_only_fields = fields
