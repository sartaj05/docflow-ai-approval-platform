from django import forms


class GlobalSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control search-input",
                "placeholder": "Search requests, users, departments, documents, audit logs...",
                "autocomplete": "off",
            }
        ),
    )

    search_type = forms.ChoiceField(
        required=False,
        choices=[
            ("all", "All Modules"),
            ("requests", "Requests"),
            ("users", "Users"),
            ("departments", "Departments"),
            ("documents", "Documents"),
            ("audit", "Audit Logs"),
        ],
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    status = forms.ChoiceField(
        required=False,
        choices=[
            ("", "All Status"),
            ("DRAFT", "Draft"),
            ("SUBMITTED", "Submitted"),
            ("IN_REVIEW", "In Review"),
            ("APPROVED", "Approved"),
            ("REJECTED", "Rejected"),
            ("CANCELLED", "Cancelled"),
        ],
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    risk_level = forms.ChoiceField(
        required=False,
        choices=[
            ("", "All Risk Levels"),
            ("LOW", "Low"),
            ("MEDIUM", "Medium"),
            ("HIGH", "High"),
        ],
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )