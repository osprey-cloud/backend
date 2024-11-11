from app.models.project import Project
from app.models.app import App
from app.models.user import User
from app.models.tags import Tag
from app.schemas.tags import TagListSchema
from app.schemas.user import UserListSchema
from app.schemas.project import ProjectListSchema
from app.schemas import AppSchema
from flask import current_app
from flask_restful import Resource, request
from app.models.project import Project
from flask_jwt_extended import jwt_required
import json
from sqlalchemy import or_


class GenericSearchView(Resource):
    @jwt_required
    def get(self):
        keywords = request.args.get('keywords', '')
        search_type = request.args.get('type', None)

        search_type_enum = ['projects', 'apps', 'users', 'tags']
        if search_type and search_type not in search_type_enum:
            return dict(
                message=f"""Invalid type provided, should be one of {
                    search_type_enum}"""
            ), 400

        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        # Schemas
        projectSchema = ProjectListSchema(many=True)
        appSchema = AppSchema(many=True)
        userSchema = UserListSchema(many=True)
        tagSchema = TagListSchema(many=True)

        overall_pagination = {
            'total': 0,
            'pages': 0,
            'page': page,
            'per_page': per_page,
            'next': None,
            'prev': page-1 if page > 1 else None
        }

        def create_pagination(pagination):
            overall_pagination['total'] = max(
                overall_pagination['total'], pagination.total)
            overall_pagination['pages'] = max(
                overall_pagination['pages'], pagination.pages)
            if pagination.next_num:
                if overall_pagination['next'] != None:
                    overall_pagination['next'] = max(overall_pagination.get(
                        'next', 0), pagination.next_num) or None
                else:
                    overall_pagination['next'] = pagination.next_num

            return {
                'total': pagination.total,
                'pages': pagination.pages,
                'page': pagination.page,
                'per_page': pagination.per_page,
                'next': pagination.next_num,
                'prev': pagination.prev_num
            }

        return_object = {}

        # Projects
        if not search_type or search_type == 'projects':
            projects_pagination = Project.query.filter(
                Project.name.ilike('%'+keywords+'%'),
                # Project.is_public == True
            ).order_by(Project.date_created.desc()).paginate(
                page=int(page), per_page=int(per_page), error_out=False)
            project_data, _ = projectSchema.dumps(projects_pagination.items)
            if projects_pagination.total > 0:
                return_object['projects'] = {
                    'pagination': create_pagination(projects_pagination),
                    'items': json.loads(project_data)
                }

        # Apps
        if not search_type or search_type == 'apps':
            apps_pagination = App.query.filter(
                App.name.ilike('%'+keywords+'%')
            ).order_by(App.date_created.desc()).paginate(
                page=int(page), per_page=int(per_page), error_out=False)
            app_data, _ = appSchema.dumps(apps_pagination.items)
            if apps_pagination.total > 0:
                return_object['apps'] = {
                    'pagination': create_pagination(apps_pagination),
                    'items': json.loads(app_data)
                }

        # Tags
        if not search_type or search_type == 'tags':
            tags_pagination = Tag.query.filter(
                Tag.name.ilike('%'+keywords+'%')
            ).order_by(Tag.date_created.desc()).paginate(
                page=int(page), per_page=int(per_page), error_out=False)
            tags_data, _ = tagSchema.dumps(tags_pagination.items)
            if tags_pagination.total > 0:
                return_object['tags'] = {
                    'pagination': create_pagination(tags_pagination),
                    'items': json.loads(tags_data)
                }

        # Users
        if not search_type or search_type == 'users':
            search_filter = or_(
                User.name.ilike(f'%{keywords}%'),
                User.email.ilike(f'%{keywords}%')
            )
            users_pagination = User.query.filter(search_filter).order_by(
                User.date_created.desc()
            ).paginate(
                page=int(page), per_page=int(per_page), error_out=False
            )
            users_data, _ = userSchema.dumps(users_pagination.items)
            if users_pagination.total > 0:
                return_object['users'] = {
                    'pagination': create_pagination(users_pagination),
                    'items': json.loads(users_data)
                }

        return dict(
            pagination=overall_pagination,
            data=return_object
        ), 200
