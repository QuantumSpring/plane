# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.db.models import AgentRun, Project, User


@pytest.fixture
def project(db, workspace, create_user):
    return Project.objects.create(name="Agent P", identifier="AGP", workspace=workspace)


@pytest.fixture
def agent_bot(db, workspace):
    from plane.db.models import WorkspaceMember

    bot = User.objects.create(
        email="cyrus-bot@example.com",
        username="cyrus-bot",
        is_bot=True,
        bot_type="AGENT",
        agent_slug="cyrus",
        display_name="Cyrus",
    )
    WorkspaceMember.objects.create(workspace=workspace, member=bot, role=15)
    return bot


@pytest.mark.contract
class TestAgentRunEndpoints:
    @pytest.mark.django_db
    def test_create_run_by_agent_slug(self, api_key_client, workspace, project, agent_bot):
        url = f"/api/v1/workspaces/{workspace.slug}/runs/"
        response = api_key_client.post(url, {"agent_slug": "cyrus", "project": str(project.id)}, format="json")
        assert response.status_code == 201, response.data
        assert response.data["status"] == "created"
        assert response.data["type"] == "comment_thread"
        assert str(response.data["agent_user"]) == str(agent_bot.id)
        assert response.data["started_at"] is not None

    @pytest.mark.django_db
    def test_create_run_unknown_agent_slug_404(self, api_key_client, workspace, project):
        url = f"/api/v1/workspaces/{workspace.slug}/runs/"
        response = api_key_client.post(url, {"agent_slug": "nope"}, format="json")
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_create_run_rejects_cross_workspace_object(self, api_key_client, workspace, project, agent_bot):
        from plane.db.models import Workspace

        other_ws = Workspace.objects.create(name="Other WS", owner=agent_bot, slug="other-ws")
        other_project = Project.objects.create(name="Other P", identifier="OTP", workspace=other_ws)
        url = f"/api/v1/workspaces/{workspace.slug}/runs/"
        response = api_key_client.post(url, {"agent_slug": "cyrus", "project": str(other_project.id)}, format="json")
        assert response.status_code == 400, response.data

    @pytest.mark.django_db
    def test_list_and_retrieve_run(self, api_key_client, workspace, project, agent_bot, create_user):
        run = AgentRun.objects.create(
            workspace=workspace, project=project, agent_user=agent_bot, created_by=create_user
        )
        list_url = f"/api/v1/workspaces/{workspace.slug}/runs/"
        response = api_key_client.get(list_url)
        assert response.status_code == 200
        detail_url = f"/api/v1/workspaces/{workspace.slug}/runs/{run.id}/"
        response = api_key_client.get(detail_url)
        assert response.status_code == 200
        assert str(response.data["id"]) == str(run.id)

    @pytest.mark.django_db
    def test_requires_api_key(self, api_client, workspace):
        response = api_client.get(f"/api/v1/workspaces/{workspace.slug}/runs/")
        assert response.status_code in (401, 403)
