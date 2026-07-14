/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { AlertTriangle, Bot, CircleCheck, HelpCircle, MessageSquare, Wrench } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Tooltip } from "@plane/propel/tooltip";
import type { TAgentRun, TAgentRunActivity, TAgentRunStatus } from "@plane/types";
import { Badge } from "@plane/ui";
import { calculateTimeAgo, renderFormattedDate, renderFormattedTime } from "@plane/utils";
// hooks
import { usePlatformOS } from "@/hooks/use-platform-os";

const STATUS_VARIANT: Record<TAgentRunStatus, "primary" | "neutral" | "success" | "warning" | "destructive"> = {
  created: "neutral",
  in_progress: "primary",
  awaiting: "warning",
  completed: "success",
  stopping: "warning",
  stopped: "neutral",
  failed: "destructive",
  stale: "neutral",
};

const ACTIVITY_ICON: Record<TAgentRunActivity["type"], typeof Bot> = {
  prompt: MessageSquare,
  thought: Bot,
  action: Wrench,
  response: CircleCheck,
  elicitation: HelpCircle,
  error: AlertTriangle,
};

const getActivityBody = (activity: TAgentRunActivity): string =>
  activity.content.type === "action"
    ? `${activity.content.action} ${JSON.stringify(activity.content.parameters)}`
    : activity.content.body;

type Props = {
  run: TAgentRun;
};

export function AgentRunItem(props: Props) {
  const { run } = props;
  // plane hooks
  const { t } = useTranslation();
  const { isMobile } = usePlatformOS();

  return (
    <div className="space-y-2 rounded-md border border-subtle p-3">
      <div className="flex items-center gap-2">
        <Bot className="h-4 w-4 shrink-0 text-tertiary" />
        <Badge variant={STATUS_VARIANT[run.status]} size="sm">
          {t(`common.agent_runs.status.${run.status}`)}
        </Badge>
        <Tooltip
          isMobile={isMobile}
          tooltipContent={`${renderFormattedDate(run.started_at)}, ${renderFormattedTime(run.started_at)}`}
        >
          <span className="text-11 whitespace-nowrap text-tertiary">{calculateTimeAgo(run.started_at)}</span>
        </Tooltip>
        {run.external_link && (
          <a
            href={run.external_link}
            target="_blank"
            rel="noreferrer noopener"
            className="text-11 text-accent-primary hover:underline"
          >
            {t("common.agent_runs.pr")}
          </a>
        )}
      </div>
      <div className="space-y-1.5">
        {run.activities.map((activity) => {
          const Icon = ACTIVITY_ICON[activity.type];
          return (
            <div
              key={activity.id}
              className={`flex items-start gap-2 text-13 ${
                activity.ephemeral ? "animate-pulse text-tertiary italic" : "text-secondary"
              }`}
            >
              <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span className="break-words whitespace-pre-wrap">{getActivityBody(activity)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
