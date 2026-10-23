from sqlalchemy import select
from ..constants import DEFAULT_SETTINGS
from ..extensions import db
from ..models import Setting


def get_settings():
    out = dict(DEFAULT_SETTINGS)
    for s in db.session.execute(select(Setting)).scalars():
        out[s.key] = s.value
    return out
