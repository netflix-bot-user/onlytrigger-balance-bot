"""
Message formatting utilities with HTML parse mode.
Clean, minimalistic, modern Telegram UI.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class Formatters:
    """Utility class for formatting bot messages with HTML."""
    
    @staticmethod
    def escape_html(text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
    
    @staticmethod
    def key_info(key_doc: Dict[str, Any]) -> str:
        """Format a key document for display."""
        status_emoji = {
            "active": "🟢",
            "used": "🔴",
            "expired": "⚫"
        }
        
        status = key_doc.get("status", "unknown")
        emoji = status_emoji.get(status, "⚪")
        key_val = Formatters.escape_html(key_doc.get('key', 'N/A'))
        
        lines = [
            f"🔑 <b>Key:</b> {key_val}",
            f"💰 <b>Target Balance:</b> ${key_doc.get('target_balance', 0)}",
            f"{emoji} <b>Status:</b> {status.capitalize()}",
            f"📅 <b>Created:</b> {Formatters.format_datetime(key_doc.get('created_at'))}"
        ]
        
        if status == "used":
            used_by = Formatters.escape_html(key_doc.get('used_by', 'N/A'))
            lines.append(f"👤 <b>Used By:</b> {used_by}")
            lines.append(f"📅 <b>Used At:</b> {Formatters.format_datetime(key_doc.get('used_at'))}")
        
        return "\n".join(lines)
    
    @staticmethod
    def keys_list(keys: List[Dict[str, Any]], page: int = 0, per_page: int = 10) -> str:
        """Format a list of keys for display."""
        if not keys:
            return "📭 <i>No keys found.</i>"
        
        status_emoji = {"active": "🟢", "used": "🔴", "expired": "⚫"}
        
        lines = ["📋 <b>Keys List</b>\n"]
        
        for key_doc in keys:
            status = key_doc.get("status", "unknown")
            emoji = status_emoji.get(status, "⚪")
            balance = key_doc.get("target_balance", 0)
            key_str = Formatters.escape_html(key_doc.get("key", "N/A"))
            
            lines.append(f"{emoji} {key_str} — <b>${balance}</b>")
        
        return "\n".join(lines)
    
    @staticmethod
    def stock_stats(stats: Dict[str, Any]) -> str:
        """Format stock statistics."""
        available = stats.get('available', 0)
        processing = stats.get('processing', 0)
        loaded = stats.get('loaded', 0)
        failed = stats.get('failed', 0)
        total = stats.get('total', 0)
        
        return f"""📦 <b>Stock Overview</b>

🟢 Available: <b>{available}</b>
🔄 Processing: <b>{processing}</b>
✅ Loaded: <b>{loaded}</b>
❌ Failed: <b>{failed}</b>

📊 Total: <b>{total}</b>"""
    
    @staticmethod
    def key_stats(stats: Dict[str, Any]) -> str:
        """Format key statistics."""
        active = stats.get('active', 0)
        used = stats.get('used', 0)
        expired = stats.get('expired', 0)
        total = stats.get('total', 0)
        
        return f"""🔑 <b>Key Overview</b>

🟢 Active: <b>{active}</b>
🔴 Used: <b>{used}</b>
⚫ Expired: <b>{expired}</b>

📊 Total: <b>{total}</b>"""
    
    @staticmethod
    def instant_stats(stats: Dict[str, Any]) -> str:
        """Format instant delivery statistics."""
        available = stats.get('available', 0)
        used = stats.get('used', 0)
        total = stats.get('total', 0)
        
        lines = [
            "⚡ <b>Instant Delivery</b>\n",
            f"🟢 Available: <b>{available}</b>",
            f"🔴 Used: <b>{used}</b>",
            f"📊 Total: <b>{total}</b>",
            "",
            "💰 <b>By Balance:</b>"
        ]
        
        distribution = stats.get("balance_distribution", {})
        if distribution:
            for balance, count in sorted(distribution.items()):
                lines.append(f"   • ${balance}: <b>{count}</b>")
        else:
            lines.append("   <i>No accounts available</i>")
        
        return "\n".join(lines)
    
    @staticmethod
    def load_analytics(analytics: Dict[str, Any]) -> str:
        """Format loading analytics."""
        total_processed = analytics.get('total_processed', 0)
        loaded = analytics.get('loaded', 0)
        failed = analytics.get('failed', 0)
        success_rate = analytics.get('success_rate', 0)
        total_balance = analytics.get('total_balance_loaded', 0)
        
        return f"""📊 <b>Loading Analytics</b>

📈 Processed: <b>{total_processed}</b>
✅ Successful: <b>{loaded}</b>
❌ Failed: <b>{failed}</b>
📉 Success Rate: <b>{success_rate}%</b>

⏱ <b>Load Times</b>
• Avg: <b>{Formatters.format_duration(analytics.get('avg_duration_seconds', 0))}</b>
• Min: <b>{Formatters.format_duration(analytics.get('min_duration_seconds', 0))}</b>
• Max: <b>{Formatters.format_duration(analytics.get('max_duration_seconds', 0))}</b>

💰 Total Loaded: <b>${total_balance:,.2f}</b>"""
    
    @staticmethod
    def overall_analytics(stats: Dict[str, Any]) -> str:
        """Format overall analytics."""
        total_loads = stats.get('total_loads', 0)
        successful = stats.get('successful_loads', 0)
        failed = stats.get('failed_loads', 0)
        partial = stats.get('partial_loads', 0)
        success_rate = stats.get('success_rate', 0)
        avg_duration = Formatters.format_duration(stats.get('avg_load_duration', 0))
        total_loaded = stats.get('total_balance_loaded', 0)
        keys_gen = stats.get('keys_generated', 0)
        keys_red = stats.get('keys_redeemed', 0)
        
        return f"""📊 <b>Analytics Overview</b>

<b>Loading</b>
• Total: <b>{total_loads}</b>
• ✅ Success: <b>{successful}</b>
• ❌ Failed: <b>{failed}</b>
• ⚠️ Partial: <b>{partial}</b>
• 📈 Rate: <b>{success_rate}%</b>

⏱ Avg Duration: <b>{avg_duration}</b>
💰 Total Loaded: <b>${total_loaded:,.2f}</b>

<b>Keys</b>
• Generated: <b>{keys_gen}</b>
• Redeemed: <b>{keys_red}</b>"""
    
    @staticmethod
    def settings_display(settings: Dict[str, Any]) -> str:
        """Format settings for display."""
        bool_emoji = lambda v: "✅" if v else "❌"
        
        load_per_round = settings.get('load_per_round', 50)
        delay = settings.get('delay_per_round', 210)
        threads = settings.get('threads', 10)
        proxy = Formatters.escape_html(settings.get('proxy', 'None') or 'None')
        retry_same = bool_emoji(settings.get('retry_same_card', True))
        halve = bool_emoji(settings.get('retry_halve_on_failure', False))
        range_enabled = bool_emoji(settings.get('instant_delivery_range_enabled', False))
        range_val = settings.get('instant_delivery_range', 50)
        
        proxy_display = proxy[:20] + "..." if len(proxy) > 20 else proxy
        
        return f"""⚙️ <b>Settings</b>

<b>Loading</b>
• Load/Round: <b>${load_per_round}</b>
• Delay: <b>{delay}s</b>
• Threads: <b>{threads}</b>
• Proxy: <b>{proxy_display}</b>

<b>Retry</b>
• Same Card: {retry_same}
• Halve on Fail: {halve}

<b>Instant Delivery</b>
• Range: {range_enabled}
• Value: <b>${range_val}</b>"""
    
    @staticmethod
    def account_delivered(
        credentials: str,
        balance: float,
        target: float,
        instant: bool = False,
        duration: float = None
    ) -> str:
        """Format delivered account message."""
        # Extract email and password from credentials
        # Format: email:password | ... - Cookies: ...
        email = "N/A"
        password = "N/A"
        
        try:
            # Try to extract email:password from the beginning
            if "|" in credentials:
                # Format: email:pass | metadata...
                email_pass = credentials.split("|")[0].strip()
            elif "Cookies:" in credentials:
                # Format: email:pass ... Cookies: ...
                email_pass = credentials.split("Cookies:")[0].strip()
            else:
                email_pass = credentials
            
            # Split email:password
            if ":" in email_pass:
                parts = email_pass.split(":")
                email = parts[0].strip()
                password = parts[1].strip() if len(parts) > 1 else "N/A"
        except Exception:
            pass
        
        email_escaped = Formatters.escape_html(email)
        password_escaped = Formatters.escape_html(password)
        
        lines = [
            "✅ <b>Delivered Successfully</b>",
            "",
            f"📧 <b>Email:</b> {email_escaped}",
            f"🔑 <b>Password:</b> {password_escaped}",
            "",
            f"💵 <b>Final Balance:</b> ${balance}",
            "🌍 <b>Use IP:</b> Canada Toronto Only",
        ]
        
        if duration is not None:
            lines.append(f"⏳ <b>Time taken:</b> {Formatters.format_duration(duration)}")
        
        return "\n".join(lines)
    
    @staticmethod
    def loading_progress(
        status: str,
        balance: float,
        target: float,
        card_info: str = None,
        elapsed: float = None,
        thread_info: str = None
    ) -> str:
        """Format loading progress message."""
        progress = min(100, (balance / target) * 100) if target > 0 else 0
        
        lines = [
            "✅ <b>Key Redeemed!</b>",
            "",
            f"📝 <b>Target:</b> ${target}",
            f"💰 <b>Balance:</b> ${balance} ({progress:.0f}%)",
        ]
        
        if elapsed is not None:
            lines.append(f"⏱ <b>Elapsed:</b> {Formatters.format_duration(elapsed)}")
        
        if card_info:
            card_escaped = Formatters.escape_html(card_info)
            lines.append(f"💳 {card_escaped}")
        
        if status:
            status_escaped = Formatters.escape_html(status)
            lines.append(f"\n<i>{status_escaped}</i>")
        
        lines.append("\n⚠️ <i>Please wait...</i>")
        
        return "\n".join(lines)
    
    @staticmethod
    def redemption_started(target: float) -> str:
        """Format initial redemption message."""
        return f"""✅ <b>Key Redeemed!</b>

📝 <b>Target:</b> ${target}
💰 <b>Balance:</b> $0 (0%)
⏱ <b>Elapsed:</b> 0s

<i>Finding best account...</i>

⚠️ <i>Please wait...</i>"""
    
    @staticmethod
    def key_refunded(
        key: str,
        target_balance: float,
        reason: str = None,
        elapsed: float = None,
        partial_balance: float = None
    ) -> str:
        """Format a beautiful key refund message."""
        key_escaped = Formatters.escape_html(key)
        
        lines = [
            "🔄 <b>Key Refunded</b>",
            "",
            f"Your key has been refunded and is ready to use again.",
            "",
            f"🔑 <b>Key:</b> {key_escaped}",
            f"💰 <b>Target:</b> ${target_balance}",
        ]
        
        if elapsed is not None:
            lines.append(f"⏱ <b>Time:</b> {Formatters.format_duration(elapsed)}")
        
        if partial_balance:
            lines.append(f"📊 <b>Best attempt:</b> ${partial_balance}")
        
        if reason:
            reason_escaped = Formatters.escape_html(reason)
            lines.append(f"\n⚠️ <i>{reason_escaped}</i>")
        
        lines.append("")
        lines.append(f"Use /redeem to try again.")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_datetime(dt: Optional[datetime]) -> str:
        """Format datetime for display."""
        if dt is None:
            return "N/A"
        
        if isinstance(dt, str):
            return dt
        
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in seconds to human readable."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins}m"
