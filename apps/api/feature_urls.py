from django.urls import path

from apps.api.audit_feed_view import AuditFeedView
from apps.api.certificate_download_view import RequestCertificateDownloadAPIView
from apps.api.certificate_metadata_view import RequestCertificateMetadataAPIView
from apps.api.delegation_candidates_view import DelegationCandidatesAPIView
from apps.api.delegation_create_view import DelegationCreateAPIView
from apps.api.delegation_deactivate_view import DelegationDeactivateAPIView
from apps.api.delegation_list_view import DelegationListAPIView
from apps.api.discussion_create_view import RequestDiscussionCreateView
from apps.api.discussion_delete_view import RequestDiscussionDeleteView
from apps.api.discussion_list_view import RequestDiscussionListView
from apps.api.discussion_reply_view import RequestDiscussionReplyView
from apps.api.global_search_view import GlobalSearchAPIView
from apps.api.policy_catalog_view import PolicyCatalogAPIView
from apps.api.policy_evaluations_view import PolicyEvaluationHistoryAPIView
from apps.api.profile_read_view import CurrentProfileView
from apps.api.profile_update_view import CurrentProfileUpdateView
from apps.api.request_audit_view import RequestAuditHistoryView
from apps.api.request_watch_preferences_view import RequestWatchPreferencesAPIView
from apps.api.request_watchers_view import RequestWatchersAPIView
from apps.api.search_suggestions_view import RequestSearchSuggestionsView


urlpatterns = [
    path("profile/", CurrentProfileView.as_view(), name="current-profile"),
    path("profile/contact/", CurrentProfileUpdateView.as_view(), name="current-profile-update"),
    path("search/", GlobalSearchAPIView.as_view(), name="global-search"),
    path("search/suggestions/", RequestSearchSuggestionsView.as_view(), name="request-search-suggestions"),
    path("audit-logs/", AuditFeedView.as_view(), name="audit-feed"),
    path("requests/<int:pk>/audit/", RequestAuditHistoryView.as_view(), name="request-audit-history"),
    path("requests/<int:pk>/discussion/", RequestDiscussionListView.as_view(), name="request-discussion-list"),
    path("requests/<int:pk>/discussion/comments/", RequestDiscussionCreateView.as_view(), name="request-discussion-create"),
    path("requests/<int:pk>/discussion/<int:comment_pk>/replies/", RequestDiscussionReplyView.as_view(), name="request-discussion-replies"),
    path("requests/<int:pk>/discussion/<int:comment_pk>/delete/", RequestDiscussionDeleteView.as_view(), name="request-discussion-delete"),
    path("delegations/", DelegationListAPIView.as_view(), name="delegation-list-api"),
    path("delegations/create/", DelegationCreateAPIView.as_view(), name="delegation-create-api"),
    path("delegations/<int:pk>/deactivate/", DelegationDeactivateAPIView.as_view(), name="delegation-deactivate-api"),
    path("delegation-candidates/", DelegationCandidatesAPIView.as_view(), name="delegation-candidates-api"),
    path("policies/", PolicyCatalogAPIView.as_view(), name="policy-catalog-api"),
    path("policy-evaluations/", PolicyEvaluationHistoryAPIView.as_view(), name="policy-evaluations-api"),
    path("requests/<int:pk>/watchers/", RequestWatchersAPIView.as_view(), name="request-watchers-api"),
    path("requests/<int:pk>/watch/preferences/", RequestWatchPreferencesAPIView.as_view(), name="request-watch-preferences-api"),
    path("requests/<int:pk>/certificate/", RequestCertificateMetadataAPIView.as_view(), name="request-certificate-metadata"),
    path("requests/<int:pk>/certificate.pdf/", RequestCertificateDownloadAPIView.as_view(), name="request-certificate-download"),
]
