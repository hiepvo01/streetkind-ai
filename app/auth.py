"""
Firebase ID token verification for FastAPI.

Usage in routes:
    from .auth import get_current_uid

    @router.get("/api/me")
    def me(uid: str = Depends(get_current_uid)):
        ...

The frontend must send:  Authorization: Bearer <firebase-id-token>
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth

from .services.firebase_client import _init_firebase

_bearer_scheme = HTTPBearer()


def get_current_uid(
    creds: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> str:
    """Verify the Firebase ID token and return the caller's UID."""
    _init_firebase()
    try:
        decoded = auth.verify_id_token(creds.credentials)
        return decoded["uid"]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase ID token",
        )
