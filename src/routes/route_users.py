import pickle

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, Request, Security, HTTPException, status, BackgroundTasks, UploadFile, File, \
    Form
from fastapi.security import OAuth2PasswordRequestForm, HTTPAuthorizationCredentials, HTTPBearer
from fastapi_limiter.depends import RateLimiter
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from src.config.config import settings
from src.database.connect import Database
from src.database.models import User
from src.repository.users import UserDB
from src.schemas.users import UserModel, UserResponse, TokenModel, RequestEmail
from src.services.auth import auth_service
from src.services.email import send_email, send_reset_password_email

# Initialize templates
templates = Jinja2Templates(directory="src/static/templates")

router = APIRouter(prefix="/auth", tags=["auth"])

database = Database()
cloudinary.config(cloud_name=settings.cloud_name,
                  api_key=settings.api_key,
                  api_secret=settings.api_secret,
                  secure=True)

get_refresh_token = HTTPBearer()


async def get_email_form_refresh_token(token: str):
    try:
        payload = jwt.decode(token, auth_service.SECRET_KEY, algorithms=[auth_service.ALGORITHM])
        email = payload.get("sub")
        return email
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: UserModel, background_tasks: BackgroundTasks, request: Request,
                 user_db: UserDB = Depends(database.get_user_db)):
    exist_user = await user_db.get_user_by_email(email=body.email)
    if exist_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account with this email already exists")
    body.password = auth_service.get_password_hash(body.password)
    new_user = await user_db.create_user(body=body)
    background_tasks.add_task(send_email, new_user.email, new_user.username, str(request.base_url))
    return new_user


@router.post("/login", response_model=TokenModel, dependencies=[Depends(RateLimiter(times=3, seconds=20))])
async def login(body: OAuth2PasswordRequestForm = Depends(), user_db: UserDB = Depends(database.get_user_db)):
    user = await user_db.get_user_by_email(email=body.username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email")
    if not user.confirmed:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not confirmed")
    if not auth_service.verify_password(body.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    # Generate JWT
    access_token = await auth_service.create_access_token(data={"sub": user.email, "test": "RomboAPI"})
    refresh_token = await auth_service.create_refresh_token(data={"sub": user.email})
    await user_db.update_token(user, refresh_token)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.get('/refresh_token')
async def refresh_token(credentials: HTTPAuthorizationCredentials = Security(get_refresh_token),
                        user_db: UserDB = Depends(database.get_user_db)):
    token = credentials.credentials
    email = await auth_service.decode_refresh_token(token)
    user = await user_db.get_user_by_email(email=email)
    if user.refresh_token != token:
        await user_db.update_token(user, None)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token = await auth_service.create_access_token(data={"sub": email})
    refresh_token = await auth_service.create_refresh_token(data={"sub": email})
    await user_db.update_token(user, refresh_token)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.get('/confirmed_email/{token}')
async def confirmed_email(token: str, user_db: UserDB = Depends(database.get_user_db)):
    email = await auth_service.get_email_from_token(token)
    user = await user_db.get_user_by_email(email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error")
    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    await user_db.confirmed_email(email)
    return {"message": "Email confirmed"}


@router.post('/request_email')
async def request_email(body: RequestEmail, background_tasks: BackgroundTasks, request: Request,
                        user_db: UserDB = Depends(database.get_user_db)):
    user = await user_db.get_user_by_email(body.email)

    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    if user:
        background_tasks.add_task(send_email, user.email, user.username, str(request.base_url))
    return {"message": "Check your email for confirmation."}


@router.patch('/avatar', response_model=UserResponse, dependencies=[Depends(RateLimiter(times=3, seconds=20))])
async def avatar(file: UploadFile = File(), user: User = Depends(auth_service.get_current_user),
                 user_db: UserDB = Depends(database.get_user_db)):
    res = cloudinary.uploader.upload(file.file, public_id=user.email, overwrite=True)
    res_url = cloudinary.CloudinaryImage(user.email).build_url(width=200, height=200, crop="fill",
                                                               version=res.get("version"))
    await user_db.update_avatar(user.email, res_url)
    auth_service.cach.set(user.email, pickle.dumps(user))
    auth_service.cach.expire(user.email, time=300)
    return user


@router.get("/reset_password/{token}", response_class=HTMLResponse)
async def reset_password_form(request: Request, token: str):
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})

@router.post("/reset_password")
async def reset_password(token: str = Form(...), newPassword: str = Form(...), confirmPassword: str = Form(...), user_db: UserDB = Depends(database.get_user_db)):
    if newPassword != confirmPassword:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    email = await auth_service.decode_reset_password_token(token)
    user = await user_db.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.password = auth_service.get_password_hash(newPassword)
    await user_db.update_password(email, user.password)
    return {"message": "Password successfully reset."}

@router.post("/request_reset_password")
async def request_reset_password(body: RequestEmail, background_tasks: BackgroundTasks, request: Request,
                                 user_db: UserDB = Depends(database.get_user_db)):
    user = await user_db.get_user_by_email(body.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    background_tasks.add_task(send_reset_password_email, user.email, user.username, str(request.base_url))
    return {"message": "Check your email for reset password link."}