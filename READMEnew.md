# DocFlow AI — Smart Document Approval & Workflow Automation SaaS

DocFlow AI is a Django-based document approval automation platform designed for offices, schools, hospitals, CA firms, agencies, local businesses, and organizations that need structured approval workflows.

The system allows users to create approval requests, upload documents, extract PDF/OCR text, run AI-based document analysis, route requests through workflows, approve/reject requests, maintain audit logs, generate reports, and manage organization users.

---

## Main Purpose

The purpose of DocFlow AI is to reduce manual approval work by digitizing:

- Document submission
- Department-based approval
- Multi-step approval workflows
- AI document summary and risk analysis
- Document upload and versioning
- OCR text extraction
- Approval reminders
- Audit trail
- Reports and PDF certificates

---

## Main Features

### 1. Organization Management

- Platform Super Admin can view all organizations.
- Super Admin can activate/deactivate organizations.
- Each organization has its own users, departments, workflows, requests, and audit logs.
- Organization data is isolated from other organizations.

### 2. User Management

Organization Admin can manage users inside their organization:

- Create users
- Assign roles
- Assign departments
- Activate/deactivate users
- Reset passwords
- Filter users

Supported roles:

- Super Admin
- Organization Admin
- Department Head
- Staff
- Approver
- Auditor

### 3. Department Management

Organization Admin can:

- Create departments
- Edit departments
- Assign department heads
- Activate/deactivate departments
- View users under departments

Departments are used for request routing and workflow assignment.

### 4. Approval Requests

Users can create document approval requests with:

- Title
- Description
- Department
- Category
- Priority
- Workflow
- Supporting documents

Requests start as Draft and can later be submitted for approval.

### 5. Document Upload

Users can upload multiple documents:

- PDF
- JPG
- JPEG
- PNG
- DOC
- DOCX

Uploaded documents are attached to approval requests.

### 6. PDF Text Extraction

For text-based PDFs, the system extracts readable text automatically.

### 7. OCR Support

For scanned PDFs and images, the system supports OCR fallback.

OCR features:

- Scanned PDF OCR
- Image OCR
- OCR confidence score
- Low confidence detection
- Manual text correction

### 8. AI Processing

Uploaded document text is sent to the AI service for:

- Summary generation
- Category detection
- Amount extraction
- Date extraction
- Risk detection
- Missing field detection

AI results are saved in both document and request records.

### 9. Workflow Management

Organization Admin can create approval workflows.

Each workflow can have multiple steps:

- Step order
- Required role
- Fixed approver
- Department-based approver
- SLA hours
- Final step marking

### 10. Approval Actions

Approvers can:

- Approve current step
- Reject request
- Add comment
- View assigned approval inbox
- Send reminders

The request moves step-by-step until final approval or rejection.

### 11. Approval Policies / Rules Engine

The policy engine supports:

- Amount-based routing
- Category-based workflow selection
- Priority auto-update
- Risk-level rules
- Dynamic approver assignment

### 12. Delegation

Users can delegate approvals during leave or vacation.

Delegation supports:

- Delegator
- Delegate user
- Date range
- Reason
- Active/inactive status

### 13. SLA and Escalation

Approval steps support:

- Due date
- SLA hours
- Overdue detection
- Reminder notifications
- Escalation tracking

### 14. Notifications

The system supports in-app notifications for:

- Approval assignment
- Request approved
- Request rejected
- Request commented
- Document uploaded
- Workflow updates

### 15. Email Notifications

SMTP email notification support includes:

- Approval assignment email
- Approval/rejection result email
- Daily pending approval summary
- Celery task support

### 16. Reports

Reports module includes:

- Approval request reports
- Department-wise reports
- Risk-level reports
- CSV export
- PDF export
- Printable approval summary

### 17. PDF Generation

The system supports:

- Request summary PDF
- Approval certificate PDF
- Organization logo/header
- Watermark
- QR verification code
- Download buttons

### 18. Audit Logging

Important actions are logged:

- Request created
- Request updated
- Request submitted
- Request approved
- Request rejected
- Document uploaded
- Document deleted
- Document replaced
- OCR correction
- User changes
- Workflow changes
- Policy changes

Audit logs include:

- User
- Organization
- IP address
- User agent
- Action
- Model name
- Object ID
- Message
- Extra data
- Timestamp

---

## Technology Stack

### Backend

- Python
- Django
- Django Templates
- Django ORM
- PostgreSQL
- Django Admin
- Celery
- Redis
- Django Celery Beat

### AI Service

- FastAPI
- PyMuPDF
- Regex-based extraction
- Risk detection
- Summary generation
- OCR support with Tesseract

### Frontend

- HTML
- CSS
- Bootstrap
- Responsive sidebar
- Django templates

### Document Processing

- PyMuPDF
- Tesseract OCR
- pdf2image
- Pillow

### Deployment Ready Features

- Environment-based settings
- Static/media settings
- SMTP settings
- Redis/Celery support
- PostgreSQL database
- Whitenoise static serving

---

## Main Project Flow

1. Super Admin manages organizations.
2. Organization Admin creates departments.
3. Organization Admin creates users.
4. Organization Admin creates approval workflows.
5. Organization Admin creates approval policies.
6. Staff creates approval request.
7. Staff uploads documents.
8. System extracts text using PDF extraction or OCR.
9. System sends extracted text to AI service.
10. AI returns summary, category, extracted fields, and risk.
11. User submits the request.
12. Workflow steps are generated.
13. First approver receives notification.
14. Approver approves, rejects, or comments.
15. Request moves to next approver.
16. Final approver approves the request.
17. Request becomes approved.
18. PDF certificate/report can be generated.
19. Audit log stores full activity history.

---

## Project Advantage

DocFlow AI helps organizations:

- Reduce paperwork
- Improve approval speed
- Track every approval
- Avoid lost documents
- Maintain audit trails
- Identify document risks
- Automate routing
- Improve transparency
- Generate reports quickly
- Build a professional digital approval system

---

## Current Status

The project currently includes core SaaS approval automation features and is ready for further polishing, testing, and production hardening.

Future improvements can include:

- Advanced AI integration with LLMs
- Better OCR accuracy
- Full dashboard charts
- Real-time notifications
- Mobile app
- Advanced role permission system
- E-signature
- Payment approval integrations
- Cloud deployment