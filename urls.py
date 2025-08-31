from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIResponseAPIView, CategoryAPIView, CategoryViewSet, GetProActiveIssues, GetUserChatHistoryAPIView,  PromptAPIView, ResponseAgent, ResponsiveAgentView, SLABreachNotificationAPIView, TicketAssignmentViewSet, TicketKAPIView, TicketPatchAPIView, TicketViewSet, ModuleAPIView, TeamAPIView, CustomerTicketViewSet, assign_ticket_api, pharmaS3FileView
from .views import CategoryAPIView, CategoryViewSet,  PromptAPIView, ResponsiveAgentView, TicketAssignmentViewSet, TicketKAPIView, TicketPatchAPIView, TicketViewSet, ModuleAPIView, TeamAPIView, CustomerTicketViewSet, TicketSolutionView, SerialTrackingView, ComplianceView

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'ticket', TicketViewSet, basename='ticket')
router.register(r'customerservice', CustomerTicketViewSet,
                basename='customer-service')
router.register(r'ticket-assignments', TicketAssignmentViewSet,
                basename='ticket-assignment')


urlpatterns = [
    path('', include(router.urls)),
    path('aimodules/', ModuleAPIView.as_view(), name='module-list-create'),
    path('aimodules/<int:pk>/', ModuleAPIView.as_view(), name='module-detail'),
    path('category/', CategoryAPIView.as_view(), name='category-list-create'),
    path('category/<int:pk>/', CategoryAPIView.as_view(), name='category-detail'),
    path('team/', TeamAPIView.as_view(), name='team-list-create'),
    path('team/<int:pk>/', TeamAPIView.as_view(), name='team-detail'),
    path('aitickets/', TicketKAPIView.as_view(), name='get-all-tickets'),
    path('aitickets/<int:pk>/', TicketKAPIView.as_view(), name='get-ticket-by-id'),
    path('aitickets/<int:pk>/update/',
         TicketPatchAPIView.as_view(), name='ticket-update'),
    path('prompts/', PromptAPIView.as_view(), name='prompt_api'),
    path('ticket-status/<int:ticket_id>/',
         ResponsiveAgentView.as_view(), name='ticket_status'),
    path('ai-response/', AIResponseAPIView.as_view(), name='ai-response'),
    path('solutionagent/<int:ticket_id>/', TicketSolutionView.as_view(),
         name='get_solutionagent_response'),
    path("pharma-industry-agent/", SerialTrackingView.as_view(),
         name="pharma-industry-agent"),
    path("pharma-industry-files/", pharmaS3FileView.as_view(), name="s3-file-api"),
    path("response-agent/<int:ticket_id>/",
         ResponseAgent.as_view(), name="get_ticket"),
    path("compliance-issues-agent/", ComplianceView.as_view(),
         name="compliance-issues-agent"),
    path("assign_ticket/", assign_ticket_api, name="assign_ticket"),
    path("send-sla-breach-emails/", SLABreachNotificationAPIView.as_view(),
         name="send_sla_breach_emails"),
    path('get-user-chat/', GetUserChatHistoryAPIView.as_view(),
         name='get-user-chat-history'),
    path("pro-active-issues/", GetProActiveIssues.as_view(),
         name="pro_active_issues"),
]
