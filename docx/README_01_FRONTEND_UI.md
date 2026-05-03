# DocFlow AI - Frontend and UI README

## 1. Frontend Overview

DocFlow AI uses Django templates with Bootstrap 5 and custom CSS. The frontend is not a separate React/Vue app. All pages are rendered from Django templates and styled using two main CSS files:

```text
static/css/app.css      # Auth pages, dashboards, internal app pages
static/css/style.css    # Public landing page
```

The frontend layout is designed around a SaaS dashboard experience with:

- Fixed desktop sidebar
- Responsive mobile drawer sidebar
- Sticky topbar
- Dashboard cards
- Modern tables
- Workflow timelines
- Audit timelines
- Upload panels
- Empty states
- Role based menu visibility
- Super Admin separate dashboard

## 2. Main Template Structure

Recommended template structure:

```text
templates/
├── base.html
├── landing.html
├── accounts/
│   ├── login.html
│   ├── super_admin_login.html
│   ├── register_organization.html
│   └── profile.html
├── dashboard/
│   ├── super_admin_dashboard.html
│   ├── organization_admin_dashboard.html
│   ├── department_head_dashboard.html
│   ├── staff_dashboard.html
│   ├── approver_dashboard.html
│   ├── auditor_dashboard.html
│   └── partials/
│       └── request_table.html
├── departments/
│   ├── department_list.html
│   ├── department_detail.html
│   ├── department_form.html
│   ├── department_users.html
│   └── department_confirm_delete.html
├── approvals/
│   ├── request_list.html
│   ├── request_form.html
│   ├── request_detail.html
│   ├── request_confirm_delete.html
│   ├── approval_inbox.html
│   ├── workflow_list.html
│   ├── workflow_form.html
│   ├── workflow_detail.html
│   ├── workflow_confirm_delete.html
│   ├── workflow_step_form.html
│   └── workflow_step_confirm_delete.html
├── documents/
│   ├── attachment_upload.html
│   ├── attachment_detail.html
│   └── attachment_confirm_delete.html
├── audit/
│   ├── audit_log_list.html
│   └── audit_log_detail.html
└── superadmin/
    ├── organization_list.html
    ├── organization_detail.html
    └── user_list.html
```

## 3. `base.html` Purpose

`base.html` is the master layout for authenticated pages. It contains:

- Sidebar navigation
- Mobile hamburger menu
- Sidebar overlay for mobile
- Sticky topbar
- User profile pill
- Logout button
- Messages block
- `{% block content %}` for page content

Role based menus:

### Super Admin Sidebar

```text
Super Dashboard
Organizations
Platform Users
All Requests
Audit Logs
Profile
```

### Organization Users Sidebar

```text
Dashboard
Requests
Approval Inbox
Departments
Workflows
Audit Logs
Profile
```

Menu visibility depends on user role. For example, audit logs should be visible mainly to Organization Admin and Auditor.

## 4. Public Landing Page

`landing.html` is a separate public page. It uses:

```text
static/css/style.css
```

It should contain:

- Navbar
- Login link
- Register Organization link
- Hero section
- Product benefits
- Approval flow card
- Best-for badges

Recommended public flow:

```text
/                       -> landing.html
/accounts/login/        -> normal user login
/accounts/super-login/  -> Super Admin login
/accounts/register-organization/ -> organization signup
```

## 5. Dashboard Pages

Each role has its own dashboard template.

### Super Admin Dashboard

Shows platform wide data:

- Total organizations
- Active/inactive organizations
- Total users
- Organization admins
- Total departments
- Total requests
- Pending requests
- Approved requests
- Recent organizations
- Recent users
- Recent approval requests
- Recent audit logs

### Organization Admin Dashboard

Shows organization scoped data:

- Total requests
- Draft requests
- Pending requests
- Approved requests
- Rejected requests
- Recent requests

### Department Head Dashboard

Shows department scoped requests.

### Staff Dashboard

Shows requests created by logged-in staff user.

### Approver Dashboard

Shows assigned approval steps:

- Assigned approvals
- Urgent approvals
- Approval history
- Recent assigned requests

### Auditor Dashboard

Shows organization wide audit and approval overview.

## 6. Frontend Components

The CSS defines reusable components:

```text
.page-header
.eyebrow
.page-subtitle
.stats-grid
.metric-card
.metric-icon
.panel-card
.panel-card-header
.help-card
.modern-table
.status-badge
.info-list
.empty-state
.workflow-timeline
.action-timeline
.upload-box
.extracted-text-box
.audit-message-box
.audit-json-box
```

Use these classes consistently across all new templates.

## 7. Status Badge Mapping

Use these classes:

```text
.status-draft      -> Draft, Pending, Cancelled
.status-submitted  -> Submitted, Medium, Commented
.status-review     -> In Review, High, Status Changed
.status-approved   -> Approved, Active, Low Risk
.status-rejected   -> Rejected, Inactive, Urgent, High Risk
```

## 8. Responsive Design

The project supports:

- Desktop fixed sidebar
- Tablet/mobile drawer sidebar
- Mobile overlay
- Scrollable tables
- Stacked cards
- Full width buttons on small screens
- Compact timelines

Important frontend rule:

Do not hide the sidebar permanently on mobile. Instead, convert it into a drawer using:

```text
.sidebar.show
.mobile-overlay.show
.mobile-menu-btn
.sidebar-close-btn
```

## 9. Frontend Testing Checklist

Use this checklist after updating templates:

- Login page opens correctly
- Super Admin login redirects to Super Admin dashboard
- Normal user login redirects by role
- Sidebar links do not break
- Mobile hamburger opens sidebar
- Escape key closes sidebar
- Tables scroll horizontally on mobile
- Dashboard cards stack properly
- Request detail page shows action box for assigned approver
- Audit logs page opens
- Document upload page is responsive
- Workflow builder pages are responsive
- Logout works

## 10. Common Frontend Problems

### Sidebar not showing on mobile

Make sure `base.html` contains:

```html
<button type="button" class="mobile-menu-btn" id="mobileMenuBtn">☰</button>
```

and `app.css` contains mobile drawer rules.

### Old CSS still showing

Run:

```bash
python manage.py collectstatic
```

Then hard refresh browser:

```text
Ctrl + F5
```

### Broken URL in template

Check the URL name in the corresponding app `urls.py`.

Example:

```django
{% url 'approvals:request_detail' item.pk %}
```

requires:

```python
app_name = "approvals"
path("requests/<int:pk>/", views.request_detail, name="request_detail")
```
