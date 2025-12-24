"""add_page_pricing_to_model_pricing

Revision ID: f8a9b0c1d2e3
Revises: 4fcf8d68cda2
Create Date: 2025-12-23 10:00:00.000000

Adds page-based and document-based pricing columns to model_pricing table
to support converters like LlamaParse that charge per page instead of per token.

Also seeds LlamaParse pricing data.
"""
from typing import Sequence, Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'f8a9b0c1d2e3'
down_revision: Union[str, None] = '4fcf8d68cda2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# LlamaParse pricing configuration
# Pricing: 1 credit per page (based on LlamaCloud free tier: 1000 pages/day)
LLAMAPARSE_PRICING = {
    "model_name": "llamaparse",
    "display_name": "LlamaParse Document Converter",
    "provider": "llamaindex",
    "pricing_type": "page",
    "credit_rate_per_page": 1.0,  # 1 credit per page
    "input_price_per_million": 0.0,  # Not token-based
    "output_price_per_million": 0.0,  # Not token-based
    "supports_vision": False,
    "supports_text": False,
    "supports_markdown_conversion": True,
    "supports_json_mode": False,
    "is_document_converter": True,
    "converter_type": "document_to_markdown",
    "is_active": True,
}


def upgrade() -> None:
    # Add pricing_type column with default 'token' for existing records
    op.add_column('model_pricing', sa.Column(
        'pricing_type',
        sa.String(length=20),
        nullable=False,
        server_default='token'
    ))

    # Add credit_rate_per_page for page-based pricing
    op.add_column('model_pricing', sa.Column(
        'credit_rate_per_page',
        sa.Numeric(precision=10, scale=4),
        nullable=True
    ))

    # Add credit_rate_per_document for document-based pricing
    op.add_column('model_pricing', sa.Column(
        'credit_rate_per_document',
        sa.Numeric(precision=10, scale=4),
        nullable=True
    ))

    # Add converter_type for document converters
    op.add_column('model_pricing', sa.Column(
        'converter_type',
        sa.String(length=50),
        nullable=True
    ))

    # Add is_document_converter flag
    op.add_column('model_pricing', sa.Column(
        'is_document_converter',
        sa.Boolean(),
        nullable=False,
        server_default='false'
    ))

    # Add check constraint for valid page rate (0 to 1000 credits per page)
    op.create_check_constraint(
        'model_pricing_valid_page_rate',
        'model_pricing',
        'credit_rate_per_page IS NULL OR (credit_rate_per_page >= 0 AND credit_rate_per_page <= 1000.0000)'
    )

    # Add check constraint for valid document rate (0 to 10000 credits per document)
    op.create_check_constraint(
        'model_pricing_valid_document_rate',
        'model_pricing',
        'credit_rate_per_document IS NULL OR (credit_rate_per_document >= 0 AND credit_rate_per_document <= 10000.0000)'
    )

    # Add index for document converter lookups
    op.create_index(
        'idx_model_pricing_is_document_converter',
        'model_pricing',
        ['is_document_converter'],
        unique=False
    )

    # Seed LlamaParse pricing data
    # First, get a system user ID for created_by (use the first admin user)
    connection = op.get_bind()
    result = connection.execute(
        sa.text("""
            SELECT id FROM users
            WHERE role = 'owner' OR role = 'admin'
            ORDER BY created_at ASC
            LIMIT 1
        """)
    )
    row = result.fetchone()

    if row:
        created_by_user_id = row[0]
        now = datetime.now(timezone.utc)

        # Check if LlamaParse pricing already exists to avoid duplicates
        existing = connection.execute(
            sa.text("""
                SELECT id FROM model_pricing
                WHERE model_name = :model_name AND provider = :provider
            """),
            {"model_name": LLAMAPARSE_PRICING["model_name"], "provider": LLAMAPARSE_PRICING["provider"]}
        ).fetchone()

        if not existing:
            # Insert LlamaParse pricing record
            connection.execute(
                sa.text("""
                    INSERT INTO model_pricing (
                        id, provider, model_name, display_name,
                        input_price_per_million, output_price_per_million,
                        supports_vision, supports_text, supports_markdown_conversion, supports_json_mode,
                        pricing_type, credit_rate_per_page,
                        converter_type, is_document_converter,
                        is_default_extraction, is_default_markdown, is_default_llm,
                        effective_from, is_active,
                        created_by, created_at
                    ) VALUES (
                        gen_random_uuid(), :provider, :model_name, :display_name,
                        :input_price, :output_price,
                        :supports_vision, :supports_text, :supports_markdown, :supports_json,
                        :pricing_type, :credit_rate_per_page,
                        :converter_type, :is_document_converter,
                        false, false, false,
                        :effective_from, :is_active,
                        :created_by, :created_at
                    )
                """),
                {
                    "provider": LLAMAPARSE_PRICING["provider"],
                    "model_name": LLAMAPARSE_PRICING["model_name"],
                    "display_name": LLAMAPARSE_PRICING["display_name"],
                    "input_price": LLAMAPARSE_PRICING["input_price_per_million"],
                    "output_price": LLAMAPARSE_PRICING["output_price_per_million"],
                    "supports_vision": LLAMAPARSE_PRICING["supports_vision"],
                    "supports_text": LLAMAPARSE_PRICING["supports_text"],
                    "supports_markdown": LLAMAPARSE_PRICING["supports_markdown_conversion"],
                    "supports_json": LLAMAPARSE_PRICING["supports_json_mode"],
                    "pricing_type": LLAMAPARSE_PRICING["pricing_type"],
                    "credit_rate_per_page": LLAMAPARSE_PRICING["credit_rate_per_page"],
                    "converter_type": LLAMAPARSE_PRICING["converter_type"],
                    "is_document_converter": LLAMAPARSE_PRICING["is_document_converter"],
                    "effective_from": now,
                    "is_active": LLAMAPARSE_PRICING["is_active"],
                    "created_by": created_by_user_id,
                    "created_at": now,
                }
            )


def downgrade() -> None:
    # Remove seeded LlamaParse pricing data
    connection = op.get_bind()
    connection.execute(
        sa.text("""
            DELETE FROM model_pricing
            WHERE model_name = :model_name AND provider = :provider
        """),
        {"model_name": LLAMAPARSE_PRICING["model_name"], "provider": LLAMAPARSE_PRICING["provider"]}
    )

    # Drop index
    op.drop_index('idx_model_pricing_is_document_converter', table_name='model_pricing')

    # Drop check constraints
    op.drop_constraint('model_pricing_valid_document_rate', 'model_pricing', type_='check')
    op.drop_constraint('model_pricing_valid_page_rate', 'model_pricing', type_='check')

    # Drop columns
    op.drop_column('model_pricing', 'is_document_converter')
    op.drop_column('model_pricing', 'converter_type')
    op.drop_column('model_pricing', 'credit_rate_per_document')
    op.drop_column('model_pricing', 'credit_rate_per_page')
    op.drop_column('model_pricing', 'pricing_type')
