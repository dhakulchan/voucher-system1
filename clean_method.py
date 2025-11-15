def clean_html_tags(self, text):
    """Clean HTML tags from text and handle line breaks properly"""
    if not text:
        return ""
    
    import re
    
    # Convert text to string
    text = str(text)
    
    # CRITICAL: Handle line breaks FIRST before any other processing
    # Convert Windows line endings (\r\n) to <br/> tags first
    text = text.replace('\r\n', '<br/>')
    text = text.replace('\r', '<br/>')  
    text = text.replace('\n', '<br/>')
    
    # Convert HTML line breaks and paragraph tags
    text = re.sub(r'<br\s*/?>', '<br/>', text, flags=re.IGNORECASE)
    text = re.sub(r'<p\s*>', '<br/>', text, flags=re.IGNORECASE)
    text = re.sub(r'</p\s*>', '<br/>', text, flags=re.IGNORECASE)
    
    # Convert pipes to line breaks (for flight info)
    text = text.replace('|', '<br/>')
    
    # Remove all other HTML tags
    clean = re.compile('<(?!br/)[^>]*>')
    text = re.sub(clean, '', text)
    
    # Convert <br/> tags to actual newlines
    text = text.replace('<br/>', '\n')
    
    # Clean up multiple consecutive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)  # 3+ newlines → 2 newlines  
    text = re.sub(r'\n{2}', '\n', text)     # 2 newlines → 1 newline
    
    # Remove leading/trailing whitespace but preserve internal newlines
    lines = text.split('\n')
    clean_lines = [line.strip() for line in lines]
    
    # Remove empty lines at start and end only
    while clean_lines and not clean_lines[0]:
        clean_lines.pop(0)
    while clean_lines and not clean_lines[-1]:
        clean_lines.pop()
        
    return '\n'.join(clean_lines)
