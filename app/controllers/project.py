import datetime
import json
from types import SimpleNamespace
from app.helpers.cost_modal import CostModal
from app.helpers.alias import create_alias
from app.helpers.admin import is_authorised_project_user, is_owner_or_admin, is_current_or_admin, is_admin
from app.helpers.role_search import has_role
from app.helpers.activity_logger import log_activity
from app.helpers.kube import create_kube_clients, delete_cluster_app, disable_project, enable_project, check_kube_error_code
from app.models.billing_invoice import BillingInvoice
from app.models.project_users import ProjectUser
from app.models.user import User
from app.models.clusters import Cluster
from app.models.project import Project
from app.schemas import ProjectSchema, AppSchema, ProjectUserSchema, ClusterSchema
from app.helpers.decorators import admin_required
import datetime
from flask_restful import Resource, request
from kubernetes import client
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt_claims
from app.schemas.monitoring_metrics import BillingMetricsSchema, ProjectGraphSchema
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_, func
from app.helpers.crane_app_logger import logger
from flask import current_app, render_template
from app.helpers.email import send_email
from app.helpers.pagination import paginate


class ProjectsView(Resource):

    @jwt_required
    def post(self):
        """
        """
        current_user_id = get_jwt_identity()
        current_user_roles = get_jwt_claims()['roles']

        project_schema = ProjectSchema()

        project_data = request.get_json()

        validated_project_data, errors = project_schema.load(project_data)
        if errors:
            return dict(status='fail', message=errors), 400

        if not has_role(current_user_roles, 'administrator'):
            validated_project_data['owner_id'] = current_user_id
        # check if project already exists
        existing_project = Project.find_first(
            name=validated_project_data['name'],
            owner_id=validated_project_data['owner_id'])

        if existing_project:
            return dict(
                status='fail',
                message=f'''project with name {
                    validated_project_data["name"]} already exists'''
            ), 409
        try:
            validated_project_data['alias'] =\
                create_alias(validated_project_data['name'])
            namespace_name = validated_project_data['alias']
            cluster_id = validated_project_data['cluster_id']
            cluster = Cluster.get_by_id(cluster_id)

            if not cluster:
                return dict(
                    status='fail',
                    message=f'cluster {cluster_id} not found'
                ), 404

            kube_host = cluster.host
            kube_token = cluster.token

            kube_client = create_kube_clients(kube_host, kube_token)

            # create namespace in cluster
            cluster_namespace = kube_client.kube.create_namespace(
                client.V1Namespace(
                    metadata=client.V1ObjectMeta(name=namespace_name)
                ))

            # create project in database
            if cluster_namespace:

                ingress_name = f"{validated_project_data['alias']}-ingress"

                ingress_meta = client.V1ObjectMeta(
                    name=ingress_name
                )

                ingress_default_rule = client.V1IngressRule(
                    host="traefik-ui.cranecloud.io",
                    http=client.V1HTTPIngressRuleValue(
                        paths=[client.V1HTTPIngressPath(
                            path="/*",
                            path_type="ImplementationSpecific",
                            backend=client.V1IngressBackend(
                                service=client.V1IngressServiceBackend(
                                    name="traefik-web-ui-ext",
                                    port=client.V1ServiceBackendPort(
                                        number=80
                                    )
                                )
                            )
                        )]
                    )
                )

                ingress_spec = client.V1IngressSpec(
                    rules=[ingress_default_rule]
                )

                ingress_body = client.V1Ingress(
                    metadata=ingress_meta,
                    spec=ingress_spec
                )

                kube_client.networking_api.create_namespaced_ingress(
                    namespace=namespace_name,
                    body=ingress_body
                )

                project = Project(**validated_project_data)

                # Add user as owner of project
                new_role = ProjectUser(
                    role="owner",
                    user_id=project.owner_id
                )
                project.users.append(new_role)

            saved = project.save()

            if not saved:
                log_activity('Project', status='Failed',
                             operation='Create',
                             description="Internal Server Error",
                             a_cluster_id=cluster_id)

                # delete the namespace
                kube_client.kube.delete_namespace(namespace_name)

                return dict(status="fail", message="Internal Server Error"), 500

            # create a billing invoice on project creation
            new_invoice = BillingInvoice(project_id=project.id)

            saved_new_invoice = new_invoice.save()

            if not saved_new_invoice:
                return dict(
                    status='fail',
                    message='An error occured during creation of a new invoice record'), 400

            # create a billing invoice on project creation
            new_invoice = BillingInvoice(project_id=project.id)

            saved_new_invoice = new_invoice.save()

            if not saved_new_invoice:
                return dict(
                    status='fail',
                    message='An error occured during creation of a new invoice record'), 400

            # create a billing invoice on project creation
            new_invoice = BillingInvoice(project_id=project.id)

            saved_new_invoice = new_invoice.save()

            if not saved_new_invoice:
                return dict(
                    status='fail',
                    message='An error occured during creation of a new invoice record'), 400

            new_project_data, errors = project_schema.dump(project)
            log_activity('Project', status='Success',
                         operation='Create',
                         description='Created project Successfully',
                         a_project_id=project.id,
                         a_cluster_id=cluster_id)

            return dict(status='success', data=dict(project=new_project_data)), 201

        except client.rest.ApiException as e:
            log_activity('Project', status='Failed',
                         operation='Create',
                         description=e.body,
                         a_cluster_id=cluster_id)
            return dict(status='fail', message=str(e.body)), check_kube_error_code(e.status)

        except Exception as err:
            log_activity('Project', status='Failed',
                         operation='Create',
                         description=err.body,
                         a_cluster_id=cluster_id)
            return dict(status='fail', message=str(err)), 500

    @jwt_required
    def get(self):
        """
        """
        current_user_id = get_jwt_identity()
        current_user_roles = get_jwt_claims()['roles']
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        keywords = request.args.get('keywords', '')
        disabled = request.args.get('disabled')
        project_type = request.args.get('project_type')

        graph_filter_data = {
            'start': request.args.get('start', '2018-01-01'),
            'end': request.args.get('end', datetime.datetime.now().strftime('%Y-%m-%d')),
            'set_by': request.args.get('set_by', 'month')
        }
        series = request.args.get('series', 'false').lower() == 'true'

        project_schema = ProjectSchema(many=True)
        projects = []
        pagination_data = {}

        filter_mapping = {
            'disabled': disabled,
            'project_type': project_type
        }

        # count items per project category
        project_metadata = {}
        for category in filter_mapping.keys():
            distinct_counts = Project.query.with_entities(getattr(Project, category), func.count(
                getattr(Project, category))).group_by(getattr(Project, category)).all()
            if category == 'disabled':
                project_metadata[category] = distinct_counts[0][1] if distinct_counts else 0
            else:
                project_metadata[category] = dict(distinct_counts)

        # Identify which attribute to filter on
        attribute, attribute_value = next(
            ((k, v) for k, v in filter_mapping.items() if v), (None, None))

        if has_role(current_user_roles, 'administrator'):

            if (keywords == ''):
                if attribute:
                    paginated = (Project.query.filter(getattr(Project, attribute) == attribute_value).order_by(
                        Project.date_created.desc()).paginate(page=page, per_page=per_page, error_out=False))
                    projects = paginated.items
                    pagination_data = {
                        'total': paginated.total,
                        'pages': paginated.pages,
                        'page': paginated.page,
                        'per_page': paginated.per_page,
                        'next': paginated.next_num,
                        'prev': paginated.prev_num
                    }

                else:
                    paginated = Project.find_all(
                        paginate=True, page=page, per_page=per_page)
                    projects = paginated.items
                    pagination_data = paginated.pagination
            else:
                paginated = Project.query.filter(Project.name.ilike('%'+keywords+'%')).order_by(Project.date_created.desc()).paginate(
                    page=page, per_page=per_page, error_out=False)
                projects = paginated.items
                pagination_data = {
                    'total': paginated.total,
                    'pages': paginated.pages,
                    'page': paginated.page,
                    'per_page': paginated.per_page,
                    'next': paginated.next_num,
                    'prev': paginated.prev_num
                }
        else:
            try:

                if (keywords == ''):
                    if attribute:
                        paginated = (Project.query.filter(getattr(Project, attribute) == attribute_value).order_by(
                            Project.date_created.desc()).paginate(page=page, per_page=per_page, error_out=False))
                        projects = paginated.items
                        pagination = {
                            'total': paginated.total,
                            'pages': paginated.pages,
                            'page': paginated.page,
                            'per_page': paginated.per_page,
                            'next': paginated.next_num,
                            'prev': paginated.prev_num
                        }
                    else:
                        pagination = Project.query.filter(or_(Project.owner_id == current_user_id, Project.users.any(
                            ProjectUser.user_id == current_user_id))).order_by(Project.date_created.desc()).paginate(
                            page=page, per_page=per_page, error_out=False)
                else:

                    pagination = Project.query.filter(Project.owner_id == current_user_id, Project.name.ilike('%'+keywords+'%'), Project.users.any(
                        ProjectUser.user_id == current_user_id)).order_by(Project.date_created.desc()).paginate(
                        page=page, per_page=per_page, error_out=False)

                projects = pagination.items
                if pagination:
                    pagination_data = {
                        'total': pagination.total,
                        'pages': pagination.pages,
                        'page': pagination.page,
                        'per_page': pagination.per_page,
                        'next': pagination.next_num,
                        'prev': pagination.prev_num
                    }
            except SQLAlchemyError:
                pagination = None
                return dict(status='fail', message='Internal Server Error'), 500

        project_data, errors = project_schema.dumps(projects)

        if errors:
            return dict(status='fail', message=errors), 500

        # Updating user's last login
        user = User.get_by_id(current_user_id)
        user.last_seen = datetime.datetime.now()
        user.save()
        # ADD a logger for when user.save does not work

         # If series is requested, include graph data based on filtered dates
        if series:
            validated_query_data, errors = ProjectGraphSchema().load(graph_filter_data)
            if errors:
                return dict(status='fail', message=errors), 400

            start = validated_query_data['start']
            end = validated_query_data['end']
            set_by = validated_query_data['set_by']

            # Get graph data from Project model
            graph_data = Project.graph_data(start=start, end=end, set_by=set_by)

            return dict(
                status='success',
                data=dict(
                    metadata=project_metadata,
                    pagination=pagination_data,
                    # projects=json.loads(project_data),
                    graph_data=graph_data
                )
            ), 200

        return dict(
            status='success',
            data=dict(
                metadata=project_metadata,
                pagination=pagination_data,
                projects=json.loads(project_data)
            )
        ), 200

class ProjectDetailView(Resource):

    @jwt_required
    def get(self, project_id):
        """
        """
        current_user_id = get_jwt_identity()
        current_user_roles = get_jwt_claims()['roles']

        project_schema = ProjectSchema()

        project = Project.get_by_id(project_id)

        if not project:
            return dict(
                status='fail',
                message=f'project {project_id} not found'
            ), 404

        if not is_owner_or_admin(project, current_user_id, current_user_roles):
            if not is_authorised_project_user(project, current_user_id, 'member'):
                return dict(status='fail', message='unauthorised'), 403

        project_data, errors = project_schema.dumps(project)
        if errors:
            return dict(status='fail', message=errors), 500

        # return cluster information
        cluster_schema = ClusterSchema()
        project_cluster = project.cluster
        cluster_data, errors = cluster_schema.dumps(project_cluster)

        # if user not an admin
        if not is_admin(current_user_roles):
            return dict(status='success', data=dict(
                project=dict(**json.loads(project_data)), cluster=json.loads(cluster_data))), 200
        else:
            apps_schema = AppSchema(many=True)
            users_schema = ProjectUserSchema(many=True)
            apps = project.apps
            users = project.users
            apps_data, errors = apps_schema.dumps(apps)
            users_data, errors = users_schema.dumps(users)
            return dict(status='success', data=dict(
                project=dict(**json.loads(project_data),
                             apps=json.loads(apps_data),
                             users=json.loads(users_data),
                             cluster=json.loads(cluster_data)
                             ))), 200

    @jwt_required
    def delete(self, project_id):
        """
        """

        current_user_id = get_jwt_identity()
        current_user_roles = get_jwt_claims()['roles']

        project = Project.get_by_id(project_id)

        if not project:
            return dict(
                status='fail',
                message=f'project {project_id} not found'
            ), 404
        if not is_owner_or_admin(project, current_user_id, current_user_roles):
            return dict(status='fail', message='unauthorised'), 403

        try:
            # get cluster for the project
            cluster = Cluster.get_by_id(project.cluster_id)

            if not cluster:
                return dict(status='fail', message='cluster not found'), 500

            kube_host = cluster.host
            kube_token = cluster.token

            kube_client = create_kube_clients(kube_host, kube_token)

            # check and delete apps within a project
            apps_list = project.apps
            if apps_list:
                for app in apps_list:
                    delete_cluster_app(kube_client, project.alias, app)
                    # delete the app from the database
                    deleted = app.soft_delete()

            # get corresponding namespace
            try:
                namespace = kube_client.kube.read_namespace(project.alias)
                # delete namespace if it exists
                if namespace:
                    kube_client.kube.delete_namespace(project.alias)
            except Exception as e:
                # if unable to get namespace, it means it is already deleted
                pass

            deleted = project.soft_delete()

            if not deleted:
                log_activity('Project', status='Failed',
                             operation='Delete',
                             description='Internal server error',
                             a_project_id=project_id,
                             a_cluster_id=project.cluster_id)
                return dict(status='fail', message='deletion failed'), 500

            log_activity('Project', status='Success',
                         operation='Delete',
                         description='Deleted project Successfully',
                         a_project_id=project.id,
                         a_cluster_id=project.cluster_id)
            return dict(
                status='success',
                message=f'project {project_id} deleted successfully'
            ), 200

        except client.rest.ApiException as e:
            if e.status == 404:
                """
                deletes apps and project from db if not found on the cluster
                """
                apps_list = project.apps
                if apps_list:
                    for app in apps_list:
                        # delete the app from the database
                        deleted = app.soft_delete()

                deleted = project.soft_delete()

                if not deleted:
                    return dict(status='fail', message='deletion failed'), 500
                log_activity('Project', status='Success',
                             operation='Delete',
                             description='Deleted project Successfully',
                             a_project_id=project.id,
                             a_cluster_id=project.cluster_id)
                return dict(
                    status='success',
                    message=f'project {project_id} deleted successfully'
                ), 200
            log_activity('Project', status='Failed',
                         operation='Delete',
                         description=e.reason,
                         a_project_id=project_id,
                         a_cluster_id=project.cluster_id)
            return dict(status='fail', message=e.reason), check_kube_error_code(e.status)

        except Exception as e:
            log_activity('Project', status='Failed',
                         operation='Delete',
                         description=str(e),
                         a_project_id=project_id,
                         a_cluster_id=project.cluster_id)
            return dict(status='fail', message=str(e)), 500

    @jwt_required
    def patch(self, project_id):
        """
        """

        try:
            current_user_id = get_jwt_identity()
            current_user_roles = get_jwt_claims()['roles']

            project_schema = ProjectSchema(
                only=("name", "description", "organisation", "project_type"), partial=True)

            project_data = request.get_json()

            validate_project_data, errors = project_schema.load(project_data)

            existing_project = False

            if errors:
                return dict(status='fail', message=errors), 400

            if 'name' in validate_project_data:
                existing_project = Project.find_first(
                    name=validate_project_data['name'],
                    owner_id=current_user_id)

            if existing_project:
                return dict(
                    status='fail',
                    message=f'''project with name {
                        validate_project_data["name"]} already exists'''
                ), 409

            project = Project.get_by_id(project_id)

            if not project:
                return dict(status='fail', message=f'Project {project_id} not found'), 404

            if not is_owner_or_admin(project, current_user_id, current_user_roles):
                if not is_authorised_project_user(project, current_user_id, 'admin'):
                    return dict(status='fail', message='unauthorised'), 403

            updated = Project.update(project, **validate_project_data)

            if not updated:
                log_activity('Project', status='Failed',
                             operation='Update',
                             description='Internal Server Error',
                             a_project_id=project.id,
                             a_cluster_id=project.cluster_id
                             )
                return dict(status='fail', message='internal server error'), 500

            log_activity('Project', status='Success',
                         operation='Update',
                         description='Updated project Successfully',
                         a_project_id=project.id,
                         a_cluster_id=project.cluster_id)
            return dict(
                status='success',
                message=f'project {project_id} updated successfully'
            ), 200

        except Exception as e:
            return dict(status='fail', message=str(e)), 500


class UserProjectsView(Resource):

    @jwt_required
    def get(self, user_id):
        """
        """

        current_user_id = get_jwt_identity()
        current_user = User.get_by_id(current_user_id)
        # current_user_roles = get_jwt_claims()['roles']
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # open endpoint
        # if not is_current_or_admin(user_id, current_user_id, current_user_roles):
        #     return dict(status='fail', message='unauthorised'), 403

        project_schema = ProjectSchema(many=True)
        user = User.get_by_id(user_id)

        pinned_projects = Project.query.join(
            ProjectUser, Project.id == ProjectUser.project_id
        ).filter(
            ProjectUser.user_id == user_id,
            ProjectUser.pinned == True,
            Project.deleted == False
        ).all()

        pagination_meta_data, projects = paginate(
            user.projects, per_page, page)

        user_projects, errors = project_schema.dumps(
            projects)

        pinned_projects, errs = project_schema.dumps(pinned_projects)

        if errors and errs:
            return dict(status='fail', message='Internal server error'), 500

        return dict(
            status='success',
            data=dict(
                pagination={**pagination_meta_data,
                            'pinned_count': len(pinned_projects)},
                pinned=json.loads(pinned_projects),
                projects=json.loads(user_projects),
            )
        ), 200


class ClusterProjectsView(Resource):

    @admin_required
    def get(self, cluster_id):
        """
        Get projects in a cluster
        """

        current_user_roles = get_jwt_claims()['roles']
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        if not is_admin(current_user_roles):
            return dict(status='fail', message='user unauthorised'), 403

        project_schema = ProjectSchema(many=True)
        cluster = Cluster.get_by_id(cluster_id)

        if not cluster:
            return dict(status='fail', message=f'Cluster with id {cluster_id} not found'), 404

        projects = cluster.projects
        projects = Project.find_all(
            cluster_id=cluster_id, paginate=True, page=page, per_page=per_page)

        projects_json, errors = project_schema.dumps(projects.items)

        if errors:
            return dict(status='fail', message='Internal server error'), 500

        return dict(
            status='success',
            data=dict(
                pagination=projects.pagination,
                projects=json.loads(projects_json))
        ), 200


class ProjectGetCostsView(Resource):
    @jwt_required
    def post(self, project_id):
        current_user_id = get_jwt_identity()
        current_user_roles = get_jwt_claims()['roles']

        project_billing_schema = BillingMetricsSchema()
        project_billing_data = request.get_json()

        validated_query_data, errors = project_billing_schema.load(
            project_billing_data)

        project = Project.get_by_id(project_id)

        if not project:
            return dict(
                status='fail',
                message=f'project {project_id} not found'
            ), 404

        if not is_owner_or_admin(project, current_user_id, current_user_roles):
            return dict(status='fail', message='unauthorised'), 403

        creation_timestamp = int(project.date_created.timestamp())

        # TODO: Have start date begin from last bill payment date
        start = validated_query_data.get('start', creation_timestamp)
        end = validated_query_data.get(
            'end', int(datetime.datetime.now().timestamp()))
        series = validated_query_data.get('series', False)
        show_deployments = validated_query_data.get('show_deployments', False)

        if show_deployments:
            series = False
        window = validated_query_data.get('window', None)

        if not window:
            window = f'{start},{end}'

        namespace = project.alias
        # namespace = 'liqo'
        cost_url = project.cluster.cost_modal_url

        if not cost_url:
            return dict(status='fail', message='No cost modal url provided, please contact your administrator'), 404

        cost_modal = CostModal(cost_url)

        cost_data = cost_modal.get_namespace_cost(
            window, namespace, series=series, show_deployments=show_deployments)

        if cost_data is False:
            return dict(status='fail', message='Error occurred'), 500

        return dict(status='success', data=dict(cost_data=cost_data)), 200


class ProjectDisableView(Resource):
    @jwt_required
    def post(self, project_id):

        # check credentials
        current_user_id = get_jwt_identity()
        current_user_roles = get_jwt_claims()['roles']

        project = Project.get_by_id(project_id)
        if not project:
            return dict(status='fail', message=f'Project with id {project_id} not found'), 404

        if not is_owner_or_admin(project, current_user_id, current_user_roles):
            if not is_authorised_project_user(project, current_user_id, 'admin'):
                logger.warning(
                    f'User with id {current_user_id} is not authorized to access Project with id {project_id}')
                return dict(status='fail', message='unauthorised'), 403

        if project.disabled:
            return dict(status='fail', message=f'Project with id {project_id} is already disabled'), 409

        disabled_project = disable_project(
            project, is_admin(current_user_roles))

        if type(disabled_project) == SimpleNamespace:
            status_code = disabled_project.status_code if disabled_project.status_code else 500
            return dict(status='fail', message=disabled_project.message), status_code

        receipient_users = [user.user for user in project.users]
        project_owner = User.get_by_id(project.owner_id)

        for user in receipient_users:

            html_layout = render_template(
                'user/project_disable_enable.html',
                email=user.email,
                name=user.name,
                is_project_owner=(user.id == project.owner_id),
                owner_name=project_owner.name,
                project_name=project.name,
                admin_disabled=is_admin(current_user_roles),
                status='disabled')

            send_email(
                user.email,
                f'Status of your project {project.name}' if (
                    user.id == project.owner_id) else f'Status of project {project.name} you are contributing to.',
                html_layout,
                current_app.config["MAIL_DEFAULT_SENDER"],
                current_app._get_current_object(),
            )

        return dict(
            status='success',
            message=f'project {project_id} disabled successfully'
        ), 200


class ProjectEnableView(Resource):
    @jwt_required
    def post(self, project_id):

        # check credentials
        current_user_id = get_jwt_identity()
        current_user_roles = get_jwt_claims()['roles']

        project = Project.get_by_id(project_id)
        if not project:
            return dict(status='fail', message=f'Project with id {project_id} not found'), 404

        if not is_owner_or_admin(project, current_user_id, current_user_roles):
            if not is_authorised_project_user(project, current_user_id, 'admin'):
                return dict(status='fail', message='unauthorised'), 403

        if not project.disabled:
            return dict(status='fail', message=f'Project with id {project_id} is already enabled'), 409

        # Prevent users from enabling admin disabled projects
        if project.admin_disabled and not is_admin(current_user_roles):
            return dict(status='fail', message=f'You are not authorised to disable Project with id {project_id}, please contact an admin'), 403

        enabled_project = enable_project(project)

        if type(enabled_project) == SimpleNamespace:
            status_code = enabled_project.status_code if enabled_project.status_code else 500
            return dict(status='fail', message=enabled_project.message), status_code

        receipient_users = [user.user for user in project.users]
        project_owner = User.get_by_id(project.owner_id)

        for user in receipient_users:

            html_layout = render_template(
                'user/project_disable_enable.html',
                email=user.email,
                name=user.name,
                is_project_owner=(user.id == project.owner_id),
                owner_name=project_owner.name,
                project_name=project.name,
                admin_disabled=is_admin(current_user_roles),
                status='enabled')

            send_email(
                user.email,
                f'Status of your project {project.name}' if (
                    user.id == project.owner_id) else f'Status of project {project.name} you are contributing to.',
                html_layout,
                current_app.config["MAIL_DEFAULT_SENDER"],
                current_app._get_current_object(),
            )

        return dict(
            status='success',
            message=f'project {project_id} enabled successfully'
        ), 201


class ProjectPinView(Resource):
    @jwt_required
    def post(self, project_id):

        current_user_id = get_jwt_identity()
        project = Project.get_by_id(project_id)

        project_user = ProjectUser.query.filter_by(
            user_id=current_user_id, project_id=project_id).first()

        if not is_authorised_project_user(project, current_user_id, 'member'):
            return dict(status='fail', message='unauthorised'), 403

        if project_user.pinned:
            return dict(
                message='The project is already pinned',
                status='fail'
            ), 409

        pinned_projects_count = ProjectUser.count(
            user_id=current_user_id, pinned=True)

        if pinned_projects_count >= 6:
            return dict(
                status='Fail',
                message='Pinned projects cant be more than 6'
            ), 409

        project_user.pinned = True
        project_user.save()

        return dict(
            status='Success',
            message=f'Project {project_id} pinned successfully'
        ), 200

    @jwt_required
    def delete(self, project_id):

        current_user_id = get_jwt_identity()
        project = Project.get_by_id(project_id)

        project_user = ProjectUser.query.filter_by(
            user_id=current_user_id, project_id=project_id).first()

        if not is_authorised_project_user(project, current_user_id, 'member'):
            return dict(status='fail', message='unauthorised'), 403

        project_user.pinned = False
        project_user.save()

        return dict(
            status='Success',
            message=f'Project {project_id} unpinned successfully'
        ), 200
