"""
Business logic for games/consoles: queries and validation.
"""
import logging

from apps.games.models import GameConsole
from apps.common.exceptions import ConsoleNotFoundError

logger = logging.getLogger("apps.games")


class GameService:
    """Stateless game/console operations."""

    @staticmethod
    def list_active_consoles():
        return GameConsole.objects.filter(is_active=True)

    @staticmethod
    def get_console(console_id):
        try:
            return GameConsole.objects.get(pk=console_id, is_active=True)
        except GameConsole.DoesNotExist:
            raise ConsoleNotFoundError(f"Console #{console_id} not found.")
