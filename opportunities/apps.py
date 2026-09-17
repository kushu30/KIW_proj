import logging

from django.apps import AppConfig

from core.exceptions import DatasetLoadError

logger = logging.getLogger(__name__)


class OpportunitiesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "opportunities"

    def ready(self) -> None:
        from opportunities import store

        try:
            store.initialize()
        except DatasetLoadError:
            logger.exception("failed to load dataset at startup")
            raise
