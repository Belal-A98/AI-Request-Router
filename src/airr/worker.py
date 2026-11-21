"""Compatibility and CLI entrypoint; background logic belongs to feature modules."""
from .modules.classification.worker import process_classification_once
from .modules.delivery.worker import process_delivery_once

__all__ = ['process_classification_once', 'process_delivery_once']


def main() -> None:
    import argparse
    from .config import Settings
    from .db import make_engine, make_session_factory

    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=['classify', 'deliver'])
    args = parser.parse_args()
    settings = Settings.from_env()
    sf = make_session_factory(make_engine(settings.db_url))
    operation = process_classification_once if args.kind == 'classify' else process_delivery_once
    print('Processed' if operation(sf) else 'No eligible item')


if __name__ == '__main__':
    main()
