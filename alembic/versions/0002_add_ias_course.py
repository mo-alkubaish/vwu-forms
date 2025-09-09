"""Add optional IAS course column using enum

Revision ID: 0002
Revises: 0001
Create Date: 2025-09-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type if it doesn't exist
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'iascourse') THEN
                CREATE TYPE iascourse AS ENUM (
                    'IAS 111','IAS 121','IAS 131','IAS 212','IAS 321','IAS 322','IAS 330','IAS 430'
                );
            END IF;
        END$$;
        """
    )

    iascourse = pg.ENUM(
        'IAS 111','IAS 121','IAS 131','IAS 212','IAS 321','IAS 322','IAS 330','IAS 430',
        name='iascourse', create_type=False
    )

    # Add nullable column to registrationform
    op.add_column(
        'registrationform',
        sa.Column('ias_course', iascourse, nullable=True)
    )


def downgrade() -> None:
    # Drop the column first
    op.drop_column('registrationform', 'ias_course')

    # Then drop enum type (safe if no other dependencies)
    op.execute("DROP TYPE IF EXISTS iascourse")

