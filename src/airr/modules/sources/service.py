"""Manage high-entropy source credentials outside the HTTP request boundary."""
import hashlib
import re
import secrets
from sqlalchemy import select
from .models import Source

_SOURCE_ID = re.compile(r'[a-zA-Z][a-zA-Z0-9_-]{0,49}\Z')


def digest_api_key(api_key: str) -> str:
    """SHA-256 is suitable here only for randomly generated 256-bit credentials."""
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()


def _new_key() -> str:
    return 'airr_src_' + secrets.token_urlsafe(32)


def provision_source(sf, source_id: str) -> str:
    if not _SOURCE_ID.fullmatch(source_id) or source_id == 'default':
        raise ValueError('Invalid or reserved source identifier')
    key = _new_key()
    with sf.begin() as session:
        if session.get(Source, source_id) is not None:
            raise ValueError('Source already exists')
        session.add(Source(id=source_id, key_digest=digest_api_key(key), enabled=True))
    return key  # Show once to the local operator; never store or log the plaintext.


def rotate_source_key(sf, source_id: str) -> str:
    key = _new_key()
    with sf.begin() as session:
        source = session.get(Source, source_id)
        if source is None:
            raise ValueError('Source does not exist')
        source.key_digest = digest_api_key(key)
    return key


def set_source_enabled(sf, source_id: str, enabled: bool) -> None:
    with sf.begin() as session:
        source = session.get(Source, source_id)
        if source is None:
            raise ValueError('Source does not exist')
        source.enabled = enabled


def resolve_source_key(sf, api_key: str) -> Source | None:
    """Return a detached source record; caller enforces enabled state."""
    with sf() as session:
        source = session.scalar(select(Source).where(Source.key_digest == digest_api_key(api_key)))
        if source is None:
            return None
        return Source(id=source.id, key_digest=source.key_digest, enabled=source.enabled)
