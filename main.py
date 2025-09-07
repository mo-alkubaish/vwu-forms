from fastapi import FastAPI, Form, Depends
from sqlmodel import SQLModel, Field, create_engine, Session, select
from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError
from typing import Optional
from enum import Enum
import uvicorn
import os


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI(title="KFUPM Event Registration Form", lifespan=lifespan)

class UserType(str, Enum):
    student = "طالب"
    employee = "موظف"
    employee_son = "ابن موظف"
    na = "غير مطبق"


class AcademicLevel(str, Enum):
    freshman = "السنة الأولى"
    sophomore = "السنة الثانية"
    junior = "السنة الثالثة"
    senior = "السنة الرابعة"
    graduate = "دراسات عليا"
    na = "غير مطبق"

class HowHeard(str, Enum):
    social_media = "وسائل تواصل اجتماعي"
    ataa_community = "مجتمع عطاء"
    email = "ايميل"
    other = "أخرى"

class RegistrationForm(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str = Field(min_length=2)
    middle_name: str = Field(min_length=2)
    last_name: str = Field(min_length=2)
    university_id: Optional[str] = Field(None, description="الرقم الجامعي (اختياري)")
    phone: str = Field(min_length=10, description="رقم الجوال")
    user_type: UserType = Field(description="طالب أو موظف")
    academic_level: AcademicLevel = Field(description="المرحلة الدراسية")
    how_heard: HowHeard = Field(description="كيف سمع عن الملتقى")

# ---------- API Schemas (Request/Response) ----------
class RegistrationRead(SQLModel):
    id: int
    first_name: str
    middle_name: str
    last_name: str
    university_id: Optional[str] = None
    phone: str
    user_type: UserType
    academic_level: AcademicLevel
    how_heard: HowHeard


class RegistrationResponse(SQLModel):
    message: str
    data: RegistrationRead


class RegistrationsList(SQLModel):
    registrations: list[RegistrationRead]

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://forms_user:forms_password@localhost:5432/kfupm_forms")

# Normalize deprecated Postgres scheme used by some providers (e.g., Heroku)
# SQLAlchemy 2.x requires 'postgresql://' instead of 'postgres://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def ensure_database_exists(url_str: str) -> None:
    """Ensure the target Postgres database exists; create if missing.

    Connects to the server's default 'postgres' database using the same
    credentials/host, checks pg_database, and creates the target DB if absent.
    """
    try:
        url = make_url(url_str)
        if url.get_backend_name() != "postgresql":
            return  # Only handle Postgres automatically

        target_db = url.database or "forms"
        if not target_db:
            return

        admin_url = url.set(database="postgres")

        # AUTOCOMMIT is required for CREATE DATABASE in Postgres
        admin_engine = create_engine(str(admin_url), isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": target_db},
            ).scalar() 
            if not exists:
                safe_name = target_db.replace('"', '""')
                conn.execute(text(f'CREATE DATABASE "{safe_name}"'))
                print(f"Created database '{target_db}'.")
    except OperationalError as e:
        # Likely the server isn't reachable or creds lack CREATEDB privilege
        print(f"Warning: could not verify/create database '{url_str}': {e}")
    except Exception as e:
        # Non-fatal; app may still start if DB gets created externally
        print(f"Warning: ensure_database_exists error: {e}")


# Ensure DB exists before creating the app engine and tables
ensure_database_exists(DATABASE_URL)
engine = create_engine(DATABASE_URL)

def get_session():
    with Session(engine) as session:
        yield session




@app.post("/submit", response_model=RegistrationResponse)
async def submit_form(
    first_name: str = Form(...),
    middle_name: str = Form(...),
    last_name: str = Form(...),
    university_id: Optional[str] = Form(None),
    phone: str = Form(...),
    user_type: UserType = Form(...),
    academic_level: AcademicLevel = Form(...),
    how_heard: HowHeard = Form(...),
    session: Session = Depends(get_session)
):
    registration = RegistrationForm(
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        university_id=university_id or None,
        phone=phone,
        user_type=user_type,
        academic_level=academic_level,
        how_heard=how_heard
    )
    
    session.add(registration)
    session.commit()
    session.refresh(registration)
    
    return {
        "message": "تم التسجيل بنجاح",
        "data": registration
    }

@app.get("/registrations", response_model=RegistrationsList)
async def get_registrations(session: Session = Depends(get_session)):
    registrations = session.exec(select(RegistrationForm)).all()
    return {"registrations": [reg for reg in registrations]}

@app.get("/health", status_code=200)
async def health():
    return {"status": "OK"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
