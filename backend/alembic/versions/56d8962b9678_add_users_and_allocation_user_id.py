"""add users and allocation user_id

Revision ID: 56d8962b9678
Revises: 954fa84e6c85
Create Date: 2026-07-26 00:29:15.293800

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '56d8962b9678'
down_revision: Union[str, Sequence[str], None] = '954fa84e6c85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # La contrainte FK n'est pas créée au niveau SQLite : ALTER TABLE ADD
    # CONSTRAINT n'existe pas, et un batch_alter_table reconstruirait la table
    # allocations (qui porte déjà une FK auto-référente parent_id) sur des
    # données réelles. SQLite n'applique pas les FK par défaut de toute façon ;
    # la relation reste déclarée côté modèle SQLAlchemy.
    op.add_column("allocations", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_allocations_user_id"), "allocations", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_allocations_user_id"), table_name="allocations")
    op.drop_column("allocations", "user_id")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
