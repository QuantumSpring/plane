/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { Loader } from "@plane/ui";

export function AgentRunsLoader() {
  return (
    <Loader className="space-y-3">
      <Loader.Item height="34px" width="100%" />
      <Loader.Item height="34px" width="100%" />
    </Loader>
  );
}
