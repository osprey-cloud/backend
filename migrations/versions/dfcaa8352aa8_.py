"""empty message

Revision ID: dfcaa8352aa8
Revises: da1b79f5b466
Create Date: 2022-05-13 13:12:16.012712

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'dfcaa8352aa8'
down_revision = 'da1b79f5b466'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('billing_metrics', sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False))
    op.create_foreign_key(None, 'billing_metrics', 'billing_invoices', ['invoice_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'billing_metrics', type_='foreignkey')
    op.drop_column('billing_metrics', 'invoice_id')
    # ### end Alembic commands ###
