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

    # Create table if it does not already exist
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS registrationform (
            id SERIAL PRIMARY KEY,
            first_name VARCHAR NOT NULL,
            middle_name VARCHAR,
            last_name VARCHAR NOT NULL,
            university_id VARCHAR,
            phone VARCHAR NOT NULL,
            email VARCHAR,
            user_type usertype NOT NULL,
            academic_level academiclevel NOT NULL,
            how_heard howheard NOT NULL
        );
        """
    )


def downgrade() -> None:
    op.drop_table("registrationform")

    # Drop enums after table removal (no-op if already absent)
    op.execute("DROP TYPE IF EXISTS howheard")
    op.execute("DROP TYPE IF EXISTS academiclevel")
    op.execute("DROP TYPE IF EXISTS usertype")
