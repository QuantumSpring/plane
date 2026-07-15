/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { set } from "lodash-es";
import { action, makeObservable, observable, runInAction } from "mobx";
import { computedFn } from "mobx-utils";
// types
import type { TAgentRun, TAgentRunIdMap, TAgentRunMap } from "@plane/types";
// services
import { AgentRunService } from "@/services/issue";
// types
import type { IIssueDetail } from "./root.store";

export interface IIssueAgentRunStoreActions {
  // actions
  fetchAgentRuns: (workspaceSlug: string, projectId: string, issueId: string) => Promise<TAgentRun[]>;
}

export interface IIssueAgentRunStore extends IIssueAgentRunStoreActions {
  // observables
  loader: boolean;
  agentRuns: TAgentRunIdMap;
  agentRunMap: TAgentRunMap;
  // helper methods
  getAgentRunsByIssueId: (issueId: string) => TAgentRun[] | undefined;
}

export class IssueAgentRunStore implements IIssueAgentRunStore {
  // observables
  loader: boolean = false;
  agentRuns: TAgentRunIdMap = {};
  agentRunMap: TAgentRunMap = {};
  // root store
  rootIssueDetailStore: IIssueDetail;
  // services
  agentRunService: AgentRunService;

  constructor(rootStore: IIssueDetail) {
    makeObservable(this, {
      // observables
      loader: observable.ref,
      agentRuns: observable,
      agentRunMap: observable,
      // actions
      fetchAgentRuns: action,
    });
    // root store
    this.rootIssueDetailStore = rootStore;
    // services
    this.agentRunService = new AgentRunService();
  }

  // helper methods
  getAgentRunsByIssueId = computedFn((issueId: string) => {
    const runIds = this.agentRuns[issueId];
    if (!runIds) return undefined;
    return runIds.map((id) => this.agentRunMap[id]).filter(Boolean);
  });

  // actions
  fetchAgentRuns = async (workspaceSlug: string, projectId: string, issueId: string) => {
    this.loader = true;
    try {
      const runs = await this.agentRunService.getIssueAgentRuns(workspaceSlug, projectId, issueId);
      runInAction(() => {
        set(
          this.agentRuns,
          issueId,
          runs.map((run) => run.id)
        );
        runs.forEach((run) => set(this.agentRunMap, run.id, run));
        this.loader = false;
      });
      return runs;
    } catch (error) {
      this.loader = false;
      throw error;
    }
  };
}
