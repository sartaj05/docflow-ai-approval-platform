from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.report_views import ReportAccessMixin
from apps.reports.services.report_helpers import export_risk_summary_to_csv


class RiskReportCSVAPIView(ReportAccessMixin, APIView):
    def get(self, request):
        queryset = self.get_queryset(request)
        if queryset is None:
            return Response({"detail": "You do not have access to reports."}, status=403)
        return export_risk_summary_to_csv(queryset)
