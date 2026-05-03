from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.search_app.forms import GlobalSearchForm
from apps.search_app.services.search_engine import build_global_search_results


@login_required
def global_search(request):
    form = GlobalSearchForm(request.GET or None)

    results = {
        "query": "",
        "search_type": "all",
        "requests": [],
        "users": [],
        "departments": [],
        "documents": [],
        "audit_logs": [],
        "counts": {
            "requests": 0,
            "users": 0,
            "departments": 0,
            "documents": 0,
            "audit_logs": 0,
            "total": 0,
        },
    }

    if form.is_valid():
        results = build_global_search_results(
            user=request.user,
            cleaned_data=form.cleaned_data,
        )

    return render(
        request,
        "search_app/global_search.html",
        {
            "page_title": "Global Search",
            "form": form,
            "results": results,
        },
    )