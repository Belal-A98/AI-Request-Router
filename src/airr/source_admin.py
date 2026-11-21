"""Local-only source provisioning CLI; never expose credential operations via HTTP."""
import argparse
from .config import Settings
from .db import make_engine, make_session_factory
from .modules.sources.service import provision_source, rotate_source_key, set_source_enabled


def main() -> None:
    parser = argparse.ArgumentParser(description='Operator source credential management')
    parser.add_argument('action', choices=('create', 'rotate', 'enable', 'disable'))
    parser.add_argument('source_id')
    args = parser.parse_args()
    engine = make_engine(Settings.from_env().db_url)
    try:
        sf = make_session_factory(engine)
        if args.action == 'create':
            key = provision_source(sf, args.source_id)
        elif args.action == 'rotate':
            key = rotate_source_key(sf, args.source_id)
        else:
            set_source_enabled(sf, args.source_id, args.action == 'enable')
            key = None
        if key is not None:
            print('NEW_SOURCE_KEY=' + key)
            print('Store the credential securely now; it cannot be retrieved later.')
        else:
            print('Source status updated.')
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
