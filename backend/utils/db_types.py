"""
Custom database types for cross-database compatibility
"""
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.

    Uses PostgreSQL's UUID type when using PostgreSQL,
    otherwise uses CHAR(36), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value

        # Normalise to a real UUID first so that a string input and a UUID
        # input cannot take different paths.
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))

        if dialect.name == 'postgresql':
            # psycopg2 adapts uuid.UUID natively. Passing a str here instead
            # makes SQLAlchemy's insertmanyvalues unable to match the returned
            # sentinel values against the parameter sets, which breaks every
            # bulk insert on Postgres with "Can't match sentinel values".
            return value

        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            else:
                return value
