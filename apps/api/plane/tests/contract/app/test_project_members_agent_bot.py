# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Agent bots (User.is_bot=True, bot_type="AGENT") must be surfaced in the
member-facing lists that feed the assignee dropdown and the @mention picker,
so a human can assign/mention an agent (e.g. "Cyrus") from the work-item UI.

Plane's OSS endpoints previously excluded ALL bots via `member__is_bot=False`.
This blanket filter is replaced with one that keeps humans AND agent bots,
while still hiding non-agent bots (e.g. WORKSPACE_SEED).
"""

import pytest

from plane.db.models import Project, ProjectMember, User, Workspace, WorkspaceMember


def _project_members_url(slug: str, project_id) -> str:
    return f"/api/workspaces/{slug}/projects/{project_id}/members/"


def _entity_search_url(slug: str, project_id, query: str = "") -> str:
    return f"/api/workspaces/{slug}/entity-search/?query_type=user_mention&project_id={project_id}&query={query}"


def _workspace_mention_url(slug: str, query: str = "") -> str:
    """entity-search for @mentions WITHOUT project_id — hits the workspace-wide branch."""
    return f"/api/workspaces/{slug}/entity-search/?query_type=user_mention&query={query}"


@pytest.fixture
def project(db, workspace, create_user):
    """A project owned by ``create_user`` (workspace owner / admin)."""
    project = Project.objects.create(
        name="Agent Project",
        identifier="AGT",
        workspace=workspace,
        created_by=create_user,
    )
    ProjectMember.objects.create(workspace=workspace, project=project, member=create_user, role=20, is_active=True)
    return project


def _make_agent_bot(workspace, project, *, agent_slug="cyrus") -> User:
    bot = User.objects.create(
        email=f"{agent_slug}-agent@bots.local",
        username=f"{agent_slug}-agent",
        display_name="Cyrus",
        is_bot=True,
        bot_type="AGENT",
        agent_slug=agent_slug,
    )
    bot.set_unusable_password()
    bot.save()
    WorkspaceMember.objects.create(workspace=workspace, member=bot, role=15, is_active=True)
    ProjectMember.objects.create(workspace=workspace, project=project, member=bot, role=15, is_active=True)
    return bot


def _make_non_agent_bot(workspace, project, *, bot_type=None) -> User:
    bot = User.objects.create(
        email="workspace-seed-bot@bots.local",
        username="workspace-seed-bot",
        display_name="Workspace Seed",
        is_bot=True,
        bot_type=bot_type,
    )
    bot.set_unusable_password()
    bot.save()
    WorkspaceMember.objects.create(workspace=workspace, member=bot, role=15, is_active=True)
    ProjectMember.objects.create(workspace=workspace, project=project, member=bot, role=15, is_active=True)
    return bot


def _make_human(workspace, project, *, email="human@plane.so") -> User:
    user = User.objects.create(email=email, username=email.split("@")[0], first_name="Human")
    user.set_password("test-password")
    user.save()
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15, is_active=True)
    ProjectMember.objects.create(workspace=workspace, project=project, member=user, role=15, is_active=True)
    return user


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectMembersAgentBotVisibility:
    def test_agent_bot_appears_in_project_members_list(self, session_client, workspace, project):
        bot = _make_agent_bot(workspace, project)

        response = session_client.get(_project_members_url(workspace.slug, project.id))

        assert response.status_code == 200
        member_ids = {str(m["member"]) for m in response.data}
        assert str(bot.id) in member_ids

    def test_non_agent_bot_does_not_appear_in_project_members_list(self, session_client, workspace, project):
        bot = _make_non_agent_bot(workspace, project, bot_type="WORKSPACE_SEED")

        response = session_client.get(_project_members_url(workspace.slug, project.id))

        assert response.status_code == 200
        member_ids = {str(m["member"]) for m in response.data}
        assert str(bot.id) not in member_ids

    def test_bot_with_no_bot_type_does_not_appear_in_project_members_list(self, session_client, workspace, project):
        bot = _make_non_agent_bot(workspace, project, bot_type=None)

        response = session_client.get(_project_members_url(workspace.slug, project.id))

        assert response.status_code == 200
        member_ids = {str(m["member"]) for m in response.data}
        assert str(bot.id) not in member_ids

    def test_human_member_still_appears_in_project_members_list(self, session_client, workspace, project):
        human = _make_human(workspace, project)

        response = session_client.get(_project_members_url(workspace.slug, project.id))

        assert response.status_code == 200
        member_ids = {str(m["member"]) for m in response.data}
        assert str(human.id) in member_ids

    def test_agent_bot_appears_in_mention_search(self, session_client, workspace, project):
        bot = _make_agent_bot(workspace, project)

        response = session_client.get(_entity_search_url(workspace.slug, project.id, query="cyrus"))

        assert response.status_code == 200
        mention_ids = {str(u["member__id"]) for u in response.data.get("user_mention", [])}
        assert str(bot.id) in mention_ids

    def test_non_agent_bot_does_not_appear_in_mention_search(self, session_client, workspace, project):
        bot = _make_non_agent_bot(workspace, project, bot_type="WORKSPACE_SEED")

        response = session_client.get(_entity_search_url(workspace.slug, project.id))

        assert response.status_code == 200
        mention_ids = {str(u["member__id"]) for u in response.data.get("user_mention", [])}
        assert str(bot.id) not in mention_ids

    def test_agent_bot_appears_in_workspace_wide_mention_search(self, session_client, workspace, project):
        """Workspace-wide branch (no project_id): the WorkspaceMember query must surface
        the AGENT bot while still hiding a non-agent (WORKSPACE_SEED) bot."""
        agent = _make_agent_bot(workspace, project)
        seed = _make_non_agent_bot(workspace, project, bot_type="WORKSPACE_SEED")

        response = session_client.get(_workspace_mention_url(workspace.slug))

        assert response.status_code == 200
        mention_ids = {str(u["member__id"]) for u in response.data.get("user_mention", [])}
        assert str(agent.id) in mention_ids
        assert str(seed.id) not in mention_ids

    def test_agent_bot_from_other_workspace_absent_from_mention_search(
        self, session_client, workspace, project, create_user
    ):
        """Cross-workspace isolation: the widened Q filter must not weaken workspace
        scoping. An AGENT bot that is a member of workspace B must not leak into
        workspace A's mention search — neither the project-scoped nor the workspace-wide branch."""
        workspace_b = Workspace.objects.create(name="Other Workspace", owner=create_user, slug="other-workspace")
        WorkspaceMember.objects.create(workspace=workspace_b, member=create_user, role=20, is_active=True)
        project_b = Project.objects.create(
            name="Other Project", identifier="OTH", workspace=workspace_b, created_by=create_user
        )
        ProjectMember.objects.create(
            workspace=workspace_b, project=project_b, member=create_user, role=20, is_active=True
        )
        foreign_bot = _make_agent_bot(workspace_b, project_b, agent_slug="cyrus-b")

        # Workspace-wide branch scoped to workspace A must not include the workspace-B bot.
        ws_response = session_client.get(_workspace_mention_url(workspace.slug))
        assert ws_response.status_code == 200
        ws_ids = {str(u["member__id"]) for u in ws_response.data.get("user_mention", [])}
        assert str(foreign_bot.id) not in ws_ids

        # Project-scoped branch scoped to workspace A's project must not include it either.
        proj_response = session_client.get(_entity_search_url(workspace.slug, project.id))
        assert proj_response.status_code == 200
        proj_ids = {str(u["member__id"]) for u in proj_response.data.get("user_mention", [])}
        assert str(foreign_bot.id) not in proj_ids
