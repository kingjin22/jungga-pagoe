from fastapi import APIRouter
import app.db_supabase as db

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
async def get_stats():
    return db.get_stats()
