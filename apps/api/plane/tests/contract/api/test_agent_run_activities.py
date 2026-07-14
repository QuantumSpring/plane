# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import uuid

import pytest

from plane.db.models import AgentRun, AgentRunActivity, Project, User


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


@pytest.fixture
def foreign_run(db, agent_bot, create_user):
    """A run that lives in a *different* workspace (B) the caller cannot reach."""
    from plane.db.models import Workspace
    workspace_b = Workspace.objects.create(name="Other WS", owner=agent_bot, slug="other-ws")
    run_b = AgentRun.objects.create(
        workspace=workspace_b, agent_user=agent_bot, created_by=create_user
    )
    activity_b = AgentRunActivity.objects.create(
        agent_run=run_b,
        workspace=workspace_b,
        type="response",
        content={"type": "response", "body": "secret"},
    )
    return run_b, activity_b


def _post_activity(client, workspace, run, body):
    return client.post(
        f"/api/v1/workspaces/{workspace.slug}/runs/{run.id}/activities/", body, format="json"
    )


@pytest.mark.contract
class TestAgentRunActivityEndpoints:
    @pytest.mark.django_db
    def test_first_activity_moves_run_in_progress(self, api_key_client, workspace, run):
        response = _post_activity(
            api_key_client, workspace, run,
            {"type": "thought", "content": {"type": "thought", "body": "planning"}, "ephemeral": True},
        )
        assert response.status_code == 201, response.data
        run.refresh_from_db()
        assert run.status == "in_progress"

    @pytest.mark.django_db
    def test_stop_signal_completes_run(self, api_key_client, workspace, run):
        response = _post_activity(
            api_key_client, workspace, run,
            {"type": "response", "content": {"type": "response", "body": "done"}, "signal": "stop"},
        )
        assert response.status_code == 201
        run.refresh_from_db()
        assert run.status == "completed"
        assert run.ended_at is not None

    @pytest.mark.django_db
    def test_error_activity_fails_run(self, api_key_client, workspace, run):
        response = _post_activity(
            api_key_client, workspace, run,
            {"type": "error", "content": {"type": "error", "body": "boom"}},
        )
        assert response.status_code == 201
        run.refresh_from_db()
        assert run.status == "failed"
        assert run.error_metadata.get("body") == "boom"

    @pytest.mark.django_db
    def test_elicitation_moves_run_awaiting(self, api_key_client, workspace, run):
        response = _post_activity(
            api_key_client, workspace, run,
            {"type": "elicitation", "content": {"type": "elicitation", "body": "pick one"}, "signal": "select"},
        )
        assert response.status_code == 201
        run.refresh_from_db()
        assert run.status == "awaiting"

    @pytest.mark.django_db
    def test_new_activity_supersedes_previous_ephemerals(self, api_key_client, workspace, run):
        _post_activity(api_key_client, workspace, run,
                       {"type": "thought", "content": {"type": "thought", "body": "one"}, "ephemeral": True})
        _post_activity(api_key_client, workspace, run,
                       {"type": "thought", "content": {"type": "thought", "body": "two"}, "ephemeral": True})
        live = AgentRunActivity.objects.filter(agent_run=run)
        assert live.count() == 1
        assert live.first().content["body"] == "two"

    @pytest.mark.django_db
    def test_terminal_run_rejects_activities(self, api_key_client, workspace, run):
        run.status = "completed"
        run.save()
        response = _post_activity(
            api_key_client, workspace, run,
            {"type": "thought", "content": {"type": "thought", "body": "late"}},
        )
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_list_and_retrieve_activities(self, api_key_client, workspace, run):
        created = _post_activity(
            api_key_client, workspace, run,
            {"type": "response", "content": {"type": "response", "body": "hi"}},
        ).data
        response = api_key_client.get(f"/api/v1/workspaces/{workspace.slug}/runs/{run.id}/activities/")
        assert response.status_code == 200
        response = api_key_client.get(
            f"/api/v1/workspaces/{workspace.slug}/runs/{run.id}/activities/{created['id']}/"
        )
        assert response.status_code == 200
        assert response.data["content"]["body"] == "hi"

    @pytest.mark.django_db
    def test_client_supplied_project_is_ignored(self, api_key_client, workspace, agent_bot, create_user):
        project = Project.objects.create(name="Run P", identifier="RNP", workspace=workspace)
        run = AgentRun.objects.create(
            workspace=workspace, project=project, agent_user=agent_bot, created_by=create_user
        )
        bogus_project = str(uuid.uuid4())
        response = _post_activity(
            api_key_client, workspace, run,
            {"type": "response", "content": {"type": "response", "body": "hi"}, "project": bogus_project},
        )
        assert response.status_code == 201, response.data
        activity = AgentRunActivity.objects.get(id=response.data["id"])
        assert str(activity.project_id) == str(project.id)
        assert str(activity.project_id) != bogus_project

    @pytest.mark.django_db
    def test_list_activities_isolated_across_workspaces(self, api_key_client, workspace, foreign_run):
        run_b, _ = foreign_run
        # B's run id served under A's slug: must not leak B's activities.
        response = api_key_client.get(
            f"/api/v1/workspaces/{workspace.slug}/runs/{run_b.id}/activities/"
        )
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            assert response.data["results"] == []

    @pytest.mark.django_db
    def test_detail_activity_isolated_across_workspaces(self, api_key_client, workspace, foreign_run):
        run_b, activity_b = foreign_run
        response = api_key_client.get(
            f"/api/v1/workspaces/{workspace.slug}/runs/{run_b.id}/activities/{activity_b.id}/"
        )
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_post_to_foreign_run_rejected(self, api_key_client, workspace, foreign_run):
        run_b, _ = foreign_run
        response = api_key_client.post(
            f"/api/v1/workspaces/{workspace.slug}/runs/{run_b.id}/activities/",
            {"type": "thought", "content": {"type": "thought", "body": "intrusion"}},
            format="json",
        )
        assert response.status_code in (403, 404)
