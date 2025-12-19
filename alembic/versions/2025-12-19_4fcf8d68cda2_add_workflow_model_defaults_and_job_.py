"""add_workflow_model_defaults_and_job_markdown_model

Revision ID: 4fcf8d68cda2
Revises: 26e70b1cb2f6
Create Date: 2025-12-19 10:00:57.049374

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4fcf8d68cda2'
down_revision: Union[str, None] = '26e70b1cb2f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add model_defaults column to workflow_versions table
    # Structure:
    # {
    #   "extraction": {"provider": "google", "model": "gemini-2.5-flash"},
    #   "markdown_converter": {"converter": "gemini_vision", "model": "gemini-2.5-flash"},
    #   "llm": {"provider": "google", "model": "gemini-2.5-flash"}
    # }
    op.add_column(
        'workflow_versions',
        sa.Column('model_defaults', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )

    # Add markdown_converter_model column to extraction_jobs table
    # Tracks which model was used for the markdown conversion step
    op.add_column(
        'extraction_jobs',
        sa.Column('markdown_converter_model', sa.String(length=100), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('extraction_jobs', 'markdown_converter_model')
    op.drop_column('workflow_versions', 'model_defaults')
