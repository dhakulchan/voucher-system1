#!/usr/bin/env python3
"""
Simplify template conditions to always show Thai data.
"""

import re

def simplify_template():
    """Simplify template conditions for better data display."""
    
    with open('templates/pdf/quote_template_final_v2.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simplify Service Detail section
    service_pattern = r'{% if booking\.description %}\s*\{\{ booking\.description\|replace.*?%}\s*{% elif service_detail %}\s*\{\{ service_detail\|replace.*?%}\s*{% elif booking\.description %}\s*\{\{ booking\.description\|replace.*?%}'
    service_replacement = '''{% if booking.description %}
            {{ booking.description|replace('\\n', '<br>')|safe }}
            {% elif service_detail %}
            {{ service_detail|replace('\\n', '<br>')|safe }}'''
    
    content = re.sub(service_pattern, service_replacement, content, flags=re.DOTALL)
    
    # Simplify Name List section - remove complex conditions
    name_pattern = r'{% if name_list %}\s*\{\{ name_list\|replace.*?%}\s*{% elif booking\.guest_list.*?{% endif %}\s*{% endif %}'
    name_replacement = '''{% if name_list %}
            {{ name_list|replace('\\n', '<br>')|safe }}
            {% elif booking.guest_list %}
            {{ booking.guest_list|replace('\\n', '<br>')|safe }}
            {% else %}
            -
            {% endif %}'''
    
    content = re.sub(name_pattern, name_replacement, content, flags=re.DOTALL)
    
    # Simplify Flight Info section
    flight_pattern = r'{% if flight_info %}\s*\{\{ flight_info\|replace.*?%}\s*{% elif booking\.flight_info %}\s*\{\{ booking\.flight_info\|replace.*?%}'
    flight_replacement = '''{% if flight_info %}
            {{ flight_info|replace('\\n', '<br>')|safe }}
            {% elif booking.flight_info %}
            {{ booking.flight_info|replace('\\n', '<br>')|safe }}'''
    
    content = re.sub(flight_pattern, flight_replacement, content, flags=re.DOTALL)
    
    with open('templates/pdf/quote_template_final_v2.html', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ Simplified template conditions for better Thai data display")

if __name__ == '__main__':
    simplify_template()