from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace


def operation(summary, description, status="200", parameters=None, request_body=None):
    result = {
        "summary": summary,
        "responses": {status: {"description": description}},
    }
    if parameters:
        result["parameters"] = parameters
    if request_body:
        result["requestBody"] = request_body
    return result


def path_parameter(name):
    return {
        "name": name,
        "in": "path",
        "required": True,
        "schema": {"type": "integer"},
    }


class OpenAPISchemaView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        request_filters = [
            {"name": "status", "in": "query", "schema": {"type": "string"}},
            {"name": "category", "in": "query", "schema": {"type": "string"}},
            {"name": "priority", "in": "query", "schema": {"type": "string"}},
            {"name": "q", "in": "query", "schema": {"type": "string"}},
            {"name": "date_from", "in": "query", "schema": {"type": "string", "format": "date"}},
            {"name": "date_to", "in": "query", "schema": {"type": "string", "format": "date"}},
            {"name": "page", "in": "query", "schema": {"type": "integer"}},
            {"name": "page_size", "in": "query", "schema": {"type": "integer", "maximum": 100}},
        ]
        request_body = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["title"],
                        "properties": {
                            "title": {"type": "string"},
                            "category": {"type": "string"},
                            "priority": {"type": "string"},
                            "description": {"type": "string"},
                            "department": {"type": "integer", "nullable": True},
                            "workflow": {"type": "integer", "nullable": True},
                        },
                    },
                },
            },
        }
        upload_body = {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["file"],
                        "properties": {
                            "file": {"type": "string", "format": "binary"},
                        },
                    },
                },
            },
        }
        paths = {
            "/": {
                "get": operation("List API resources", "Resource links."),
            },
            "/requests/": {
                "get": operation(
                    "List requests visible to the current user",
                    "Paginated request results.",
                    parameters=request_filters,
                ),
                "post": operation(
                    "Create a request draft",
                    "Draft created or validation errors returned.",
                    status="201",
                    request_body=request_body,
                ),
            },
            "/requests/{id}/": {
                "parameters": [path_parameter("id")],
                "get": operation("Get request details", "Request details."),
                "patch": operation("Edit the creator's draft", "Updated request."),
            },
            "/requests/{id}/submit/": {
                "parameters": [path_parameter("id")],
                "post": operation("Submit a draft into its approval workflow", "Submitted request."),
            },
            "/requests/{id}/cancel/": {
                "parameters": [path_parameter("id")],
                "post": operation("Cancel an eligible request", "Cancelled request."),
            },
            "/requests/{id}/archive/": {
                "parameters": [path_parameter("id")],
                "get": operation(
                    "Download the final archive for an approved request",
                    "ZIP archive with request history and documents.",
                ),
            },
            "/workflows/": {
                "get": operation("List active organization workflows", "Workflow options."),
            },
            "/departments/": {
                "get": operation("List active organization departments", "Department options."),
            },
            "/inbox/": {
                "get": operation("List pending steps assigned to the current user", "Approval inbox."),
            },
            "/inbox/bulk-action/": {
                "post": operation(
                    "Bulk approve, reject, or comment on assigned steps",
                    "Counts and per-step errors.",
                ),
            },
            "/approval-steps/{step_pk}/approve/": {
                "parameters": [path_parameter("step_pk")],
                "post": operation("Approve an assigned step", "Approval result."),
            },
            "/approval-steps/{step_pk}/reject/": {
                "parameters": [path_parameter("step_pk")],
                "post": operation("Reject an assigned step", "Rejection result."),
            },
            "/approval-steps/{step_pk}/comment/": {
                "parameters": [path_parameter("step_pk")],
                "post": operation("Comment on an assigned step", "Comment result."),
            },
            "/requests/{id}/timeline/": {
                "parameters": [path_parameter("id")],
                "get": operation("Get request activity history", "Timeline items."),
            },
            "/requests/{id}/watch/": {
                "parameters": [path_parameter("id")],
                "post": operation("Set whether the current user watches a request", "Watcher state."),
            },
            "/requests/{request_pk}/attachments/": {
                "parameters": [path_parameter("request_pk")],
                "get": operation("List request attachments", "Attachment metadata."),
                "post": operation(
                    "Upload a file to the creator's draft",
                    "Uploaded attachment.",
                    status="201",
                    request_body=upload_body,
                ),
            },
            "/attachments/{attachment_pk}/download/": {
                "parameters": [path_parameter("attachment_pk")],
                "get": operation("Download an authorized attachment", "File content."),
            },
            "/notifications/": {
                "get": operation("List current user's notifications", "Notification results."),
            },
            "/notifications/{notification_pk}/read/": {
                "parameters": [path_parameter("notification_pk")],
                "post": operation("Mark a notification as read", "Updated notification."),
            },
            "/notifications/read-all/": {
                "post": operation("Mark all current user's notifications as read", "Number marked read."),
            },
            "/notifications/preferences/": {
                "get": operation("Get notification preferences", "Current preferences."),
                "patch": operation("Update notification preferences", "Saved preferences."),
            },
            "/reports/summary/": {
                "get": operation(
                    "Get request, department, and risk summaries",
                    "Aggregated report data for the user's permitted scope.",
                ),
            },
            "/reports/requests.csv": {
                "get": operation(
                    "Export filtered requests as CSV",
                    "CSV file containing requests in the user's permitted scope.",
                ),
            },
            "/auth/token/": {
                "post": operation(
                    "Issue or rotate the current user's API token",
                    "New token secret.",
                    status="201",
                ),
                "delete": operation(
                    "Revoke the current user's API token",
                    "Token revocation result.",
                ),
            },
        }
        schema = {
            "openapi": "3.0.3",
            "info": {
                "title": "DocFlow AI API",
                "version": "1.0.0",
                "description": "Authenticated, organization-scoped document approval API.",
            },
            "servers": [{"url": request.build_absolute_uri("/api/v1/")}],
            "security": [{"basicAuth": []}, {"sessionAuth": []}],
            "paths": paths,
            "components": {
                "securitySchemes": {
                    "basicAuth": {"type": "http", "scheme": "basic"},
                    "sessionAuth": {"type": "apiKey", "in": "cookie", "name": "sessionid"},
                    "tokenAuth": {"type": "apiKey", "in": "header", "name": "Authorization"},
                },
            },
        }
        return Response(schema)
