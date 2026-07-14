/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type TAgentRunStatus =
  | "created"
  | "in_progress"
  | "awaiting"
  | "completed"
  | "stopping"
  | "stopped"
  | "failed"
  | "stale";

export type TAgentRunActivityType = "prompt" | "thought" | "action" | "response" | "elicitation" | "error";

export type TAgentRunActivityContent =
  | { type: "action"; action: string; parameters: Record<string, string> }
  | { type: Exclude<TAgentRunActivityType, "action">; body: string };

export type TAgentRunActivity = {
  id: string;
  agent_run: string;
  type: TAgentRunActivityType;
  content: TAgentRunActivityContent;
  ephemeral: boolean;
  signal: "auth_request" | "continue" | "select" | "stop";
  actor: string | null;
  created_at: string;
};

// Models the APP endpoint payload (nested `activities`), NOT the webhook `data` payload
// (which carries no activities and adds *_detail keys). Don't conflate the two.
export type TAgentRun = {
  id: string;
  agent_user: string;
  issue: string | null;
  project: string | null;
  status: TAgentRunStatus;
  type: "comment_thread" | "assignment";
  started_at: string;
  ended_at: string | null;
  external_link: string | null;
  created_at: string;
  activities: TAgentRunActivity[];
};

export type TAgentRunIdMap = Record<string, string[]>; // issueId -> runIds
export type TAgentRunMap = Record<string, TAgentRun>; // runId -> run
