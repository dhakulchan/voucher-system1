import re
from config import Config

def clean_simple_html(text: str) -> str:
    """Shared simple HTML sanitizer for PDF generation.
    - Normalizes newlines to <br/>
    - Removes dangerous tags & event handlers
    - Whitelists tags (intersection with safe superset or Config override)
    - Optionally strips entire <span>...</span> blocks if span not allowed
    - Removes NUL characters
    """
    if not text:
        return ''
    # Normalize newlines
    text = text.replace('\r\n','\n').replace('\r','\n')
    text = re.sub(r'\n+', '\n', text)
    # Remove script / style / iframe / object like blocks with content
    text = re.sub(r'<\s*(script|style|iframe|object|embed|link|meta)[^>]*>.*?<\s*/\s*\1>', '', text, flags=re.I|re.S)
    # Event handlers & protocols
    text = re.sub(r'on[a-zA-Z]+\s*=\s*"[^"]*"', '', text)
    text = re.sub(r"on[a-zA-Z]+\s*=\s*'[^']*'", '', text)
    text = re.sub(r'(?i)javascript:', '', text)
    text = re.sub(r'(?i)data:', '', text)
    # Allowed tags
    safe_superset = {'b','strong','i','em','u','br','p','ul','ol','li'}
    cfg_allowed = set(getattr(Config, 'PDF_ALLOWED_TAGS', list(safe_superset)))
    allowed = cfg_allowed & safe_superset or safe_superset
    # Remove span blocks entirely if not allowed
    if 'span' not in allowed:
        text = re.sub(r'<span[^>]*>.*?</span>', '', text, flags=re.I|re.S)
    # Convert newlines
    text = text.replace('\n','<br/>')
    # Strip attributes / tags not allowed
    def repl_tag(m):
        slash, tag = m.group(1), m.group(2).lower()
        if tag in allowed:
            if tag == 'br':
                return '<br/>'
            return f"<{slash}{tag}>"
        return ''
    text = re.sub(r'<(/?)([A-Za-z0-9]+)(?:\s+[^>]*)?>', repl_tag, text)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    if '\x00' in text:
        text = text.replace('\x00','')
    return text
