"""Fish analysis modules (status classification)."""

from .fish_status_classifier import SimpleFishStatusClassifier
from .activity_analyzer import ActivityFishStatusClassifier

__all__ = [
    'SimpleFishStatusClassifier',
    'ActivityFishStatusClassifier',
]
