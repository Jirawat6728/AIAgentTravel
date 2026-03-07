"""
บริการผู้จองร่วม (Family/Cotravelers) — แยกจากโปรไฟล์ส่วนตัวใน MongoDB
เก็บใน collection user_family เหมือน user_saved_cards (หนึ่ง doc ต่อ user พร้อม updated_at)
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ชื่อ collection
USER_FAMILY_COLLECTION = "user_family"


async def get_user_family(db, user_id: str) -> List[Dict[str, Any]]:
    """
    ดึงรายการผู้จองร่วมจาก user_family collection
    Fallback: ถ้ายังไม่มีใน user_family ให้อ่านจาก users.family (legacy)
    """
    if db is None or not user_id:
        return []
    try:
        coll = db[USER_FAMILY_COLLECTION]
        doc = await coll.find_one({"user_id": user_id})
        if doc is not None and "family" in doc:
            return doc.get("family") or []
        # Legacy: อ่านจาก users.family
        users_coll = db["users"]
        user_doc = await users_coll.find_one({"user_id": user_id})
        if user_doc and user_doc.get("family") is not None:
            legacy = user_doc.get("family") or []
            # migrate: คัดลอกไป user_family ครั้งแรกที่อ่าน
            try:
                now = datetime.utcnow()
                await coll.update_one(
                    {"user_id": user_id},
                    {"$set": {"family": legacy, "user_id": user_id, "updated_at": now.isoformat() + "Z"}},
                    upsert=True,
                )
                # ลบออกจาก users เพื่อไม่อ่านซ้ำ
                await users_coll.update_one(
                    {"user_id": user_id},
                    {"$unset": {"family": 1}},
                )
            except Exception as e:
                logger.warning(f"Migration family to user_family failed: {e}")
            return legacy
        return []
    except Exception as e:
        logger.warning(f"get_user_family failed for {user_id}: {e}")
        return []


async def save_user_family(db, user_id: str, family: List[Dict[str, Any]]) -> None:
    """บันทึกรายการผู้จองร่วมลง user_family collection (เหมือน user_saved_cards มี updated_at)"""
    if db is None or not user_id:
        return
    try:
        now = datetime.utcnow()
        coll = db[USER_FAMILY_COLLECTION]
        await coll.update_one(
            {"user_id": user_id},
            {"$set": {"family": family or [], "user_id": user_id, "updated_at": now.isoformat() + "Z"}},
            upsert=True,
        )
        # ลบ family ออกจาก users ถ้ามี ( legacy cleanup )
        users_coll = db["users"]
        await users_coll.update_one(
            {"user_id": user_id},
            {"$unset": {"family": 1}},
        )
    except Exception as e:
        logger.error(f"save_user_family failed for {user_id}: {e}")
        raise


async def add_family_member(db, user_id: str, member: Dict[str, Any]) -> List[Dict[str, Any]]:
    """เพิ่มผู้จองร่วม 1 คน (เหมือน $push ใน user_saved_cards)"""
    if db is None or not user_id or not member:
        return []
    try:
        now = datetime.utcnow()
        coll = db[USER_FAMILY_COLLECTION]
        await coll.update_one(
            {"user_id": user_id},
            {"$push": {"family": member}, "$set": {"user_id": user_id, "updated_at": now.isoformat() + "Z"}},
            upsert=True,
        )
        doc = await coll.find_one({"user_id": user_id})
        return doc.get("family") or []
    except Exception as e:
        logger.error(f"add_family_member failed for {user_id}: {e}")
        raise


async def update_family_member(db, user_id: str, member_id: str, member: Dict[str, Any]) -> List[Dict[str, Any]]:
    """อัปเดตผู้จองร่วมตาม id (เหมือนแก้ไข element ใน array)"""
    if db is None or not user_id or not member_id:
        return []
    try:
        now = datetime.utcnow()
        coll = db[USER_FAMILY_COLLECTION]
        doc = await coll.find_one({"user_id": user_id})
        if not doc:
            return []
        family = doc.get("family") or []
        idx = next((i for i, m in enumerate(family) if m.get("id") == member_id), None)
        if idx is None:
            return family
        member_merged = dict(family[idx])
        for k, v in member.items():
            if k != "id":
                member_merged[k] = v
        family[idx] = member_merged
        await coll.update_one(
            {"user_id": user_id},
            {"$set": {"family": family, "updated_at": now.isoformat() + "Z"}},
        )
        return family
    except Exception as e:
        logger.error(f"update_family_member failed for {user_id}: {e}")
        raise


async def delete_family_member(db, user_id: str, member_id: str) -> List[Dict[str, Any]]:
    """ลบผู้จองร่วมตาม id (เหมือน $pull ใน user_saved_cards)"""
    if db is None or not user_id or not member_id:
        return []
    try:
        now = datetime.utcnow()
        coll = db[USER_FAMILY_COLLECTION]
        result = await coll.update_one(
            {"user_id": user_id},
            {"$pull": {"family": {"id": member_id}}, "$set": {"updated_at": now.isoformat() + "Z"}},
        )
        if result.matched_count == 0:
            return []
        doc = await coll.find_one({"user_id": user_id})
        return doc.get("family") or []
    except Exception as e:
        logger.error(f"delete_family_member failed for {user_id}: {e}")
        raise


async def get_user_with_family(db, user_id: str) -> Optional[Dict[str, Any]]:
    """
    ดึง user document พร้อม family ที่ merge จาก user_family
    สำหรับ API ที่ต้อง return user เต็มรูปแบบ
    """
    if db is None or not user_id:
        return None
    try:
        users_coll = db["users"]
        user_doc = await users_coll.find_one({"user_id": user_id})
        if not user_doc:
            return None
        family = await get_user_family(db, user_id)
        result = dict(user_doc)
        result["family"] = family
        return result
    except Exception as e:
        logger.warning(f"get_user_with_family failed for {user_id}: {e}")
        return None
