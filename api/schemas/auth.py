from pydantic import BaseModel, EmailStr


class RegisterSchema(BaseModel):

    name: str
    email: EmailStr
    password: str
    church_name: str


class LoginSchema(BaseModel):

    email: EmailStr
    password: str