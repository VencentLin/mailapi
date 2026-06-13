"""foundation schema

Revision ID: 20260613_0001
Revises:
Create Date: 2026-06-13
"""

import sqlalchemy as sa
from alembic import op

revision = "20260613_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("key_prefix", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])

    op.create_table(
        "mail_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=False),
        sa.Column("owner_type", sa.String(length=20), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("default_proxy", sa.String(length=512), nullable=True),
        sa.Column("last_protocol", sa.String(length=32), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column("remark", sa.String(length=500), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_via", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mail_accounts_email", "mail_accounts", ["email"], unique=True)
    op.create_index("ix_mail_accounts_owner_type", "mail_accounts", ["owner_type"])
    op.create_index("ix_mail_accounts_owner_user_id", "mail_accounts", ["owner_user_id"])

    op.create_table(
        "mail_account_claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mail_account_id", sa.Integer(), sa.ForeignKey("mail_accounts.id"), nullable=False),
        sa.Column("claimed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("previous_owner_type", sa.String(length=40), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "mail_fetch_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("api_key_id", sa.Integer(), sa.ForeignKey("api_keys.id"), nullable=True),
        sa.Column("mail_account_id", sa.Integer(), sa.ForeignKey("mail_accounts.id"), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("mailbox", sa.String(length=40), nullable=False),
        sa.Column("operation", sa.String(length=40), nullable=False),
        sa.Column("source_protocol", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mail_fetch_logs_trace_id", "mail_fetch_logs", ["trace_id"])
    op.create_index("ix_mail_fetch_logs_user_id", "mail_fetch_logs", ["user_id"])
    op.create_index("ix_mail_fetch_logs_api_key_id", "mail_fetch_logs", ["api_key_id"])
    op.create_index("ix_mail_fetch_logs_mail_account_id", "mail_fetch_logs", ["mail_account_id"])
    op.create_index("ix_mail_fetch_logs_email", "mail_fetch_logs", ["email"])
    op.create_index("ix_mail_fetch_logs_error_code", "mail_fetch_logs", ["error_code"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.String(length=80), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_mail_fetch_logs_error_code", table_name="mail_fetch_logs")
    op.drop_index("ix_mail_fetch_logs_email", table_name="mail_fetch_logs")
    op.drop_index("ix_mail_fetch_logs_mail_account_id", table_name="mail_fetch_logs")
    op.drop_index("ix_mail_fetch_logs_api_key_id", table_name="mail_fetch_logs")
    op.drop_index("ix_mail_fetch_logs_user_id", table_name="mail_fetch_logs")
    op.drop_index("ix_mail_fetch_logs_trace_id", table_name="mail_fetch_logs")
    op.drop_table("mail_fetch_logs")

    op.drop_table("mail_account_claims")

    op.drop_index("ix_mail_accounts_owner_user_id", table_name="mail_accounts")
    op.drop_index("ix_mail_accounts_owner_type", table_name="mail_accounts")
    op.drop_index("ix_mail_accounts_email", table_name="mail_accounts")
    op.drop_table("mail_accounts")

    op.drop_index("ix_api_keys_key_prefix", table_name="api_keys")
    op.drop_index("ix_api_keys_user_id", table_name="api_keys")
    op.drop_table("api_keys")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
