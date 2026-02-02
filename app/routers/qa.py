from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func
from pydantic import BaseModel
from .. import models, schemas, dependencies

router = APIRouter(prefix="/qa", tags=["QA Dashboard"])

class QAFeedbackRequest(BaseModel):
    feedback: str # Mandatory feedback
    approved: bool # True = Final Approval, False = Fail QA

# 1. RANDOM CASE ASSIGNMENT
@router.post("/assign-random", response_model=schemas.CaseResponse)
def assign_random_case(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    if current_user.role != models.UserRole.QA:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Find a random case that is not already assigned to QA and not returned.
    # This allows QA to pick from cases that are QA pending, completed, or otherwise available
    case = db.query(models.Case).filter(
        models.Case.assigned_qa_id == None,
        models.Case.status != models.CaseStatus.RETURNED
    ).order_by(func.random()).first()

    if not case:
        raise HTTPException(status_code=404, detail="No cases available for QA at the moment")

    # Assign it to this QA user
    case.assigned_qa_id = current_user.id
    db.commit()
    db.refresh(case)
    return case

# 2. VIEW MY ASSIGNED CASES
@router.get("/my-cases", response_model=list[schemas.CaseResponse])
def get_my_qa_cases(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    if current_user.role != models.UserRole.QA:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    return db.query(models.Case).filter(models.Case.assigned_qa_id == current_user.id).all()


@router.get("/cases", response_model=list[schemas.CaseResponse])
def get_qa_pool_cases(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    if current_user.role != models.UserRole.QA:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Return all cases that QA can work on (all cases except those never assigned)
    # This includes COMPLETED (approved by QA) and RETURNED (rejected by QA) so QA can see their work
    cases = db.query(models.Case).order_by(models.Case.created_at.desc()).all()
    return cases

# 3. SUBMIT QA FEEDBACK (Final Step)
@router.post("/cases/{case_id}/feedback")
def submit_qa_feedback(
    case_id: int,
    request: QAFeedbackRequest,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    if current_user.role != models.UserRole.QA:
        raise HTTPException(status_code=403, detail="Not authorized")

    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # QA can audit any case independently (no assignment check needed)
    # Update Feedback and mark as audited by this QA
    case.qa_feedback = request.feedback
    case.assigned_qa_id = current_user.id
    
    if request.approved:
        case.status = models.CaseStatus.COMPLETED
        msg = "Case Closed. QA Approved."
    else:
        # If QA fails it, maybe send back to GP?
        # For this demo, let's mark it RETURNED
        case.status = models.CaseStatus.RETURNED
        msg = "Case Returned. QA Rejected."

    db.commit()
    return {"message": msg, "status": case.status}