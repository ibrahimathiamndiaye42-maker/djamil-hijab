from ..extensions import db
from ..models import AuditLog


def log(user, action, entity_type=None, entity_ref=None, details=None):
    db.session.add(AuditLog(user_id=user.id if user else None, user_name=user.full_name if user else None,
                            action=action, entity_type=entity_type, entity_ref=entity_ref, details=details))
