from pydantic import BaseModel

class Question(BaseModel):
    question: str

class Upload(BaseModel):
    department: str
    file_paths: list[str]

class Login(BaseModel):
    username: str
    password: str
