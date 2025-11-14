from .models import Base, Document, IngestionState, VisitedUrl

# Lazy wrappers to avoid importing db.py at package import time
def create_sqlite_engine(db_path):
	from .db import create_sqlite_engine as _f
	return _f(db_path)

def create_engine_from_url(db_url):
	from .db import create_engine_from_url as _f
	return _f(db_url)

def init_db(db_path):
	from .db import init_db as _f
	return _f(db_path)

def migrate_db(db_path):
	from .db import migrate_db as _f
	return _f(db_path)

