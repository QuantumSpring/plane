# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.conf import settings
from django.db import models
from django.utils import timezone

# Module imports
from plane.db.models.workspace import WorkspaceBaseModel


class AgentRun(WorkspaceBaseModel):
    class StatusEnum(models.TextChoices):
        CREATED = "created", "Created"
        IN_PROGRESS = "in_progress", "In Progress"
        AWAITING = "awaiting", "Awaiting"
        COMPLETED = "completed", "Completed"
        STOPPING = "stopping", "Stopping"
        STOPPED = "stopped", "Stopped"
        FAILED = "failed", "Failed"
        STALE = "stale", "Stale"

    class TypeEnum(models.TextChoices):
        COMMENT_THREAD = "comment_thread", "Comment Thread"
        ASSIGNMENT = "assignment", "Assignment"  # fork extension; Cloud has only comment_thread

    NON_TERMINAL_STATUSES = (
        StatusEnum.CREATED,
        StatusEnum.IN_PROGRESS,
        StatusEnum.AWAITING,
        StatusEnum.STOPPING,
    )

    agent_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agent_runs"
    )
    issue = models.ForeignKey(
        "db.Issue", on_delete=models.CASCADE, related_name="agent_runs", null=True, blank=True
    )
    source_comment = models.ForeignKey(
        "db.IssueComment", on_delete=models.SET_NULL,
        related_name="triggered_agent_runs", null=True, blank=True,
    )
    comment = models.ForeignKey(
        "db.IssueComment", on_delete=models.SET_NULL,
        related_name="agent_runs", null=True, blank=True,
    )
    status = models.CharField(max_length=30, choices=StatusEnum.choices, default=StatusEnum.CREATED)
    type = models.CharField(max_length=30, choices=TypeEnum.choices, default=TypeEnum.COMMENT_THREAD)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    stopped_at = models.DateTimeField(null=True, blank=True)
    stopped_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="stopped_agent_runs", null=True, blank=True,
    )
    external_link = models.URLField(max_length=1024, null=True, blank=True)
    error_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Agent Run"
        verbose_name_plural = "Agent Runs"
        db_table = "agent_runs"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.workspace_id} {self.id} {self.status}"


class AgentRunActivity(WorkspaceBaseModel):
    class TypeEnum(models.TextChoices):
        PROMPT = "prompt", "Prompt"
        THOUGHT = "thought", "Thought"
        ACTION = "action", "Action"
        RESPONSE = "response", "Response"
        ELICITATION = "elicitation", "Elicitation"
        ERROR = "error", "Error"

    class SignalEnum(models.TextChoices):
        AUTH_REQUEST = "auth_request", "Auth Request"
        CONTINUE = "continue", "Continue"
        SELECT = "select", "Select"
        STOP = "stop", "Stop"

    agent_run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="activities")
    type = models.CharField(max_length=30, choices=TypeEnum.choices)
    content = models.JSONField(default=dict)
    content_metadata = models.JSONField(default=dict, blank=True)
    ephemeral = models.BooleanField(default=False)
    signal = models.CharField(max_length=30, choices=SignalEnum.choices, default=SignalEnum.CONTINUE)
    signal_metadata = models.JSONField(default=dict, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="agent_run_activities", null=True, blank=True,
    )
    comment = models.ForeignKey(
        "db.IssueComment", on_delete=models.SET_NULL,
        related_name="agent_run_activities", null=True, blank=True,
    )

    class Meta:
        verbose_name = "Agent Run Activity"
        verbose_name_plural = "Agent Run Activities"
        db_table = "agent_run_activities"
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.agent_run_id} {self.type}"
