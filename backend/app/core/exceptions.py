"""
ข้อยกเว้นกำหนดเอง สำหรับการจัดการข้อผิดพลาดระดับ production
"""


class AgentException(Exception):
    """Base exception for agent-related errors"""
    pass


class StorageException(AgentException):
    """Exception raised for storage operations"""
    pass


class LLMException(AgentException):
    """Exception raised for LLM API errors"""
    pass


class ValidationException(AgentException):
    """Exception raised for data validation errors"""
    pass


class AmadeusException(AgentException):
    """Exception raised for Amadeus API errors"""
    pass
