"""extend_model_pricing_with_capabilities

Revision ID: 26e70b1cb2f6
Revises: i9j0k1l2m3n4
Create Date: 2025-12-19 09:56:17.512866

Extends ModelPricing table to serve as single source of truth for:
- Model provider (google, openai, qwen, deepseek)
- Model capabilities (vision, text, markdown conversion)
- Default model selection for different use cases
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26e70b1cb2f6'
down_revision: Union[str, None] = 'i9j0k1l2m3n4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to model_pricing table
    # First add columns as nullable to allow backfill
    op.add_column('model_pricing', sa.Column('provider', sa.String(length=50), nullable=True))
    op.add_column('model_pricing', sa.Column('display_name', sa.String(length=200), nullable=True))
    op.add_column('model_pricing', sa.Column('supports_vision', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('model_pricing', sa.Column('supports_text', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('model_pricing', sa.Column('supports_markdown_conversion', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('model_pricing', sa.Column('supports_json_mode', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('model_pricing', sa.Column('max_output_tokens', sa.Integer(), nullable=True))
    op.add_column('model_pricing', sa.Column('context_window', sa.Integer(), nullable=True))
    op.add_column('model_pricing', sa.Column('is_default_extraction', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('model_pricing', sa.Column('is_default_markdown', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('model_pricing', sa.Column('is_default_llm', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('model_pricing', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

    # Backfill provider based on model_name patterns
    op.execute("""
        UPDATE model_pricing
        SET provider = CASE
            WHEN model_name LIKE 'gemini%' THEN 'google'
            WHEN model_name LIKE 'gpt%' THEN 'openai'
            WHEN model_name LIKE 'qwen%' THEN 'qwen'
            WHEN model_name LIKE 'deepseek%' THEN 'deepseek'
            ELSE 'google'
        END
        WHERE provider IS NULL
    """)

    # Backfill display_name from model_name
    op.execute("""
        UPDATE model_pricing
        SET display_name = CASE
            WHEN model_name = 'gemini-2.5-flash' THEN 'Gemini 2.5 Flash'
            WHEN model_name = 'gemini-2.5-pro' THEN 'Gemini 2.5 Pro'
            WHEN model_name = 'gemini-1.5-flash' THEN 'Gemini 1.5 Flash'
            WHEN model_name = 'gemini-1.5-pro' THEN 'Gemini 1.5 Pro'
            WHEN model_name = 'gpt-4o' THEN 'GPT-4o'
            WHEN model_name = 'gpt-4o-mini' THEN 'GPT-4o Mini'
            WHEN model_name = 'gpt-4-vision-preview' THEN 'GPT-4 Vision'
            WHEN model_name = 'gpt-4-turbo' THEN 'GPT-4 Turbo'
            WHEN model_name = 'gpt-3.5-turbo' THEN 'GPT-3.5 Turbo'
            WHEN model_name = 'qwen3-vl-8b-instruct' THEN 'Qwen3 VL 8B'
            WHEN model_name = 'deepseek-chat' THEN 'DeepSeek Chat'
            ELSE model_name
        END
        WHERE display_name IS NULL
    """)

    # Backfill supports_vision for known vision models
    op.execute("""
        UPDATE model_pricing
        SET supports_vision = TRUE
        WHERE model_name IN (
            'gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-1.5-flash', 'gemini-1.5-pro',
            'gpt-4o', 'gpt-4o-mini', 'gpt-4-vision-preview', 'gpt-4-turbo',
            'qwen3-vl-8b-instruct'
        )
    """)

    # Backfill supports_markdown_conversion for known markdown converters
    op.execute("""
        UPDATE model_pricing
        SET supports_markdown_conversion = TRUE
        WHERE model_name IN (
            'gemini-2.5-flash', 'gemini-2.5-pro',
            'gpt-4o', 'gpt-4-vision-preview',
            'qwen3-vl-8b-instruct'
        )
    """)

    # Backfill supports_json_mode for models that support it
    op.execute("""
        UPDATE model_pricing
        SET supports_json_mode = TRUE
        WHERE model_name IN (
            'gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-1.5-flash', 'gemini-1.5-pro',
            'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'
        )
    """)

    # Set default extraction model (gemini-2.5-flash)
    op.execute("""
        UPDATE model_pricing
        SET is_default_extraction = TRUE
        WHERE model_name = 'gemini-2.5-flash' AND is_active = TRUE
        AND NOT EXISTS (
            SELECT 1 FROM model_pricing WHERE is_default_extraction = TRUE
        )
    """)

    # Set default markdown model (gemini-2.5-flash)
    op.execute("""
        UPDATE model_pricing
        SET is_default_markdown = TRUE
        WHERE model_name = 'gemini-2.5-flash' AND is_active = TRUE
        AND NOT EXISTS (
            SELECT 1 FROM model_pricing WHERE is_default_markdown = TRUE
        )
    """)

    # Set default LLM model (gpt-4o if exists, otherwise gemini-2.5-flash)
    op.execute("""
        UPDATE model_pricing
        SET is_default_llm = TRUE
        WHERE model_name = 'gpt-4o' AND is_active = TRUE
        AND NOT EXISTS (
            SELECT 1 FROM model_pricing WHERE is_default_llm = TRUE
        )
    """)
    op.execute("""
        UPDATE model_pricing
        SET is_default_llm = TRUE
        WHERE model_name = 'gemini-2.5-flash' AND is_active = TRUE
        AND NOT EXISTS (
            SELECT 1 FROM model_pricing WHERE is_default_llm = TRUE
        )
    """)

    # Now make provider and boolean columns NOT NULL
    op.alter_column('model_pricing', 'provider',
                    existing_type=sa.String(length=50),
                    nullable=False,
                    server_default='google')
    op.alter_column('model_pricing', 'supports_vision',
                    existing_type=sa.Boolean(),
                    nullable=False,
                    server_default='false')
    op.alter_column('model_pricing', 'supports_text',
                    existing_type=sa.Boolean(),
                    nullable=False,
                    server_default='true')
    op.alter_column('model_pricing', 'supports_markdown_conversion',
                    existing_type=sa.Boolean(),
                    nullable=False,
                    server_default='false')
    op.alter_column('model_pricing', 'supports_json_mode',
                    existing_type=sa.Boolean(),
                    nullable=False,
                    server_default='false')
    op.alter_column('model_pricing', 'is_default_extraction',
                    existing_type=sa.Boolean(),
                    nullable=False,
                    server_default='false')
    op.alter_column('model_pricing', 'is_default_markdown',
                    existing_type=sa.Boolean(),
                    nullable=False,
                    server_default='false')
    op.alter_column('model_pricing', 'is_default_llm',
                    existing_type=sa.Boolean(),
                    nullable=False,
                    server_default='false')

    # Create new indexes
    op.create_index('idx_model_pricing_provider', 'model_pricing', ['provider'], unique=False)
    op.create_index('idx_model_pricing_provider_model', 'model_pricing', ['provider', 'model_name'], unique=False)
    op.create_index('idx_model_pricing_is_active', 'model_pricing', ['is_active'], unique=False)


def downgrade() -> None:
    # Drop new indexes
    op.drop_index('idx_model_pricing_is_active', table_name='model_pricing')
    op.drop_index('idx_model_pricing_provider_model', table_name='model_pricing')
    op.drop_index('idx_model_pricing_provider', table_name='model_pricing')

    # Drop new columns
    op.drop_column('model_pricing', 'updated_at')
    op.drop_column('model_pricing', 'is_default_llm')
    op.drop_column('model_pricing', 'is_default_markdown')
    op.drop_column('model_pricing', 'is_default_extraction')
    op.drop_column('model_pricing', 'context_window')
    op.drop_column('model_pricing', 'max_output_tokens')
    op.drop_column('model_pricing', 'supports_json_mode')
    op.drop_column('model_pricing', 'supports_markdown_conversion')
    op.drop_column('model_pricing', 'supports_text')
    op.drop_column('model_pricing', 'supports_vision')
    op.drop_column('model_pricing', 'display_name')
    op.drop_column('model_pricing', 'provider')
