/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import type { TAgentRunStatus } from "@plane/types";
import { Collapsible, CollapsibleButton } from "@plane/ui";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// local imports
import { AgentRunItem } from "./agent-run-item";
import { AgentRunsLoader } from "./loader";

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
};

// statuses for which the run is still in flight and worth polling for
const ACTIVE_STATUSES: Set<TAgentRunStatus> = new Set(["created", "in_progress", "awaiting", "stopping"]);

export const AgentRuns = observer(function AgentRuns(props: Props) {
  const { workspaceSlug, projectId, issueId } = props;
  // plane hooks
  const { t } = useTranslation();
  // states
  const [isOpen, setIsOpen] = useState(true);
  // store hooks
  const {
    agentRun: { getAgentRunsByIssueId, fetchAgentRuns, loader },
  } = useIssueDetail();

  // derived values
  const runs = getAgentRunsByIssueId(issueId);
  const hasActiveRun = !!runs?.some((run) => ACTIVE_STATUSES.has(run.status));

  // poll while a run is active; stop polling once every run has reached a terminal state
  useSWR(
    `ISSUE_AGENT_RUNS_${workspaceSlug}_${projectId}_${issueId}`,
    () => fetchAgentRuns(workspaceSlug, projectId, issueId),
    { refreshInterval: hasActiveRun ? 5000 : 0 }
  );

  if (runs === undefined && loader) return <AgentRunsLoader />;
  if (!runs || runs.length === 0) return null;

  return (
    <div className="py-2">
      <Collapsible
        isOpen={isOpen}
        onToggle={() => setIsOpen((prev) => !prev)}
        buttonClassName="w-full"
        title={
          <CollapsibleButton
            isOpen={isOpen}
            title={t("common.agent_runs.title")}
            indicatorElement={<span className="text-14 !leading-3 text-tertiary">{runs.length}</span>}
          />
        }
      >
        <div className="space-y-2 px-2.5 pb-3">
          {runs.map((run) => (
            <AgentRunItem key={run.id} run={run} />
          ))}
        </div>
      </Collapsible>
    </div>
  );
});
