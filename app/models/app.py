from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text as sa_text
from app.models import db
from app.models.model_mixin import ModelMixin, SoftDeleteQuery
from app.models.app_state import AppState


class App(ModelMixin):
    __tablename__ = 'app'
    # SoftDeleteQuery is used to filter out deleted records
    query_class = SoftDeleteQuery

    id = db.Column(UUID(as_uuid=True), primary_key=True,
                   server_default=sa_text("uuid_generate_v4()"))
    name = db.Column(db.String(256), nullable=True)
    image = db.Column(db.String(256), nullable=True)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'project.id'), nullable=False)
    url = db.Column(db.String(256), nullable=True)
    alias = db.Column(db.String(256), nullable=True, unique=True)
    port = db.Column(db.Integer, nullable=False)
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())
    deleted = db.Column(db.Boolean, default=False)
    has_custom_domain = db.Column(db.Boolean, nullable=False, default=False)
    command = db.Column(db.String(256), nullable=True)
    replicas = db.Column(db.Integer, nullable=True)
    private_image = db.Column(db.Boolean, default=False)
    disabled = db.Column(db.Boolean, default=False)
    admin_disabled = db.Column(db.Boolean, default=False)
    app_status = db.relationship(
        "AppState", backref='app_state', lazy=True)
    is_ai = db.Column(db.Boolean, default=False)
    is_notebook = db.Column(db.Boolean, default=False)
    is_modal = db.Column(db.Boolean, default=False)
    model_image_uri = db.Column(db.String(256), nullable=True)
    api_type = db.Column(db.String(256), nullable=True)
    model_server = db.Column(db.String(256), nullable=True)
