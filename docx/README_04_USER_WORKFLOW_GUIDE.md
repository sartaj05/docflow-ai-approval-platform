# DocFlow AI - User Workflow Guide

## 1. Purpose

This README explains how users operate DocFlow AI from registration to final approval. It is written for Super Admin, Organization Admin, Staff, Department Head, Approver, and Auditor.

## 2. Complete User Flow

```text
Super Admin creates/monitors platform
Organization registers workspace
Organization Admin logs in
Organization Admin creates departments
Organization Admin creates workflows
Staff creates approval request
Staff uploads documents
Staff submits request
System generates approval steps
Approver reviews request
Approver approves/rejects/comments
Final request status is updated
Auditor reviews history and audit logs
```

## 3. Super Admin Workflow

### 3.1 Login

Super Admin uses separate login page:

```text
/accounts/super-login/
```

After login, Super Admin goes to:

```text
/dashboard/super-admin/
```

Super Admin should not need Django admin panel for daily work.

### 3.2 Super Admin Dashboard

Super Admin dashboard shows:

- Total organizations
- Active organizations
- Inactive organizations
- Total users
- Organization admins
- Total departments
- Total requests
- Pending requests
- Approved requests
- Recent organizations
- Recent users
- Recent requests
- Recent audit activity

### 3.3 Manage Organizations

URL:

```text
/super-admin/organizations/
```

Super Admin can:

- Search organizations
- Filter active/inactive
- Open organization detail
- Activate organization
- Deactivate organization

### 3.4 Manage Users

URL:

```text
/super-admin/users/
```

Super Admin can:

- Search users
- Filter by role
- Filter by status
- Activate user
- Deactivate user

Super Admin cannot deactivate own account.

## 4. Organization Registration Workflow

Public URL:

```text
/accounts/register-organization/
```

Organization registration creates:

- Organization record
- First organization admin user
- User profile connected to organization

After registration, Organization Admin can login from:

```text
/accounts/login/
```

## 5. Organization Admin Workflow

### 5.1 Login

URL:

```text
/accounts/login/
```

After login, Organization Admin redirects to Organization Admin dashboard.

### 5.2 Create Departments

URL:

```text
/departments/
```

Steps:

1. Click `+ Create Department`.
2. Enter department name.
3. Add description.
4. Select department head if available.
5. Keep department active.
6. Save.

Rules:

- Department belongs only to logged-in organization.
- Department name cannot duplicate inside same organization.
- Department head selection shows only active users from the organization.
- Selected head profile becomes Department Head.

### 5.3 Create Workflows

URL:

```text
/approvals/workflows/
```

Steps:

1. Click `+ Create Workflow`.
2. Add workflow name.
3. Select category.
4. Add description.
5. Keep active.
6. Save.
7. Open workflow detail.
8. Add workflow steps.

### 5.4 Add Workflow Steps

Steps:

1. Click `+ Add Step`.
2. Enter step order.
3. Select required role.
4. Optional: select fixed approver.
5. Optional: enable department-based assignment.
6. Optional: mark final step.
7. Save.

Assignment logic:

```text
Fixed approver has highest priority.
Department-based assignment uses request department head.
If both are empty, system assigns by required role.
If no user is found, organization admin is fallback.
```

Do not select fixed approver and department-based assignment together.

## 6. Staff Request Creation Workflow

### 6.1 Create Request

URL:

```text
/approvals/requests/create/
```

Steps:

1. Select department.
2. Select approval workflow.
3. Enter title.
4. Select category.
5. Select priority.
6. Enter description.
7. Save as draft.

Request status becomes:

```text
DRAFT
```

### 6.2 Upload Documents

From request detail page, click:

```text
Upload Documents
```

Allowed files:

```text
PDF, JPG, JPEG, PNG, DOC, DOCX
```

Rules:

- Upload allowed only while request is draft.
- Multiple files can be uploaded.
- PDF text extraction runs automatically.
- Upload creates audit log.

### 6.3 Edit Draft

Staff can edit request while status is:

```text
DRAFT
```

After submission, request becomes locked for editing.

### 6.4 Submit Request

Click:

```text
Submit Request
```

System checks:

- Request is draft
- Request has workflow
- Workflow has steps

After submission:

```text
Request status -> IN_REVIEW
Approval steps generated
First step -> current pending
Audit log created
Request timeline updated
```

## 7. Approver Workflow

### 7.1 Approval Inbox

URL:

```text
/approvals/inbox/
```

Approver sees only current pending steps assigned to them.

Inbox shows:

- Request number
- Title
- Department
- Priority
- Current step
- Created by
- Review button
- Approve button
- Reject button

### 7.2 Review Request

Click `Review` to open request detail.

Approver can see:

- Request information
- Attached documents
- Extracted PDF text
- Workflow timeline
- AI placeholder data
- Meta details
- Timeline actions

### 7.3 Add Comment

If request is assigned to approver, an action box appears:

```text
Your Approval Action
```

Approver can add a comment without approving/rejecting.

This creates:

```text
ApprovalAction COMMENTED
AuditLog COMMENTED
```

### 7.4 Approve Step

Approver submits approval comment optional.

System does:

```text
Current step -> APPROVED
If next step exists -> next step becomes current
If no next step -> request becomes APPROVED
Timeline updated
Audit log created
```

### 7.5 Reject Request

Approver must enter rejection reason.

System does:

```text
Current step -> REJECTED
Remaining pending steps -> SKIPPED
Request -> REJECTED
Timeline updated
Audit log created
```

## 8. Department Head Workflow

Department Head can be part of approval workflows.

If workflow step is department-based:

```text
System assigns request department head
```

Department Head can:

- View department requests
- Open approval inbox if assigned
- Review request
- Approve/reject/comment

## 9. Auditor Workflow

Auditor logs in and opens Auditor Dashboard.

Auditor can:

- View total requests
- View approved/rejected counts
- View recent requests
- View recent audit logs
- Open audit log list
- Open audit log detail

Auditor should not modify approvals.

## 10. Request Status Meaning

```text
DRAFT       -> Created but not submitted
SUBMITTED   -> Submitted and waiting workflow generation or transition
IN_REVIEW   -> Approval steps are active
APPROVED    -> All required steps approved
REJECTED    -> One approver rejected
CANCELLED   -> Request creator cancelled request
```

## 11. Approval Step Status Meaning

```text
PENDING     -> Waiting approval
APPROVED    -> Step approved
REJECTED    -> Step rejected
SKIPPED     -> Step skipped after rejection
```

## 12. Priority Meaning

```text
LOW
MEDIUM
HIGH
URGENT
```

Urgent and High priority requests should be reviewed first.

## 13. Risk Meaning

AI risk values:

```text
LOW       -> No major risk found
MEDIUM    -> Missing fields or some warning notes
HIGH      -> Multiple missing fields or suspicious indicators
```

Current AI logic is rule based and can be improved later with LLM or ML models.

## 14. Audit Log Usage

Audit logs show:

- Who performed action
- Which organization
- What action
- Which model/object
- IP address
- User-agent
- Extra metadata
- Timestamp

Audit logs are important for compliance and debugging.

## 15. Full Example Scenario

### Step A: Setup

1. Super Admin logs in.
2. Organization registers or exists.
3. Organization Admin logs in.
4. Organization Admin creates Finance Department.
5. Organization Admin assigns a Department Head.
6. Organization Admin creates workflow `Vendor Payment Approval`.
7. Organization Admin adds:
   - Step 1: Department-based Department Head
   - Step 2: Fixed Approver Finance Manager
   - Step 3: Org Admin final step

### Step B: Staff Request

1. Staff logs in.
2. Staff creates request `Vendor invoice payment for ABC Traders`.
3. Staff selects Finance Department.
4. Staff selects Vendor Payment workflow.
5. Staff uploads invoice PDF.
6. PDF text extraction stores extracted text.
7. Staff submits request.

### Step C: Approval

1. Department Head sees request in inbox.
2. Department Head approves.
3. Finance Manager becomes current approver.
4. Finance Manager adds comment and approves.
5. Org Admin becomes final approver.
6. Org Admin approves.
7. Request status becomes Approved.

### Step D: Audit

Auditor opens audit logs and sees:

```text
Request created
Document uploaded
Request submitted
Step 1 approved
Step 2 commented
Step 2 approved
Step 3 approved
Request finally approved
```

## 16. User Mistake Handling

### User selected wrong workflow

Allowed only while draft. Edit request and change workflow.

### User uploaded wrong document

Allowed only while draft. Delete attachment and upload correct file.

### Request already submitted

Request is locked. User can cancel if allowed.

### Approver rejected by mistake

Current system marks request rejected. Future feature can add reopen/resubmit.

### No approver assigned

Check workflow step assignment logic and organization users.
