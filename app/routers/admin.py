from pathlib import Path
import shutil
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload
from .. import models, utils, oauth2
from ..database import get_db

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

router = APIRouter(
    prefix="/admin",
    tags=['Admin']
)

# Upload directory configuration
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Max file size: 5MB
MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp"}

# Helper function to save uploaded file
async def save_uploaded_file(file: UploadFile) -> str:
    """Save uploaded file and return relative path"""
    if not file:
        return None
    
    # Validate file type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File harus berupa gambar (JPEG, PNG, atau WebP)"
        )
    
    # Read file content and check size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ukuran file maksimum 5MB"
        )
    
    # Generate unique filename
    ext = Path(file.filename).suffix.lower() or ".jpg"
    filename = f"{uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / filename
    
    # Save file
    with file_path.open("wb") as f:
        f.write(contents)
    
    # Return relative path for URL
    return f"/static/uploads/{filename}"

# Dependency untuk autentikasi admin
def get_admin_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    try:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
        token_data = oauth2.verify_access_token(token, credentials_exception)
        user = db.query(models.UserLogin).filter(models.UserLogin.id == token_data.id).first()
        if not user:
            raise credentials_exception
        return user
    except:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

# Admin Login Routes
@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login", response_class=HTMLResponse)
async def admin_login(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    email = form_data.get("email")
    password = form_data.get("password")
    
    user = db.query(models.UserLogin).filter(models.UserLogin.email == email).first()
    if not user or not utils.verify_password(password, user.password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Email atau password salah"
        })
    
    # Create access token
    access_token = oauth2.create_access_token(data={"user_id": user.id})
    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    response.set_cookie(key="admin_token", value=access_token, httponly=True, max_age=86400)
    return response

# Admin Dashboard Routes
@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    profiles = (
        db.query(models.Profile)
        .filter(models.Profile.userInput == current_user.id)
        .options(
            selectinload(models.Profile.skills),
            selectinload(models.Profile.experiences),
            selectinload(models.Profile.projects),
        )
        .all()
    )
    return templates.TemplateResponse("admin.html", {"request": request, "profiles": profiles})

@router.get("/profile/create", response_class=HTMLResponse)
async def create_profile_page(request: Request, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    return templates.TemplateResponse("profile_form.html", {"request": request, "profile": None})

@router.post("/profile/create", response_class=HTMLResponse)
async def create_profile_submit(
    request: Request,
    name: str = Form(...),
    age: int = Form(...),
    education: str = Form(...),
    university: str = Form(...),
    biography: str = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)
):
    # Handle file upload
    image_path = None
    if image and image.filename:
        image_path = await save_uploaded_file(image)
    
    new_profile = models.Profile(
        name=name,
        age=age,
        education=education,
        university=university,
        biography=biography,
        image=image_path,
        userInput=current_user.id
    )
    db.add(new_profile)
    db.commit()
    
    return RedirectResponse(url="/admin/dashboard", status_code=303)

@router.get("/profile/{profile_id}/edit", response_class=HTMLResponse)
async def edit_profile_page(profile_id: int, request: Request, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    return templates.TemplateResponse("profile_form.html", {"request": request, "profile": profile})

@router.post("/profile/{profile_id}/edit", response_class=HTMLResponse)
async def edit_profile_submit(
    profile_id: int,
    request: Request,
    name: str = Form(...),
    age: int = Form(...),
    education: str = Form(...),
    university: str = Form(...),
    biography: str = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)
):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    # Handle file upload
    if image and image.filename:
        # Delete old image if exists
        if profile.image and profile.image.startswith("/static/uploads/"):
            old_file = Path(__file__).resolve().parent.parent / profile.image.lstrip("/")
            if old_file.exists():
                old_file.unlink(missing_ok=True)
        
        profile.image = await save_uploaded_file(image)
    
    profile.name = name
    profile.age = age
    profile.education = education
    profile.university = university
    profile.biography = biography
    
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=303)

@router.post("/profile/{profile_id}/delete", response_class=HTMLResponse)
async def delete_profile_submit(profile_id: int, request: Request, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    db.delete(profile)
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=303)

# Skill Management Routes
@router.get("/profile/{profile_id}/skills", response_class=HTMLResponse)
async def manage_skills(profile_id: int, request: Request, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    skills = db.query(models.Skill).filter(models.Skill.profile_id == profile_id).order_by(models.Skill.category.desc()).all()
    return templates.TemplateResponse("skills.html", {"request": request, "profile": profile, "skills": skills})

@router.get("/profile/{profile_id}/skills/create", response_class=HTMLResponse)
async def create_skill_page(profile_id: int, request: Request, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    return templates.TemplateResponse("skill_form.html", {"request": request, "skill": None, "profile_id": profile_id})

@router.post("/profile/{profile_id}/skills/create", response_class=HTMLResponse)
async def create_skill_submit(
    profile_id: int,
    request: Request,
    category: str = Form(...),
    skill: str = Form(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)
):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    new_skill = models.Skill(
        profile_id=profile_id,
        category=category,
        skill=skill
    )
    db.add(new_skill)
    db.commit()
    
    return RedirectResponse(url=f"/admin/profile/{profile_id}/skills", status_code=303)

@router.get("/profile/{profile_id}/skills/{skill_id}/edit", response_class=HTMLResponse)
async def edit_skill_page(profile_id: int, skill_id: int, request: Request, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    skill = db.query(models.Skill).filter(models.Skill.id == skill_id, models.Skill.profile_id == profile_id).first()
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    
    return templates.TemplateResponse("skill_form.html", {"request": request, "skill": skill, "profile_id": profile_id})

@router.post("/profile/{profile_id}/skills/{skill_id}/edit", response_class=HTMLResponse)
async def edit_skill_submit(
    profile_id: int,
    skill_id: int,
    request: Request,
    category: str = Form(...),
    skill: str = Form(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)
):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    skill_obj = db.query(models.Skill).filter(models.Skill.id == skill_id, models.Skill.profile_id == profile_id).first()
    if not skill_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    
    skill_obj.category = category
    skill_obj.skill = skill
    
    db.commit()
    return RedirectResponse(url=f"/admin/profile/{profile_id}/skills", status_code=303)

@router.post("/profile/{profile_id}/skills/{skill_id}/delete", response_class=HTMLResponse)
async def delete_skill_submit(profile_id: int, skill_id: int, request: Request, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    skill = db.query(models.Skill).filter(models.Skill.id == skill_id, models.Skill.profile_id == profile_id).first()
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    
    db.delete(skill)
    db.commit()
    return RedirectResponse(url=f"/admin/profile/{profile_id}/skills", status_code=303)


# Project Management Routes
@router.get("/profile/{profile_id}/projects", response_class=HTMLResponse)
async def manage_projects(profile_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(get_admin_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    projects = db.query(models.Project).filter(models.Project.profile_id == profile_id).order_by(models.Project.id.desc()).all()
    return templates.TemplateResponse("projects.html", {"request": request, "profile": profile, "projects": projects})


@router.get("/profile/{profile_id}/projects/create", response_class=HTMLResponse)
async def create_project_page(profile_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(get_admin_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    return templates.TemplateResponse("project_form.html", {"request": request, "project": None, "profile_id": profile_id})


@router.post("/profile/{profile_id}/projects/create", response_class=HTMLResponse)
async def create_project_submit(
    profile_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    link: str = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_admin_user),
):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    new_project = models.Project(
        profile_id=profile_id,
        name=name,
        description=description,
        link=link or None,
    )
    db.add(new_project)
    db.commit()

    return RedirectResponse(url=f"/admin/profile/{profile_id}/projects", status_code=303)


@router.get("/profile/{profile_id}/projects/{project_id}/edit", response_class=HTMLResponse)
async def edit_project_page(profile_id: int, project_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(get_admin_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    project = db.query(models.Project).filter(models.Project.id == project_id, models.Project.profile_id == profile_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return templates.TemplateResponse("project_form.html", {"request": request, "project": project, "profile_id": profile_id})


@router.post("/profile/{profile_id}/projects/{project_id}/edit", response_class=HTMLResponse)
async def edit_project_submit(
    profile_id: int,
    project_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    link: str = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_admin_user),
):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    project = db.query(models.Project).filter(models.Project.id == project_id, models.Project.profile_id == profile_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    project.name = name
    project.description = description
    project.link = link or None

    db.commit()
    return RedirectResponse(url=f"/admin/profile/{profile_id}/projects", status_code=303)


@router.post("/profile/{profile_id}/projects/{project_id}/delete", response_class=HTMLResponse)
async def delete_project_submit(profile_id: int, project_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(get_admin_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    project = db.query(models.Project).filter(models.Project.id == project_id, models.Project.profile_id == profile_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    db.delete(project)
    db.commit()
    return RedirectResponse(url=f"/admin/profile/{profile_id}/projects", status_code=303)

# Experience Management Routes
@router.get("/profile/{profile_id}/experiences", response_class=HTMLResponse)
async def manage_experiences(profile_id: int, request: Request, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    experiences = db.query(models.Experience).filter(models.Experience.profile_id == profile_id).order_by(models.Experience.start_date.desc()).all()
    return templates.TemplateResponse("experiences.html", {"request": request, "profile": profile, "experiences": experiences})

@router.get("/profile/{profile_id}/experiences/create", response_class=HTMLResponse)
async def create_experience_page(profile_id: int, request: Request, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    return templates.TemplateResponse("experience_form.html", {"request": request, "experience": None, "profile_id": profile_id})

@router.post("/profile/{profile_id}/experiences/create", response_class=HTMLResponse)
async def create_experience_submit(
    profile_id: int,
    request: Request,
    company: str = Form(...),
    position: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(None),
    description: str = Form(...),
    is_current: str = Form(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)
):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    # Parse dates
    from datetime import datetime
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = None if is_current or not end_date else datetime.strptime(end_date, '%Y-%m-%d').date()
    
    new_experience = models.Experience(
        profile_id=profile_id,
        company=company,
        position=position,
        start_date=start_date_obj,
        end_date=end_date_obj,
        description=description
    )
    db.add(new_experience)
    db.commit()
    
    return RedirectResponse(url=f"/admin/profile/{profile_id}/experiences", status_code=303)

@router.get("/profile/{profile_id}/experiences/{exp_id}/edit", response_class=HTMLResponse)
async def edit_experience_page(profile_id: int, exp_id: int, request: Request, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    experience = db.query(models.Experience).filter(models.Experience.id == exp_id, models.Experience.profile_id == profile_id).first()
    if not experience:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")
    
    return templates.TemplateResponse("experience_form.html", {"request": request, "experience": experience, "profile_id": profile_id})

@router.post("/profile/{profile_id}/experiences/{exp_id}/edit", response_class=HTMLResponse)
async def edit_experience_submit(
    profile_id: int,
    exp_id: int,
    request: Request,
    company: str = Form(...),
    position: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(None),
    description: str = Form(...),
    is_current: str = Form(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)
):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    experience = db.query(models.Experience).filter(models.Experience.id == exp_id, models.Experience.profile_id == profile_id).first()
    if not experience:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")
    
    # Parse dates
    from datetime import datetime
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = None if is_current or not end_date else datetime.strptime(end_date, '%Y-%m-%d').date()
    
    experience.company = company
    experience.position = position
    experience.start_date = start_date_obj
    experience.end_date = end_date_obj
    experience.description = description
    
    db.commit()
    return RedirectResponse(url=f"/admin/profile/{profile_id}/experiences", status_code=303)

@router.post("/profile/{profile_id}/experiences/{exp_id}/delete", response_class=HTMLResponse)
async def delete_experience_submit(profile_id: int, exp_id: int, request: Request, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile or profile.userInput != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    experience = db.query(models.Experience).filter(models.Experience.id == exp_id, models.Experience.profile_id == profile_id).first()
    if not experience:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")
    
    db.delete(experience)
    db.commit()
    return RedirectResponse(url=f"/admin/profile/{profile_id}/experiences", status_code=303)
