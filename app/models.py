from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, text, ForeignKey, Date
from .database import Base
from sqlalchemy.orm import relationship

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    userInput = Column(Integer, ForeignKey("users.id"), nullable=False)   
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    education = Column(String, nullable=False)
    university = Column(String, nullable=False)
    biography = Column(String, nullable=False)
    image = Column(String, nullable=True)

    skills = relationship("Skill", back_populates="profile")
    experiences = relationship("Experience", back_populates="profile")
    projects = relationship("Project", back_populates="profile")
    # user = relationship("User")

class UserLogin(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, unique = True)
    password = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))

class Skill(Base):  
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"))
    category = Column(String, nullable=False)
    skill = Column(String, nullable=False)

    profile = relationship("Profile", back_populates="skills")

class Experience(Base):
    __tablename__ = "experiences"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"))
    company = Column(String, nullable=False)
    position = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    description = Column(String, nullable=False)

    profile = relationship("Profile", back_populates="experiences")

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"))
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    link = Column(String, nullable=True)

    profile = relationship("Profile", back_populates="projects")