"""add_inbound_email_tables

Revision ID: 10f061e424e9
Revises: 8a2c3f5d9e1b
Create Date: 2026-01-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '10f061e424e9'
down_revision: Union[str, None] = '8a2c3f5d9e1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create inbound_email_addresses table
    op.create_table(
        'inbound_email_addresses',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('created_by_user_id', sa.UUID(), nullable=True),
        sa.Column('email_prefix', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('allowed_senders', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Job configuration fields
        sa.Column('schema_definition_id', sa.UUID(), nullable=True),
        sa.Column('extraction_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('custom_prompt', sa.Text(), nullable=True),
        sa.Column('model_provider', sa.String(50), nullable=False, server_default='google'),
        sa.Column('model_name', sa.String(100), nullable=False, server_default='gemini-2.5-flash'),
        sa.Column('split_mode', sa.String(20), nullable=False, server_default='batch'),
        sa.Column('extraction_mode', sa.String(20), nullable=False, server_default='vllm'),
        sa.Column('markdown_converter', sa.String(50), nullable=True),
        sa.Column('markdown_format', sa.String(50), nullable=True),
        sa.Column('callback_url', sa.String(1024), nullable=True),
        sa.Column('llamaextract_mode', sa.String(20), nullable=True),
        sa.Column('llamaextract_target', sa.String(20), nullable=True),
        # Statistics
        sa.Column('emails_received_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('documents_processed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_email_at', sa.DateTime(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['schema_definition_id'], ['schema_definitions.id'], ondelete='SET NULL'),
    )

    # Create indexes for inbound_email_addresses
    op.create_index('idx_inbound_email_addresses_tenant_id', 'inbound_email_addresses', ['tenant_id'])
    op.create_index('idx_inbound_email_addresses_is_active', 'inbound_email_addresses', ['is_active'])
    op.create_index('idx_inbound_email_addresses_email_prefix', 'inbound_email_addresses', ['email_prefix'], unique=True)
    op.create_index('idx_inbound_email_addresses_created_at', 'inbound_email_addresses', ['created_at'])

    # Create inbound_email_logs table
    op.create_table(
        'inbound_email_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('inbound_email_address_id', sa.UUID(), nullable=False),
        # Sender information
        sa.Column('sender_email', sa.String(255), nullable=False),
        sa.Column('sender_name', sa.String(255), nullable=True),
        sa.Column('subject', sa.String(1000), nullable=True),
        sa.Column('message_id', sa.String(500), nullable=True),
        # Processing status
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        # Attachment details
        sa.Column('attachment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('attachment_names', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('total_attachment_size_bytes', sa.Integer(), nullable=True),
        # Created entities
        sa.Column('document_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('extraction_job_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Raw metadata
        sa.Column('raw_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Timestamps
        sa.Column('received_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['inbound_email_address_id'], ['inbound_email_addresses.id'], ondelete='CASCADE'),
    )

    # Create indexes for inbound_email_logs
    op.create_index('idx_inbound_email_logs_inbound_email_address_id', 'inbound_email_logs', ['inbound_email_address_id'])
    op.create_index('idx_inbound_email_logs_status', 'inbound_email_logs', ['status'])
    op.create_index('idx_inbound_email_logs_sender_email', 'inbound_email_logs', ['sender_email'])
    op.create_index('idx_inbound_email_logs_received_at', 'inbound_email_logs', ['received_at'])

    # Add permissions for inbound emails
    op.execute("""
        INSERT INTO permissions (id, name, description, resource, action, created_at)
        VALUES
            (gen_random_uuid(), 'inbound_emails:create', 'Create inbound email addresses', 'inbound_emails', 'create', NOW()),
            (gen_random_uuid(), 'inbound_emails:read', 'Read inbound email addresses', 'inbound_emails', 'read', NOW()),
            (gen_random_uuid(), 'inbound_emails:update', 'Update inbound email addresses', 'inbound_emails', 'update', NOW()),
            (gen_random_uuid(), 'inbound_emails:delete', 'Delete inbound email addresses', 'inbound_emails', 'delete', NOW())
        ON CONFLICT (name) DO NOTHING;
    """)

    # Grant permissions to admin and member roles
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('admin', 'member')
        AND p.name IN ('inbound_emails:create', 'inbound_emails:read', 'inbound_emails:update', 'inbound_emails:delete')
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    # Remove role permissions first
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE name LIKE 'inbound_emails:%'
        );
    """)

    # Remove permissions
    op.execute("""
        DELETE FROM permissions WHERE name LIKE 'inbound_emails:%';
    """)

    # Drop indexes for inbound_email_logs
    op.drop_index('idx_inbound_email_logs_received_at', table_name='inbound_email_logs')
    op.drop_index('idx_inbound_email_logs_sender_email', table_name='inbound_email_logs')
    op.drop_index('idx_inbound_email_logs_status', table_name='inbound_email_logs')
    op.drop_index('idx_inbound_email_logs_inbound_email_address_id', table_name='inbound_email_logs')

    # Drop inbound_email_logs table
    op.drop_table('inbound_email_logs')

    # Drop indexes for inbound_email_addresses
    op.drop_index('idx_inbound_email_addresses_created_at', table_name='inbound_email_addresses')
    op.drop_index('idx_inbound_email_addresses_email_prefix', table_name='inbound_email_addresses')
    op.drop_index('idx_inbound_email_addresses_is_active', table_name='inbound_email_addresses')
    op.drop_index('idx_inbound_email_addresses_tenant_id', table_name='inbound_email_addresses')

    # Drop inbound_email_addresses table
    op.drop_table('inbound_email_addresses')
