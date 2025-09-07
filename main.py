from fastapi import FastAPI, Form, Depends
from sqlmodel import SQLModel, Field, create_engine, Session, select
from typing import Optional
from enum import Enum
import uvicorn
import os

app = FastAPI(title="KFUPM Event Registration Form")

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

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://forms_user:forms_password@localhost:5432/kfupm_forms")
engine = create_engine(DATABASE_URL)

def get_session():
    with Session(engine) as session:
        yield session


@app.on_event("startup")
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

@app.post("/submit")
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
        "data": registration.dict()
    }

@app.get("/registrations")
async def get_registrations(session: Session = Depends(get_session)):
    registrations = session.exec(select(RegistrationForm)).all()
    return {"registrations": [reg.dict() for reg in registrations]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
