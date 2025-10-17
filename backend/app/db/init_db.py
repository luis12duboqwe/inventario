"""Utilities to initialise the database."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Device, Store


def init_db(session: Session) -> None:
    """Ensure base entities exist."""

    if not session.execute(select(Store)).first():
        demo_store = Store(name="Central", location="HQ", timezone="UTC")
        session.add(demo_store)
        session.flush()

        session.add(
            Device(
                store_id=demo_store.id,
                sku="DEMO-001",
                name="Equipo de demostración",
                quantity=5,
            )
        )
        session.commit()
