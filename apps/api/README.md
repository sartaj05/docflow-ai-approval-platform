# DocFlow AI REST API

Base URL: /api/v1/

The API uses Django REST Framework and requires an authenticated user with an active account and organization. Request and attachment visibility follows the user's role and organization. Authentication supports sessions, HTTP Basic, and per-user API tokens. Use HTTPS for remote access. Create or rotate a token with POST /api/v1/auth/token/; revoke it with DELETE /api/v1/auth/token/. Send the returned value in the Authorization header as Token followed by the token.

The OpenAPI 3 schema is available at GET /api/v1/schema/. The version root at GET /api/v1/ lists the available resources.

Authenticated API users are limited to 120 requests per minute. Token issue and rotation requests are limited to 5 per hour.

## Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET, POST | /requests/ | List visible requests or create a draft |
| GET, PATCH | /requests/{id}/ | Read a request or edit the creator's draft |
| POST | /requests/{id}/submit/ | Submit a draft into its approval workflow |
| POST | /requests/{id}/cancel/ | Cancel an eligible request |
| GET | /requests/{id}/archive/ | Download the approved request's final ZIP archive |
| GET | /workflows/, /departments/ | List active organization options |
| GET | /inbox/ | List pending approval steps assigned to the user |
| POST | /inbox/bulk-action/ | Approve, reject, or comment on up to 100 assigned steps |
| POST | /approval-steps/{id}/approve/ | Approve an assigned step |
| POST | /approval-steps/{id}/reject/ | Reject an assigned step |
| POST | /approval-steps/{id}/comment/ | Comment on an assigned step |
| GET | /requests/{id}/timeline/ | Read activity history |
| POST | /requests/{id}/watch/ | Set watching to true or false |
| GET, POST | /requests/{id}/attachments/ | List or upload attachments |
| GET | /attachments/{id}/download/ | Download an authorized attachment |
| GET | /notifications/ | List notifications (status=all, read, or unread) |
| POST | /notifications/{id}/read/ | Mark one notification as read |
| POST | /notifications/read-all/ | Mark all notifications as read |
| GET, PATCH | /notifications/preferences/ | Read or update the user's preferences |
| POST, DELETE | /auth/token/ | Issue, rotate, or revoke the current user's API token |
| GET | /reports/summary/ | Read request, department, and risk summaries |
| GET | /reports/requests.csv | Export filtered requests to CSV |
| GET | /profile/ | Read the authenticated user's profile |
| PATCH | /profile/contact/ | Update the user's name, phone, or designation |
| GET | /search/ | Search authorized requests, users, departments, documents, and audit logs |
| GET | /search/suggestions/?q=... | Get request title or number suggestions |
| GET | /audit-logs/ | Browse organization audit events (organization admins and auditors) |
| GET | /requests/{id}/audit/ | Read audit events for an authorized request |
| GET | /requests/{id}/discussion/ | List request discussion threads |
| POST | /requests/{id}/discussion/comments/ | Add a discussion comment; message supports @username mentions |
| GET, POST | /requests/{id}/discussion/{comment_id}/replies/ | Read or add replies to a comment |
| POST | /requests/{id}/discussion/{comment_id}/delete/ | Soft-delete your own comment (or an org admin can remove it) |
| GET | /delegations/ | List organization approval delegations |
| POST | /delegations/create/ | Create a delegation using eligible organization users and a valid date range |
| POST | /delegations/{id}/deactivate/ | Deactivate a delegation as its delegator or an org admin |
| GET | /delegation-candidates/ | List eligible users for approval delegation |
| GET | /policies/ | Read organization approval policy rules |
| GET | /policy-evaluations/ | Read paginated policy evaluation history; optional request_id filter |
| GET | /requests/{id}/watchers/ | List active watchers on an authorized request |
| GET, PATCH | /requests/{id}/watch/preferences/ | Read or update your watcher notification settings |
| GET | /requests/{id}/certificate/ | Read the approved request's certificate metadata |
| GET | /requests/{id}/certificate.pdf/ | Download the approved request's certificate |

Request lists accept status, category, priority, q, date_from, and date_to filters. Results are paginated with page and page_size; page_size is capped at 100.

Draft creation accepts JSON fields title, category, priority, description, department, and workflow. File uploads use multipart/form-data with the file field. Rejections require a non-empty comment.
