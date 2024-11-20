from flask import current_app
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text as sa_text
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token
from datetime import timedelta

from ..models import db

from app.models.model_mixin import ModelMixin


class Followers(ModelMixin):
    """ followers table definition """

    _tablename_ = "followers"
    follower_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey('user.id'), nullable=False, primary_key=True)
    followed_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey('user.id'), nullable=False, primary_key=True)

    def __init__(self, follower_id, followed_id):
        """ initialize with follower_id and followed_id """
        self.follower_id = follower_id
        self.followed_id = followed_id


class User(ModelMixin):
    """ user table definition """

    _tablename_ = "users"

    # fields of the user table
    id = db.Column(UUID(as_uuid=True), primary_key=True,
                   server_default=sa_text("uuid_generate_v4()"))
    email = db.Column(db.String(256), unique=True, nullable=False, default="")
    name = db.Column(db.String(256), nullable=False, default="")
    username = db.Column(db.String(256), nullable=False, default="")
    password = db.Column(db.String(256), nullable=False, default="")
    verified = db.Column(db.Boolean, nullable=False, default=False)
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())
    last_seen = db.Column(db.DateTime, default=db.func.current_timestamp())
    projects = db.relationship('Project', backref='owner', lazy=True)
    organisation = db.Column(db.String(256), nullable=True, default="")
    other_projects = db.relationship('ProjectUser', back_populates='user')
    is_beta_user = db.Column(db.Boolean, nullable=False, default=False)
    credits = db.relationship('Credit', backref='user', lazy=True)
    credit_assignments = db.relationship(
        'CreditAssignment', backref='user', lazy=True)
    disabled = db.Column(db.Boolean, default=False)
    admin_disabled = db.Column(db.Boolean, default=False)
    followed_projects = db.relationship(
        'ProjectFollowers', back_populates='user')
    is_public = db.Column(db.Boolean, default=True)
    followed_tags = db.relationship(
        'TagFollowers', back_populates='user')

    def __init__(self, email, name, password, organisation=None):
        """ initialize with email, username and password """
        self.email = email
        self.name = name
        self.username = name
        self.organisation = organisation
        self.password = Bcrypt().generate_password_hash(password).decode()

    def password_is_valid(self, password):
        """ checks the password against it's hash to validate the user's password """
        return Bcrypt().check_password_hash(self.password, password)

    def generate_token(self, user):
        """ generates the access token """

        # set token expiry period
        expiry = timedelta(days=10)

        return create_access_token(user, expires_delta=expiry)

    followed = db.relationship(
        'User', secondary='followers',
        primaryjoin=(Followers.follower_id == id),
        secondaryjoin=(Followers.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic'
    )

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(Followers.followed_id == user.id).count() > 0

    def is_followed_by(self, user):
        return self.followers.filter(Followers.follower_id == user.id).count() > 0

    def __repr__(self):
        return "<User: {}>".format(self.email)
