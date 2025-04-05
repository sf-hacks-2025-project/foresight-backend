import datetime

def calculate_relative_timestamp(timestamp: float) -> str:
    """Calculates a human-readable relative timestamp (e.g. '5 minutes ago').
    Args:
        timestamp: Unix timestamp (seconds since epoch)

    Returns:
        A string representing how long ago the timestamp was (e.g. '5 minutes ago')
    """
    now = datetime.datetime.now()
    dt = datetime.datetime.fromtimestamp(timestamp)
    diff = now - dt
    
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return 'just now' if seconds <= 10 else f'{seconds} seconds ago'
    
    minutes = seconds // 60
    if minutes < 60:
        return f'{minutes} minute ago' if minutes == 1 else f'{minutes} minutes ago'
        
    hours = minutes // 60
    if hours < 24:
        return f'{hours} hour ago' if hours == 1 else f'{hours} hours ago'
        
    days = hours // 24
    if days < 30:
        return f'{days} day ago' if days == 1 else f'{days} days ago'
        
    months = days // 30
    if months < 12:
        return f'{months} month ago' if months == 1 else f'{months} months ago'
        
    years = months // 12
    return f'{years} year ago' if years == 1 else f'{years} years ago'