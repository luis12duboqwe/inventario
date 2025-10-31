"""Utilities to initialise the database."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.transactions import flush_session, transactional_session
from ..models.device import Device
from ..models.store import Store


def init_db(session: Session) -> None:
    """Ensure base entities exist."""

    if not session.execute(select(Store)).first():
        with transactional_session(session):
            demo_store = Store(name="Central", location="HQ", timezone="UTC")
            session.add(demo_store)
            flush_session(session)

            session.add(
                Device(
                    store_id=demo_store.id,
                    sku="DEMO-001",
                    name="Equipo de demostración",
                    quantity=5,
                )
            )
