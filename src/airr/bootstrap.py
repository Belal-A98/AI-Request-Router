"""Development-only schema bootstrap; use versioned migrations in production."""
from .config import Settings
from .db import Base,make_engine
from . import models # noqa

def main():
    engine=make_engine(Settings.from_env().db_url)
    Base.metadata.create_all(engine)
    print('Local development schema created. Do not use create_all for production upgrades.')

if __name__ == '__main__':main()
