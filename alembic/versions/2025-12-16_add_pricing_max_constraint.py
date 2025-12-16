"""add_pricing_max_constraint

Add upper bound CHECK constraint to model_pricing table
to prevent setting extremely high prices.

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2025-12-16
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'f6g7h8i9j0k1'
down_revision = 'e5f6g7h8i9j0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add upper bound constraint (max $10,000 per 1M tokens)
    op.create_check_constraint(
        'model_pricing_max_prices',
        'model_pricing',
        'input_price_per_million <= 10000.0000 AND output_price_per_million <= 10000.0000'
    )


def downgrade() -> None:
    op.drop_constraint('model_pricing_max_prices', 'model_pricing', type_='check')
