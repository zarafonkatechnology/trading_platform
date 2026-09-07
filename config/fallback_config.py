FALLBACK_CONFIG = {
    'enabled': True,                    # Enable/disable fallback
    'log_warnings': True,               # Log when fallback is used
    'max_fallback_cycles': 10,          # Max cycles before alert
    'alert_on_fallback': True,          # Send Telegram alert
    'fallback_ttl': 30,                 # Cache fallback data for 30 sec
}
