"""add_model_pricing_and_job_costs

Add model_pricing table for admin-configurable pricing and
cost fields to extraction_jobs for immutable cost storage.

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2025-12-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd4e5f6g7h8i9'
down_revision = 'c3d4e5f6g7h8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create model_pricing table
    op.create_table(
        'model_pricing',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('input_price_per_million', sa.Numeric(10, 4), nullable=False),
        sa.Column('output_price_per_million', sa.Numeric(10, 4), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('effective_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
        sa.CheckConstraint('effective_until IS NULL OR effective_until > effective_from', name='model_pricing_valid_dates'),
        sa.CheckConstraint('input_price_per_million >= 0 AND output_price_per_million >= 0', name='model_pricing_valid_prices'),
    )

    # 2. Create indexes for efficient lookups
    op.create_index('idx_model_pricing_model_name', 'model_pricing', ['model_name'])
    op.create_index('idx_model_pricing_effective_from', 'model_pricing', ['effective_from'])
    op.create_index('idx_model_pricing_active', 'model_pricing', ['is_active'], postgresql_where=sa.text('is_active = TRUE'))
    op.create_index(
        'idx_model_pricing_lookup',
        'model_pricing',
        ['model_name', 'effective_from', 'effective_until'],
        postgresql_where=sa.text('is_active = TRUE')
    )

    # 3. Add cost fields to extraction_jobs
    op.add_column('extraction_jobs', sa.Column('estimated_cost_usd', sa.Numeric(10, 6), nullable=True))
    op.add_column('extraction_jobs', sa.Column('pricing_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # 4. Create index for cost reporting
    op.create_index(
        'idx_extraction_jobs_cost',
        'extraction_jobs',
        ['estimated_cost_usd'],
        postgresql_where=sa.text('estimated_cost_usd IS NOT NULL')
    )

    # 5. Seed default pricing from current hardcoded values
    # Note: This uses the platform admin user created by seed.py
    op.execute("""
        INSERT INTO model_pricing (id, model_name, input_price_per_million, output_price_per_million,
                                   effective_from, is_active, created_by, created_at, notes)
        SELECT
            gen_random_uuid(),
            vals.model_name,
            vals.input_price,
            vals.output_price,
            CURRENT_TIMESTAMP,
            TRUE,
            (SELECT id FROM users WHERE email = 'admin@platform.local' LIMIT 1),
            CURRENT_TIMESTAMP,
            'Initial pricing from hardcoded defaults'
        FROM (VALUES
            ('gemini-2.5-flash', 0.15, 0.60),
            ('gpt-4-vision-preview', 10.00, 30.00),
            ('gpt-4o', 5.00, 15.00),
            ('deepseek-chat', 0.27, 1.10),
            ('default', 0.50, 1.50)
        ) AS vals(model_name, input_price, output_price)
        WHERE EXISTS (SELECT 1 FROM users WHERE email = 'admin@platform.local')
    """)


def downgrade() -> None:
    # Remove index from extraction_jobs
    op.drop_index('idx_extraction_jobs_cost', table_name='extraction_jobs')

    # Remove columns from extraction_jobs
    op.drop_column('extraction_jobs', 'pricing_snapshot')
    op.drop_column('extraction_jobs', 'estimated_cost_usd')

    # Drop indexes from model_pricing
    op.drop_index('idx_model_pricing_lookup', table_name='model_pricing')
    op.drop_index('idx_model_pricing_active', table_name='model_pricing')
    op.drop_index('idx_model_pricing_effective_from', table_name='model_pricing')
    op.drop_index('idx_model_pricing_model_name', table_name='model_pricing')

    # Drop model_pricing table
    op.drop_table('model_pricing')
