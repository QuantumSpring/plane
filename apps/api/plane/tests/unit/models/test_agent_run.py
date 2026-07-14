# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from django.db import IntegrityError

from plane.db.models import AgentRun, AgentRunActivity, Project, User, Webhook


@pytest.mark.unit
class TestAgentRunModels:
    @pytest.mark.django_db
    def test_agent_run_defaults(self, workspace, create_user):
        project = Project.objects.create(name="P", identifier="P", workspace=workspace)
        bot = User.objects.create(
            email="bot@example.com", username="bot-cyrus", is_bot=True, bot_type="AGENT", agent_slug="cyrus"
        )
        run = AgentRun.objects.create(
            workspace=workspace, project=project, agent_user=bot, created_by=create_user
        )
        assert run.status == "created"
        assert run.type == "comment_thread"
        assert run.started_at is not None
        assert run.ended_at is None
        assert run.error_metadata == {}

    @pytest.mark.django_db
    def test_agent_run_activity_defaults(self, workspace, create_user):
        bot = User.objects.create(
            email="bot2@example.com", username="bot-cyrus2", is_bot=True, bot_type="AGENT", agent_slug="cyrus2"
        )
        run = AgentRun.objects.create(workspace=workspace, agent_user=bot, created_by=create_user)
        activity = AgentRunActivity.objects.create(
            workspace=workspace, agent_run=run, type="thought",
            content={"type": "thought", "body": "hm"},
        )
        assert activity.ephemeral is False
        assert activity.signal == "continue"
        assert list(run.activities.all()) == [activity]

    @pytest.mark.django_db
    def test_agent_slug_unique(self, workspace):
        User.objects.create(email="a@example.com", username="agent-a", is_bot=True, agent_slug="dup")
        with pytest.raises(IntegrityError):
            User.objects.create(email="b@example.com", username="agent-b", is_bot=True, agent_slug="dup")

    @pytest.mark.django_db
    def test_webhook_agent_run_flag_default(self, workspace):
        webhook = Webhook.objects.create(workspace=workspace, url="https://example.com/hook")
        assert webhook.agent_run is False

    def test_non_terminal_statuses_cover_enum(self):
        # If StatusEnum grows, this forces NON_TERMINAL_STATUSES to be reconsidered.
        assert set(AgentRun.NON_TERMINAL_STATUSES) == set(AgentRun.StatusEnum.values) - {
            "completed",
            "stopped",
            "failed",
            "stale",
        }
