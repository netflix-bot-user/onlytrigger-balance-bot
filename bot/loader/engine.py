"""
Loader Engine - Manages the loading queue and processes accounts.

Supports parallel loading where multiple accounts are loaded simultaneously.
When one account reaches the target, others are stopped and handled appropriately.
"""
import asyncio
import logging
from typing import Optional, Callable, Any, Dict, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field

from .api import OnlyFansAPI, fetch_rules
from bot.database import AccountsDB, InstantDeliveryDB, get_settings, AnalyticsDB
from bot.utils.notifications import AdminNotifier

logger = logging.getLogger(__name__)


@dataclass
class LoadTask:
    """Represents a single account loading task in parallel loading."""
    account_id: str
    credentials: str
    task: asyncio.Task = None
    started: bool = False
    current_balance: float = 0.0
    initial_balance: float = 0.0
    cancelled: bool = False
    result: Dict[str, Any] = field(default_factory=dict)


class LoaderEngine:
    """
    Manages account loading operations.
    
    Handles:
    - Loading accounts from stock
    - Saving partial loads to instant delivery
    - Progress tracking and callbacks
    - Analytics logging
    """
    
    def __init__(self):
        self._api: Optional[OnlyFansAPI] = None
        self._settings: Dict[str, Any] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize the loader engine."""
        if self._initialized:
            return
        
        # Fetch dynamic rules
        await fetch_rules()
        
        # Load settings
        self._settings = await get_settings()
        
        # Initialize API client
        proxy = self._settings.get("proxy", "")
        self._api = OnlyFansAPI(proxy=proxy if proxy else None)
        
        self._initialized = True
    
    async def validate_proxy(self) -> Tuple[bool, str]:
        """
        Validate proxy before loading to avoid burning accounts.
        
        Returns:
            Tuple of (success, message)
        """
        await self.initialize()
        
        proxy = self._settings.get("proxy", "")
        if not proxy:
            # No proxy configured - allow but warn
            return True, "No proxy configured"
        
        async with OnlyFansAPI(proxy=proxy) as api:
            return await api.validate_proxy()
    
    async def reload_settings(self):
        """Reload settings from database."""
        self._settings = await get_settings()
        
        # Update proxy if changed
        proxy = self._settings.get("proxy", "")
        if self._api:
            self._api.proxy = proxy if proxy else None
    
    async def load_account(
        self,
        account_id: str,
        credentials: str,
        target_balance: float,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Load a single account to target balance.
        
        Args:
            account_id: Database ID of the account
            credentials: Account credentials string
            target_balance: Target balance to reach
            progress_callback: Async callback for progress updates
            
        Returns:
            Dict with load result
        """
        await self.initialize()
        
        start_time = datetime.now(timezone.utc)
        
        # Get loading settings
        amount_per_round = self._settings.get("load_per_round", 50)
        delay = self._settings.get("delay_per_round", 210)
        retry_same_card = self._settings.get("retry_same_card", True)
        retry_halve = self._settings.get("retry_halve_on_failure", False)
        
        async with self._api:
            result = await self._api.load_account(
                credentials=credentials,
                target=target_balance,
                amount_per_round=amount_per_round,
                delay=delay,
                retry_same_card=retry_same_card,
                retry_halve_on_failure=retry_halve,
                progress_callback=progress_callback
            )
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # Update account in database
        if result["success"]:
            await AccountsDB.mark_loaded(
                account_id=account_id,
                initial_balance=result["initial_balance"],
                final_balance=result["final_balance"],
                target_balance=target_balance,
                cards_used=result["cards_used"],
                cards_total=result["cards_total"],
                load_attempts=result["load_attempts"]
            )
        else:
            final_balance = result["final_balance"]
            
            # Check if partial load - save to instant delivery
            if final_balance > result["initial_balance"]:
                await InstantDeliveryDB.add(
                    credentials=credentials,
                    balance=final_balance,
                    original_target=target_balance,
                    source="partial_load"
                )
                
                await AccountsDB.mark_failed(
                    account_id=account_id,
                    error_message=f"Partial load: ${final_balance}/${target_balance}",
                    final_balance=final_balance
                )
                
                # Log partial load analytics
                await AnalyticsDB.log_load(
                    account_id=account_id,
                    success=False,
                    target_balance=target_balance,
                    final_balance=final_balance,
                    duration_seconds=duration,
                    partial=True
                )
            else:
                await AccountsDB.mark_failed(
                    account_id=account_id,
                    error_message=result.get("error", "Unknown error"),
                    final_balance=final_balance
                )
                
                # Log failed load analytics
                await AnalyticsDB.log_load(
                    account_id=account_id,
                    success=False,
                    target_balance=target_balance,
                    final_balance=final_balance,
                    duration_seconds=duration,
                    partial=False
                )
        
        if result["success"]:
            # Log successful load analytics
            await AnalyticsDB.log_load(
                account_id=account_id,
                success=True,
                target_balance=target_balance,
                final_balance=result["final_balance"],
                duration_seconds=duration,
                partial=False
            )
        
        result["duration_seconds"] = duration
        return result
    
    async def _load_account_with_cancel(
        self,
        load_task: LoadTask,
        target_balance: float,
        cancel_event: asyncio.Event,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Load a single account with cancellation support for parallel loading.
        
        Args:
            load_task: The LoadTask object tracking this load
            target_balance: Target balance to reach
            cancel_event: Event that signals cancellation
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict with load result
        """
        start_time = datetime.now(timezone.utc)
        load_task.started = True
        
        # Get loading settings
        amount_per_round = self._settings.get("load_per_round", 50)
        delay = self._settings.get("delay_per_round", 210)
        retry_same_card = self._settings.get("retry_same_card", True)
        retry_halve = self._settings.get("retry_halve_on_failure", False)
        
        # Create a wrapper callback that checks for cancellation
        async def cancel_aware_callback(status, balance, target, card_info=None):
            load_task.current_balance = balance
            if cancel_event.is_set():
                raise asyncio.CancelledError("Another account reached target")
            if progress_callback:
                await progress_callback(status, balance, target, card_info)
        
        try:
            proxy = self._settings.get("proxy") or None
            logger.info(f"[LoadTask {load_task.account_id[:8]}] Starting load, target=${target_balance}, proxy={bool(proxy)}")
            
            async with OnlyFansAPI(proxy=proxy) as api:
                result = await api.load_account(
                    credentials=load_task.credentials,
                    target=target_balance,
                    amount_per_round=amount_per_round,
                    delay=delay,
                    retry_same_card=retry_same_card,
                    retry_halve_on_failure=retry_halve,
                    progress_callback=cancel_aware_callback,
                    cancel_event=cancel_event
                )
            
            load_task.initial_balance = result.get("initial_balance", 0)
            load_task.current_balance = result.get("final_balance", 0)
            load_task.result = result
            
            logger.info(f"[LoadTask {load_task.account_id[:8]}] Result: success={result.get('success')}, "
                       f"balance=${result.get('final_balance', 0)}, error={result.get('error')}")
            
        except asyncio.CancelledError:
            load_task.cancelled = True
            load_task.result = {
                "success": False,
                "cancelled": True,
                "initial_balance": load_task.initial_balance,
                "final_balance": load_task.current_balance,
                "error": "Cancelled - another account reached target"
            }
            result = load_task.result
        except Exception as e:
            logger.error(f"[LoadTask {load_task.account_id[:8]}] Unexpected error: {e}")
            load_task.result = {
                "success": False,
                "cancelled": False,
                "initial_balance": load_task.initial_balance,
                "final_balance": load_task.current_balance,
                "error": f"Unexpected error: {str(e)}"
            }
            result = load_task.result
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        load_task.result["duration_seconds"] = duration
        
        return load_task.result
    
    async def _parallel_load(
        self,
        target_balance: float,
        num_threads: int,
        progress_callback: Optional[Callable] = None
    ) -> Tuple[Optional[LoadTask], List[LoadTask]]:
        """
        Load multiple accounts in parallel, stopping when one succeeds.
        
        Args:
            target_balance: Target balance to reach
            num_threads: Number of accounts to load simultaneously
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (winning_task, all_tasks) where winning_task is None if all failed
        """
        # Get multiple accounts from stock
        accounts = await AccountsDB.get_multiple_available(num_threads)
        
        if not accounts:
            return None, []
        
        # Create load tasks
        load_tasks: List[LoadTask] = []
        for i, account in enumerate(accounts, 1):
            task = LoadTask(
                account_id=str(account["_id"]),
                credentials=account["credentials"]
            )
            task.thread_num = i  # Track thread number for display
            load_tasks.append(task)
        
        # Create cancellation event
        cancel_event = asyncio.Event()
        winner: Optional[LoadTask] = None
        
        # Create aggregated progress callback that shows best thread
        import time
        last_aggregate_update = [0]
        
        async def aggregated_progress(task: LoadTask, status: str, balance: float, target: float, card_info: str = None):
            """Show progress from the lead account (highest balance)."""
            if not progress_callback:
                return
            
            current_time = time.time()
            
            # Find the lead account (highest balance)
            lead_task = max(load_tasks, key=lambda t: t.current_balance)
            active_count = sum(1 for t in load_tasks if t.started and not t.cancelled)
            
            # Decide if we should show this update
            should_show = False
            
            # Always show if it's the lead task and rate limit passed
            if task == lead_task and (current_time - last_aggregate_update[0]) >= 2:
                should_show = True
            
            # Force update if we haven't shown anything in 5 seconds
            elif (current_time - last_aggregate_update[0]) >= 5:
                should_show = True
                
            if not should_show:
                return
                
            last_aggregate_update[0] = current_time
            
            # Format status to show parallel info
            parallel_status = f"[{active_count}/{len(load_tasks)} threads] {status}"
            
            await progress_callback(parallel_status, balance, target, card_info)
        
        async def load_and_check(task: LoadTask):
            nonlocal winner
            
            # Create task-specific callback
            async def task_callback(status, balance, target, card_info=None):
                await aggregated_progress(task, status, balance, target, card_info)
            
            result = await self._load_account_with_cancel(
                load_task=task,
                target_balance=target_balance,
                cancel_event=cancel_event,
                progress_callback=task_callback
            )
            
            if result.get("success") and not cancel_event.is_set():
                # This task won - signal others to stop
                winner = task
                cancel_event.set()
            
            return result
        
        # Start all tasks
        async_tasks = []
        for load_task in load_tasks:
            async_task = asyncio.create_task(load_and_check(load_task))
            load_task.task = async_task
            async_tasks.append(async_task)
        
        # Wait for all to complete (or be cancelled)
        await asyncio.gather(*async_tasks, return_exceptions=True)
        
        return winner, load_tasks
    
    async def _handle_parallel_results(
        self,
        winner: Optional[LoadTask],
        all_tasks: List[LoadTask],
        target_balance: float,
        user_id: int,
        key: str
    ) -> Dict[str, Any]:
        """
        Handle the results of parallel loading.
        
        - Winner: Mark as loaded, return to user
        - Started but cancelled with balance: Send to instant delivery (paused_loading, resumable)
        - Started but cancelled with no balance: Return to stock
        - Not started: Return to stock
        """
        # Handle non-winning tasks
        for task in all_tasks:
            if task == winner:
                continue
            
            if task.started and task.current_balance > task.initial_balance:
                # Has partial balance - save to instant delivery as resumable
                await InstantDeliveryDB.add(
                    credentials=task.credentials,
                    balance=task.current_balance,
                    original_target=target_balance,
                    source="paused_loading",
                    reason=InstantDeliveryDB.REASON_PAUSED,
                    resumable=True,
                    stock_account_id=task.account_id
                )
                await AccountsDB.mark_failed(
                    account_id=task.account_id,
                    error_message=f"Paused at ${task.current_balance} - another thread finished",
                    final_balance=task.current_balance
                )
                await AnalyticsDB.log_load(
                    account_id=task.account_id,
                    success=False,
                    target_balance=target_balance,
                    final_balance=task.current_balance,
                    duration_seconds=task.result.get("duration_seconds", 0),
                    partial=True
                )
            elif task.started and task.cancelled:
                # Started but cancelled before gaining balance - return to stock
                # Account still has unused cards, don't waste it
                await AccountsDB.reset_to_available(task.account_id)
            elif task.started:
                # Started, not cancelled, but no balance - all cards exhausted, mark as failed
                cards_used = task.result.get("cards_used", 0)
                cards_total = task.result.get("cards_total", 0)
                if cards_total > 0 and cards_used >= cards_total:
                    # All cards tried - truly failed
                    await AccountsDB.mark_failed(
                        account_id=task.account_id,
                        error_message="All cards exhausted - no balance loaded",
                        final_balance=task.current_balance
                    )
                else:
                    # Not all cards tried - return to stock
                    await AccountsDB.reset_to_available(task.account_id)
            else:
                # Never started - return to stock
                await AccountsDB.reset_to_available(task.account_id)
        
        # Handle winner
        if winner:
            await AccountsDB.mark_loaded(
                account_id=winner.account_id,
                initial_balance=winner.initial_balance,
                final_balance=winner.current_balance,
                target_balance=target_balance,
                cards_used=winner.result.get("cards_used", 0),
                cards_total=winner.result.get("cards_total", 0),
                load_attempts=winner.result.get("load_attempts", 0)
            )
            await AnalyticsDB.log_load(
                account_id=winner.account_id,
                success=True,
                target_balance=target_balance,
                final_balance=winner.current_balance,
                duration_seconds=winner.result.get("duration_seconds", 0),
                partial=False
            )
            await AnalyticsDB.log_key_redeemed(key, user_id, instant=False)
            
            return {
                "success": True,
                "credentials": winner.credentials,
                "balance": winner.current_balance,
                "instant": False,
                "account_id": winner.account_id,
                "duration": winner.result.get("duration_seconds", 0),
                "threads_used": len(all_tasks)
            }
        else:
            # All failed - collect error details
            errors = []
            for t in all_tasks:
                if t.result:
                    err = t.result.get("error", "Unknown")
                    if err and err not in errors:
                        errors.append(err)
            
            # Check if any had partial loads
            partial_tasks = [t for t in all_tasks if t.current_balance > t.initial_balance]
            if partial_tasks:
                best_partial = max(partial_tasks, key=lambda t: t.current_balance)
                return {
                    "success": False,
                    "error": f"All loads failed. Best partial: ${best_partial.current_balance}",
                    "instant": False,
                    "partial_balance": best_partial.current_balance
                }
            else:
                # Build detailed error message
                error_summary = "; ".join(errors[:3]) if errors else "Unknown error"
                logger.error(f"All {len(all_tasks)} accounts failed: {errors}")
                return {
                    "success": False,
                    "error": f"All accounts failed to load ({error_summary})",
                    "instant": False,
                    "details": errors
                }
    
    async def process_redemption(
        self,
        target_balance: float,
        user_id: int,
        key: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Process a key redemption - find or load an account.
        
        Uses parallel loading: loads multiple accounts simultaneously,
        stops others when one reaches target.
        
        Args:
            target_balance: Target balance from the key
            user_id: Telegram user ID redeeming the key
            key: The key being redeemed
            progress_callback: Async callback for progress updates
            
        Returns:
            Dict with credentials, balance, instant (bool), error (if any)
        """
        await self.initialize()
        
        # Validate proxy before loading to avoid burning accounts
        proxy = self._settings.get("proxy", "")
        if proxy:
            proxy_ok, proxy_msg = await self.validate_proxy()
            if not proxy_ok:
                await AdminNotifier.proxy_error(proxy_msg)
                return {
                    "success": False,
                    "error": f"Proxy validation failed: {proxy_msg}",
                    "instant": False,
                    "proxy_error": True
                }
        
        # First, check instant delivery for exact/range match
        instant_account = await InstantDeliveryDB.find_for_target(target_balance)
        
        if instant_account:
            # Mark as used
            await InstantDeliveryDB.mark_used(
                account_id=str(instant_account["_id"]),
                user_id=user_id,
                key_used=key
            )
            
            # Log redemption
            await AnalyticsDB.log_key_redeemed(key, user_id, instant=True)
            
            return {
                "success": True,
                "credentials": instant_account["credentials"],
                "balance": instant_account["balance"],
                "instant": True,
                "account_id": str(instant_account["_id"])
            }
        
        # Check for resumable account that can be continued
        resumable = await InstantDeliveryDB.find_resumable_for_target(target_balance)
        if resumable:
            # Try to claim and continue loading
            claimed = await InstantDeliveryDB.claim_for_resume(str(resumable["_id"]))
            if claimed:
                # Continue loading this account
                result = await self._resume_loading(
                    instant_account=claimed,
                    target_balance=target_balance,
                    progress_callback=progress_callback
                )
                
                if result["success"]:
                    await AnalyticsDB.log_key_redeemed(key, user_id, instant=False)
                    return result
                # If resume failed, continue to try fresh accounts
        
        # Get thread count from settings
        num_threads = self._settings.get("threads", 1)
        
        # Maximum retry rounds to prevent infinite loops
        max_rounds = self._settings.get("max_retry_rounds", 100)
        
        all_errors = []
        best_partial = None
        round_num = 0
        
        # Keep retrying until success, no more stock, or max rounds reached
        while round_num < max_rounds:
            round_num += 1
            
            # Check if bot is paused (simulates no stock)
            settings = await get_settings()
            if settings.get("paused", False):
                if round_num == 1:
                    return {
                        "success": False,
                        "error": "No accounts available in stock",
                        "instant": False
                    }
                else:
                    # Treat as ran out of stock after some attempts
                    break
            
            # Check if we have enough stock
            stock_count = await AccountsDB.count(status="available")
            if stock_count == 0:
                if round_num == 1:
                    return {
                        "success": False,
                        "error": "No accounts available in stock",
                        "instant": False
                    }
                else:
                    # Ran out of stock after some attempts
                    break
            
            # Use min of threads setting and available stock
            actual_threads = min(num_threads, stock_count)
            
            logger.info(f"[Redemption] Round {round_num}, {actual_threads} threads, {stock_count} stock available")
            
            # Notify progress callback about retry
            if progress_callback and round_num > 1:
                await progress_callback(
                    status=f"Retrying with new accounts (round {round_num})...",
                    balance=best_partial or 0,
                    target=target_balance,
                    card_info=None
                )
            
            if actual_threads == 1:
                # Single thread mode
                account = await AccountsDB.get_available()
                if not account:
                    break
                
                logger.info(f"[SingleThread] Round {round_num}: Loading account {str(account['_id'])[:8]}, target=${target_balance}")
                
                result = await self.load_account(
                    account_id=str(account["_id"]),
                    credentials=account["credentials"],
                    target_balance=target_balance,
                    progress_callback=progress_callback
                )
                
                logger.info(f"[SingleThread] Result: success={result.get('success')}, "
                           f"balance=${result.get('final_balance', 0)}, error={result.get('error')}")
                
                if result["success"]:
                    await AnalyticsDB.log_key_redeemed(key, user_id, instant=False)
                    return {
                        "success": True,
                        "credentials": account["credentials"],
                        "balance": result["final_balance"],
                        "instant": False,
                        "account_id": str(account["_id"]),
                        "duration": result.get("duration_seconds", 0)
                    }
                else:
                    # Track partial loads
                    if result["final_balance"] > result["initial_balance"]:
                        if best_partial is None or result["final_balance"] > best_partial:
                            best_partial = result["final_balance"]
                    
                    # Track errors
                    err = result.get("error", "Unknown error")
                    if err not in all_errors:
                        all_errors.append(err)
                    
                    # Continue to next round
                    continue
            
            # Parallel loading mode
            winner, all_tasks = await self._parallel_load(
                target_balance=target_balance,
                num_threads=actual_threads,
                progress_callback=progress_callback
            )
            
            if winner:
                # Success! Handle and return
                return await self._handle_parallel_results(
                    winner=winner,
                    all_tasks=all_tasks,
                    target_balance=target_balance,
                    user_id=user_id,
                    key=key
                )
            else:
                # All failed this round - collect errors and partial loads
                for t in all_tasks:
                    if t.result:
                        err = t.result.get("error")
                        if err and err not in all_errors:
                            all_errors.append(err)
                        if t.current_balance > t.initial_balance:
                            if best_partial is None or t.current_balance > best_partial:
                                best_partial = t.current_balance
                
                # Handle partial saves for this round (already done in _handle_parallel_results indirectly)
                await self._handle_parallel_results(
                    winner=None,
                    all_tasks=all_tasks,
                    target_balance=target_balance,
                    user_id=user_id,
                    key=key
                )
                
                logger.info(f"[Redemption] Round {round_num}/{max_rounds} failed, will retry...")
                # Continue to next round
        
        # All rounds exhausted or max reached - return failure
        if round_num >= max_rounds:
            logger.warning(f"[Redemption] Max retry rounds ({max_rounds}) reached, giving up")
        error_summary = "; ".join(all_errors[:3]) if all_errors else "All accounts failed"
        logger.error(f"[Redemption] All {round_num} rounds failed. Errors: {all_errors}")
        
        if best_partial:
            return {
                "success": False,
                "error": f"All attempts failed. Best partial: ${best_partial}",
                "instant": False,
                "partial_balance": best_partial
            }
        else:
            return {
                "success": False,
                "error": f"All accounts failed ({error_summary})",
                "instant": False
            }
    
    async def _resume_loading(
        self,
        instant_account: Dict[str, Any],
        target_balance: float,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Resume loading on a paused instant delivery account.
        
        Args:
            instant_account: The instant delivery account document
            target_balance: New target balance to reach
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict with load result
        """
        account_id = str(instant_account["_id"])
        credentials = instant_account["credentials"]
        current_balance = instant_account["balance"]
        
        # Calculate remaining amount to load
        remaining = target_balance - current_balance
        
        if remaining <= 0:
            # Already at or above target - just return it
            return {
                "success": True,
                "credentials": credentials,
                "balance": current_balance,
                "instant": True,
                "account_id": account_id,
                "resumed": True
            }
        
        start_time = datetime.now(timezone.utc)
        
        # Get loading settings
        amount_per_round = self._settings.get("load_per_round", 50)
        delay = self._settings.get("delay_per_round", 210)
        retry_same_card = self._settings.get("retry_same_card", True)
        retry_halve = self._settings.get("retry_halve_on_failure", False)
        
        try:
            async with OnlyFansAPI(proxy=self._settings.get("proxy") or None) as api:
                result = await api.load_account(
                    credentials=credentials,
                    target=target_balance,
                    amount_per_round=amount_per_round,
                    delay=delay,
                    retry_same_card=retry_same_card,
                    retry_halve_on_failure=retry_halve,
                    progress_callback=progress_callback
                )
        except Exception as e:
            # Update instant delivery with current state
            await InstantDeliveryDB.update_after_resume(
                account_id=account_id,
                new_balance=current_balance,
                success=False,
                new_target=target_balance
            )
            return {
                "success": False,
                "error": str(e),
                "instant": False
            }
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        final_balance = result.get("final_balance", current_balance)
        
        if result["success"]:
            # Successfully reached target
            await InstantDeliveryDB.update_after_resume(
                account_id=account_id,
                new_balance=final_balance,
                success=True,
                new_target=target_balance
            )
            return {
                "success": True,
                "credentials": credentials,
                "balance": final_balance,
                "instant": False,
                "account_id": account_id,
                "duration": duration,
                "resumed": True
            }
        else:
            # Failed to reach target - update balance and make available again
            await InstantDeliveryDB.update_after_resume(
                account_id=account_id,
                new_balance=final_balance,
                success=False,
                new_target=target_balance
            )
            return {
                "success": False,
                "error": result.get("error", "Failed to complete loading"),
                "instant": False,
                "partial_balance": final_balance if final_balance > current_balance else None
            }


# Global engine instance
_engine: Optional[LoaderEngine] = None


def get_loader_engine() -> LoaderEngine:
    """Get the global loader engine instance."""
    global _engine
    if _engine is None:
        _engine = LoaderEngine()
    return _engine
