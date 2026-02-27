from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional
from datetime import datetime

class CreateUser(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    email: EmailStr

class Userlogin(BaseModel):
    email: EmailStr
    password: str

class token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: Optional[int] = None

class CreateProfile(BaseModel):
    name: str
    age: int
    education: str
    university: str
    biography: str
    image: Optional[str] = None
    userInput: Optional[int] = None

class Skill(BaseModel):
    profile_id: int
    category: str
    skill: str

class SkillResponse(BaseModel):
    category: str
    skill: str

class UpdateSkill(BaseModel):
    category: Optional[str] = None
    skill: Optional[str] = None

class Experience(BaseModel):
    profile_id: int
    company: str
    position: str
    start_date: datetime
    end_date: Optional[datetime] = None
    description: str

class ExperienceResponse(BaseModel):
    company: str
    position: str
    start_date: datetime
    end_date: Optional[datetime] = None
    description: str

class UpdateExperience(BaseModel):
    company: Optional[str] = None
    position: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    description: Optional[str] = None

class Project(BaseModel):
    profile_id: int
    name: str
    description: str
    link: Optional[str] = None

class ProjectResponse(BaseModel):
    name: str
    description: str
    link: Optional[str] = None

class UpdateProject(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    link: Optional[str] = None
class ProfileResponse(BaseModel):
    id: int
    userInput: int
    created_at: datetime
    name: str
    age: int
    education: str
    university: str
    biography: str
    image: Optional[str] = None
    skills: Optional[list[SkillResponse]] = []
    experiences: Optional[list[ExperienceResponse]] = []

class UpdateProfile(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    education: Optional[str] = None
    university: Optional[str] = None
    biography: Optional[str] = None
    image: Optional[str] = None