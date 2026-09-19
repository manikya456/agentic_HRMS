import time
import random
import logging
from typing import Callable, Any, Tuple

logger = logging.getLogger("agentic.retry")


def bounded_retry(
    func: Callable[[], Any],
    max_retries: int = 3,
    base_delay: float = 0.5,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[type, ...] = (Exception,),
) -> Tuple[Any, int, bool]:
    """
    Executes a callable within a bounded exponential backoff retry loop.
    
    Returns:
        Tuple of (result, retry_count, succeeded)
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            result = func()
            return result, attempt, True
        except exceptions as exc:
            last_error = exc
            if attempt == max_retries - 1:
                break
            delay = base_delay * (backoff_factor ** attempt)
            if jitter:
                delay += random.uniform(0.1, 0.4)
            logger.warning(
                f"[AgentRetry] Attempt {attempt + 1}/{max_retries} failed with {exc}. Retrying in {delay:.2f}s..."
            )
            time.sleep(delay)

    logger.error(f"[AgentRetry] All {max_retries} attempts failed: {last_error}")
    raise last_error
