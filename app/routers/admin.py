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
        .options(selectinload(models.Profile.skills), selectinload(models.Profile.experiences))
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
