"""add_platform_api_tables

Revision ID: e7c20523cf4f
Revises: 10f061e424e9
Create Date: 2026-01-05 18:11:31.685876

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e7c20523cf4f'
down_revision: Union[str, None] = '10f061e424e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create platform_applications table
    op.create_table(
        'platform_applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('webhook_url', sa.String(500), nullable=True),
        sa.Column('webhook_secret', sa.String(255), nullable=True),
        sa.Column('allowed_ips', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('rate_limit_per_hour', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_platform_applications_slug', 'platform_applications', ['slug'], unique=True)
    op.create_index('idx_platform_applications_is_active', 'platform_applications', ['is_active'])
    op.create_index('idx_platform_applications_created_at', 'platform_applications', ['created_at'])

    # Create platform_api_keys table
    op.create_table(
        'platform_api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False),
        sa.Column('token_prefix', sa.String(24), nullable=False),
        sa.Column('scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_ip', sa.String(45), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['platform_applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['revoked_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_platform_api_keys_application_id', 'platform_api_keys', ['application_id'])
    op.create_index('idx_platform_api_keys_token_hash', 'platform_api_keys', ['token_hash'], unique=True)
    op.create_index('idx_platform_api_keys_token_prefix', 'platform_api_keys', ['token_prefix'])
    op.create_index('idx_platform_api_keys_is_active', 'platform_api_keys', ['is_active'])
    op.create_index('idx_platform_api_keys_expires_at', 'platform_api_keys', ['expires_at'])

    # Create platform_audit_logs table
    op.create_table(
        'platform_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('endpoint', sa.String(255), nullable=False),
        sa.Column('method', sa.String(10), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('request_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['application_id'], ['platform_applications.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['api_key_id'], ['platform_api_keys.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_platform_audit_logs_application_id', 'platform_audit_logs', ['application_id'])
    op.create_index('idx_platform_audit_logs_action', 'platform_audit_logs', ['action'])
    op.create_index('idx_platform_audit_logs_resource_type', 'platform_audit_logs', ['resource_type'])
    op.create_index('idx_platform_audit_logs_created_at', 'platform_audit_logs', ['created_at'])
    op.create_index(
        'idx_platform_audit_logs_app_action_created',
        'platform_audit_logs',
        ['application_id', 'action', 'created_at']
    )


def downgrade() -> None:
    # Drop platform_audit_logs table
    op.drop_index('idx_platform_audit_logs_app_action_created', table_name='platform_audit_logs')
    op.drop_index('idx_platform_audit_logs_created_at', table_name='platform_audit_logs')
    op.drop_index('idx_platform_audit_logs_resource_type', table_name='platform_audit_logs')
    op.drop_index('idx_platform_audit_logs_action', table_name='platform_audit_logs')
    op.drop_index('idx_platform_audit_logs_application_id', table_name='platform_audit_logs')
    op.drop_table('platform_audit_logs')

    # Drop platform_api_keys table
    op.drop_index('idx_platform_api_keys_expires_at', table_name='platform_api_keys')
    op.drop_index('idx_platform_api_keys_is_active', table_name='platform_api_keys')
    op.drop_index('idx_platform_api_keys_token_prefix', table_name='platform_api_keys')
    op.drop_index('idx_platform_api_keys_token_hash', table_name='platform_api_keys')
    op.drop_index('idx_platform_api_keys_application_id', table_name='platform_api_keys')
    op.drop_table('platform_api_keys')

    # Drop platform_applications table
    op.drop_index('idx_platform_applications_created_at', table_name='platform_applications')
    op.drop_index('idx_platform_applications_is_active', table_name='platform_applications')
    op.drop_index('idx_platform_applications_slug', table_name='platform_applications')
    op.drop_table('platform_applications')
