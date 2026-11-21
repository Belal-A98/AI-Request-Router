from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Base(DeclarativeBase):
    pass

def make_engine(db_url: str):
    kw = {'pool_pre_ping': True}
    if make_url(db_url).get_backend_name() == 'sqlite':
        kw['connect_args'] = {'timeout': 20, 'check_same_thread': False}
    engine = create_engine(db_url, **kw)
    if make_url(db_url).get_backend_name() == 'sqlite':
        @event.listens_for(engine, 'connect')
        def configure_sqlite(conn, _):
            cur=conn.cursor()
            cur.execute('PRAGMA busy_timeout=20000')
            cur.execute('PRAGMA foreign_keys=ON')
            cur.close()
    return engine

def make_session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False)
