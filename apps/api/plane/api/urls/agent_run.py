# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.api.views import AgentRunDetailAPIEndpoint, AgentRunListCreateAPIEndpoint

urlpatterns = [
    path(
        "workspaces/<str:slug>/runs/",
        AgentRunListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="agent-runs",
    ),
    path(
        "workspaces/<str:slug>/runs/<uuid:run_id>/",
        AgentRunDetailAPIEndpoint.as_view(http_method_names=["get"]),
        name="agent-run-detail",
    ),
]
