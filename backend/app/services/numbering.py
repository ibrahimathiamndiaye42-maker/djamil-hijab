from datetime import datetime, timezone
from ..extensions import db
from ..models import NumberSequence


def _next(key):
    if db.engine.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
        db.session.execute(insert(NumberSequence).values(key=key, value=0).on_conflict_do_nothing())
    row = db.session.get(NumberSequence, key, with_for_update=True)
    if row is None:
        row = NumberSequence(key=key, value=0)
        db.session.add(row)
        db.session.flush()
    row.value += 1
    db.session.flush()
    return row.value


def code(prefix, width=6, yearly=False):
    """Génère un identifiant unique sans doublon : PRD-000001, FAC-2026-000001..."""
    year = datetime.now(timezone.utc).year
    if yearly:
        return f"{prefix}-{year}-{_next(f'{prefix}-{year}'):0{width}d}"
    return f"{prefix}-{_next(prefix):0{width}d}"
