from fastapi import FastAPI, Form, Depends, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel, Field, create_engine, Session, select
from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError
from typing import Optional
from enum import Enum
from pydantic import EmailStr
import uvicorn
import os
import time
import logging


from contextlib import asynccontextmanager
from pathlib import Path

def run_alembic_migrations(database_url: str) -> bool:
    """Run Alembic migrations to 'head' if a migration setup exists.

    Returns True if migrations were found and executed (or there were none to
    apply). Returns False if no Alembic setup is present in the project.
    Raises an exception if a migration run is attempted but fails.
    """
    try:
        from alembic import command
        from alembic.config import Config
    except Exception:
        # Alembic not installed/available
        return False

    # Allow disabling migrations explicitly
    if os.getenv("SKIP_MIGRATIONS", "").lower() in {"1", "true", "yes"}:
        return False

    # Detect Alembic layout
    cwd = Path(__file__).resolve().parent
    ini_path = cwd / "alembic.ini"
    migrations_dir = Path(os.getenv("ALEMBIC_SCRIPT_LOCATION", cwd / "alembic"))

    has_ini = ini_path.is_file()
    has_dir = migrations_dir.is_dir()
    if not has_ini and not has_dir:
        return False

    cfg = Config(str(ini_path)) if has_ini else Config()
    # Always ensure these main options are set from our runtime env
    cfg.set_main_option("sqlalchemy.url", database_url)
    cfg.set_main_option("script_location", str(migrations_dir))

    # Optional: make autogenerate comparisons more accurate if env.py respects these
    cfg.set_main_option("compare_type", "true")
    cfg.set_main_option("compare_server_default", "true")

    # Run upgrade
    command.upgrade(cfg, "head")
    print("Applied Alembic migrations to head.")
    return True

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        wait_for_database(DATABASE_URL)
        # If Alembic migrations are available, run them; otherwise fall back to create_all
        ran_migrations = False
        try:
            ran_migrations = run_alembic_migrations(DATABASE_URL)
        except Exception as mig_err:
            # If a migration setup exists but fails, surface the error clearly
            print(f"ERROR: Alembic migrations failed: {mig_err}")
            raise

        if not ran_migrations:
            SQLModel.metadata.create_all(engine)
            print("No Alembic setup detected; created tables via metadata.")
    except Exception as e:
        print(f"ERROR: Database initialization failed. Details: {e}")
        raise
    yield

app = FastAPI(title="KFUPM Event Registration Form", lifespan=lifespan)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Global exception handler for logging 500 errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception in {request.url}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Configure CORS
cors_origins_env = os.getenv("CORS_ORIGINS", "*")
if cors_origins_env.strip() == "*":
    _allow_origins = ["*"]
    _allow_credentials = False  # credentials not allowed with wildcard origins per spec
else:
    _allow_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
    _allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class IASCourses(str, Enum):
    IAS_111 = "IAS 111"
    IAS_121 = "IAS 121"
    IAS_131 = "IAS 131"
    IAS_212 = "IAS 212"
    IAS_321 = "IAS 321"
    IAS_322 = "IAS 322"
    IAS_330 = "IAS 330"
    IAS_430 = "IAS 430"

class RegistrationForm(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str = Field(min_length=2)
    middle_name: Optional[str] = Field(default=None, min_length=2)
    last_name: str = Field(min_length=2)
    ias_course: Optional[IASCourses] = Field(default=None)
    university_id: Optional[str] = Field(None, description="الرقم الجامعي (اختياري)")
    phone: str = Field(min_length=10, description="رقم الجوال")
    email: Optional[EmailStr] = Field(default=None, description="البريد الإلكتروني")
    user_type: UserType = Field(description="طالب أو موظف")
    academic_level: AcademicLevel = Field(description="المرحلة الدراسية")
    how_heard: HowHeard = Field(description="كيف سمع عن الملتقى")

# ---------- API Schemas (Request/Response) ----------
class RegistrationRead(SQLModel):
    id: int
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    university_id: Optional[str] = None
    phone: str
    email: Optional[EmailStr] = None
    user_type: str
    academic_level: str
    how_heard: str
    ias_course: Optional[str] = None

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


def _mask_url(url_str: str) -> str:
    try:
        u = make_url(url_str)
        if u.password:
            u = u.set(password="***")
        return str(u)
    except Exception:
        return url_str


def _create_database_if_missing(url_str: str) -> None:
    url = make_url(url_str)
    if url.get_backend_name() != "postgresql":
        return

    target_db = url.database or "forms"
    if not target_db:
        return

    # Allow skipping DB creation (useful when the user lacks CREATEDB)
    if os.getenv("DB_SKIP_CREATE", "").lower() in {"1", "true", "yes"}:
        return

    # Optional separate admin URL (e.g., superuser) for creating the DB
    admin_url_env = os.getenv("DB_ADMIN_URL")
    admin_url = make_url(admin_url_env) if admin_url_env else url.set(database="postgres")
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


def _is_auth_error(err: Exception) -> bool:
    msg = str(err).lower()
    return "password authentication failed" in msg or "authentication failed" in msg


def _is_db_missing_error(err: Exception) -> bool:
    msg = str(err).lower()
    return "does not exist" in msg and "database" in msg


def wait_for_database(url_str: str) -> None:
    """Wait for DB server readiness and ensure target DB exists.

    Retries connections with backoff; attempts to create the target
    Postgres database if it doesn't exist. Raises after max attempts
    with a clear, masked message.
    """
    max_attempts = int(os.getenv("DB_MAX_RETRIES", "30"))
    interval = float(os.getenv("DB_RETRY_INTERVAL", "2.0"))

    last_err: Optional[Exception] = None
    url = make_url(url_str)
    is_pg = url.get_backend_name() == "postgresql"

    for attempt in range(1, max_attempts + 1):
        try:
            # First, try to connect to the target DB directly
            test_engine = create_engine(url_str)
            with test_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database is ready.")
            return
        except OperationalError as e:
            # Decide whether to attempt DB creation or fail fast
            if _is_auth_error(e):
                raise RuntimeError(
                    "Authentication failed for the provided DATABASE_URL. "
                    f"Checked {_mask_url(url_str)}. If your password contains special characters, "
                    "URL-encode it (e.g., @ -> %40)."
                ) from e

            if is_pg and _is_db_missing_error(e):
                try:
                    _create_database_if_missing(url_str)
                    # After creation, loop will retry the connection
                except Exception as ce:
                    last_err = ce
                    print(
                        f"Could not create database via admin connection: {ce}. "
                        "Set DB_ADMIN_URL for a superuser, or set DB_SKIP_CREATE=1 if DB is created externally."
                    )
            else:
                last_err = e
                print(
                    f"Waiting for database ({attempt}/{max_attempts}) at {_mask_url(url_str)}: {e}"
                )
        except Exception as e:
            last_err = e
            print(
                f"Waiting for database ({attempt}/{max_attempts}) at {_mask_url(url_str)}: {e}"
            )

        time.sleep(interval)

    masked = _mask_url(url_str)
    raise RuntimeError(
        "Database not ready after retries. "
        f"Checked {masked}. Last error: {last_err}"
    )


# Create engine (connections are opened lazily)
engine = create_engine(DATABASE_URL)

def get_session():
    with Session(engine) as session:
        yield session




@app.post("/submit", response_model=RegistrationResponse)
async def submit_form(
    first_name: str = Form(...),
    middle_name: Optional[str] = Form(None),
    last_name: str = Form(...),
    university_id: Optional[str] = Form(None),
    phone: str = Form(...),
    email: Optional[EmailStr] = Form(None),
    user_type: UserType = Form(...),
    academic_level: AcademicLevel = Form(...),
    how_heard: HowHeard = Form(...),
    ias_course: Optional[IASCourses] = Form(None),
    session: Session = Depends(get_session)
):
    try:
        registration = RegistrationForm(
            first_name=first_name,
            middle_name=middle_name or None,
            last_name=last_name,
            university_id=university_id or None,
            phone=phone,
            email=email or None,
            user_type=user_type,
            academic_level=academic_level,
            how_heard=how_heard,
            ias_course=ias_course or None
        )
        session.add(registration)
        session.commit()
        session.refresh(registration)
        return {
            "message": "تم التسجيل بنجاح",
            "data": registration
        }
    except Exception as e:
        logging.error(f"Error in submit_form: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/registrations", response_model=RegistrationsList)
async def get_registrations(
    session: Session = Depends(get_session),
    x_api_key: str = Header(..., alias="X-API-Key")
):
    try:
        required_key = os.getenv("API_KEY", "changeme")
        if x_api_key != required_key:
            raise HTTPException(status_code=401, detail="Invalid or missing API key.")
        registrations = session.exec(select(RegistrationForm)).all()
        return {"registrations": [reg for reg in registrations]}
    except Exception as e:
        logging.error(f"Error in get_registrations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health", status_code=200)
async def health():
    return {"status": "OK"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

