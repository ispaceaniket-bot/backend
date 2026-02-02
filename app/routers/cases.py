import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, dependencies

router = APIRouter(prefix="/cases", tags=["Cases"])

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/", response_model=schemas.CaseResponse)
def create_case(
    case_data: schemas.CaseCreate, 
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db)
):
    if current_user.role != models.UserRole.CLAIMANT:
        raise HTTPException(status_code=403, detail="Only claimants can create cases")

    new_case = models.Case(
        claimant_id=current_user.id,
        description=case_data.description,
        date_of_birth=case_data.date_of_birth,
        status=models.CaseStatus.PENDING
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    return new_case

@router.get("/my", response_model=list[schemas.CaseResponse])
def get_my_cases(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    return (
        db.query(models.Case)
        .filter(models.Case.claimant_id == current_user.id)
        .all()
    )

@router.get("/{case_id}/documents/", response_model=list[schemas.DocumentResponse])
def get_case_documents(
    case_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    documents = db.query(models.Document).filter(models.Document.case_id == case_id).all()
    return documents

@router.get("/{case_id}/download/{document_id}")
def download_document(
    case_id: int,
    document_id: int,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db)
):
    document = db.query(models.Document).filter(
        models.Document.id == document_id,
        models.Document.case_id == case_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    return FileResponse(
        path=document.file_path,
        filename=document.filename,
        media_type=document.file_type
    )

@router.post("/{case_id}/upload/")
async def upload_document(
    case_id: int, 
    file: UploadFile = File(...), 
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db)
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    await file.seek(0)

    file_location = f"{UPLOAD_DIR}/{case_id}_{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    new_doc = models.Document(
        case_id=case_id,
        filename=file.filename,
        file_path=file_location,
        file_type=file.content_type
    )
    db.add(new_doc)
    db.commit()
    return {"filename": file.filename, "status": "uploaded"}

@router.post("/{case_id}/discuss/", response_model=schemas.MessageResponse)
def post_message(
    case_id: int, 
    msg: schemas.MessageCreate, 
    current_user: models.User = Depends(dependencies.get_current_user), 
    db: Session = Depends(dependencies.get_db)
):
    new_msg = models.Message(
        case_id=case_id,
        sender_id=current_user.id,
        content=msg.content
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    return new_msg

@router.get("/{case_id}/discuss/", response_model=List[schemas.MessageResponse])
def get_messages(
    case_id: int, 
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    messages = db.query(models.Message).filter(models.Message.case_id == case_id).all()
    result = []
    for msg in messages:
        sender = db.query(models.User).filter(models.User.id == msg.sender_id).first()
        result.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "content": msg.content,
            "timestamp": msg.timestamp,
            "sender_username": sender.username if sender else "Unknown",
            "sender_role": sender.role.value if sender else "Unknown",
        })
    return result

@router.delete("/{case_id}")
def delete_case(
    case_id: int,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db)
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Only claimant who created the case can delete it
    if case.claimant_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the case creator can delete it")
    
    # Delete associated documents
    documents = db.query(models.Document).filter(models.Document.case_id == case_id).all()
    for doc in documents:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
        db.delete(doc)
    
    # Delete associated messages
    messages = db.query(models.Message).filter(models.Message.case_id == case_id).all()
    for msg in messages:
        db.delete(msg)
    
    # Delete the case
    db.delete(case)
    db.commit()
    
    # Reset the sequence to the highest remaining ID (PostgreSQL specific)
    try:
        max_id = db.query(models.Case).all()
        if max_id:
            max_id_value = max([c.id for c in max_id])
            db.execute(f"ALTER SEQUENCE cases_id_seq RESTART WITH {max_id_value + 1}")
        else:
            # If no cases left, restart from 1
            db.execute("ALTER SEQUENCE cases_id_seq RESTART WITH 1")
        db.commit()
    except Exception as e:
        print(f"Error resetting sequence: {e}")
    
    return {"status": "deleted", "case_id": case_id}