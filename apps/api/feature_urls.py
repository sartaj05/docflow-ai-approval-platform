from django.urls import path

from apps.api.profile_read_view import CurrentProfileView


urlpatterns = [
    path("profile/", CurrentProfileView.as_view(), name="current-profile"),
]

from apps.api.profile_update_view import CurrentProfileUpdateView
urlpatterns.append(path('profile/contact/', CurrentProfileUpdateView.as_view(), name='current-profile-update'))

from apps.api.global_search_view import GlobalSearchAPIView
urlpatterns.append(path('search/', GlobalSearchAPIView.as_view(), name='global-search'))

from apps.api.search_suggestions_view import RequestSearchSuggestionsView
urlpatterns.append(path('search/suggestions/', RequestSearchSuggestionsView.as_view(), name='request-search-suggestions'))

from apps.api.audit_feed_view import AuditFeedView
urlpatterns.append(path('audit-logs/', AuditFeedView.as_view(), name='audit-feed'))

from apps.api.request_audit_view import RequestAuditHistoryView
urlpatterns.append(path('requests/<int:pk>/audit/', RequestAuditHistoryView.as_view(), name='request-audit-history'))

from apps.api.discussion_list_view import RequestDiscussionListView
urlpatterns.append(path('requests/<int:pk>/discussion/', RequestDiscussionListView.as_view(), name='request-discussion-list'))

from apps.api.discussion_create_view import RequestDiscussionCreateView
urlpatterns.append(path('requests/<int:pk>/discussion/comments/', RequestDiscussionCreateView.as_view(), name='request-discussion-create'))

from apps.api.discussion_reply_view import RequestDiscussionReplyView
urlpatterns.append(path('requests/<int:pk>/discussion/<int:comment_pk>/replies/', RequestDiscussionReplyView.as_view(), name='request-discussion-replies'))

from apps.api.discussion_delete_view import RequestDiscussionDeleteView
urlpatterns.append(path('requests/<int:pk>/discussion/<int:comment_pk>/delete/', RequestDiscussionDeleteView.as_view(), name='request-discussion-delete'))

from apps.api.delegation_list_view import DelegationListAPIView
urlpatterns.append(path('delegations/', DelegationListAPIView.as_view(), name='delegation-list-api'))

from apps.api.delegation_create_view import DelegationCreateAPIView
urlpatterns.append(path('delegations/create/', DelegationCreateAPIView.as_view(), name='delegation-create-api'))

from apps.api.delegation_deactivate_view import DelegationDeactivateAPIView
urlpatterns.append(path('delegations/<int:pk>/deactivate/', DelegationDeactivateAPIView.as_view(), name='delegation-deactivate-api'))

from apps.api.delegation_candidates_view import DelegationCandidatesAPIView
urlpatterns.append(path('delegation-candidates/', DelegationCandidatesAPIView.as_view(), name='delegation-candidates-api'))

from apps.api.policy_catalog_view import PolicyCatalogAPIView
urlpatterns.append(path('policies/', PolicyCatalogAPIView.as_view(), name='policy-catalog-api'))

from apps.api.policy_evaluations_view import PolicyEvaluationHistoryAPIView
urlpatterns.append(path('policy-evaluations/', PolicyEvaluationHistoryAPIView.as_view(), name='policy-evaluations-api'))

from apps.api.request_watchers_view import RequestWatchersAPIView
urlpatterns.append(path('requests/<int:pk>/watchers/', RequestWatchersAPIView.as_view(), name='request-watchers-api'))

from apps.api.request_watch_preferences_view import RequestWatchPreferencesAPIView
urlpatterns.append(path('requests/<int:pk>/watch/preferences/', RequestWatchPreferencesAPIView.as_view(), name='request-watch-preferences-api'))

from apps.api.certificate_metadata_view import RequestCertificateMetadataAPIView
urlpatterns.append(path('requests/<int:pk>/certificate/', RequestCertificateMetadataAPIView.as_view(), name='request-certificate-metadata'))
