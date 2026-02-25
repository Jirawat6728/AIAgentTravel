"""โมดูล storage: อินเทอร์เฟซและตัวจัดเก็บ (JSON, MongoDB). ใช้ MongoDB 100% ใน production."""
from app.storage.interface import StorageInterface
from app.storage.json_storage import JsonFileStorage
from app.storage.mongodb_storage import MongoStorage

__all__ = ["StorageInterface", "JsonFileStorage", "MongoStorage"]
