"""
Export toàn bộ SQLAlchemy Models cho Mediscan AI.
"""

from app.models.user import User
from app.models.profile import UserProfileModel
from app.models.medication import UserMedicationModel
from app.models.history import ScanHistoryModel
from app.models.reminder import ReminderModel

__all__ = [
    "User",
    "UserProfileModel",
    "UserMedicationModel",
    "ScanHistoryModel",
    "ReminderModel",
]
