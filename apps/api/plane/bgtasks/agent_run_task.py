# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import json
import uuid

# Third party imports
from bs4 import BeautifulSoup
from celery import shared_task

# Module imports
from plane.bgtasks.notification_task import extract_comment_mentions
from plane.db.models import AgentRun, AgentRunActivity, Issue, IssueComment, User
from plane.utils.exception_logger import log_exception


def _strip_html(html):
    try:
        return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)
    except Exception:
        return html or ""


def _valid_uuids(ids):
    """Keep only well-formed UUID strings so a single malformed mention id
    can't abort the whole comment (a bad value would otherwise raise inside
    the id__in query)."""
    out = []
    for i in ids:
        try:
            uuid.UUID(str(i))
            out.append(i)
        except (ValueError, TypeError):
            continue
    return out


def _workspace_agent_bots(user_ids, workspace_id):
    if not user_ids:
        return User.objects.none()
    return User.objects.filter(
        id__in=user_ids,
        is_bot=True,
        bot_type="AGENT",
        member_workspace__workspace_id=workspace_id,
        member_workspace__is_active=True,
    ).distinct()


def _start_or_prompt_run(bot, issue, actor_id, prompt, run_type, source_comment=None):
    # Assumes serial arrival per issue+bot: there is no row lock here, so two
    # near-simultaneous triggers could both miss the active run. That is fine
    # for comment traffic, where prompts arrive one at a time.
    active_run = (
        AgentRun.objects.filter(
            issue=issue, agent_user=bot, status__in=AgentRun.NON_TERMINAL_STATUSES
        )
        .order_by("-created_at")
        .first()
    )
    is_new_run = active_run is None
    if is_new_run:
        # Build-then-save (not objects.create) so created_by_id reaches
        # BaseModel.save(); objects.create() drops the kwarg and, with no
        # request user in the celery context, the audit user would be nulled.
        run = AgentRun(
            workspace_id=issue.workspace_id,
            project_id=issue.project_id,
            issue=issue,
            agent_user=bot,
            type=run_type,
            source_comment=source_comment,
        )
        run.save(created_by_id=actor_id)
    else:
        run = active_run

    activity = AgentRunActivity(
        workspace_id=issue.workspace_id,
        project_id=issue.project_id,
        agent_run=run,
        type="prompt",
        content={"type": "prompt", "body": prompt},
        actor_id=actor_id,
        comment=source_comment,
    )
    activity.save(created_by_id=actor_id)

    if not is_new_run and run.status == AgentRun.StatusEnum.AWAITING:
        run.status = AgentRun.StatusEnum.IN_PROGRESS
        run.save(update_fields=["status", "updated_at"])

    dispatch_agent_run_webhook(run, "created" if is_new_run else "prompted", prompt)
    return run


def _handle_comment_created(requested_data, issue_id, actor_id, workspace_id):
    data = json.loads(requested_data) if requested_data else {}
    comment_html = data.get("comment_html", "")
    actor = User.objects.filter(id=actor_id).first()
    if actor is None or actor.is_bot:
        return
    mentioned_ids = _valid_uuids(extract_comment_mentions(comment_html))
    bots = _workspace_agent_bots(mentioned_ids, workspace_id)
    if not bots:
        return
    issue = Issue.objects.get(id=issue_id)
    source_comment = IssueComment.objects.filter(id=data.get("id")).first()
    prompt = _strip_html(comment_html)
    for bot in bots:
        try:
            _start_or_prompt_run(
                bot, issue, actor_id, prompt, AgentRun.TypeEnum.COMMENT_THREAD, source_comment=source_comment
            )
        except Exception as e:
            log_exception(e)


def _handle_assignees_changed(requested_data, current_instance, issue_id, actor_id, workspace_id):
    requested = json.loads(requested_data) if requested_data else {}
    current = json.loads(current_instance) if current_instance else {}
    new_ids = set(requested.get("assignee_ids", []) or [])
    old_ids = set((current or {}).get("assignee_ids", []) or [])
    added = new_ids - old_ids
    actor = User.objects.filter(id=actor_id).first()
    if actor is None or actor.is_bot:
        return
    bots = _workspace_agent_bots(_valid_uuids(list(added)), workspace_id)
    if not bots:
        return
    issue = Issue.objects.get(id=issue_id)
    prompt = f"{issue.name}\n\n{_strip_html(issue.description_html)}"
    for bot in bots:
        try:
            _start_or_prompt_run(bot, issue, actor_id, prompt, AgentRun.TypeEnum.ASSIGNMENT)
        except Exception as e:
            log_exception(e)


@shared_task
def agent_run_trigger(
    type, requested_data, current_instance, issue_id, actor_id, project_id, workspace_id, epoch
):
    # Signature is fixed by the issue_activity pipeline contract (hook wired up
    # in Task 6); each positional arg mirrors what that dispatcher passes.
    try:
        if type == "comment.activity.created":
            _handle_comment_created(requested_data, issue_id, actor_id, workspace_id)
        elif type in ("issue.activity.created", "issue.activity.updated"):
            _handle_assignees_changed(
                requested_data, current_instance, issue_id, actor_id, workspace_id
            )
    except Exception as e:
        log_exception(e)


def dispatch_agent_run_webhook(agent_run, action, prompt):
    """Implemented in Task 7 - placeholder so tests can patch it."""
    pass
