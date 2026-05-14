from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace, scoped_requests


class RequestSearchSuggestionsView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response({"suggestions": []})
        matches = scoped_requests(request.user).filter(Q(title__icontains=query))
        if query.upper().startswith("REQ-") and query.split("-")[-1].isdigit():
            matches = matches | scoped_requests(request.user).filter(pk=int(query.split("-")[-1]))
        matches = matches.order_by("-created_at").distinct()[:8]
        return Response({"suggestions": [{
            "id": item.pk,
            "request_number": item.request_number,
            "title": item.title,
            "status": item.status,
        } for item in matches]})
