"""add_markdown_pipeline_support

Revision ID: 67afd920ae17
Revises: 922d747266dd
Create Date: 2025-11-17 22:54:29.793347

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67afd920ae17'
down_revision: Union[str, None] = '922d747266dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add markdown pipeline support to document_pages and extraction_jobs tables."""
    # Add markdown fields to document_pages table
    op.add_column('document_pages', sa.Column('markdown_content', sa.Text(), nullable=True))
    op.add_column('document_pages', sa.Column('markdown_provider', sa.String(length=50), nullable=True))
    op.add_column('document_pages', sa.Column('markdown_generated_at', sa.DateTime(), nullable=True))

    # Add index for markdown_generated_at for query optimization
    op.create_index('idx_document_pages_markdown_generated', 'document_pages', ['markdown_generated_at'])

    # Add markdown fields to extraction_jobs table
    op.add_column('extraction_jobs', sa.Column('markdown_converter', sa.String(length=50), nullable=True))
    op.add_column('extraction_jobs', sa.Column('markdown_format', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Remove markdown pipeline support from document_pages and extraction_jobs tables."""
    # Remove markdown fields from extraction_jobs table
    op.drop_column('extraction_jobs', 'markdown_format')
    op.drop_column('extraction_jobs', 'markdown_converter')

    # Remove index and markdown fields from document_pages table
    op.drop_index('idx_document_pages_markdown_generated', table_name='document_pages')
    op.drop_column('document_pages', 'markdown_generated_at')
    op.drop_column('document_pages', 'markdown_provider')
    op.drop_column('document_pages', 'markdown_content')
