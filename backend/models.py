from pydantic import BaseModel
from typing import List, Optional

class Question(BaseModel):
    question: str
    username: Optional[str] = None

class Upload(BaseModel):
    department: str
    file_paths: list[str]

class Login(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str
    allowed_departments: List[str]

class AccessUpdate(BaseModel):
    allowed_departments: List[str]
