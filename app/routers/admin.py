from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, dependencies

router = APIRouter(prefix="/admin", tags=["Admin"])

# 1. GET LIST OF GPs (For the Dropdown)
@router.get("/gps", response_model=List[schemas.SimpleUser])
def get_all_gps(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Fetch only users who are GPs
    gps = db.query(models.User).filter(models.User.role == models.UserRole.GP).all()
    return gps

# 2. GET ALL CASES (For Admin Dashboard)
@router.get("/cases/all", response_model=List[schemas.CaseResponse])
def get_all_cases(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return db.query(models.Case).all()

# 3. VIEW PENDING CASES
@router.get("/cases/pending", response_model=List[schemas.CaseResponse])
def view_pending_cases(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return db.query(models.Case).filter(
        models.Case.status.in_([models.CaseStatus.PENDING, models.CaseStatus.REVIEW])
    ).all()

# 4. REVIEW CASE (Details)
@router.get("/cases/{case_id}")
def review_case_details(
    case_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    documents = db.query(models.Document).filter(models.Document.case_id == case_id).all()
    
    return {"case": case, "documents": documents}

# 5. ASSIGN GP, SPECIALTY & SLA
@router.post("/cases/{case_id}/assign")
def assign_gp(
    case_id: int,
    request: schemas.AssignGPRequest,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Validate the GP exists
    gp_user = db.query(models.User).filter(models.User.id == request.gp_id).first()
    if not gp_user or gp_user.role != models.UserRole.GP:
        raise HTTPException(status_code=400, detail="Selected user is not a GP")

    # Update Case Logic
    case.assigned_gp_id = request.gp_id
    case.specialty = request.specialty
    case.sla_deadline = request.sla_deadline
    
    # Change status to ASSIGNED so it appears in the GP's dashboard
    case.status = models.CaseStatus.ASSIGNED 
    
    db.commit()
    return {
        "message": f"Case assigned to {gp_user.username}",
        "specialty": request.specialty,
        "deadline": request.sla_deadline
    }