from sqlalchemy import create_engine

database_path = "sqlite+pysqlite:////home/dlbpointon/Documents/cbscripts/cbscripts.db"

engine = create_engine(database_path, echo=True)
