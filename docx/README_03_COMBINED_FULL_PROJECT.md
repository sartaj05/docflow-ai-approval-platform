# DocFlow AI - Combined Full Project README

## 1. Project Summary

DocFlow AI is a complete document approval automation SaaS. It combines Django backend, Django templates frontend, PostgreSQL database, document attachment management, audit logging, and FastAPI based AI document analysis.

The project is designed for offices, schools, hospitals, CA firms, agencies, local businesses, and internal organizations that need a structured approval workflow.

## 2. What the Project Solves

Many organizations still handle approvals using manual files, WhatsApp messages, emails, printed forms, or Excel trackers. This causes:

- Lost documents
- No clear approval status
- No audit history
- Manual follow-ups
- Delay in approvals
- No role based access
- No organization level data separation
- No risk or missing field detection

DocFlow AI solves this by providing:

- Digital approval requests
- Workflow based sequential approvals
- File upload and text extraction
- AI summary and risk placeholders
- Audit logs
- Role based dashboards
- Organization scoped SaaS design
- Super Admin platform dashboard

## 3. High Level Architecture

```text
Browser
  |
  | Django templates + Bootstrap + app.css/style.css
  v
Django Web Application
  |
  | PostgreSQL
  v
Database

Django Documents App
  |
  | extracted text
  v
FastAPI AI Service
  |
  | summary, category, risk, fields
  v
Django AI fields updated
```

## 4. Apps Included

```text
accounts       -> user, profile, role, auth
organizations  -> organization workspace
departments    -> organization departments
approvals      -> requests, workflows, steps, actions
documents      -> attachments, extraction, AI fields
audit          -> audit logs
dashboard      -> role dashboards
superadmin     -> custom platform management
```

## 5. User Roles

### Super Admin

Platform level owner. Has separate login. Does not need Django admin panel.

Can:

- View Super Admin dashboard
- View all organizations
- Activate/deactivate organizations
- View all users
- Activate/deactivate users
- View all approval requests
- View audit logs

### Organization Admin

Admin of one organization.

Can:

- Create departments
- Assign department heads
- Create workflows
- Add workflow steps
- View organization requests
- View audit logs
- Create approval requests

### Department Head

Head of a department.

Can:

- View department requests
- Participate in workflow approval
- View departments
- View workflows

### Staff

Normal employee/user.

Can:

- Create approval request
- Upload documents while draft
- Submit request
- Track own requests
- Cancel own request when allowed

### Approver

Approves assigned steps.

Can:

- View approval inbox
- Review assigned requests
- Add comment
- Approve step
- Reject request

### Auditor

Read-only compliance role.

Can:

- View organization requests
- View audit logs
- View auditor dashboard

## 6. Important URLs

```text
/                                   Public landing page
/accounts/login/                    Normal login
/accounts/super-login/              Super Admin login
/accounts/register-organization/    Organization registration
/accounts/profile/                  Profile
/dashboard/                         Role based dashboard redirect
/dashboard/super-admin/             Super Admin dashboard
/departments/                       Department list
/approvals/requests/                Approval request list
/approvals/inbox/                   Approval inbox
/approvals/workflows/               Workflow list
/documents/attachments/<id>/         Attachment detail
/audit/logs/                        Audit logs
/super-admin/organizations/          Platform organizations
/super-admin/users/                  Platform users
```

## 7. Database Models

### User and Profile

```text
User
UserProfile
```

User stores login identity. Profile stores organization, role, department, designation, and phone.

### Organization

```text
Organization
```

Tenant root. Every normal user belongs to one organization.

### Department

```text
Department
```

Belongs to organization. Can have a department head.

### Approval Models

```text
DocumentRequest
ApprovalWorkflow
ApprovalWorkflowStep
ApprovalStep
ApprovalAction
```

### Document Models

```text
DocumentAttachment
```

Stores uploaded files and AI fields.

### Audit Models

```text
AuditLog
```

Stores activity history.

## 8. Full Approval Lifecycle

```text
1. Staff creates request as Draft
2. Staff uploads documents
3. Staff submits request
4. System generates approval steps from selected workflow
5. First step becomes current
6. Assigned approver sees request in Approval Inbox
7. Approver comments, approves, or rejects
8. If approved, request moves to next step
9. If last step approved, request becomes Approved
10. If rejected, request becomes Rejected and remaining steps are skipped
11. Timeline records all actions
12. Audit log stores every important event
```

## 9. Document Lifecycle

```text
1. User opens draft request detail
2. User clicks Upload Documents
3. User selects one or multiple files
4. System validates file extension and size
5. File is saved as DocumentAttachment
6. If PDF, text is extracted
7. Audit log records upload
8. Attachment appears on request detail page
9. User can open attachment detail
10. User can delete attachment only while request is draft
```

## 10. AI Lifecycle

Current AI service supports:

- Amount extraction
- Date extraction
- Category detection
- Summary generation
- Missing field detection
- Risk level detection

AI response maps to Django fields:

```text
summary             -> ai_summary
category            -> ai_category
extracted_fields    -> ai_extracted_data
risk_level          -> risk_level
risk_notes          -> risk_notes
success             -> ai_processed
```

## 11. Audit Lifecycle

Audit logs are created for:

```text
Request created
Request updated
Request submitted
Request cancelled
Request deleted
Step approved
Step rejected
Step commented
Document uploaded
Document deleted
Department created
Department updated
Department deleted
Organization status changed
User status changed
```

Each audit log stores:

```text
organization
user
action
model_name
object_id
message
ip_address
user_agent
extra_data
created_at
```

## 12. Installation Summary

```bash
git clone <repo-url>
cd docflow_ai
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

FastAPI service:

```bash
cd docflow_ai_service
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

## 13. Environment Variables

```env
SECRET_KEY=django-insecure-docflow-ai-local-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_NAME=docflow_ai
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_HOST=localhost
DATABASE_PORT=5432
AI_SERVICE_URL=http://localhost:8001
AI_SERVICE_TIMEOUT=15
```

## 14. Production Notes

For production:

- Set `DEBUG=False`
- Use strong `SECRET_KEY`
- Configure real domain in `ALLOWED_HOSTS`
- Configure `CSRF_TRUSTED_ORIGINS`
- Use PostgreSQL
- Serve static files with WhiteNoise or Nginx
- Serve media securely
- Use HTTPS
- Use Gunicorn/Uvicorn
- Run FastAPI as separate service
- Add Celery worker if background AI processing is needed
- Add backups for database and media files

## 15. Current Project Completion Status

Completed till now:

```text
Accounts app
Organization app
Departments app
Approval request module
Document attachment module
Approval workflow module
Approve/reject/comment logic
Audit logging module
Dashboards
Super Admin custom dashboard
Templates and responsive CSS
FastAPI AI microservice base
```

Recommended next modules:

```text
Notification module
AI integration service inside Django
PDF approval certificate/report generation
Email notifications
Celery background AI processing
Advanced reports
User management inside organization dashboard
```
