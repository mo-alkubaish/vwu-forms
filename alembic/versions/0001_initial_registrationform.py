"""Initial schema for RegistrationForm

Revision ID: 0001
Revises: 
Create Date: 2025-09-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums only if they do not already exist
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'usertype') THEN
                CREATE TYPE usertype AS ENUM ('student','employee','employee_son','na');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'academiclevel') THEN
                CREATE TYPE academiclevel AS ENUM ('freshman','sophomore','junior','senior','graduate','na');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'howheard') THEN
                CREATE TYPE howheard AS ENUM ('social_media','ataa_community','email','other');
            END IF;
        END$$;
        """
    )

    usertype = pg.ENUM('student','employee','employee_son','na', name='usertype', create_type=False)
    academiclevel = pg.ENUM('freshman','sophomore','junior','senior','graduate','na', name='academiclevel', create_type=False)
    howheard = pg.ENUM('social_media','ataa_community','email','other', name='howheard', create_type=False)

    # Create table only if it does not already exist (in case of prior create_all)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "registrationform" not in inspector.get_table_names():
        op.create_table(
            "registrationform",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("first_name", sa.String(), nullable=False),
            sa.Column("middle_name", sa.String(), nullable=True),
            sa.Column("last_name", sa.String(), nullable=False),
            sa.Column("university_id", sa.String(), nullable=True),
            sa.Column("phone", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=True),
            sa.Column("user_type", usertype, nullable=False),
            sa.Column("academic_level", academiclevel, nullable=False),
            sa.Column("how_heard", howheard, nullable=False),
        )


def downgrade() -> None:
    op.drop_table("registrationform")

    # Drop enums after table removal (no-op if already absent)
    op.execute("DROP TYPE IF EXISTS howheard")
    op.execute("DROP TYPE IF EXISTS academiclevel")
    op.execute("DROP TYPE IF EXISTS usertype")
