"""'Init'

Revision ID: 645e793bc57c
Revises: f6978d2c9a7d
Create Date: 2024-07-25 01:23:26.430812

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '645e793bc57c'
down_revision: Union[str, None] = 'f6978d2c9a7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('contacts', sa.Column('birthday', sa.Date(), nullable=False))
    op.drop_column('contacts', 'birthdate')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('contacts', sa.Column('birthdate', sa.DATE(), autoincrement=False, nullable=False))
    op.drop_column('contacts', 'birthday')
    # ### end Alembic commands ###
