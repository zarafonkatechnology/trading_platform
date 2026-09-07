"""
Market Hours Detection for Agents
Teaches agents when markets are open/closed
"""

from datetime import datetime, time
import pytz

class MarketHours:
    """Detect if markets are open for trading"""
    
    # Forex market hours (Sunday 22:00 UTC to Friday 22:00 UTC)
    FOREX_OPEN_UTC = 22  # Sunday 10 PM UTC
    FOREX_CLOSE_UTC = 22  # Friday 10 PM UTC
    
    # Major market sessions (UTC)
    SESSIONS = {
        'SYDNEY': {'open': 22, 'close': 7, 'timezone': 'Australia/Sydney'},
        'TOKYO': {'open': 0, 'close': 9, 'timezone': 'Asia/Tokyo'},
        'LONDON': {'open': 8, 'close': 17, 'timezone': 'Europe/London'},
        'NEW_YORK': {'open': 13, 'close': 22, 'timezone': 'America/New_York'}
    }
    
    @staticmethod
    def is_forex_open():
        """Check if forex market is currently open"""
        now_utc = datetime.now(pytz.UTC)
        
        # Check if it's weekend (Saturday or Sunday)
        if now_utc.weekday() == 5:  # Saturday
            return False, "Market closed - Saturday (Weekend)"
        if now_utc.weekday() == 6:  # Sunday
            # Sunday is open only after 22:00 UTC
            if now_utc.hour >= 22:
                return True, "Market opening - Sunday session starting"
            return False, "Market closed - Sunday (before 22:00 UTC)"
        
        # Weekday (Monday to Friday)
        if now_utc.weekday() == 4:  # Friday
            # Friday closes at 22:00 UTC
            if now_utc.hour >= 22:
                return False, "Market closed - Friday after 22:00 UTC"
        
        return True, "Market open for trading"
    
    @staticmethod
    def get_current_session():
        """Get the currently active trading session"""
        now_utc = datetime.now(pytz.UTC)
        current_hour = now_utc.hour
        
        if 22 <= current_hour or current_hour < 7:
            return "SYDNEY", "Asia-Pacific session"
        elif 0 <= current_hour < 9:
            return "TOKYO", "Asian session"
        elif 8 <= current_hour < 17:
            return "LONDON", "European session"
        elif 13 <= current_hour < 22:
            return "NEW_YORK", "US session"
        else:
            return "CLOSED", "Inter-session period"
    
    @staticmethod
    def get_next_open_time():
        """Get the next market open time"""
        now_utc = datetime.now(pytz.UTC)
        
        # If it's Sunday before 22:00, open today at 22:00
        if now_utc.weekday() == 6 and now_utc.hour < 22:
            next_open = now_utc.replace(hour=22, minute=0, second=0, microsecond=0)
            return next_open, "Today at 22:00 UTC"
        
        # If it's Friday after 22:00 or Saturday, open Sunday at 22:00
        if (now_utc.weekday() == 4 and now_utc.hour >= 22) or now_utc.weekday() == 5:
            days_to_sunday = (6 - now_utc.weekday()) % 7
            next_open = now_utc.replace(hour=22, minute=0, second=0, microsecond=0) + timedelta(days=days_to_sunday)
            return next_open, f"Sunday at 22:00 UTC (in {days_to_sunday} days)"
        
        # Otherwise, market is open
        return None, "Market is currently open"
    
    @staticmethod
    def should_trade():
        """Main function for agents - should they trade right now?"""
        is_open, reason = MarketHours.is_forex_open()
        
        if not is_open:
            return {
                'can_trade': False,
                'reason': reason,
                'action': 'HOLD',
                'confidence': 100,
                'message': f"📅 {reason}. No trading until markets reopen."
            }
        
        session, session_name = MarketHours.get_current_session()
        
        return {
            'can_trade': True,
            'reason': f"Market open - {session_name}",
            'session': session,
            'action': None,
            'confidence': 100
        }
