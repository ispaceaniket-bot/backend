from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from .. import models, schemas, dependencies

router = APIRouter(prefix="/gp", tags=["GP Dashboard"])

# Schema for the Decision
class DecisionRequest(BaseModel):
    decision: str  # "approve" or "deny"
    comment: str   # Mandatory comment

# 1. VIEW ASSIGNED CASES
@router.get("/cases", response_model=List[schemas.CaseResponse])
def get_assigned_cases(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    if current_user.role != models.UserRole.GP:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Return all cases assigned to me (use DB, not local storage)
    cases = db.query(models.Case).filter(
        models.Case.assigned_gp_id == current_user.id
    ).order_by(models.Case.created_at.desc()).all()
    return cases

# 2. MAKE DECISION (Approve/Deny)
@router.post("/cases/{case_id}/decision")
def make_decision(
    case_id: int,
    request: DecisionRequest,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    if current_user.role != models.UserRole.GP:
        raise HTTPException(status_code=403, detail="Not authorized")

    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    
    # Security: Ensure this case is actually assigned to this GP
    if not case or case.assigned_gp_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found or not assigned to you")

    # LOGIC: Move to QA or Back to Claimant
    if request.decision.lower() == "approve":
        # GP approval — mark as completed (final approval) so UI reflects Approved
        case.status = models.CaseStatus.COMPLETED
        message = "Case Approved. Marked as completed."
    elif request.decision.lower() == "deny":
        case.status = models.CaseStatus.RETURNED
        message = "Case Denied. Returned to Claimant."
    else:
        raise HTTPException(status_code=400, detail="Decision must be 'approve' or 'deny'")
    
    # Save the mandatory comment
    case.gp_decision_comment = request.comment
    db.commit()
    
    return {"status": "success", "message": message, "new_case_status": case.status}