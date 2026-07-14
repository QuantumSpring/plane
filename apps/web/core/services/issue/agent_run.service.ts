/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { TAgentRun } from "@plane/types";
import { APIService } from "@/services/api.service";

export class AgentRunService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async getIssueAgentRuns(workspaceSlug: string, projectId: string, issueId: string): Promise<TAgentRun[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/agent-runs/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
