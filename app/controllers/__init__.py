# import all controllers

from .index import IndexView
from .users import (
    UsersView, UserLoginView, UserEmailVerificationView, UserFollowersView, UserFollowView,
    EmailVerificationRequest, ForgotPasswordView, ResetPasswordView, UserDisableView, UserEnableView,
    UserDetailView, AdminLoginView, OAuthView, UserDataSummaryView, UserAdminUpdateView, InActiveUsersView)
from .deployments import DeploymentsView
from .clusters import (
    ClustersView, ClusterDetailView, ClusterNamespacesView,
    ClusterNamespaceDetailView, ClusterNodesView, ClusterNodeDetailView,
    ClusterDeploymentsView, ClusterDeploymentDetailView, ClusterPvcsView,
    ClusterPvcDetailView, ClusterPVsView, ClusterPVDetailView,
    ClusterPodsView, ClusterPodDetailView, ClusterServicesView,
    ClusterServiceDetailView, ClusterJobsView, ClusterJobDetailView,
    ClusterStorageClassView, ClusterStorageClassDetailView)
from .roles import RolesView, RolesDetailView
from .credit_assignments import CreditAssignmentView, CreditAssignmentDetailView
from .credits import CreditView, CreditDetailView
from .user_role import UserRolesView
from .transactions import TransactionRecordView, TransactionRecordDetailView, CreditTransactionRecordView, CreditPurchaseTransactionRecordView
from .project import (
    ProjectsView, ProjectDetailView, UserProjectsView, ProjectGetCostsView, ClusterProjectsView, ProjectPinView,
    ProjectDisableView, ProjectEnableView)
from .app import (AppsView, ProjectAppsView, AppDetailView, AppLogsView, MLProjectAppsView,
                  AppRevertView, AppReviseView, AppRedeployView, AppDisableView, AppEnableView, AppDockerWebhookListenerView)
from .registry import RegistriesView
from .billing_invoice import (
    BillingInvoiceView, BillingInvoiceNotificationView)
from .system_status import SystemSummaryView
from .project_users import ProjectUsersView, ProjectUsersTransferView, ProjectUsersHandleInviteView, ProjectFollowingView
from .activity_feed import ActivityFeedView
from .tags import TagsView, TagsDetailView, TagFollowingView
from .generic_search import GenericSearchView
