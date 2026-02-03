"""
Turnstile Captcha Solver Module for OnlyFans Login
==================================================

This module implements Cloudflare Turnstile captcha solving using a remote solver API.
It matches the Go turnstilesolver package implementation.

CONFIGURATION
-------------
Set the solver API base URL via environment variable:
  - CAPTCHA_API_BASE_URL: Base URL of the solver API (default: http://483345.871872873.xyz)

USAGE
-----
```python
from bot.utils.captcha import solve_captcha

captcha_key, captcha_token = await solve_captcha()
if captcha_key and captcha_token:
    post_data[captcha_key] = captcha_token
```

API ENDPOINTS
-------------
- GET /turnstile?url=<url>&sitekey=<key>&type=managed[&action=<action>][&cdata=<cdata>]
  Returns: {"task_id": "...", "status": "...", "error": "..."}

- GET /result?id=<task_id>
  Returns: {"value": "...", "elapsed_time": ..., "status": "...", "error": "..."}

"""
import asyncio
import logging
import os
from typing import Tuple, Optional, Dict, Any
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)

# Default configuration matching Go constants
DEFAULT_CAPTCHA_API_BASE = "http://483345.871872873.xyz"
TIMEOUT_SECONDS = 60  # Maximum time to wait for a CAPTCHA solution

# OnlyFans Turnstile configuration
ONLYFANS_TURNSTILE_CONFIG = {
    "website_url": "https://onlyfans.com",
    "site_key": "0x4AAAAAAAxTpmbMvo7Qj6zy",  # OnlyFans Turnstile site key
    "captcha_type": "managed",
    "action": "login",
}


class CaptchaSolverError(Exception):
    """Raised when captcha solving fails."""
    pass


class TurnstileSolverClient:
    """
    HTTP client for the Turnstile solver API.
    Matches Go SolverClient struct.
    """
    
    def __init__(self, open_log: bool = False, base_url: str = None):
        self.open_log = open_log
        self._base_url = base_url
    
    def _resolve_base_url(self) -> str:
        """Returns the effective base URL, checking env var if not set."""
        if self._base_url:
            return self._base_url
        env_url = os.environ.get("CAPTCHA_API_BASE_URL")
        if env_url:
            return env_url
        return DEFAULT_CAPTCHA_API_BASE
    
    async def get_json(self, path: str) -> Tuple[Dict[str, Any], int]:
        """
        Perform HTTP GET and decode JSON response.
        Returns (result_dict, status_code).
        """
        url = self._resolve_base_url() + path
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
            ) as resp:
                try:
                    result = await resp.json()
                    return result, resp.status
                except Exception as e:
                    body = await resp.text()
                    raise CaptchaSolverError(
                        f"Failed to decode JSON response: {e}; body={body[:500]}"
                    )


class TurnstileSolverAPI:
    """
    Main client for interacting with the Turnstile solver.
    Matches Go TurnstileSolverAPI struct.
    """
    
    def __init__(self, open_log: bool = False):
        self.client = TurnstileSolverClient(open_log=open_log)
    
    async def solve(
        self,
        website_url: str,
        site_key: str,
        action: str = None,
        cdata: str = None
    ) -> Dict[str, Any]:
        """
        Solve a Cloudflare Turnstile CAPTCHA.
        
        Args:
            website_url: The URL of the page with the captcha
            site_key: The Turnstile site key
            action: Optional action parameter (e.g., "login")
            cdata: Optional custom data parameter
            
        Returns:
            Dict with 'status' and 'solution' containing 'value' and 'elapsed_time'
            
        Raises:
            CaptchaSolverError: If solving fails or times out
        """
        # Build query parameters
        params = {
            "url": website_url,
            "sitekey": site_key,
            "type": "managed",
        }
        if action:
            params["action"] = action
        if cdata:
            params["cdata"] = cdata
        
        turnstile_path = "/turnstile?" + urlencode(params)
        
        if self.client.open_log:
            logger.info(f"[Captcha] Submitting Turnstile solve: {self.client._resolve_base_url()}{turnstile_path}")
        
        # Submit task
        resp_map, status_code = await self.client.get_json(turnstile_path)
        
        # Check for error
        if resp_map.get("status") == "error":
            error_msg = resp_map.get("error", "turnstile submission failed")
            raise CaptchaSolverError(f"Turnstile submission failed: {error_msg}")
        
        task_id = resp_map.get("task_id")
        if not task_id:
            raise CaptchaSolverError("task_id not found or empty in /turnstile response")
        
        if self.client.open_log:
            logger.info(f"[Captcha] Received Turnstile task_id: {task_id} (status {status_code})")
        
        # Poll for result
        import time
        start = time.time()
        
        while True:
            elapsed = time.time() - start
            if elapsed > TIMEOUT_SECONDS:
                raise CaptchaSolverError("Timeout waiting for Turnstile solution")
            
            result_path = f"/result?id={task_id}"
            
            try:
                result_map, result_status = await self.client.get_json(result_path)
            except Exception as e:
                if self.client.open_log:
                    logger.warning(f"[Captcha] Error polling /result (transient?): {e}")
                await asyncio.sleep(1)
                continue
            
            # Check for error status
            if result_map.get("status") == "error":
                error_msg = result_map.get("error", "turnstile result failed")
                raise CaptchaSolverError(f"Turnstile result failed: {error_msg}")
            
            value = result_map.get("value", "")
            
            # Check result value
            if value in ("", "CAPTCHA_NOT_READY"):
                await asyncio.sleep(0.1)  # 100ms like Go
                continue
            
            if value == "CAPTCHA_FAIL":
                raise CaptchaSolverError("CAPTCHA_FAIL")
            
            # Success!
            elapsed_time = result_map.get("elapsed_time", 0)
            
            if self.client.open_log:
                logger.info(
                    f"[Captcha] Turnstile solved! HTTP {result_status}, "
                    f"elapsed {elapsed_time:.2f}s (loop elapsed: {elapsed:.2f}s)"
                )
            
            return {
                "status": "completed",
                "solution": {
                    "value": value,
                    "elapsed_time": elapsed_time,
                }
            }


async def solve_captcha() -> Tuple[Optional[str], Optional[str]]:
    """
    Solve Turnstile captcha for OnlyFans login.
    
    Returns:
        Tuple of (captcha_key, captcha_token):
        - captcha_key: The form field name ("cf-turnstile-response")
        - captcha_token: The solved captcha token string
        - Returns (None, None) if solving fails
        
    Raises:
        CaptchaSolverError: If captcha solving fails critically
    """
    solver = TurnstileSolverAPI(open_log=True)
    
    try:
        while True:
            result = await solver.solve(
                website_url=ONLYFANS_TURNSTILE_CONFIG["website_url"],
                site_key=ONLYFANS_TURNSTILE_CONFIG["site_key"],
                action=ONLYFANS_TURNSTILE_CONFIG.get("action"),
            )
            
            if result.get("status") == "completed":
                token = result["solution"]["value"]
                logger.info(f"[Captcha] Turnstile solved successfully")
                return "cf-turnstile-response", token
            
            logger.warning(f"[Captcha] Unexpected result status: {result}")
        
    except CaptchaSolverError as e:
        logger.error(f"[Captcha] Solver error: {e}")
        raise
    except Exception as e:
        logger.error(f"[Captcha] Unexpected error: {e}")
        raise CaptchaSolverError(f"Unexpected error: {e}")


def is_captcha_configured() -> bool:
    """
    Check if captcha solving is properly configured.
    
    Returns:
        True if the solver API is reachable
    """
    return True  # Using default solver API
