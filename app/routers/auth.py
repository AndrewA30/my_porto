#router to create authentication endpoints, seperti login, register, dll
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, schemas, utils, oauth2
from ..database import get_db
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# endpoint untuk create user baru
@router.post("/create", status_code=status.HTTP_201_CREATED, response_model=schemas.UserResponse)
def create_user(new_user: schemas.CreateUser, db: Session = Depends(get_db)):
    # check if email already exists
    user = db.query(models.UserLogin).filter(models.UserLogin.email == new_user.email).first()
    if user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    # hash password
    hashed_password = utils.hash_password(new_user.password)
    new_user.password = hashed_password

    # create user baru
    new_user = models.UserLogin(**new_user.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

#endpoint untuk login user
@router.post("/login", response_model=schemas.token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.UserLogin).filter(models.UserLogin.email == form_data.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Credential")
    
    if not utils.verify_password(form_data.password, user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Credential")
    
    # create token
    access_token = oauth2.create_access_token(data={"user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}   