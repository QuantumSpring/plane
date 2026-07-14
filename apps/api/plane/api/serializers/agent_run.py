# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import serializers

# Module imports
from plane.db.models import AgentRun, AgentRunActivity

from .base import BaseSerializer


class AgentRunSerializer(BaseSerializer):
    """
    Read-only serializer for agent runs exposed via the external API.
    """

    creator = serializers.UUIDField(source="created_by_id", read_only=True)

    class Meta:
        model = AgentRun
        fields = [
            "id",
            "agent_user",
            "issue",
            "project",
            "workspace",
            "status",
            "type",
            "source_comment",
            "comment",
            "creator",
            "started_at",
            "ended_at",
            "stopped_at",
            "stopped_by",
            "external_link",
            "error_metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AgentRunCreateSerializer(BaseSerializer):
    """
    Serializer for creating agent runs via the external API.

    Mirrors the SDK's CreateAgentRunRequest: agent_slug identifies the agent
    to invoke, with the remaining fields scoping the run to an issue/comment.
    """

    agent_slug = serializers.CharField(write_only=True)

    class Meta:
        model = AgentRun
        fields = [
            "agent_slug",
            "issue",
            "project",
            "comment",
            "source_comment",
            "external_link",
            "type",
        ]


class AgentRunActivitySerializer(BaseSerializer):
    """
    Read-only serializer for agent run activities exposed via the external API.
    """

    class Meta:
        model = AgentRunActivity
        fields = [
            "id",
            "agent_run",
            "type",
            "content",
            "content_metadata",
            "ephemeral",
            "signal",
            "signal_metadata",
            "actor",
            "comment",
            "project",
            "workspace",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AgentRunActivityCreateSerializer(BaseSerializer):
    """
    Serializer for creating agent run activities via the external API.

    Mirrors the SDK's CreateAgentRunActivityRequest, which excludes "prompt"
    since prompt activities are created by the server, not posted by clients.
    Also validates that the shape of `content` matches the declared `type`.
    """

    type = serializers.ChoiceField(
        choices=[choice for choice in AgentRunActivity.TypeEnum.values if choice != "prompt"]
    )

    class Meta:
        model = AgentRunActivity
        fields = [
            "type",
            "content",
            "content_metadata",
            "signal",
            "signal_metadata",
            "ephemeral",
            "project",
        ]

    def validate(self, data):
        content = data.get("content") or {}
        activity_type = data.get("type")

        if not isinstance(content, dict):
            raise serializers.ValidationError({"content": "content must be an object"})

        if content.get("type") != activity_type:
            raise serializers.ValidationError({"content": "content.type must match activity type"})

        if activity_type == "action":
            if "action" not in content or not isinstance(content.get("parameters", {}), dict):
                raise serializers.ValidationError(
                    {"content": "action content requires 'action' and object 'parameters'"}
                )
        elif not isinstance(content.get("body"), str):
            raise serializers.ValidationError({"content": "content.body must be a string"})

        return data
