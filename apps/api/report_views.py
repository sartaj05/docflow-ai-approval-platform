from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasActiveWorkspace
from apps.reports.services.report_helpers import (
    apply_report_filters,
    build_report_summary,
    can_view_reports,
    export_requests_to_csv,
    get_department_summary,
    get_report_queryset,
    get_risk_summary,
)


class ReportAccessMixin:
    permission_classes = [IsAuthenticated, HasActiveWorkspace]

    def get_queryset(self, request):
        if not can_view_reports(request.user):
            return None
        return apply_report_filters(get_report_queryset(request.user), request)


class ReportSummaryView(ReportAccessMixin, APIView):
    def get(self, request):
        queryset = self.get_queryset(request)
        if queryset is None:
            return Response({"detail": "You do not have access to reports."}, status=403)
        return Response({
            "summary": build_report_summary(queryset),
            "departments": list(get_department_summary(queryset)),
            "risk_levels": list(get_risk_summary(queryset)),
        })


class RequestReportCSVView(ReportAccessMixin, APIView):
    def get(self, request):
        queryset = self.get_queryset(request)
        if queryset is None:
            return Response({"detail": "You do not have access to reports."}, status=403)
        return export_requests_to_csv(queryset)
