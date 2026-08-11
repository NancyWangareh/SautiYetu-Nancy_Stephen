"""add_budget_type_and_line_items

Revision ID: 9a3294c7b25f
Revises: bd48873cbc1f
Create Date: 2026-08-11 06:56:57.358389

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a3294c7b25f'
down_revision: Union[str, Sequence[str], None] = 'bd48873cbc1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('budget_documents', sa.Column('budget_type', sa.String(length=20), nullable=True))

    # SQLite requires batch mode for ALTER with FK constraints
    with op.batch_alter_table('budget_matches') as batch_op:
        batch_op.add_column(sa.Column('matched_line_item_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('matched_amount', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_budget_matches_line_item',
            'budget_line_items',
            ['matched_line_item_id'], ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('budget_matches') as batch_op:
        batch_op.drop_constraint('fk_budget_matches_line_item', type_='foreignkey')
        batch_op.drop_column('matched_amount')
        batch_op.drop_column('matched_line_item_id')

    op.drop_column('budget_documents', 'budget_type')