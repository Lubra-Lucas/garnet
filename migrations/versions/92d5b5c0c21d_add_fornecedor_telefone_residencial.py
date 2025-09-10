"""add fornecedor.telefone_residencial

Revision ID: 92d5b5c0c21d
Revises: 068d239bc4ff
Create Date: 2025-09-10 23:35:44.015038

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92d5b5c0c21d'
down_revision: Union[str, Sequence[str], None] = '068d239bc4ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
