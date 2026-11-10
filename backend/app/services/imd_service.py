"""India Meteorological Department (IMD) Service.

Provides district-wise weather warning retrieval for Pune District / Maharashtra
with support for official API credentials, graceful degradation, and unconfigured fallback.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.config import settings
from app.schemas.environmental import (
    IMDWarningItem,
    IMDWarningsResponse,
)

logger = logging.getLogger("climaforge.imd_service")


class IMDService:
    """Service client for India Meteorological Department weather warnings."""

    def __init__(self) -> None:
        self.base_url = settings.imd_api_base_url.rstrip("/")
        self.api_key = settings.imd_api_key.strip() if settings.imd_api_key else ""
        self.enabled = settings.imd_enabled
        self.timeout = settings.imd_timeout_seconds
        self._cached_warnings: Optional[IMDWarningsResponse] = None
        self._cache_timestamp: float = 0.0
        self._cache_ttl = 900.0  # 15 minutes

    async def get_district_warnings(
        self,
        district: str = "Pune",
        state: str = "Maharashtra",
        force_refresh: bool = False,
    ) -> IMDWarningsResponse:
        """Fetch official district warnings from IMD, or return truthful unconfigured fallback."""
        now = datetime.now(timezone.utc).timestamp()
        if not force_refresh and self._cached_warnings and (now - self._cache_timestamp) < self._cache_ttl:
            return self._cached_warnings

        if not self.enabled or not self.api_key:
            logger.info("IMD API integration is not enabled or credentials are unconfigured.")
            response = self._build_unconfigured_response(district, state)
            self._cached_warnings = response
            self._cache_timestamp = now
            return response

        # Live IMD API execution
        headers = {
            "Accept": "application/json",
            "X-Api-Key": self.api_key,
            "User-Agent": "CLIMAFORGE-Climate-Risk-Engine/1.0",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(
                    f"{self.base_url}/district-warnings",
                    params={"district": district, "state": state},
                    headers=headers,
                )

            if res.status_code == 200:
                data = res.json()
                response = self._parse_imd_response(district, state, data)
                self._cached_warnings = response
                self._cache_timestamp = now
                return response

            if res.status_code in (401, 403):
                logger.warning("IMD API authentication failure (HTTP %s)", res.status_code)
                return self._build_error_response(
                    district, state, error="Authentication failed: invalid or expired IMD_API_KEY."
                )

            logger.warning("IMD API returned HTTP %s: %s", res.status_code, res.text)
            return self._build_error_response(
                district, state, error=f"IMD API returned HTTP {res.status_code}"
            )

        except httpx.TimeoutException:
            logger.warning("IMD API timed out after %s seconds", self.timeout)
            return self._build_error_response(
                district, state, error=f"IMD connection timed out after {self.timeout}s"
            )
        except Exception as exc:
            logger.error("IMD service exception: %s", exc)
            return self._build_error_response(district, state, error=str(exc))

    def _parse_imd_response(
        self,
        district: str,
        state: str,
        data: Dict[str, Any],
    ) -> IMDWarningsResponse:
        """Parse genuine IMD API response JSON into validated schema."""
        raw_warnings = data.get("warnings") or []
        items: List[IMDWarningItem] = []

        for idx, w in enumerate(raw_warnings):
            raw_level = str(w.get("color", "GREEN")).upper()
            if raw_level not in ("GREEN", "YELLOW", "ORANGE", "RED", "NO_WARNING"):
                raw_level = "GREEN"

            items.append(
                IMDWarningItem(
                    warning_id=f"IMD-{district.upper()}-{idx + 1}-{int(datetime.now(timezone.utc).timestamp())}",
                    district=district,
                    state=state,
                    warning_level=raw_level,  # type: ignore[arg-type]
                    warning_type=w.get("warning_type", "GENERAL_WEATHER"),
                    valid_from=datetime.fromisoformat(w["valid_from"]) if "valid_from" in w else None,
                    valid_to=datetime.fromisoformat(w["valid_to"]) if "valid_to" in w else None,
                    headline=w.get("headline", f"IMD Weather Advisory for {district}"),
                    description=w.get("description", "No detailed description provided by provider."),
                    issued_by="India Meteorological Department (IMD)",
                    source_url="https://mausam.imd.gov.in/",
                    freshness_status="LIVE",
                )
            )

        return IMDWarningsResponse(
            district=district,
            state=state,
            provider_status="CONFIGURED_LIVE",
            warnings=items,
            fetched_timestamp=datetime.now(timezone.utc),
            attribution="India Meteorological Department (IMD) / RMC Mumbai",
            disclaimer="Official IMD warnings are advisory. Follow local district disaster management authority instructions.",
        )

    def _build_unconfigured_response(self, district: str, state: str) -> IMDWarningsResponse:
        """Return clear, non-hallucinatory status when IMD credentials are not configured."""
        sample_warning = IMDWarningItem(
            warning_id=f"IMD-UNCONFIGURED-{district.upper()}",
            district=district,
            state=state,
            warning_level="NO_WARNING",
            warning_type="NONE",
            valid_from=datetime.now(timezone.utc),
            valid_to=None,
            headline=f"IMD Live Warnings Unconfigured for {district}",
            description=(
                f"Official IMD API integration is currently dormant (IMD_ENABLED=false). "
                f"Live weather, precipitation, and rain forecasts remain fully active via Open-Meteo. "
                f"To enable live IMD bulletins, set IMD_ENABLED=true and supply IMD_API_KEY in backend/.env."
            ),
            issued_by="India Meteorological Department (Reference)",
            source_url="https://api.imd.gov.in/public/api_reference.html",
            freshness_status="UNAVAILABLE",
        )

        return IMDWarningsResponse(
            district=district,
            state=state,
            provider_status="UNCONFIGURED_FALLBACK",
            warnings=[sample_warning],
            fetched_timestamp=datetime.now(timezone.utc),
            attribution="India Meteorological Department (IMD) Reference Portal",
            disclaimer="IMD provider is unconfigured in local environment. Weather observations continue via Open-Meteo.",
        )

    def _build_error_response(self, district: str, state: str, error: str) -> IMDWarningsResponse:
        """Return safe error payload when IMD API call fails."""
        error_item = IMDWarningItem(
            warning_id=f"IMD-ERROR-{district.upper()}",
            district=district,
            state=state,
            warning_level="NO_WARNING",
            warning_type="PROVIDER_ERROR",
            valid_from=datetime.now(timezone.utc),
            valid_to=None,
            headline=f"IMD Warnings Temporarily Unavailable ({error})",
            description=f"Could not reach IMD warning endpoints: {error}. Falling back to Open-Meteo precipitation models.",
            issued_by="India Meteorological Department",
            source_url="https://mausam.imd.gov.in/",
            freshness_status="UNAVAILABLE",
        )

        return IMDWarningsResponse(
            district=district,
            state=state,
            provider_status="PROVIDER_UNAVAILABLE",
            warnings=[error_item],
            fetched_timestamp=datetime.now(timezone.utc),
            attribution="India Meteorological Department (IMD)",
            disclaimer="Official IMD warnings temporarily unavailable. Follow municipal disaster management instructions.",
        )


# Global singleton instance
imd_service = IMDService()

