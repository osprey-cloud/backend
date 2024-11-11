
import datetime
from flask_jwt_extended import get_jwt_identity
from app.models.user import User
# from app.tasks import celery_app
# from flask_pymongo import MongoClient
# import os
import requests
# import json
from app.helpers.crane_app_logger import logger
from flask import current_app
from app.schemas.project import ProjectListSchema
from app.schemas.tags import TagListSchema
from app.schemas.user import UserSchema
from app.schemas.app import AppSchema
from app.models.project import Project
from app.models.tags import Tag
from app.models.app import App
from flask import request



def log_activity(model: str, status: str, operation: str, description: str, a_user_id=None, a_app=None, a_project=None, a_cluster_id=None):
    LOGGER_APP_URL = current_app.config.get('LOGGER_APP_URL')
    if not LOGGER_APP_URL:
        return

    try:
        user_id = get_jwt_identity()
        user = User.get_by_id(user_id)
        user_email = user.email if user else None
        user_name = user.name if user else None
        date = str(datetime.datetime.now())
        a_app_id = None
        a_project_id = None
        a_tag_ids = None

        if a_app:
            a_app_id = a_app_id.id
            a_project = a_app.project
        if a_project:
            a_project_id = a_project.id
            a_tag_ids = [tag.tag_id for tag in a_project.tags]
            a_cluster_id = a_project.cluster_id

        data = {
            'user_id': user_id,
            'user_email': user_email,
            'user_name': user_name,
            'creation_date': date,
            'operation': operation,
            'model': model,
            'status': status,
            'description':  str(description),
            'a_user_id': str(a_user_id) if a_user_id else None,
            'a_app_id': str(a_app_id) if a_app_id else None,
            'a_project_id': str(a_project_id) if a_project_id else None,
            'a_tag_ids': list(map(str, a_tag_ids)) if a_tag_ids else None,
            'a_cluster_id': str(a_cluster_id) if a_cluster_id else None
        }
        result = requests.post(
            f"{LOGGER_APP_URL}/api/activities", json=data)
        log = result.json()
        logger.info(f"Logging activity: {log['message']}")
    except Exception as e:
        logger.error(f"Error logging activity: {str(e)}")
        pass

def get_logs(params):
    LOGGER_APP_URL = current_app.config.get('LOGGER_APP_URL')
    user_feed = requests.get(
        f"{LOGGER_APP_URL}/api/activities",
        params=params,
        headers={'Authorization': request.headers.get('Authorization')}
    )
    return user_feed

def filter_logs(user_activities):
    project_schema = ProjectListSchema()
    app_schema = AppSchema()
    tag_schema = TagListSchema()
    user_schema = UserSchema()

    public_activities = []

    for item in user_activities:
        if item['model'] == 'Project' or item['model'] == 'App' or item['model'] == 'Database':
            project = Project.get_by_id(item['a_project_id'])
            if not project.is_public:
                continue
            project_data, _ = project_schema.dump(project)
            item['project'] = project_schema.dump(project_data)[0]
            

        tags_list = item.get('a_tag_ids', [])
        if tags_list and len(tags_list) > 0:
            tags = []
            for tag_id in item['a_tag_ids']:
                tag = Tag.get_by_id(tag_id)
                tag_data, _ = tag_schema.dump(tag)
                tags.append(tag_data)
            item['tags'] = tags

        if item['model'] == 'App':
            app = App.get_by_id(item['a_app_id'])
            app_data, _ = app_schema.dump(app)
            item['app'] = app_schema.dump(app_data)[0]

        if item['model'] == 'User' and item['a_user_id'] != None:
            user = User.get_by_id(item['a_user_id'])
            user_data, _ = user_schema.dump(user)
            item['a_user'] = user_schema.dump(user_data)[0]

        elif item['model'] == 'Database':
            pass

        public_activities.append(item)

    return public_activities
