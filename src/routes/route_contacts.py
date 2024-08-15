from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi_limiter.depends import RateLimiter

from src.database.connect import Database
from src.database.models import User
from src.repository.contacts import ContactDB
from src.schemas.contacts import ContactsResponse, ContactCreate, ContactUpdate
from src.schemas.roles import RoleEnum
from src.services.auth import auth_service
from src.services.roles import RoleAccess

router = APIRouter()
database = Database()


@router.get("/healthchecker", tags=["default"])
async def get_healthcheck(contact_db: ContactDB = Depends(database.get_contact_db)):
    try:
        # Make a simple query
        result = await contact_db.healthcheck()
        if result is None:
            raise HTTPException(status_code=500, detail="Database is not configured correctly")
        return {"message": "Welcome to FastAPI. The API is up and running!"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Could not connect to the database")


@router.get("/contacts", response_model=List[ContactsResponse])
async def read_contacts(limit: int = 100, offset: int = 0,
                        first_name: Optional[str] = Query(None),
                        last_name: Optional[str] = Query(None),
                        email: Optional[str] = Query(None),
                        contact_db: ContactDB = Depends(database.get_contact_db),
                        user: User = Depends(auth_service.get_current_user)):
    contacts = await contact_db.get_contacts(offset=offset, limit=limit, first_name=first_name, last_name=last_name,
                                             email=email, user=user)
    return contacts


@router.get("/contacts/all/",
            dependencies=[Depends(RoleAccess([RoleEnum.admin.value, RoleEnum.moderator.value]))],
            response_model=List[ContactsResponse],
            tags=["admin"])
async def read_contacts(limit: int = 100, offset: int = 0,
                        first_name: Optional[str] = Query(None),
                        last_name: Optional[str] = Query(None),
                        email: Optional[str] = Query(None),
                        contact_db: ContactDB = Depends(database.get_contact_db),):
    contacts = await contact_db.get_contacts_all(offset=offset,
                                                 limit=limit,
                                                 first_name=first_name,
                                                 last_name=last_name,
                                                 email=email)
    return contacts


@router.get("/contacts/{contact_id}", response_model=ContactsResponse)
async def read_contact(contact_id: int, contact_db: ContactDB = Depends(database.get_contact_db),
                       user: User = Depends(auth_service.get_current_user)):
    contact = await contact_db.get_contact(contact_id, user)
    if contact is None:
        raise HTTPException(status_code=404, detail=f"Contact id = {contact_id} not found")
    return contact


@router.get("/contacts/birthday/{days_number}", response_model=List[ContactsResponse])
async def read_contacts_birthday(days_number: int = Path(ge=7),
                                 contact_db: ContactDB = Depends(database.get_contact_db),
                                 user: User = Depends(auth_service.get_current_user)):
    contacts = await contact_db.get_contacts_birthday(days_number=days_number, user=user)
    return contacts


@router.post("/contacts", response_model=ContactsResponse, dependencies=[Depends(RateLimiter(times=5, seconds=20))])
async def create_contact(body: ContactCreate, contact_db: ContactDB = Depends(database.get_contact_db),
                         user: User = Depends(auth_service.get_current_user)):
    contact = await contact_db.create_contact(body=body, user=user)
    return contact


@router.put("/contacts/{contact_id}", dependencies=[Depends(RateLimiter(times=1, seconds=20))])
async def update_contact(body: ContactUpdate, contact_id: int = Path(ge=1),
                         contact_db: ContactDB = Depends(database.get_contact_db),
                         user: User = Depends(auth_service.get_current_user)):
    contact = await contact_db.update_contact(contact_id=contact_id, body=body, user=user)
    if contact is None:
        raise HTTPException(status_code=404, detail=f"Contact with id = {contact_id} not found")
    return contact


@router.delete("/contacts/{contact_id}", status_code=204)
async def delete_contact(contact_id: int, contact_db: ContactDB = Depends(database.get_contact_db),
                         user: User = Depends(auth_service.get_current_user)):
    contact = await contact_db.delete_contact(contact_id=contact_id, user=user)
    if contact is None:
        raise HTTPException(status_code=404, detail=f"Contact with id={contact_id} not found")
