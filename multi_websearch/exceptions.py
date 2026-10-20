"""Provider-specific exceptions used for fallback decisions."""


class ProviderError(Exception):
    """Base error for any provider failure."""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        self.message = message
        super().__init__(f"[{provider}] {message}")


class AuthError(ProviderError):
    """Missing or invalid API key / authentication failure."""

    def __init__(self, provider: str, message: str = "authentication failed"):
        super().__init__(provider, message)


class RateLimitError(ProviderError):
    """Quota exhausted, rate limited, or 429-style response."""

    def __init__(self, provider: str, message: str = "rate limit / quota exhausted"):
        super().__init__(provider, message)


class TemporaryError(ProviderError):
    """Transient network / 5xx / timeout – worth trying next provider."""

    def __init__(self, provider: str, message: str = "temporary failure"):
        super().__init__(provider, message)
