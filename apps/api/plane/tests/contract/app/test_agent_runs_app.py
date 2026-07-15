# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from rest_framework.test import APIClient

from plane.db.models import AgentRun, AgentRunActivity, Issue, Project, ProjectMember, State, User


@pytest.mark.contract
class TestAgentRunsAppEndpoint:
    @pytest.mark.django_db
    def test_lists_runs_with_activities(self, session_client, create_user, workspace):
        project = Project.objects.create(name="P", identifier="P", workspace=workspace)
        ProjectMember.objects.create(project=project, member=create_user, role=20)
        state = State.objects.create(name="Todo", group="unstarted", project=project, workspace=workspace)
        issue = Issue.objects.create(name="I", project=project, workspace=workspace, state=state)
        bot = User.objects.create(
            email="b@example.com", is_bot=True, bot_type="AGENT", agent_slug="cyrus", username="cyrus-bot"
        )
        run = AgentRun.objects.create(
            workspace=workspace, project=project, issue=issue, agent_user=bot, created_by=create_user
        )
        AgentRunActivity.objects.create(
            workspace=workspace, project=project, agent_run=run,
            type="prompt", content={"type": "prompt", "body": "go"},
        )
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/agent-runs/"
        response = session_client.get(url)
        assert response.status_code == 200
        assert len(response.data) == 1
        assert str(response.data[0]["id"]) == str(run.id)
        assert response.data[0]["activities"][0]["content"]["body"] == "go"

    @pytest.mark.django_db
    def test_non_member_forbidden(self, create_user, workspace):
        project = Project.objects.create(name="P", identifier="P", workspace=workspace)
        state = State.objects.create(name="Todo", group="unstarted", project=project, workspace=workspace)
        issue = Issue.objects.create(name="I", project=project, workspace=workspace, state=state)
        # A user who is NOT a member of the project.
        outsider = User.objects.create(email="outsider@example.com", username="outsider")
        client = APIClient()
        client.force_authenticate(user=outsider)
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/agent-runs/"
        response = client.get(url)
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_runs_are_scoped_to_the_requested_issue(self, session_client, create_user, workspace):
        project = Project.objects.create(name="P", identifier="P", workspace=workspace)
        ProjectMember.objects.create(project=project, member=create_user, role=20)
        state = State.objects.create(name="Todo", group="unstarted", project=project, workspace=workspace)
        issue_a = Issue.objects.create(name="A", project=project, workspace=workspace, state=state)
        issue_b = Issue.objects.create(name="B", project=project, workspace=workspace, state=state)
        bot = User.objects.create(
            email="b@example.com", is_bot=True, bot_type="AGENT", agent_slug="cyrus", username="cyrus-bot"
        )
        AgentRun.objects.create(
            workspace=workspace, project=project, issue=issue_a, agent_user=bot, created_by=create_user
        )
        # Issue B has no runs; issue A's run must not leak into issue B's list.
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue_b.id}/agent-runs/"
        response = session_client.get(url)
        assert response.status_code == 200
        assert response.data == []
