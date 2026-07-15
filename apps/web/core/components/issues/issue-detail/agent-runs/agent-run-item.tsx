/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { AlertTriangle, Bot, CircleCheck, HelpCircle, MessageSquare, Wrench } from "lucide-react";
import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
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

// Activity bodies are markdown; render them so **bold**, `code`, lists and links
// display properly. Keep color/weight inherited from the row so ephemeral styling
// (italic + muted) still applies. Extra props react-markdown passes are ignored.
const Heading = ({ children }: { children?: ReactNode }) => (
  <span className="mt-1.5 block font-semibold text-primary">{children}</span>
);

const MARKDOWN_COMPONENTS = {
  p: ({ children }: { children?: ReactNode }) => <span className="block">{children}</span>,
  h1: Heading,
  h2: Heading,
  h3: Heading,
  h4: Heading,
  h5: Heading,
  h6: Heading,
  strong: ({ children }: { children?: ReactNode }) => <strong className="font-semibold">{children}</strong>,
  em: ({ children }: { children?: ReactNode }) => <em>{children}</em>,
  code: ({ children }: { children?: ReactNode }) => (
    <code className="font-mono rounded bg-layer-1 px-1">{children}</code>
  ),
  ul: ({ children }: { children?: ReactNode }) => <ul className="ml-4 list-disc">{children}</ul>,
  ol: ({ children }: { children?: ReactNode }) => <ol className="ml-4 list-decimal">{children}</ol>,
  li: ({ children }: { children?: ReactNode }) => <li>{children}</li>,
  hr: () => <hr className="my-2 border-subtle" />,
  blockquote: ({ children }: { children?: ReactNode }) => (
    <blockquote className="border-l-2 border-subtle pl-2 text-tertiary">{children}</blockquote>
  ),
  a: ({ href, children }: { href?: string; children?: ReactNode }) => (
    <a href={href} target="_blank" rel="noreferrer noopener" className="text-accent-primary hover:underline">
      {children}
    </a>
  ),
};

// Some agents delimit collapsible sections with `+++Title … +++` markers, which
// aren't standard markdown. Normalize them to bold section headings so they render
// cleanly instead of showing the literal `+++`.
const normalizeAgentMarkdown = (md: string): string =>
  md.replace(/^\+\+\+[ \t]*(.+?)[ \t]*$/gm, "\n**$1**\n").replace(/^\+\+\+[ \t]*$/gm, "");

// Agents vary in how they shape `action` content (the SDK uses `parameters: object`;
// some send `parameter: string`), so read defensively and never surface "undefined".
function ActivityContent({ activity }: { activity: TAgentRunActivity }): ReactNode {
  const content = activity.content as Record<string, unknown>;
  if (content.type === "action") {
    const label = typeof content.action === "string" ? content.action : "action";
    const raw = content.parameters ?? content.parameter;
    let params = "";
    if (typeof raw === "string") params = raw;
    else if (raw && typeof raw === "object" && Object.keys(raw).length > 0) params = JSON.stringify(raw);
    return (
      <span>
        {label}
        {params && <code className="font-mono ml-1.5 rounded bg-layer-1 px-1 text-12">{params}</code>}
      </span>
    );
  }
  const body = typeof content.body === "string" ? content.body : "";
  return <ReactMarkdown components={MARKDOWN_COMPONENTS}>{normalizeAgentMarkdown(body)}</ReactMarkdown>;
}

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
              <div className="min-w-0 break-words">
                <ActivityContent activity={activity} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
