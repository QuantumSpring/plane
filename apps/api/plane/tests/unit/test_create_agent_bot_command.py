# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from django.core.management import call_command

from plane.db.models import APIToken, User, WorkspaceMember


@pytest.mark.unit
class TestCreateAgentBot:
    @pytest.mark.django_db
    def test_creates_bot_member_and_token(self, workspace, capsys):
        call_command(
            "create_agent_bot",
            workspace_slug=workspace.slug,
            slug="cyrus",
            display_name="Cyrus",
        )
        bot = User.objects.get(agent_slug="cyrus")
        assert bot.is_bot and bot.bot_type == "AGENT"
        assert WorkspaceMember.objects.filter(workspace=workspace, member=bot, role=15).exists()
        token = APIToken.objects.get(user=bot)
        assert token.user_type == 1
        assert token.token in capsys.readouterr().out

    @pytest.mark.django_db
    def test_idempotent(self, workspace):
        call_command("create_agent_bot", workspace_slug=workspace.slug, slug="cyrus", display_name="Cyrus")
        call_command("create_agent_bot", workspace_slug=workspace.slug, slug="cyrus", display_name="Cyrus")
        assert User.objects.filter(agent_slug="cyrus").count() == 1
