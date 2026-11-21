"""Application settings; secrets come from environment, never source control."""
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    source_key: str
    reviewer_key: str
    db_url: str
    classifier_mode: str = 'rules'
    enable_external_delivery: bool = False

    def __post_init__(self):
        if len(self.source_key) < 20 or len(self.reviewer_key) < 20:
            raise ValueError('Source and reviewer keys must be at least 20 characters')
        if self.source_key.startswith('REPLACE_') or self.reviewer_key.startswith('REPLACE_'):
            raise ValueError('Template keys are not usable secrets')
        if self.source_key == self.reviewer_key:
            raise ValueError('Source and reviewer keys must be distinct')
        if self.classifier_mode not in {'rules'}:
            raise ValueError('Only rules mode is implemented and verified')
        if self.enable_external_delivery:
            raise ValueError('External delivery is not yet implemented or approved')
        if not self.db_url.startswith(('sqlite:', 'sqlite+pysqlite:', 'postgresql+psycopg:')):
            raise ValueError('DATABASE_URL must be sqlite: or postgresql+psycopg:')

    @classmethod
    def from_env(cls):
        return cls(
            source_key=os.environ.get('AIRR_SOURCE_KEY', ''),
            reviewer_key=os.environ.get('AIRR_REVIEWER_KEY', ''),
            db_url=os.environ.get('DATABASE_URL', 'sqlite+pysqlite:///./airr.sqlite'),
            classifier_mode=os.environ.get('AIRR_CLASSIFIER_MODE', 'rules'),
            enable_external_delivery=os.environ.get('AIRR_ENABLE_EXTERNAL_DELIVERY', 'false').lower() == 'true',
        )
