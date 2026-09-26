from cbscripts.db import models
from cbscripts.db.engine import engine


def create_database() -> None:
    models.Base.metadata.create_all(engine)


def drop_database() -> None:
    models.Base.metadata.drop_all(engine)


def reset_database() -> None:
    drop_database()
    create_database()


if __name__ == "__main__":
    create_database()
