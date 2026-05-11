from django.urls import path

from apps.api.report_views import ReportSummaryView, RequestReportCSVView


urlpatterns = [
    path("reports/summary/", ReportSummaryView.as_view(), name="report-summary"),
    path("reports/requests.csv", RequestReportCSVView.as_view(), name="report-requests-csv"),
]
