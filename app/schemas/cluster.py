from marshmallow import Schema, fields, validate


class ClusterSchema(Schema):

    id = fields.UUID(dump_only=True)
    name = fields.String(required=True, error_message={
        "required": "name is required"},
        validate=[
            validate.Regexp(
                regex=r'^(?!\s*$)', error='name should be a valid string'
            ),
    ])
    host = fields.String(required=True, error_message={
        "required": "host is required"},
        validate=[
            validate.Regexp(
                regex=r'^(?!\s*$)', error='host should be a valid string'
            ),
    ])
    token = fields.String(load_only=True, required=True, error_message={
        "required": "token is required"},
        validate=[
            validate.Regexp(
                regex=r'^(?!\s*$)', error='token should be a valid string'
            ),
    ])
    description = fields.String(required=True, error_message={
        "required": "description is required"},
        validate=[
            validate.Regexp(
                regex=r'^(?!\s*$)', error='description should be a valid string'
            ),
    ])
    prometheus_url = fields.String(
        validate=[
            validate.Regexp(
                regex=r'^(?!\s*$)', error='host should be a valid string'
            ),
        ]
    )
    cost_modal_url = fields.String(
        validate=[
            validate.Regexp(
                regex=r'^(?!\s*$)', error='host should be a valid string'
            ),
        ]
    )
    sub_domain = fields.String(required=True)
    date_created = fields.Date(dump_only=True)


class ClusterDetailSchema(ClusterSchema):
    token = fields.String()
