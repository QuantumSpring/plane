# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json
from unittest.mock import patch

import pytest

from plane.bgtasks.agent_run_task import agent_run_trigger
from plane.db.models import AgentRun, AgentRunActivity, Issue, IssueComment, Project, State, User


@pytest.fixture
def project(db, workspace):
    return Project.objects.create(name="Agent P", identifier="AGP", workspace=workspace)


@pytest.fixture
def issue(db, workspace, project):
    state = State.objects.create(name="Todo", group="unstarted", project=project, workspace=workspace)
    return Issue.objects.create(name="Fix it", project=project, workspace=workspace, state=state)


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
def second_agent_bot(db, workspace):
    from plane.db.models import WorkspaceMember
    bot = User.objects.create(
        email="atlas-bot@example.com", is_bot=True, bot_type="AGENT",
        agent_slug="atlas", display_name="Atlas", username="atlas-bot",
    )
    WorkspaceMember.objects.create(workspace=workspace, member=bot, role=15)
    return bot


@pytest.fixture
def non_member_agent_bot(db):
    """An agent bot with no WorkspaceMember row in the triggering workspace."""
    return User.objects.create(
        email="ghost-bot@example.com", is_bot=True, bot_type="AGENT",
        agent_slug="ghost", display_name="Ghost", username="ghost-bot",
    )


def mention_html(user):
    return (
        f'<p><mention-component entity_name="user_mention" '
        f'entity_identifier="{user.id}"></mention-component> fix the failing test</p>'
    )


def mention_html_multi(*users):
    tags = "".join(
        f'<mention-component entity_name="user_mention" '
        f'entity_identifier="{u.id}"></mention-component>'
        for u in users
    )
    return f"<p>{tags} fix the failing test</p>"


def run_comment_trigger(workspace, project, issue, comment, actor):
    with patch("plane.bgtasks.agent_run_task.dispatch_agent_run_webhook") as dispatch:
        agent_run_trigger(
            type="comment.activity.created",
            requested_data=json.dumps({"id": str(comment.id), "comment_html": comment.comment_html}),
            current_instance=None,
            issue_id=str(issue.id),
            actor_id=str(actor.id),
            project_id=str(project.id),
            workspace_id=str(workspace.id),
            epoch=1,
        )
    return dispatch


@pytest.mark.unit
class TestCommentTrigger:
    @pytest.mark.django_db
    def test_mention_creates_run_and_prompt_activity(self, workspace, project, issue, agent_bot, create_user):
        comment = IssueComment.objects.create(
            issue=issue, project=project, workspace=workspace,
            actor=create_user, comment_html=mention_html(agent_bot),
        )
        dispatch = run_comment_trigger(workspace, project, issue, comment, create_user)
        run = AgentRun.objects.get(issue=issue, agent_user=agent_bot)
        assert run.type == "comment_thread"
        assert run.status == "created"
        assert run.source_comment_id == comment.id
        prompt = AgentRunActivity.objects.get(agent_run=run, type="prompt")
        assert "fix the failing test" in prompt.content["body"]
        dispatch.assert_called_once_with(run, "created", prompt.content["body"])

    @pytest.mark.django_db
    def test_no_mention_no_run(self, workspace, project, issue, agent_bot, create_user):
        comment = IssueComment.objects.create(
            issue=issue, project=project, workspace=workspace,
            actor=create_user, comment_html="<p>just chatting</p>",
        )
        run_comment_trigger(workspace, project, issue, comment, create_user)
        assert AgentRun.objects.count() == 0

    @pytest.mark.django_db
    def test_bot_author_is_ignored(self, workspace, project, issue, agent_bot):
        comment = IssueComment.objects.create(
            issue=issue, project=project, workspace=workspace,
            actor=agent_bot, comment_html=mention_html(agent_bot),
        )
        run_comment_trigger(workspace, project, issue, comment, agent_bot)
        assert AgentRun.objects.count() == 0

    @pytest.mark.django_db
    def test_mention_on_active_run_adds_prompt_not_new_run(
        self, workspace, project, issue, agent_bot, create_user
    ):
        first = IssueComment.objects.create(
            issue=issue, project=project, workspace=workspace,
            actor=create_user, comment_html=mention_html(agent_bot),
        )
        run_comment_trigger(workspace, project, issue, first, create_user)
        run = AgentRun.objects.get()
        run.status = "awaiting"
        run.save()

        followup = IssueComment.objects.create(
            issue=issue, project=project, workspace=workspace,
            actor=create_user, comment_html=mention_html(agent_bot),
        )
        dispatch = run_comment_trigger(workspace, project, issue, followup, create_user)
        assert AgentRun.objects.count() == 1
        run.refresh_from_db()
        assert run.status == "in_progress"  # follow-up prompt resumes an awaiting run
        assert AgentRunActivity.objects.filter(agent_run=run, type="prompt").count() == 2
        assert dispatch.call_args[0][1] == "prompted"

    @pytest.mark.django_db
    def test_created_by_is_persisted(self, workspace, project, issue, agent_bot, create_user):
        comment = IssueComment.objects.create(
            issue=issue, project=project, workspace=workspace,
            actor=create_user, comment_html=mention_html(agent_bot),
        )
        run_comment_trigger(workspace, project, issue, comment, create_user)
        run = AgentRun.objects.get(issue=issue, agent_user=agent_bot)
        assert run.created_by_id == create_user.id
        prompt = AgentRunActivity.objects.get(agent_run=run, type="prompt")
        assert prompt.created_by_id == create_user.id

    @pytest.mark.django_db
    def test_multiple_bots_mentioned_creates_multiple_runs(
        self, workspace, project, issue, agent_bot, second_agent_bot, create_user
    ):
        comment = IssueComment.objects.create(
            issue=issue, project=project, workspace=workspace,
            actor=create_user, comment_html=mention_html_multi(agent_bot, second_agent_bot),
        )
        run_comment_trigger(workspace, project, issue, comment, create_user)
        assert AgentRun.objects.count() == 2
        assert AgentRun.objects.filter(agent_user=agent_bot).count() == 1
        assert AgentRun.objects.filter(agent_user=second_agent_bot).count() == 1

    @pytest.mark.django_db
    def test_non_member_bot_mention_no_run(
        self, workspace, project, issue, non_member_agent_bot, create_user
    ):
        comment = IssueComment.objects.create(
            issue=issue, project=project, workspace=workspace,
            actor=create_user, comment_html=mention_html(non_member_agent_bot),
        )
        run_comment_trigger(workspace, project, issue, comment, create_user)
        assert AgentRun.objects.count() == 0
