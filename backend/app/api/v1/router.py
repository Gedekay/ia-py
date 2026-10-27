from fastapi import APIRouter

from app.api.v1 import admin, analyses, auth, documents, dossiers, users


router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(dossiers.router)
router.include_router(documents.router)
router.include_router(analyses.router)
router.include_router(admin.router)