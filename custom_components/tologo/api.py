"""API Client for Tologo integration."""
import asyncio
import logging
import time
from typing import Any

import aiohttp

from .const import (
    API_BASE_URL,
    ENDPOINT_LOGIN,
    ENDPOINT_OPEN_DOOR,
    ENDPOINT_TOKEN_REFRESH,
    ENDPOINT_USER_DOORS,
)

_LOGGER = logging.getLogger(__name__)

# Minimum seconds between open_door calls for the same door
DOOR_COOLDOWN_SECONDS = 5


class TologoApiError(Exception):
    """Generic API Error."""


class TologoAuthError(TologoApiError):
    """Authentication Error."""


class TologoRateLimitError(TologoApiError):
    """Rate limit (429) Error."""


class TologoApiClient:
    """API Client for Tologo."""

    def __init__(
        self,
        hass,
        session: aiohttp.ClientSession,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_update_callback=None,
    ) -> None:
        """Initialize the API client."""
        self.hass = hass
        self._session = session
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._token_update_callback = token_update_callback
        self._refresh_lock = asyncio.Lock()
        self._last_open_door: dict[str | int, float] = {}

    async def login(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate with the API."""
        payload = {"email": email, "password": password}
        try:
            async with self._session.post(
                f"{API_BASE_URL}{ENDPOINT_LOGIN}",
                json=payload,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=10,
            ) as response:
                if response.status == 401:
                    raise TologoAuthError("Invalid credentials")
                response.raise_for_status()
                data = await response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                return data
        except TimeoutError as err:
            raise TologoApiError("Timeout error logging in") from err
        except aiohttp.ClientError as err:
            raise TologoApiError(f"Client error logging in: {err}") from err

    async def _refresh_tokens(self) -> None:
        """Refresh the access token.

        Uses _refresh_lock to ensure only one refresh happens at a time.
        If the token was already refreshed by another coroutine while we
        waited for the lock, we skip the refresh.
        """
        old_token = self.access_token

        async with self._refresh_lock:
            # If the token changed while we waited for the lock, another
            # coroutine already refreshed it — nothing to do.
            if self.access_token != old_token:
                _LOGGER.debug("Token already refreshed by another task, skipping")
                return

            if not self.access_token:
                raise TologoAuthError("No access token to refresh")

            payload = {"access_token": self.access_token}
            try:
                async with self._session.post(
                    f"{API_BASE_URL}{ENDPOINT_TOKEN_REFRESH}",
                    json=payload,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.refresh_token}",
                    },
                    timeout=10,
                ) as response:
                    if response.status in (401, 403):
                        raise TologoAuthError("Refresh token expired or invalid")
                    if response.status == 429:
                        raise TologoRateLimitError(
                            "Rate limited during token refresh, try again later"
                        )
                    response.raise_for_status()
                    data = await response.json()

                    new_access = data.get("access_token")
                    new_refresh = data.get("refresh_token", self.refresh_token)

                    if new_access:
                        self.access_token = new_access
                        self.refresh_token = new_refresh

                        if self._token_update_callback:
                            self._token_update_callback(
                                {
                                    "access_token": self.access_token,
                                    "refresh_token": self.refresh_token,
                                }
                            )
                    else:
                        raise TologoAuthError("Invalid refresh response format")

            except TimeoutError as err:
                raise TologoApiError("Timeout error refreshing token") from err
            except aiohttp.ClientError as err:
                raise TologoApiError(f"Client error refreshing token: {err}") from err

    async def _request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> Any:
        """Make a request to the API."""
        headers = kwargs.setdefault("headers", {})
        headers["Accept"] = "application/json"
        headers["Content-Type"] = "application/json"
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        url = f"{API_BASE_URL}{endpoint}"

        try:
            async with self._session.request(
                method, url, timeout=10, **kwargs
            ) as response:
                if response.status == 401:
                    # Token might be expired — refresh and retry once
                    _LOGGER.debug("Received 401, attempting token refresh")
                    await self._refresh_tokens()
                    return await self._retry_request(method, url, **kwargs)

                if response.status == 429:
                    raise TologoRateLimitError(
                        f"Rate limited by API (429) on {endpoint}"
                    )

                response.raise_for_status()
                return await response.json()

        except TimeoutError as err:
            raise TologoApiError(f"Timeout error requesting {endpoint}") from err
        except aiohttp.ClientError as err:
            raise TologoApiError(f"Client error requesting {endpoint}: {err}") from err

    async def _retry_request(self, method: str, url: str, **kwargs: Any) -> Any:
        """Retry a request after token refresh."""
        # Update the Authorization header with the new token
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        kwargs["headers"] = headers

        try:
            async with self._session.request(
                method, url, timeout=10, **kwargs
            ) as response:
                if response.status == 401:
                    raise TologoAuthError("Authentication failed even after token refresh")
                if response.status == 429:
                    raise TologoRateLimitError(
                        f"Rate limited by API (429) on retry: {url}"
                    )
                response.raise_for_status()
                return await response.json()
        except TimeoutError as err:
            raise TologoApiError(f"Timeout error retrying request: {err}") from err
        except aiohttp.ClientError as err:
            raise TologoApiError(f"Client error retrying request: {err}") from err

    async def get_doors(self) -> dict[str, Any]:
        """Get user doors."""
        return await self._request("GET", ENDPOINT_USER_DOORS)

    def check_door_cooldown(self, door_id: str | int) -> None:
        """Check if a door is still in cooldown.

        Raises TologoRateLimitError if the door was opened too recently.
        This is a synchronous check — no network call.
        """
        now = time.monotonic()
        last = self._last_open_door.get(door_id, 0.0)
        elapsed = now - last

        if elapsed < DOOR_COOLDOWN_SECONDS:
            remaining = DOOR_COOLDOWN_SECONDS - elapsed
            raise TologoRateLimitError(
                f"Door {door_id} was opened recently, please wait {remaining:.0f}s"
            )

    async def open_door(self, door_id: str | int) -> dict[str, Any]:
        """Open a door.

        Enforces a per-door cooldown to prevent rapid-fire requests
        that would trigger API rate limiting (429).
        """
        self.check_door_cooldown(door_id)

        self._last_open_door[door_id] = time.monotonic()
        try:
            return await self._request(
                "POST", ENDPOINT_OPEN_DOOR.format(door_id), json={"access_type": "app"}
            )
        except Exception:
            # If the request fails, clear the cooldown so the user can retry
            self._last_open_door.pop(door_id, None)
            raise
