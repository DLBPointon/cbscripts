from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def get_engine(database_path: str) -> Engine:
    print(database_path)
    return create_engine(
        f"sqlite+pysqlite:///{database_path}",
        echo=True,
    )
