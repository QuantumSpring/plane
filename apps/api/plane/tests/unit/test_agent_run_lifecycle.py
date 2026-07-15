# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.api.views.agent_run import apply_activity_lifecycle
from plane.db.models import AgentRun, AgentRunActivity, User


@pytest.fixture
def agent_bot(db, workspace):
    from plane.db.models import WorkspaceMember
    bot = User.objects.create(
        email="cyrus-bot@example.com", is_bot=True, bot_type="AGENT",
        agent_slug="cyrus", display_name="Cyrus", username="cyrus-bot",
    )
    WorkspaceMember.objects.create(workspace=workspace, member=bot, role=15)
    return bot


@pytest.fixture
def run(db, workspace, agent_bot, create_user):
    return AgentRun.objects.create(workspace=workspace, agent_user=agent_bot, created_by=create_user)


@pytest.mark.unit
class TestApplyActivityLifecycle:
    @pytest.mark.django_db
    def test_prompt_on_awaiting_resumes_in_progress(self, run):
        """The prompt->in_progress branch is unreachable via the POST endpoint
        (the create serializer excludes 'prompt'), so cover it directly."""
        run.status = "awaiting"
        run.save(update_fields=["status"])
        activity = AgentRunActivity(
            agent_run=run, type="prompt", content={"type": "prompt", "body": "go on"},
        )
        apply_activity_lifecycle(run, activity)
        run.refresh_from_db()
        assert run.status == "in_progress"

    @pytest.mark.django_db
    def test_error_with_stop_signal_still_fails(self, run):
        """An error is a failure regardless of any accompanying stop signal."""
        activity = AgentRunActivity(
            agent_run=run,
            type="error",
            content={"type": "error", "body": "boom"},
            signal="stop",
        )
        apply_activity_lifecycle(run, activity)
        run.refresh_from_db()
        assert run.status == "failed"
        assert run.ended_at is not None
        assert run.error_metadata.get("body") == "boom"
