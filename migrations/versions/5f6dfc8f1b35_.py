"""empty message

Revision ID: 5f6dfc8f1b35
Revises: 97be381a8980
Create Date: 2024-06-11 18:48:32.755879

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5f6dfc8f1b35'
down_revision = '97be381a8980'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('is_public', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'is_public')
    # ### end Alembic commands ###
