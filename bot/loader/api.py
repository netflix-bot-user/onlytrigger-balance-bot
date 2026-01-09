"""
OnlyFans API wrapper adapted from reference script.
"""
import asyncio
import hashlib
import time
import logging
import aiohttp
from urllib.parse import urlparse
import json
from typing import Dict, List, Optional, Any
from bot.config import DEBUG

logger = logging.getLogger(__name__)

# Dynamic rules - fetched at startup
RULES = {
    "static_param": "",
    "checksum_indexes": [],
    "checksum_constant": 0,
    "prefix": "",
    "suffix": ""
}


async def fetch_rules():
    """Fetch dynamic rules from GitHub."""
    global RULES
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://raw.githubusercontent.com/rafa-9/dynamic-rules/main/rules.json",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    RULES = json.loads(text)
                    return True
                else:
                    logger.warning(f"[fetch_rules] Non-200 status: {resp.status}")
    except Exception as e:
        logger.error(f"[fetch_rules] Exception: {type(e).__name__}: {e}")
    return False


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
    })
    return headers


class OnlyFansAPI:
    """Async OnlyFans API client."""
    
    def __init__(self, proxy: str = None):
        self.proxy = proxy
        self._session: Optional[aiohttp.ClientSession] = None
    
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
        
        Args:
            credentials: Account credentials (sess:xbc:uid:ua)
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
        
        # Get user info
        me = await self.get_me(headers)
        if not me:
            result["error"] = "Failed to get user info (session expired)"
            logger.error(f"[API] Failed to get user info for uid={uid[:8]}... - session likely expired")
            return result
        
        balance = me.get('creditBalance', 0)
        result["initial_balance"] = balance
        result["final_balance"] = balance
        
        logger.info(f"[API] Account uid={uid[:8]}... initial balance=${balance}, target=${target}")
        
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
            logger.warning(f"[API] No valid cards for uid={uid[:8]}...")
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
