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
