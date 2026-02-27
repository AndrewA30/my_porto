from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload
from .. import models, schemas, utils, oauth2
from ..database import get_db

router = APIRouter(
    prefix="/portofolio",
    tags=['Portofolio']
)

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

@router.get("/", response_class=HTMLResponse)
def view_portofolio(request: Request, db: Session = Depends(get_db)):
    profile = (
        db.query(models.Profile)
        .options(
            selectinload(models.Profile.skills),
            selectinload(models.Profile.experiences),
            selectinload(models.Profile.projects),
        )
        .order_by(models.Profile.created_at.desc())
        .first()
    )
    contact_email = "aavellino591@gmail.com"

    return templates.TemplateResponse(
        "portfolio.html",
        {
            "request": request,
            "profile": profile,
            "contact_email": contact_email,
            "github_url": "https://github.com/AndrewA30?tab=repositories",
            "linkedin_url": "https://www.linkedin.com/in/andrew-avellino-99649a164/",
        },
    )

# endpoint untuk mendapatkan semua portofolio beserta skillnya dengan cara looping.
# @router.get("/all", response_model=list[schemas.ProfileResponse])
# def get_profiles(db: Session = Depends(get_db)):
#     # profiles = db.query(models.Profile, models.Skill).join(models.Skill, models.Profile.id == models.Skill.profile_id, isouter=True).all()
#     profiles = db.query(models.Profile).all()
#     for profile in profiles:
#         skills = db.query(models.Skill).filter(models.Skill.profile_id == profile.id).all()
#         profile.skills = skills
#     return profiles

# endpoint untuk mendapatkan semua portofolio beserta skill dan experience.
@router.get("/all", response_model=list[schemas.ProfileResponse])
def get_profiles(db: Session = Depends(get_db)):
    profiles = (
        db.query(models.Profile)
        .options(
            selectinload(models.Profile.skills),
            selectinload(models.Profile.experiences),
            selectinload(models.Profile.projects),
        )
        .all()
    )
    return profiles


# endpoint untuk create portofolio baru
@router.post("/create", status_code=status.HTTP_201_CREATED, response_model=schemas.ProfileResponse)
def create_profile(new_profile: schemas.CreateProfile, db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    new_profile.userInput = current_user.id
    new_profile = models.Profile(**new_profile.model_dump())
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    return new_profile

#endpoint untuk update portofolio
@router.put("/update/{id}", response_model=schemas.ProfileResponse)
def update_profile(id: int, updated_profile: schemas.UpdateProfile, db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    update_data = updated_profile.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)


    db.commit()
    db.refresh(profile)

    return profile

#endpoint untuk delete portofolio
@router.delete("/delete/{id}", status_code=status.HTTP_204_NO_CONTENT) 
def delete_profile(id: int, db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    if profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this profile")

    db.delete(profile)
    db.commit()

    return {"message": "Profile deleted successfully"}

#endpoint untuk memasukkan skill ke dalam profile
@router.post("/skill", status_code=status.HTTP_201_CREATED)
def add_skill(skill: schemas.Skill, db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == skill.profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    if profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to add skill to this profile")

    new_skill = models.Skill(**skill.model_dump())
    db.add(new_skill)
    db.commit()

    return {"message": "Skill added successfully"}

#endpoint untuk menghapus skill dari profile
@router.delete("/skill/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(id: int, db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    skill = db.query(models.Skill).filter(models.Skill.id == id).first()
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    profile = db.query(models.Profile).filter(models.Profile.id == skill.profile_id).first()
    if profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this skill")

    db.delete(skill)
    db.commit()

    return {"message": "Skill deleted successfully"}

#endpoint untuk update skill dari profile
@router.put("/skill/{id}", status_code=status.HTTP_200_OK)
def update_skill(id: int, updated_skill: schemas.UpdateSkill, db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    skill = db.query(models.Skill).filter(models.Skill.id == id).first()
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    profile = db.query(models.Profile).filter(models.Profile.id == skill.profile_id).first()
    if profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this skill")

    update_data = updated_skill.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(skill, field, value)

    db.commit()
    db.refresh(skill)

    return {"message": "Skill updated successfully"}

#endpoint untuk memasukkan experience ke dalam profile
@router.post("/experience", status_code=status.HTTP_201_CREATED, response_model=schemas.ExperienceResponse)
def add_experience(experience: schemas.Experience, db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == experience.profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    if profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to add experience to this profile")

    new_experience = models.Experience(**experience.model_dump())
    db.add(new_experience)
    db.commit()
    db.refresh(new_experience)

    return new_experience

#endpoint untuk menghapus experience dari profile
@router.delete("/experience/{id}", status_code=status.HTTP_204_NO_CONTENT) 
def delete_experience(id: int, db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    experience = db.query(models.Experience).filter(models.Experience.id == id).first()
    if not experience:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")
    profile = db.query(models.Profile).filter(models.Profile.id == experience.profile_id).first()
    if profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this experience")

    db.delete(experience)
    db.commit()

    return {"message": "Experience deleted successfully"}

#endpoint untuk update experience dari profile
@router.put("/experience/{id}", status_code=status.HTTP_200_OK)
def update_experience(id: int, updated_experience: schemas.UpdateExperience, db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    experience = db.query(models.Experience).filter(models.Experience.id == id).first()
    if not experience:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")
    profile = db.query(models.Profile).filter(models.Profile.id == experience.profile_id).first()
    if profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this experience")

    update_data = updated_experience.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(experience, field, value)

    db.commit()
    db.refresh(experience)

    return {"message": "Experience updated successfully"}