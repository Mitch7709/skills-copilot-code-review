"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


@router.get("/active", response_model=List[Dict[str, Any]])
def get_active_announcements() -> List[Dict[str, Any]]:
    """
    Get all currently active announcements.
    An announcement is active if:
    - current date >= start_date (if start_date exists)
    - current date < expiration_date
    """
    now = datetime.now()
    
    # Query for active announcements
    query = {
        "$and": [
            {"expiration_date": {"$gt": now}},
            {
                "$or": [
                    {"start_date": None},
                    {"start_date": {"$lte": now}}
                ]
            }
        ]
    }
    
    announcements = []
    for announcement in announcements_collection.find(query).sort("created_at", -1):
        # Convert ObjectId to string for JSON serialization
        announcement["_id"] = str(announcement["_id"])
        # Convert datetime to ISO format strings
        if announcement.get("start_date"):
            announcement["start_date"] = announcement["start_date"].isoformat()
        announcement["expiration_date"] = announcement["expiration_date"].isoformat()
        announcement["created_at"] = announcement["created_at"].isoformat()
        announcements.append(announcement)
    
    return announcements


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_all_announcements(teacher_username: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """
    Get all announcements (for management interface).
    Requires teacher authentication.
    """
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    announcements = []
    for announcement in announcements_collection.find().sort("created_at", -1):
        # Convert ObjectId to string for JSON serialization
        announcement["_id"] = str(announcement["_id"])
        # Convert datetime to ISO format strings
        if announcement.get("start_date"):
            announcement["start_date"] = announcement["start_date"].isoformat()
        announcement["expiration_date"] = announcement["expiration_date"].isoformat()
        announcement["created_at"] = announcement["created_at"].isoformat()
        announcements.append(announcement)
    
    return announcements


@router.post("", response_model=Dict[str, Any])
@router.post("/", response_model=Dict[str, Any])
def create_announcement(
    message: str,
    expiration_date: str,
    start_date: Optional[str] = None,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Create a new announcement.
    Requires teacher authentication.
    
    - message: The announcement text
    - expiration_date: ISO format datetime string (required)
    - start_date: ISO format datetime string (optional)
    """
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    # Validate message
    if not message or len(message.strip()) == 0:
        raise HTTPException(
            status_code=400, detail="Message cannot be empty")
    
    # Parse and validate dates
    try:
        exp_date = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid expiration_date format. Use ISO format.")
    
    start_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid start_date format. Use ISO format.")
    
    # Validate expiration date is in the future
    if exp_date <= datetime.now():
        raise HTTPException(
            status_code=400, detail="Expiration date must be in the future")
    
    # Validate start_date is before expiration_date
    if start_dt and start_dt >= exp_date:
        raise HTTPException(
            status_code=400, detail="Start date must be before expiration date")
    
    # Create announcement
    announcement = {
        "message": message.strip(),
        "start_date": start_dt,
        "expiration_date": exp_date,
        "created_at": datetime.now()
    }
    
    result = announcements_collection.insert_one(announcement)
    
    # Return the created announcement
    announcement["_id"] = str(result.inserted_id)
    if announcement.get("start_date"):
        announcement["start_date"] = announcement["start_date"].isoformat()
    announcement["expiration_date"] = announcement["expiration_date"].isoformat()
    announcement["created_at"] = announcement["created_at"].isoformat()
    
    return announcement


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    message: str,
    expiration_date: str,
    start_date: Optional[str] = None,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Update an existing announcement.
    Requires teacher authentication.
    """
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    # Validate announcement exists
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID format")
    
    announcement = announcements_collection.find_one({"_id": obj_id})
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Validate message
    if not message or len(message.strip()) == 0:
        raise HTTPException(
            status_code=400, detail="Message cannot be empty")
    
    # Parse and validate dates
    try:
        exp_date = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid expiration_date format. Use ISO format.")
    
    start_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid start_date format. Use ISO format.")
    
    # Validate start_date is before expiration_date
    if start_dt and start_dt >= exp_date:
        raise HTTPException(
            status_code=400, detail="Start date must be before expiration date")
    
    # Update announcement
    update_data = {
        "message": message.strip(),
        "start_date": start_dt,
        "expiration_date": exp_date
    }
    
    announcements_collection.update_one(
        {"_id": obj_id},
        {"$set": update_data}
    )
    
    # Return the updated announcement
    updated_announcement = announcements_collection.find_one({"_id": obj_id})
    updated_announcement["_id"] = str(updated_announcement["_id"])
    if updated_announcement.get("start_date"):
        updated_announcement["start_date"] = updated_announcement["start_date"].isoformat()
    updated_announcement["expiration_date"] = updated_announcement["expiration_date"].isoformat()
    updated_announcement["created_at"] = updated_announcement["created_at"].isoformat()
    
    return updated_announcement


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, str]:
    """
    Delete an announcement.
    Requires teacher authentication.
    """
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    # Validate announcement exists
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID format")
    
    announcement = announcements_collection.find_one({"_id": obj_id})
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Delete announcement
    announcements_collection.delete_one({"_id": obj_id})
    
    return {"message": "Announcement deleted successfully"}
