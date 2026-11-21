"""Compatibility API facade. New endpoints belong to feature router modules."""
from .app import create_app
from .core.problem import APIProblem
from .modules.requests.schemas import Intake
from .modules.reviews.schemas import Approval, Rejection

__all__ = ['create_app', 'APIProblem', 'Intake', 'Approval', 'Rejection']
