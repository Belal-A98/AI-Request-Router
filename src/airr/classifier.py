"""Backward-compatible classifier import; logic is in modules/classification."""
from .modules.classification.rules import Classification, classify

__all__ = ['Classification', 'classify']
