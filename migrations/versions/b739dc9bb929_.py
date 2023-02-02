"""empty message

Revision ID: b739dc9bb929
Revises: 9032e9181ebb
Create Date: 2023-02-02 11:01:19.699987

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b739dc9bb929'
down_revision = '9032e9181ebb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('credits', 'promotion_credits',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('credits', 'purchased_credits',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.add_column('user', sa.Column('last_seen', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'last_seen')
    op.alter_column('credits', 'purchased_credits',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('credits', 'promotion_credits',
               existing_type=sa.INTEGER(),
               nullable=True)
    # ### end Alembic commands ###
