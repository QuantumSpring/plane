# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.api.serializers import (
    AgentRunActivityCreateSerializer,
    AgentRunActivitySerializer,
    AgentRunSerializer,
)


@pytest.mark.unit
class TestAgentRunActivitySerializers:
    def test_prompt_type_rejected_on_create(self):
        serializer = AgentRunActivityCreateSerializer(
            data={"type": "prompt", "content": {"type": "prompt", "body": "hi"}}
        )
        assert not serializer.is_valid()
        assert "type" in serializer.errors

    def test_action_content_requires_action_key(self):
        serializer = AgentRunActivityCreateSerializer(
            data={"type": "action", "content": {"type": "action", "body": "wrong shape"}}
        )
        assert not serializer.is_valid()

    def test_valid_thought(self):
        serializer = AgentRunActivityCreateSerializer(
            data={
                "type": "thought",
                "content": {"type": "thought", "body": "thinking"},
                "ephemeral": True,
                "signal": "continue",
            }
        )
        assert serializer.is_valid(), serializer.errors

    def test_non_dict_content_rejected(self):
        serializer = AgentRunActivityCreateSerializer(data={"type": "thought", "content": "oops"})
        assert not serializer.is_valid()

    def test_content_type_mismatch_rejected(self):
        serializer = AgentRunActivityCreateSerializer(
            data={"type": "thought", "content": {"type": "response", "body": "x"}}
        )
        assert not serializer.is_valid()

    def test_valid_action(self):
        serializer = AgentRunActivityCreateSerializer(
            data={
                "type": "action",
                "content": {"type": "action", "action": "run_tests", "parameters": {}},
            }
        )
        assert serializer.is_valid(), serializer.errors

    def test_non_action_missing_body_rejected(self):
        serializer = AgentRunActivityCreateSerializer(data={"type": "response", "content": {"type": "response"}})
        assert not serializer.is_valid()


@pytest.mark.unit
class TestAgentRunReadSerializers:
    def test_read_serializers_bind(self):
        # Instantiating and building fields exercises the declared-field +
        # read_only_fields=fields binding, guarding against future field renames.
        assert "creator" in AgentRunSerializer().fields
        assert AgentRunActivitySerializer().fields
