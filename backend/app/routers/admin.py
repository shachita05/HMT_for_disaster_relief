"""Admin routes: user management, system health, model metrics."""
import platform
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.security import ROLE_ADMIN
from app.models.alert import Alert
from app.models.model_metric import ModelMetric
from app.models.post import Post
from app.models.user import User

router = APIRouter()


def _require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user


@router.get("/users")
def list_users(db: Session = Depends(get_db), _admin: User = Depends(_require_admin)):
    """List all users (admin only)."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.patch("/users/{user_id}/role")
def update_user_role(user_id: int, role: str, db: Session = Depends(get_db), _admin: User = Depends(_require_admin)):
    """Change a user's role (admin only)."""
    if role not in ("admin", "analyst"):
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'analyst'")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = role
    db.commit()
    return {"message": "Role updated", "id": user.id, "role": user.role}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), _admin: User = Depends(_require_admin)):
    """Delete a user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == _admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}


@router.get("/system-health")
def system_health(db: Session = Depends(get_db), _admin: User = Depends(_require_admin)):
    """Return system health metrics (admin only)."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "postgres": "connected",
        "total_posts": db.query(Post).count(),
        "total_alerts": db.query(Alert).count(),
        "total_users": db.query(User).count(),
    }


@router.get("/model-metrics")
def model_metrics(db: Session = Depends(get_db), _admin: User = Depends(_require_admin)):
    """Return ML model comparison metrics (admin only)."""
    metrics = db.query(ModelMetric).order_by(ModelMetric.f1.desc()).all()
    return [
        {
            "model_name": m.model_name,
            "accuracy": m.accuracy,
            "precision": m.precision,
            "recall": m.recall,
            "f1": m.f1,
            "confusion_matrix": m.confusion_matrix,
            "trained_at": m.trained_at.isoformat(),
        }
        for m in metrics
    ]