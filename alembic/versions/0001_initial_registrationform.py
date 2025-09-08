"""Initial schema for RegistrationForm

Revision ID: 0001
Revises: 
Create Date: 2025-09-08
"""
from alembic import op
import sqlalchemy as sa
from enum import Enum

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


# Re-declare enums used by the model to keep migration self-contained
class UserType(str, Enum):
    student = "O�O\u0015U,O\""
    employee = "U.U^O,U?"
    employee_son = "O\u0015O\"U+ U.U^O,U?"
    na = "O�USO� U.O�O\"U,"


class AcademicLevel(str, Enum):
    freshman = "O\u0015U,O3U+Oc O\u0015U,O�U^U,U%"
    sophomore = "O\u0015U,O3U+Oc O\u0015U,O�O\u0015U+USOc"
    junior = "O\u0015U,O3U+Oc O\u0015U,O�O\u0015U,O�Oc"
    senior = "O\u0015U,O3U+Oc O\u0015U,O�O\u0015O\"O1Oc"
    graduate = "O_O�O\u0015O3O\u0015O� O1U,USO\u0015"
    na = "O�USO� U.O�O\"U,"


class HowHeard(str, Enum):
    social_media = "U^O3O\u0015O�U, O�U^O\u0015O�U, O\u0015O�O�U.O\u0015O1US"
    ataa_community = "U.O�O�U.O1 O1O�O\u0015O�"
    email = "O\u0015USU.USU,"
    other = "O�OrO�U%"


def upgrade() -> None:
    # Create enums first (PostgreSQL will create distinct types)
    usertype = sa.Enum(UserType, name="usertype")
    academiclevel = sa.Enum(AcademicLevel, name="academiclevel")
    howheard = sa.Enum(HowHeard, name="howheard")

    usertype.create(op.get_bind(), checkfirst=True)
    academiclevel.create(op.get_bind(), checkfirst=True)
    howheard.create(op.get_bind(), checkfirst=True)

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

    # Drop enums after table removal
    bind = op.get_bind()
    sa.Enum(name="howheard").drop(bind, checkfirst=True)
    sa.Enum(name="academiclevel").drop(bind, checkfirst=True)
    sa.Enum(name="usertype").drop(bind, checkfirst=True)

