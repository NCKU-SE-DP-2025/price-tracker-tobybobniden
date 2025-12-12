import functools
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

def handle_crawler_exceptions(func: Callable) -> Callable:
    """Decorator to handle crawler exceptions centrally."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            # Depending on requirements, we might want to re-raise or return None/empty list
            # For now, re-raising is safer than silent failure, but logging is key.
            raise e
    return wrapper
