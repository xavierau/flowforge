"""add_markdown_token_tracking

Add token tracking fields to document_pages for markdown generation stage.
This enables full cost tracking for the two-stage markdown pipeline:
- Stage 1: Image → Markdown (vision model) - tracked on DocumentPage
- Stage 2: Markdown → JSON (text model) - tracked on ExtractionResult

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2025-12-16
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e5f6g7h8i9j0'
down_revision = 'd4e5f6g7h8i9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add markdown generation token tracking fields to document_pages
    op.add_column('document_pages', sa.Column('markdown_input_tokens', sa.Integer(), nullable=True))
    op.add_column('document_pages', sa.Column('markdown_output_tokens', sa.Integer(), nullable=True))
    op.add_column('document_pages', sa.Column('markdown_model_used', sa.String(100), nullable=True))
    op.add_column('document_pages', sa.Column('markdown_cost_usd', sa.Numeric(10, 6), nullable=True))


def downgrade() -> None:
    op.drop_column('document_pages', 'markdown_cost_usd')
    op.drop_column('document_pages', 'markdown_model_used')
    op.drop_column('document_pages', 'markdown_output_tokens')
    op.drop_column('document_pages', 'markdown_input_tokens')
