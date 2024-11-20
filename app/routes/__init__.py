from flask_restful import Api
from app.controllers import (
    IndexView, UsersView, UserLoginView, OAuthView, DeploymentsView, RolesView, InActiveUsersView, ProjectPinView,
    RolesDetailView, CreditAssignmentView, CreditAssignmentDetailView,  CreditView, UserRolesView, UserDataSummaryView, ClustersView,
    ClusterDetailView, ClusterNamespacesView,
    ClusterNamespaceDetailView, ClusterNodesView, ClusterNodeDetailView,
    ClusterDeploymentsView, ClusterDeploymentDetailView, ClusterPvcsView, ClusterPvcDetailView,
    ClusterPVDetailView, ClusterPVsView, ClusterPodsView, ClusterPodDetailView,
    ClusterServiceDetailView, ClusterServicesView, ClusterJobsView, ClusterJobDetailView,
    ClusterStorageClassView, ClusterStorageClassDetailView,
    ProjectsView, ProjectDetailView, UserProjectsView, UserEmailVerificationView,
    EmailVerificationRequest, ForgotPasswordView, ResetPasswordView, AppsView, UserDetailView, AdminLoginView,
    ProjectAppsView, AppDetailView, RegistriesView, AppLogsView,
    UserAdminUpdateView, AppRevertView, ProjectGetCostsView, TransactionRecordView, CreditTransactionRecordView, CreditPurchaseTransactionRecordView,
    BillingInvoiceView, BillingInvoiceNotificationView, SystemSummaryView, CreditDetailView, ProjectUsersView, ProjectUsersTransferView, AppReviseView,
    ProjectUsersHandleInviteView, ClusterProjectsView, ProjectDisableView, ProjectEnableView, AppRedeployView, AppDisableView, AppEnableView,
    TagsView, TagsDetailView, TagFollowingView, GenericSearchView, MLProjectAppsView,
    UserDisableView, UserEnableView, AppDockerWebhookListenerView, UserFollowersView, UserFollowView, ProjectFollowingView, ActivityFeedView)
from app.controllers.app import AppRevisionsView
from app.controllers.billing_invoice import BillingInvoiceDetailView
from app.controllers.receipts import BillingReceiptsDetailView, BillingReceiptsView
from app.controllers.transactions import TransactionRecordDetailView, TransactionVerificationView

api = Api()

# Index route
api.add_resource(IndexView, '/')

# User routes
api.add_resource(UsersView, '/users', endpoint='users')
api.add_resource(UserLoginView, '/users/login', endpoint='login')
api.add_resource(AdminLoginView, '/users/admin_login', endpoint='admin_login')
api.add_resource(UserEmailVerificationView, '/users/verify/<string:token>')
api.add_resource(EmailVerificationRequest, '/users/verify')
api.add_resource(ForgotPasswordView, '/users/forgot_password')
api.add_resource(ResetPasswordView, '/users/reset_password/<string:token>')
api.add_resource(UserDetailView, '/users/<string:user_id>')
api.add_resource(OAuthView, '/users/oauth')
api.add_resource(UserDataSummaryView, '/users/graph')
api.add_resource(UserAdminUpdateView, '/users/admin_update')
api.add_resource(InActiveUsersView, '/users/inactive_users',
                 endpoint='inactive_users')

api.add_resource(UserEnableView, '/users/<string:user_id>/enable')
api.add_resource(UserDisableView, '/users/<string:user_id>/disable')

api.add_resource(UserFollowView, '/users/<string:user_id>/following')
api.add_resource(UserFollowersView, '/users/<string:user_id>/followers')

# Activity Feed
api.add_resource(ActivityFeedView, '/activity_feed')
# Deployments
api.add_resource(DeploymentsView, '/deployments', endpoint='deployments')

# Generic search
api.add_resource(GenericSearchView, '/search')

# Clusters
api.add_resource(ClustersView, '/clusters', endpoint='clusters')
api.add_resource(ClusterDetailView, '/clusters/<string:cluster_id>')
api.add_resource(ClusterNamespacesView,
                 '/clusters/<string:cluster_id>/namespaces')
api.add_resource(ClusterNamespaceDetailView,
                 '/clusters/<string:cluster_id>/namespaces/<string:namespace_name>')
api.add_resource(ClusterNodesView, '/clusters/<string:cluster_id>/nodes')
api.add_resource(ClusterNodeDetailView,
                 '/clusters/<string:cluster_id>/nodes/<string:node_name>')
api.add_resource(ClusterDeploymentsView,
                 '/clusters/<string:cluster_id>/deployments')
api.add_resource(ClusterDeploymentDetailView,
                 '/clusters/<string:cluster_id>/deployments/<string:namespace_name>/<string:deployment_name>')
api.add_resource(ClusterPvcsView, '/clusters/<string:cluster_id>/pvcs')
api.add_resource(ClusterPvcDetailView,
                 '/clusters/<string:cluster_id>/pvcs/<string:namespace_name>/<string:pvc_name>')
api.add_resource(ClusterPVsView, '/clusters/<string:cluster_id>/pvs')
api.add_resource(ClusterPVDetailView,
                 '/clusters/<string:cluster_id>/pvs/<string:pv_name>')
api.add_resource(ClusterPodsView, '/clusters/<string:cluster_id>/pods')
api.add_resource(ClusterPodDetailView,
                 '/clusters/<string:cluster_id>/pods/<string:namespace_name>/<string:pod_name>')
api.add_resource(ClusterServicesView, '/clusters/<string:cluster_id>/services')
api.add_resource(ClusterServiceDetailView,
                 '/clusters/<string:cluster_id>/services/<string:namespace_name>/<string:service_name>')
api.add_resource(ClusterJobsView, '/clusters/<string:cluster_id>/jobs')
api.add_resource(ClusterJobDetailView,
                 '/clusters/<string:cluster_id>/jobs/<string:namespace_name>/<string:job_name>')
api.add_resource(ClusterStorageClassView,
                 '/clusters/<string:cluster_id>/storage_classes')
api.add_resource(ClusterStorageClassDetailView,
                 '/clusters/<string:cluster_id>/storage_classes/<string:storage_class_name>')
api.add_resource(ClusterProjectsView,
                 '/clusters/<string:cluster_id>/projects')

# Credit routes
api.add_resource(CreditView, '/credit', endpoint='credit')
api.add_resource(CreditDetailView, '/credit/<string:user_id>')

# Credit Assignment routes
api.add_resource(CreditAssignmentView, '/credit_assignment',
                 endpoint='credit_assignment')
api.add_resource(CreditAssignmentDetailView,
                 '/credit_assignment/<string:user_id>', endpoint='credit_assignment_detail')

# Roles routes
api.add_resource(RolesView, '/roles', endpoint='roles')
api.add_resource(RolesDetailView, '/roles/<string:role_id>',
                 endpoint='roles_detail')

# User_Roles routes
api.add_resource(UserRolesView, '/user/<string:user_id>/roles',
                 endpoint='user_roles')

# Transaction routes
api.add_resource(TransactionRecordView,
                 '/projects/<string:project_id>/transactions', endpoint='transactions')
api.add_resource(TransactionRecordDetailView,
                 '/projects/<string:project_id>/transactions/<string:record_id>')
api.add_resource(TransactionVerificationView,
                 '/projects/<string:project_id>/transactions/<string:transaction_id>/<string:tx_ref>')

# Credit Transaction route
api.add_resource(CreditTransactionRecordView,
                 '/projects/<string:project_id>/credit_transactions', endpoint='credit_transactions')

# Credit Purchase Transaction route
api.add_resource(CreditPurchaseTransactionRecordView,
                 '/projects/<string:project_id>/credit_purchase_transactions', endpoint='credit_purchase_transactions')

# Invoice routes
api.add_resource(BillingInvoiceView,
                 '/projects/<string:project_id>/invoices', endpoint='invoices')
api.add_resource(BillingInvoiceNotificationView, '/invoices/notify')
api.add_resource(BillingInvoiceDetailView,
                 '/projects/<string:project_id>/invoices/<string:invoice_id>')

# receipt routes
api.add_resource(BillingReceiptsView,
                 '/projects/<string:project_id>/receipts', endpoint='receipts')
api.add_resource(BillingReceiptsDetailView,
                 '/projects/<string:project_id>/receipts/<string:receipt_id>')

# Project route
api.add_resource(ProjectsView, '/projects', endpoint='projects')
api.add_resource(ProjectDetailView, '/projects/<string:project_id>')
api.add_resource(
    ProjectAppsView, '/projects/<string:project_id>/apps', endpoint='project_apps')
api.add_resource(ProjectGetCostsView,
                 '/projects/<string:project_id>/billing/info')
api.add_resource(ProjectDisableView,
                 '/projects/<string:project_id>/disable')
api.add_resource(ProjectEnableView,
                 '/projects/<string:project_id>/enable')
api.add_resource(ProjectPinView, '/projects/<string:project_id>/pin')
# User Project routes
api.add_resource(UserProjectsView, '/users/<string:user_id>/projects')
# Tags Routes
api.add_resource(TagsView, '/tags')
api.add_resource(TagsDetailView, '/tags/<string:tag_id>')
api.add_resource(TagFollowingView, '/tags/<string:tag_id>/following')

# App routes
api.add_resource(AppsView, '/apps')
api.add_resource(AppDetailView, '/apps/<string:app_id>')
api.add_resource(AppRevertView, '/apps/<string:app_id>/revert_url')
api.add_resource(AppRevisionsView, '/apps/<string:app_id>/revisions')
api.add_resource(
    AppReviseView, '/apps/<string:app_id>/revise/<string:revision_id>')
api.add_resource(
    AppRedeployView, '/apps/<string:app_id>/redeploy')
api.add_resource(
    AppDisableView, '/apps/<string:app_id>/disable')
api.add_resource(
    AppEnableView, '/apps/<string:app_id>/enable')
api.add_resource(
    AppDockerWebhookListenerView, '/apps/<string:app_id>/<string:user_id>/docker/<string:tag>/webhook')
api.add_resource(
    MLProjectAppsView, '/projects/<string:project_id>/apps/ml')
api.add_resource(
    AppLogsView, '/projects/<string:project_id>/apps/<string:app_id>/logs')


# Registry routes
api.add_resource(RegistriesView, '/registries')

# Project Users
api.add_resource(ProjectUsersView, '/projects/<string:project_id>/users')
api.add_resource(ProjectUsersTransferView,
                 '/projects/<string:project_id>/users/transfer')
api.add_resource(ProjectUsersHandleInviteView,
                 '/projects/<string:project_id>/users/handle_invite')
api.add_resource(ProjectFollowingView,
                 '/projects/<string:project_id>/following')

# system status
api.add_resource(SystemSummaryView, '/system_summary')
