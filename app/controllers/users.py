import json
from math import ceil
import os
from types import SimpleNamespace
from app.helpers.activity_logger import log_activity
from app.helpers.kube import disable_project, enable_project
from flask import current_app, render_template
from flask_restful import Resource, request
from flask_bcrypt import Bcrypt
from app.schemas import UserSchema, UserGraphSchema, ActivityLogSchema
from app.models.user import User
from app.models.project_users import ProjectFollowers
from app.models.role import Role
from app.helpers.confirmation import send_verification
from app.helpers.email import send_email
from app.helpers.token import validate_token
from app.helpers.decorators import admin_required
from app.helpers.pagination import paginate
from app.helpers.admin import is_admin
import requests
import secrets
import string
from sqlalchemy import Date, func, column, cast, and_, or_
from app.models import db
from datetime import datetime, timedelta
from app.models.anonymous_users import AnonymousUser
from app.models.project import Project
from app.models.project_users import ProjectUser
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt_claims
from app.helpers.admin import is_admin, is_authorised_project_user, is_owner_or_admin
from app.models import mongo
from bson.json_util import dumps
from app.models.app import App
from app.helpers.crane_app_logger import logger

from app.helpers.email_validator import is_valid_email


class UsersView(Resource):

    def post(self):
        """
        """

        user_schema = UserSchema()

        user_data = request.get_json()

        validated_user_data, errors = user_schema.load(user_data)

        if errors:
            return dict(status="fail", message=errors), 400

        email = validated_user_data.get('email', None)

        if not is_valid_email(email):
            return dict(status='fail', message=f'Invalid email address'), 400

        client_base_url = os.getenv(
            'CLIENT_BASE_URL',
            f'https://{request.host}/users'
        )

        # To do change to a frontend url
        verification_url = f"{client_base_url}/verify/"
        secret_key = current_app.config["SECRET_KEY"]
        password_salt = current_app.config["VERIFICATION_SALT"]
        sender = current_app.config["MAIL_DEFAULT_SENDER"]
        template = "user/verify.html"
        subject = "Please confirm your email"

        # get the customer role
        user_role = Role.find_first(name='customer')

        user_existant = User.query.filter_by(email=email).first()

        if user_existant:
            return dict(
                status="fail",
                message=f"Email {validated_user_data['email']} already in use."
            ), 400

        user = User(**validated_user_data)

        if user_role:
            user.roles.append(user_role)

        saved_user = user.save()

        if not saved_user:
            return dict(status='fail', message=f'Internal Server Error'), 500

        # send verification
        send_verification(
            email,
            user.name,
            verification_url,
            secret_key,
            password_salt,
            sender,
            current_app._get_current_object(),
            template,
            subject
        )

        # check if user exists in anonymous table and assign them to a project
        anonymous_user_exists = AnonymousUser.find_first(email=email)

        if anonymous_user_exists:
            project = Project.get_by_id(anonymous_user_exists.project_id)
            user_details = User.find_first(email=email)

            new_role = ProjectUser(
                role=anonymous_user_exists.role, user_id=user_details.id)
            project.users.append(new_role)
            saved_project_user = project.save()
            if not saved_project_user:
                return dict(status='fail', message=f'Internal Server Error'), 500
            deleted_anonymous_user = anonymous_user_exists.delete()

            if not deleted_anonymous_user:
                return dict(status='fail', message=f'Internal Server Error'), 500

        new_user_data, errors = user_schema.dumps(user)

        return dict(
            status='success',
            data=dict(user=json.loads(new_user_data))
        ), 201

    @jwt_required
    def get(self):
        """
        """
        current_user_id = get_jwt_identity()
        current_user = User.get_by_id(current_user_id)

        user_schema = UserSchema(many=True)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        keywords = request.args.get('keywords', '')
        verified = request.args.get('verified', None)
        is_beta = request.args.get('is_beta', None)
        series = request.args.get('series', 'false').lower() == 'true'

    # Graph filter data
        graph_filter_data = {
        'start': request.args.get('start', '2018-01-01'),
        'end': request.args.get('end', datetime.now().strftime('%Y-%m-%d')), 
        'set_by': request.args.get('set_by', 'month')
    }
        total_users = len(User.find_all())

        users = []
        # check if user is admin
        admin_role = Role.find_first(name='administrator')

        if admin_role not in current_user.roles:
            query = User.query
            if keywords:
                keyword_filter = or_(
                    User.name.ilike(f'%{keywords}%'),
                    User.email.ilike(f'%{keywords}%')
                )
                query = query.filter(keyword_filter)

            paginated = query.filter(User.verified == True).order_by(
                User.date_created.desc()).paginate(page=page, per_page=per_page, error_out=False)
            users = paginated.items
            pagination = {
                'total': paginated.total,
                'pages': paginated.pages,
                'page': paginated.page,
                'per_page': paginated.per_page,
                'next': paginated.next_num,
                'prev': paginated.prev_num
            }
            users_data, errors = user_schema.dumps(users)
            if errors:
                return dict(status='fail', message=errors), 400

            return dict(
                status='success',
                data=dict(pagination=pagination,
                          users=json.loads(users_data))
            ), 200

        meta_data = dict()
        meta_data['total_users'] = total_users
        meta_data['beta_users'] = User.query.filter_by(
            is_beta_user=True).count()
        meta_data['none_verified'] = User.query.filter_by(
            verified=False).count()
        meta_data['disabled'] = User.query.filter_by(
            disabled=True).count()

        if (keywords == ''):
            if (verified != None or is_beta != None):
                if (verified != None and is_beta != None):
                    paginated = User.query.filter(User.verified == verified, User.is_beta_user == is_beta).order_by(
                        User.date_created.desc()).paginate(page=page, per_page=per_page, error_out=False)
                else:
                    if (verified != None):
                        paginated = User.query.filter(User.verified == verified).order_by(
                            User.date_created.desc()).paginate(page=page, per_page=per_page, error_out=False)
                    else:
                        paginated = User.query.filter(User.is_beta_user == is_beta).order_by(
                            User.date_created.desc()).paginate(page=page, per_page=per_page, error_out=False)

                users = paginated.items
                pagination = {
                    'total': paginated.total,
                    'pages': paginated.pages,
                    'page': paginated.page,
                    'per_page': paginated.per_page,
                    'next': paginated.next_num,
                    'prev': paginated.prev_num
                }

            else:
                paginated = User.find_all(
                    paginate=True, page=page, per_page=per_page)
                users = paginated.items
                pagination = paginated.pagination
        else:
            if (verified != None or is_beta != None):
                if (verified != None and is_beta != None):
                    paginated = User.query.filter((User.name.ilike('%'+keywords+'%') | User.email.ilike('%'+keywords+'%')), User.verified == verified,
                                                  User.is_beta_user == is_beta).order_by(User.date_created.desc()).paginate(page=page, per_page=per_page, error_out=False)
                else:
                    if (verified != None):
                        paginated = User.query.filter((User.name.ilike('%'+keywords+'%') | User.email.ilike('%'+keywords+'%')), User.verified == verified).order_by(
                            User.date_created.desc()).paginate(page=page, per_page=per_page, error_out=False)
                    else:
                        paginated = User.query.filter((User.name.ilike('%'+keywords+'%') | User.email.ilike('%'+keywords+'%')), User.is_beta_user == is_beta).order_by(
                            User.date_created.desc()).paginate(page=page, per_page=per_page, error_out=False)

            else:
                paginated = User.query.filter(User.name.ilike('%'+keywords+'%') | User.email.ilike('%'+keywords+'%')).order_by(
                    User.date_created.desc()).paginate(page=page, per_page=per_page, error_out=False)
            users = paginated.items
            pagination = {
                'total': paginated.total,
                'pages': paginated.pages,
                'page': paginated.page,
                'per_page': paginated.per_page,
                'next': paginated.next_num,
                'prev': paginated.prev_num
            }

        users_data, errors = user_schema.dumps(users)

        if errors:
            return dict(status='fail', message=errors), 400
        


        if series:
            validated_query_data, errors = UserGraphSchema().load(graph_filter_data)
            if errors:
                return dict(status='fail', message=errors), 400

            start = validated_query_data['start']
            end = validated_query_data['end']
            set_by = validated_query_data['set_by']

            # Assuming User has a method for graph data
            graph_data = User.graph_data(start=start, end=end, set_by=set_by)

            return dict(
                status='success',
                data=dict(
                    meta_data=meta_data,
                    pagination=pagination,
                    graph_data=graph_data
                )
            ), 200
    
        return dict(
            status='success',
            data=dict(meta_data=meta_data, pagination=pagination,
                      users=json.loads(users_data))
        ), 200


class UserAdminUpdateView(Resource):

    @ admin_required
    def patch(self):
        try:
            user_schema = UserSchema(only=("is_beta_user",))

            user_data = request.get_json()
            user_id = user_data["user_id"]

            validate_user_data, errors = user_schema.load(user_data)

            if errors:
                return dict(status='fail', message=errors), 400

            user = User.get_by_id(user_id)
            if not user:
                return dict(
                    status='fail',
                    message=f'User {user_id} not found'
                ), 404

            updated = User.update(user, **validate_user_data)

            if not updated:
                return dict(
                    status='fail',
                    message='Internal Server Error'
                ), 500

            return dict(
                status='success',
                message=f'User {user_id} updated successfully'
            ), 200

        except Exception as e:
            return dict(status='fail', message=str(e)), 500


class UserLoginView(Resource):

    def post(self):
        """
        """

        user_schema = UserSchema(only=("email", "password"))

        token_schema = UserSchema()

        login_data = request.get_json()

        if login_data is None:
            return {"message": "No input data provided"}, 400

        validated_user_data, errors = user_schema.load(login_data)

        if errors:
            return dict(status='fail', message=errors), 400

        email = validated_user_data.get('email', None)
        password = validated_user_data.get('password', None)

        user = User.find_first(email=email)

        if not user:
            return dict(status='fail', message="login failed"), 401

        if user.disabled:
            return dict(
                status='fail',
                message=f'''User with id {
                    user.id} is disabled, please contact an admin'''
            ), 401

        if not user.verified:
            return dict(
                status='fail',
                message='email not verified', data=dict(verified=user.verified)
            ), 401

        # Updating user's last login
        user.last_seen = datetime.now()
        user.save()

        user_dict, errors = token_schema.dump(user)
        if user and user.password_is_valid(password):

            access_token = user.generate_token(user_dict)

            if not access_token:
                logger.error('Unable to generate access token')
                return dict(
                    status="fail",
                    message="Internal Server Error"
                ), 500

            return dict(
                status='success',
                data=dict(
                    access_token=access_token,
                    email=user.email,
                    username=user.username,
                    verified=user.verified,
                    id=str(user.id),
                    is_beta_user=user.is_beta_user,
                    name=user.name,
                )), 200

        return dict(status='fail', message="login failed"), 401


class UserDetailView(Resource):

    @jwt_required
    def get(self, user_id):
        """
        """
        user_schema = UserSchema()
        current_user_id = get_jwt_identity()
        current_user = User.get_by_id(current_user_id)

        user = User.get_by_id(user_id)

        if not user:
            return dict(
                status='fail',
                message=f'user {user_id} not found'
            ), 404

        user_data, errors = user_schema.dumps(user)

        # A count of the project records that they own in the ProjectFollowers' table is the count of users that follow their projects
        count_of_projects_followers = (
            db.session.query(func.count(ProjectFollowers.user_id))
            .join(Project, ProjectFollowers.project_id == Project.id)
            .filter(Project.owner_id == user_id)
            .scalar()
        )

        user_data = json.loads(user_data)

        user_data['projects_count'] = len(user.projects)
        user_data['following_count'] = user.followed.count()
        user_data['follower_count'] = user.followers.count()
        user_data['followed_projects_count'] = len(user.followed_projects)
        user_data['projects_followers_count'] = count_of_projects_followers

        # Identify if the person making the details request follows the user or not
        user_data['requesting_user_follows'] = user.is_followed_by(
            current_user)
        user_data['apps_count'] = sum(
            len(project.apps) for project in user.projects)

        if errors:
            return dict(status='fail', message=errors), 500

        return dict(status='success', data=dict(
            user=user_data)), 200

    def delete(self, user_id):
        """
        """

        try:
            user = User.get_by_id(user_id)

            if not user:
                return dict(
                    status='fail',
                    message=f'user {user_id} not found'
                ), 404

            deleted = user.delete()

            if not deleted:
                return dict(status='fail', message='deletion failed'), 500

            return dict(
                status='success',
                message=f'user {user_id} deleted successfully'
            ), 200

        except Exception as e:
            return dict(status='fail', message=str(e)), 500

    @jwt_required
    def patch(self, user_id):
        """
        """
        try:
            
            user_schema = UserSchema(only=("name","is_public", "organisation"),partial=True)
            user_data = request.get_json()

            current_user_id = get_jwt_identity()
            current_user_roles = get_jwt_claims()['roles']

            user = User.get_by_id(user_id)

            if (current_user_id != user_id):
                if (not is_admin(current_user_roles)):
                    return dict(
                        status='UnAuthorised',
                        message='You are not authorized to edit this users information'
                    ), 401

            validate_user_data, errors = user_schema.load(user_data)

            if errors:
                return dict(status='fail', message=errors), 400

            updated = User.update(user, **validate_user_data)

            if not updated:
                return dict(
                    status='fail',
                    message='Internal Server Error'
                ), 500

            return dict(
                status='success',
                message=f'User {user_id} updated successfully'
            ), 200

        except Exception as e:
            return dict(status='fail', message=str(e)), 500


class AdminLoginView(Resource):

    def post(self):
        """
        """

        user_schema = UserSchema(only=("email", "password"))

        token_schema = UserSchema()

        login_data = request.get_json()

        validated_user_data, errors = user_schema.load(login_data)

        if errors:
            return dict(status='fail', message=errors), 400

        email = validated_user_data.get('email', None)
        password = validated_user_data.get('password', None)

        user = User.find_first(email=email)
        admin_role = Role.find_first(name='administrator')

        if not user or not admin_role or (admin_role not in user.roles):
            return dict(status='fail', message="login failed"), 401

        if not user.verified:
            return dict(
                status='fail',
                message='Email not verified',
                data=dict(verified=user.verified)
            ), 401

        user_dict, errors = token_schema.dump(user)

        if user and user.password_is_valid(password):

            access_token = user.generate_token(user_dict)

            if not access_token:
                return dict(
                    status="fail", message="Internal Server Error"), 500

            return dict(
                status='success',
                data=dict(
                    access_token=access_token,
                    email=user.email,
                    username=user.username,
                    verified=user.verified,
                    id=str(user.id),
                )), 200

        return dict(status='fail', message="login failed"), 401


class UserEmailVerificationView(Resource):

    def get(self, token):
        """
        """

        user_schema = UserSchema()

        secret = current_app.config["SECRET_KEY"]
        salt = current_app.config["VERIFICATION_SALT"]

        email = validate_token(token, secret, salt)

        if not email:
            return dict(status="fail", message="invalid token"), 401

        user = User.find_first(**{'email': email})

        if not user:
            return dict(
                status='fail',
                message=f'User with email {email} not found'
            ), 404

        if user.verified:
            return dict(
                status='fail', message='Email is already verified'), 400

        user.verified = True

        user_saved = user.save()

        user_dict, _ = user_schema.dump(user)

        if user_saved:

            # generate access token
            access_token = user.generate_token(user_dict)

            if not access_token:
                return dict(
                    status='fail', message='Internal Server Error'), 500

            return dict(
                status='success',
                message='Email verified successfully',
                data=dict(
                    access_token=access_token,
                    email=user.email,
                    username=user.username,
                    verified=user.verified,
                    id=str(user.id),
                )), 200

        return dict(status='fail', message='Internal Server Error'), 500


class EmailVerificationRequest(Resource):

    def post(self):
        """
        """
        email_schema = UserSchema(only=("email",))

        request_data = request.get_json()

        validated_data, errors = email_schema.load(request_data)

        if errors:
            return dict(status='fail', message=errors), 400

        email = validated_data.get('email', None)
        client_base_url = os.getenv(
            'CLIENT_BASE_URL',
            f'https://{request.host}/users'
        )

        # To do, change to a frontend url
        verification_url = f"{client_base_url}/verify/"
        secret_key = current_app.config["SECRET_KEY"]
        password_salt = current_app.config["VERIFICATION_SALT"]
        sender = current_app.config["MAIL_DEFAULT_SENDER"]
        template = "user/verify.html"
        subject = "Please confirm your email"

        user = User.find_first(**{'email': email})

        if not user:
            return dict(
                status='fail',
                message=f'User with email {email} not found'
            ), 404

        # send verification
        send_verification(
            email,
            user.name,
            verification_url,
            secret_key,
            password_salt,
            sender,
            current_app._get_current_object(),
            template,
            subject
        )

        return dict(
            status='success',
            message=f'Verification link sent to {email}'
        ), 200


class ForgotPasswordView(Resource):

    def post(self):
        """
        """

        email_schema = UserSchema(only=("email",))

        request_data = request.get_json()
        validated_data, errors = email_schema.load(request_data)

        if errors:
            return dict(status='fail', message=errors), 400

        email = validated_data.get('email', None)
        client_base_url = os.getenv(
            'CLIENT_BASE_URL',
            f'https://{request.host}/users'
        )

        verification_url = f"{client_base_url}/reset_password/"
        secret_key = current_app.config["SECRET_KEY"]
        password_salt = current_app.config["PASSWORD_SALT"]
        sender = current_app.config["MAIL_DEFAULT_SENDER"]
        template = "user/reset.html"
        subject = "Password reset"

        user = User.find_first(**{'email': email})

        if not user:
            return dict(
                status='fail',
                message=f'User with email {email} not found'
            ), 404

        # send password reset link
        send_verification(
            email,
            user.name,
            verification_url,
            secret_key,
            password_salt,
            sender,
            current_app._get_current_object(),
            template,
            subject
        )

        return dict(
            status='success',
            message=f'Password reset link sent to {email}'
        ), 200


class OAuthView(Resource):

    def post(self):
        """
        """
        token_schema = UserSchema(partial=("password"),)

        request_data = request.get_json()

        if not request_data:
            return dict(
                status='fail',
                message='No data received'
            ), 400

        # Github Oauth
        code = request_data.get('code')
        if not code:
            return dict(
                status='fail',
                message='No code received'
            ), 400

        data = {
            'client_id': current_app.config.get('GITHUB_CLIENT_ID'),
            'client_secret': current_app.config.get('GITHUB_CLIENT_SECRET'),
            'code': code
        }

        # exchange the 'code' for an access token
        response = requests.post(
            url='https://github.com/login/oauth/access_token',
            data=data,
            headers={'Accept': 'application/json'}
        )

        if response.status_code != 200:
            return dict(status='fail', message="User authentication failed"), 401

        response_json = response.json()

        if response_json.get('error'):
            return dict(status='fail',
                        message=f"{response_json['error'], response_json['error_description']}"), 401

        access_token = response_json['access_token']

        # get the user details using the access token
        user_response = requests.get(
            url='https://api.github.com/user',
            headers={
                'Accept': 'application/json',
                'Authorization': f'token {access_token}'
            }
        )

        if user_response.status_code != 200:
            return dict(status='fail', message="User authentication failed"), 401

        res_json = user_response.json()

        name = res_json.get('name')
        if not name:
            name = res_json['login']
        username = res_json['login']
        email = res_json['email']

        if not email:
            new_res = requests.get(
                url='https://api.github.com/user/emails',
                headers={
                    'Accept': 'application/json',
                    'Authorization': f'token {access_token}'
                }
            )
            res_json = new_res.json()
            email = res_json[0]['email']

        user = User.find_first(email=email)

        # create the user
        if not user:
            user = User(
                email=email,
                name=name,
                password=''.join((secrets.choice(string.ascii_letters)
                                  for i in range(24))),
            )
            user.verified = True
            user.username = username
            saved_user = user.save()

            if not saved_user:
                return dict(status='fail', message=f'Internal Server Error'), 500

        # update user info
        user.name = name
        user.username = username
        user.verified = True
        updated_user = user.save()

        if not updated_user:
            return dict(status='fail', message='Internal Server Error'), 500

        # create user token
        user_dict, errors = token_schema.dump(user)

        access_token = user.generate_token(user_dict)

        if not access_token:
            return dict(
                status="fail",
                message="Internal Server Error"
            ), 500

        return dict(
            status='success',
            data=dict(
                access_token=access_token,
                email=user.email,
                name=user.name,
                username=user.username,
                verified=user.verified,
                id=str(user.id),
            )), 200


class ResetPasswordView(Resource):

    def post(self, token):

        password_schema = UserSchema(only=("password",))

        secret = current_app.config["SECRET_KEY"]
        salt = current_app.config["PASSWORD_SALT"]

        request_data = request.get_json()
        validated_data, errors = password_schema.load(request_data)

        if errors:
            return dict(status='fail', message=errors), 400

        password = validated_data['password']

        hashed_password = Bcrypt().generate_password_hash(password).decode()

        email = validate_token(token, secret, salt)

        if not email:
            return dict(status='fail', message="invalid token"), 401

        user = User.find_first(**{'email': email})

        if not user:
            return dict(
                status="fail",
                message=f'user with email {email} not found'
            ), 404

        if not user.verified:
            return dict(
                status='fail', message=f'email {email} is not verified'), 400

        user.password = hashed_password

        user_saved = user.save()

        if not user_saved:
            return dict(status='fail', message='internal server error'), 500

        return dict(
            status='success', message='password reset successfully'), 200


class UserDataSummaryView(Resource):

    @ admin_required
    def get(self):
        """
        Shows new users per month or year
        """
        user_filter_data = {
            'start': request.args.get('start', None),
            'end': request.args.get('end', None),
            'set_by': request.args.get('set_by', None)
        }

        verified = request.args.get('verified', None)
        is_beta = request.args.get('is_beta', None)
        total_users = len(User.find_all())

        meta_data = {'total_users': total_users}
        beta_count = User.query.with_entities(User.is_beta_user, func.count(
            User.is_beta_user)).group_by(User.is_beta_user).all()
        verified_count = User.query.with_entities(
            User.verified, func.count(User.verified)).group_by(User.verified).all()
        meta_data['is_beta_user'] = 0
        meta_data['verified'] = 0

        for key, value in beta_count:
            if key:
                meta_data['is_beta_user'] = value
                break

        for key, value in verified_count:
            if key:
                meta_data['verified'] = value
                break

        filter_schema = UserGraphSchema()

        validated_query_data, errors = filter_schema.load(user_filter_data)

        if errors:
            return dict(status='fail', message=errors), 400

        start = validated_query_data.get('start', '2018-01-01')
        end = validated_query_data.get('end', datetime.now())
        set_by = validated_query_data.get('set_by', 'month')

        if set_by == 'month':
            date_list = func.generate_series(
                start, end, '1 month').alias('month')
            month = column('month')
            if (verified != None or is_beta != None):
                if (verified != None):
                    user_data = db.session.query(month, func.count(User.id)).\
                        select_from(date_list).\
                        outerjoin(User, and_(func.date_trunc('month', User.date_created) == month, User.verified == verified)).\
                        group_by(month).\
                        order_by(month).\
                        all()
                else:
                    user_data = db.session.query(month, func.count(User.id)).\
                        select_from(date_list).\
                        outerjoin(User, and_(func.date_trunc('month', User.date_created) == month, User.is_beta_user == is_beta)).\
                        group_by(month).\
                        order_by(month).\
                        all()

            else:
                user_data = db.session.query(month, func.count(User.id)).\
                    select_from(date_list).\
                    outerjoin(User, func.date_trunc('month', User.date_created) == month).\
                    group_by(month).\
                    order_by(month).\
                    all()

        else:
            date_list = func.generate_series(
                start, end, '1 year').alias('year')
            year = column('year')

            if (verified != None or is_beta != None):
                if (verified != None):
                    user_data = db.session.query(year, func.count(User.id)).\
                        select_from(date_list).\
                        outerjoin(User, and_(func.date_trunc('year', User.date_created) == year, User.verified == verified)).\
                        group_by(year).\
                        order_by(year).\
                        all()
                else:
                    user_data = db.session.query(year, func.count(User.id)).\
                        select_from(date_list).\
                        outerjoin(User, and_(func.date_trunc('year', User.date_created) == year, User.is_beta_user == is_beta)).\
                        group_by(year).\
                        order_by(year).\
                        all()
            else:
                user_data = db.session.query(year, func.count(User.id)).\
                    select_from(date_list).\
                    outerjoin(User, func.date_trunc('year', User.date_created) == year).\
                    group_by(year).\
                    order_by(year).\
                    all()

        user_info = []

        for item in user_data:
            item_dict = {
                'year': item[0].year, 'month': item[0].month, 'value': item[1]
            }
            user_info.append(item_dict)
        return dict(
            status='success',
            data=dict(
                metadata=meta_data,
                graph_data=user_info)
        ), 200


class InActiveUsersView(Resource):
    computed_results = {}  # Dictionary to cache computed results
    current_date = None  # Variable to track the current date

    @ admin_required
    def get(self):
        user_schema = UserSchema(many=True)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        start_date = request.args.get("start")
        end_date = request.args.get("end")
        created_date = request.args.get("created")
        range = request.args.get("range", 0, type=int)
        today = datetime.now().date()
        keywords = request.args.get('keywords', None)

        if (start_date is not None and end_date is not None):
            if range:
                return dict(status='fail', message="Either pass `range` or `start` and `end` but not all the three."), 400
            try:
                # Standardize the date format
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                # Standardize the date format
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                return dict(status='fail', message="Invalid date format"), 400

        elif range:
            start_date = today
            end_date = today - timedelta(days=range)

        else:
            return dict(status='fail', message="Missing required parameters"), 400

        if start_date > today:
            return dict(status='fail', message="Entered date cannot be in the future"), 400

        if end_date > start_date:
            return dict(status='fail', message="Invalid date range: The start date must be earlier than the end date"), 400

        # Clear computed results for the each new day
        if self.current_date != today:
            self.current_date = today
            self.computed_results = {}

        date_range = (start_date, end_date, created_date)

        if date_range in self.computed_results:
            returned_users = self.computed_results[date_range]

        else:

            query = User.query.filter(
                cast(User.last_seen, Date) <= start_date,
                cast(User.last_seen, Date) >= end_date,
                User.verified == True
            )

            if keywords:
                keyword_filter = (User.name.ilike(
                    '%' + keywords + '%') | User.email.ilike('%' + keywords + '%'))
                query = query.filter(keyword_filter)

            if created_date:
                date_created_filter = (
                    cast(User.date_created, Date) <= today,
                    cast(User.date_created, Date) >= created_date
                )
                query = query.filter(date_created_filter)
            returned_users = query
            self.computed_results[date_range] = returned_users

        paginated = returned_users.paginate(
            page=page, per_page=per_page, error_out=False)
        users = paginated.items
        pagination = {
            'total': paginated.total,
            'pages': paginated.pages,
            'page': paginated.page,
            'per_page': paginated.per_page,
            'next': paginated.next_num,
            'prev': paginated.prev_num
        }

        users_data, errors = user_schema.dumps(users)

        if errors:
            return dict(status='fail', message=errors), 400

        return dict(
            status='success',
            data=dict(pagination=pagination, users=json.loads(users_data))
        ), 200


class UserDisableView(Resource):
    @ admin_required
    def post(self, user_id):

        user = User.get_by_id(user_id)
        if not user:
            return dict(status='fail', message=f'User with id {user_id} not found'), 404

        if user.disabled:
            return dict(status='fail', message=f'User with id {user_id} is already disabled'), 409

        for project in user.projects:
            if not project.disabled:
                disabled_project = disable_project(project)
                if type(disabled_project) == SimpleNamespace:
                    status_code = disabled_project.status_code if disabled_project.status_code else 500
                    return dict(status='fail', message=disabled_project.message), status_code

        try:
            # save user
            user.disabled = True
            user.save()
            log_activity('User', status='Success',
                         operation='Disable',
                         description='Disabled user Successfully',
                         a_user_id=user.id
                         )
            # send email
            html_layout = render_template(
                'user/user_disable_enable.html',
                email=user.email,
                name=user.name,
                status='disabled')
            send_email(
                user.email,
                'Status of your account',
                html_layout,
                current_app.config["MAIL_DEFAULT_SENDER"],
                current_app._get_current_object(),
            )

            return dict(
                status='success',
                message=f'user {user_id} disabled successfully'
            ), 200
        except Exception as err:
            log_activity('User', status='Failed',
                         operation='Disable',
                         description=err.body,
                         a_user_id=user.id
                         )
            return dict(
                status='fail',
                message=str(err)
            ), 500


class UserEnableView(Resource):
    @ jwt_required
    def post(self, user_id):

        user = User.get_by_id(user_id)
        if not user:
            return dict(status='fail', message=f'User with id {user_id} not found'), 404

        if not user.disabled:
            return dict(status='fail', message=f'User with id {user_id} is not disabled'), 409

        for project in user.projects:
            if project.disabled:
                enabled_project = enable_project(project)
                if type(enabled_project) == SimpleNamespace:
                    status_code = enabled_project.status_code if enabled_project.status_code else 500
                    return dict(status='fail', message=enabled_project.message), status_code
        try:
            # save user
            user.disabled = False
            user.save()
            log_activity('User', status='Success',
                         operation='Enable',
                         description='Enabled user Successfully',
                         a_user_id=user.id
                         )
            html_layout = render_template(
                'user/user_disable_enable.html',
                email=user.email,
                name=user.name,
                status='enabled')
            send_email(
                user.email,
                'Status of your account',
                html_layout,
                current_app.config["MAIL_DEFAULT_SENDER"],
                current_app._get_current_object(),
            )
            return dict(
                status='success',
                message=f'user {user_id} Enabled successfully'
            ), 200

        except Exception as err:
            log_activity('User', status='Failed',
                         operation='Enable',
                         description=err.body,
                         a_user_id=user.id
                         )
            return dict(
                status='fail',
                message=str(err)
            ), 500


class UserFollowView(Resource):
    @ jwt_required
    def post(self, user_id):
        current_user_id = get_jwt_identity()
        current_user = User.get_by_id(current_user_id)
        user = User.get_by_id(user_id)

        if not user:
            return dict(status='fail', message=f'User with id {user_id} not found'), 404

        if user == current_user:
            return dict(status='fail', message='You cannot follow yourself'), 400

        if user in current_user.followed:
            return dict(status='fail', message=f'You are already following user with id {user_id}'), 409

        current_user.followed.append(user)
        saved_user = current_user.save()

        if not saved_user:
            log_activity('User', status='Failed',
                         operation='Follow',
                         description=f'Failed to follow user: {user.name} ',
                         a_user_id=user_id
                         )
            return dict(status='fail', message='Internal Server Error'), 500

        log_activity('User', status='Success',
                     operation='Follow',
                     description=f'Started following user: {user.name}',
                     a_user_id=user_id
                     )
        return dict(
            status='success',
            message=f'You are now following user with id {user_id}'
        ), 201

    @ jwt_required
    def get(self, user_id):
        user = User.get_by_id(user_id)
        user_schema = UserSchema(many=True)

        followed = user.followed.all()
        users_data, errors = user_schema.dumps(followed)

        if errors:
            return dict(status='fail', message=errors), 400

        return dict(
            status='success',
            data=dict(following=json.loads(users_data))
        ), 200

    @ jwt_required
    def delete(self, user_id):
        current_user_id = get_jwt_identity()
        current_user = User.get_by_id(current_user_id)
        user = User.get_by_id(user_id)

        if not user:
            return dict(status='fail', message=f'User with id {user_id} not found'), 404

        if user not in current_user.followed:
            return dict(status='fail', message=f'You are not following user with id {user_id}'), 409

        current_user.followed.remove(user)
        saved_user = current_user.save()

        if not saved_user:
            log_activity('User', status='Failed',
                         operation='Unfollow',
                         description=f'Failed to un-follow user:  {user.name}',
                         a_user_id=user_id
                         )
            return dict(status='fail', message='Internal Server Error'), 500

        log_activity('User', status='Success',
                     operation='Unfollow',
                     description=f'Un-followed user: {user.name}',
                     a_user_id=user_id
                     )
        return dict(
            status='success',
            message=f'You have unfollowed user with id {user_id}'
        ), 200


class UserFollowersView(Resource):
    @ jwt_required
    def get(self, user_id):
        user = User.get_by_id(user_id)
        user_schema = UserSchema(many=True)

        followers = user.followers
        users_data, errors = user_schema.dumps(followers)

        if errors:
            return dict(status='fail', message=errors), 400

        return dict(
            status='success',
            data=dict(followers=json.loads(users_data))
        ), 200
