from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace
from apps.search_app.forms import GlobalSearchForm
from apps.search_app.services.search_engine import build_global_search_results


class GlobalSearchAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        form = GlobalSearchForm(request.query_params)
        if not form.is_valid():
            return Response({"detail": "Invalid search filters.", "errors": form.errors}, status=400)
        results = build_global_search_results(request.user, form.cleaned_data)
        results["requests"] = [{
            "id": item.pk,
            "request_number": item.request_number,
            "title": item.title,
            "status": item.status,
            "risk_level": item.risk_level,
            "department": item.department.name if item.department_id else None,
            "created_at": item.created_at.isoformat(),
        } for item in results["requests"]]
        results["users"] = [{
            "id": item.pk,
            "username": item.get_username(),
            "name": item.display_name,
            "department": item.profile.department.name if getattr(item, "profile", None) and item.profile.department_id else None,
        } for item in results["users"]]
        results["departments"] = [{
            "id": item.pk,
            "name": item.name,
            "head": item.head.display_name if item.head_id else None,
        } for item in results["departments"]]
        results["documents"] = [{
            "id": item.pk,
            "filename": item.original_filename,
            "request_id": item.request_id,
            "request_number": item.request.request_number,
            "file_type": item.file_type,
            "created_at": item.created_at.isoformat(),
        } for item in results["documents"]]
        results["audit_logs"] = [{
            "id": item.pk,
            "action": item.action,
            "model_name": item.model_name,
            "object_id": item.object_id,
            "message": item.message,
            "created_at": item.created_at.isoformat(),
        } for item in results["audit_logs"]]
        return Response(results)
