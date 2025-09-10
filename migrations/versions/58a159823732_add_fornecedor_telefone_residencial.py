"""add fornecedor.telefone_residencial

Revision ID: 58a159823732
Revises: 92d5b5c0c21d
Create Date: 2025-09-10 23:41:18.199152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58a159823732'
down_revision: Union[str, Sequence[str], None] = '92d5b5c0c21d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
