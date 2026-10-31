"""Errors that the API turns into a JSON body with a stable `code`."""

from __future__ import annotations


class AppError(Exception):
    def __init__(self, message: str, code: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


class LLMNotConfigured(AppError):
    def __init__(self) -> None:
        super().__init__(
            "GROQ_API_KEY is not set. Add it to the .env file in the repository root and restart the API.",
            "llm_not_configured",
            503,
        )


class LLMFailed(AppError):
    def __init__(self, node: str, detail: str) -> None:
        super().__init__(
            f"The model call for '{node}' failed after retries. {detail}",
            "llm_failed",
            502,
        )
