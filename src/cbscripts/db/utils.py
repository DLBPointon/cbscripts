from sqlalchemy.engine import Engine

from cbscripts.db import models
from cbscripts.db.engine import get_engine


def create_database(database_path: str) -> Engine:
    engine = get_engine(database_path)

    models.Base.metadata.create_all(engine)

    return engine


def drop_database(database_path: str) -> None:
    engine = get_engine(database_path)
    models.Base.metadata.drop_all(engine)


def reset_database(database_path: str) -> Engine:
    drop_database(database_path)
    return create_database(database_path)


if __name__ == "__main__":
    create_database("test.db")
