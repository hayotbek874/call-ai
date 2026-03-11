from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1f1c9a3da8e"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""CREATE EXTENSION IF NOT EXISTS "uuid-ossp";""")
    op.execute("""GRANT ALL PRIVILEGES ON DATABASE stratix TO stratix;""")

    op.create_table(
        "admins",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admins_username"), "admins", ["username"], unique=True)
    op.create_table(
        "calls",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("asterisk_call_id", sa.String(length=100), nullable=False),
        sa.Column("duration", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("recording_path", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=5), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_calls_phone"), "calls", ["phone"], unique=False)
    op.create_table(
        "client_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "client_type", sa.Enum("CRM", name="clienttype", native_enum=False), nullable=False
        ),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_type", sa.String(length=50), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("additional_data", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_client_tokens_client_type"), "client_tokens", ["client_type"], unique=False
    )
    op.create_index(
        "ix_client_tokens_client_type_expires_at",
        "client_tokens",
        ["client_type", "expires_at"],
        unique=False,
    )
    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(length=50), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_conversation_messages_phone"), "conversation_messages", ["phone"], unique=False
    )
    op.create_table(
        "conversation_summaries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_conversation_summaries_phone"), "conversation_summaries", ["phone"], unique=False
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("product_lot", sa.String(length=20), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("size", sa.String(length=20), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("delivery_cost", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("payment_method", sa.String(length=20), nullable=False),
        sa.Column("crm_lead_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_phone"), "orders", ["phone"], unique=False)
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=5), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("telegram_username", sa.String(length=255), nullable=True),
        sa.Column("telegram_first_name", sa.String(length=255), nullable=True),
        sa.Column("telegram_last_name", sa.String(length=255), nullable=True),
        sa.Column("instagram_id", sa.String(length=100), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instagram_id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_users_phone"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_orders_phone"), table_name="orders")
    op.drop_table("orders")
    op.drop_index(op.f("ix_conversation_summaries_phone"), table_name="conversation_summaries")
    op.drop_table("conversation_summaries")
    op.drop_index(op.f("ix_conversation_messages_phone"), table_name="conversation_messages")
    op.drop_table("conversation_messages")
    op.drop_index("ix_client_tokens_client_type_expires_at", table_name="client_tokens")
    op.drop_index(op.f("ix_client_tokens_client_type"), table_name="client_tokens")
    op.drop_table("client_tokens")
    op.drop_index(op.f("ix_calls_phone"), table_name="calls")
    op.drop_table("calls")
    op.drop_index(op.f("ix_admins_username"), table_name="admins")
    op.drop_table("admins")
    # ### end Alembic commands ###
