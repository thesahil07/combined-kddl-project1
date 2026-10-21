"""SQLAlchemy declarative base for future typed ORM models.

The initial migration is deliberately executed from the reviewed MySQL DDL so
generated columns and constraints remain byte-for-byte faithful to the schema.
Model groups below reserve the correct home for their future typed mappings.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
