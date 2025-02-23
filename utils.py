import logging
from functools import wraps
from typing import Any, Callable, TypeVar

import tenacity

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# TODO(PG): only retry on specific errors
LLMErrors = Exception


def retry_llm_errors(num_attempts: int = 3) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return tenacity.retry(
                reraise=True,
                stop=tenacity.stop_after_attempt(num_attempts),
                retry=tenacity.retry_if_exception_type(LLMErrors),
                after=tenacity.after_log(logger, logging.WARNING),
            )(func)(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator
