# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

# Module imports
from plane.db.models import APIToken, BotTypeEnum, Project, ProjectMember, User, Workspace, WorkspaceMember


class Command(BaseCommand):
    help = "Create (or fetch) an agent bot user, workspace membership, and API token"

    def add_arguments(self, parser):
        parser.add_argument("--workspace-slug", dest="workspace_slug", required=True)
        parser.add_argument("--slug", dest="slug", required=True, help="agent_slug, e.g. cyrus")
        parser.add_argument("--display-name", dest="display_name", required=True)
        parser.add_argument(
            "--project-id",
            dest="project_id",
            required=False,
            help="also add the bot as a project member (mention picker)",
        )

    def handle(self, *args, **options):
        workspace = Workspace.objects.filter(slug=options["workspace_slug"]).first()
        if workspace is None:
            raise CommandError(f"workspace {options['workspace_slug']} not found")

        agent_slug = options["slug"]
        bot, created = User.objects.get_or_create(
            agent_slug=agent_slug,
            defaults={
                "email": f"{agent_slug}-agent@bots.local",
                "username": f"{agent_slug}-agent",
                "display_name": options["display_name"],
                "is_bot": True,
                "bot_type": BotTypeEnum.AGENT,
            },
        )
        if created:
            bot.set_unusable_password()
            bot.save()

        WorkspaceMember.objects.get_or_create(workspace=workspace, member=bot, defaults={"role": 15})  # Member

        if options.get("project_id"):
            try:
                project = Project.objects.filter(pk=options["project_id"], workspace=workspace).first()
            except ValidationError:
                project = None
            if project is None:
                raise CommandError(f"project {options['project_id']} not found in workspace {workspace.slug}")
            ProjectMember.objects.get_or_create(project=project, member=bot, defaults={"role": 15})  # Member

        token, _ = APIToken.objects.get_or_create(
            user=bot, workspace=workspace, defaults={"user_type": 1, "label": "agent-bot"}
        )

        self.stdout.write(self.style.SUCCESS(f"bot user: {bot.id} ({bot.display_name})"))
        self.stdout.write(self.style.SUCCESS(f"PLANE_BOT_TOKEN: {token.token}"))
