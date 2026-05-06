# DocFlow AI REST API

Base URL: /api/v1/

The API uses Django REST Framework and requires an authenticated user with an active account and organization. Request and attachment visibility follows the user's role and organization. The configured DRF authentication methods are session authentication and HTTP Basic authentication. Use HTTPS for remote access.

The OpenAPI 3 schema is available at GET /api/v1/schema/. The version root at GET /api/v1/ lists the available resources.

## Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET, POST | /requests/ | List visible requests or create a draft |
| GET, PATCH | /requests/{id}/ | Read a request or edit the creator's draft |
| POST | /requests/{id}/submit/ | Submit a draft into its approval workflow |
| POST | /requests/{id}/cancel/ | Cancel an eligible request |
| GET | /workflows/, /departments/ | List active organization options |
| GET | /inbox/ | List pending approval steps assigned to the user |
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

Request lists accept status, category, priority, q, date_from, and date_to filters. Results are paginated with page and page_size; page_size is capped at 100.

Draft creation accepts JSON fields title, category, priority, description, department, and workflow. File uploads use multipart/form-data with the file field. Rejections require a non-empty comment.
