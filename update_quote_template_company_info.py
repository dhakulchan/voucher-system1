#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update Quote Template with Dynamic Company Information
Replaces hardcoded company text with Jinja2 variables
"""

import re

def update_template():
    template_path = 'templates/pdf/quote_template_final_v2_production.html'
    
    # Read template
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Company information patterns to replace
    # Note: Using the company data structure from weasyprint_quote_generator.py
    
    replacements = [
        # Company name (English)
        (
            r'DHAKUL CHAN TRAVEL SERVICE \(THAILAND\) CO\.,LTD\.',
            '{{ company.name_en }}'
        ),
        # Company name (Thai)
        (
            r'ธากุล จันทร์ ทราเวล เซอร์วิส \(ประเทศไทย\) จำกัด',
            '{{ company.name_th }}'
        ),
        # Address (English)
        (
            r'710, 716, 704, 706 Prachauthit Road, Samseenook, Huai Kwang, Bangkok 10310',
            '{{ company.address_en }}'
        ),
        # Address (Thai)
        (
            r'710, 716, 704, 706 ถนนประชาอุทิศ แขวงสามเสนนอก เขตห้วยขวาง กรุงเทพฯ 10310',
            '{{ company.address_th }}'
        ),
        # Tel
        (
            r'\+662 2744218',
            '{{ company.tel }}'
        ),
        # Fax
        (
            r'\+662 0266525',
            '{{ company.fax }}'
        ),
        # Website
        (
            r'www\.dhakulchan\.net',
            '{{ company.website }}'
        ),
        # Email
        (
            r'dhakulchan@gmail\.com',
            '{{ company.email }}'
        ),
        # License
        (
            r'T\.A\.T License 11/03659',
            '{{ company.license }}'
        )
    ]
    
    # Apply replacements
    modified = content
    changes_made = []
    
    for pattern, replacement in replacements:
        matches = re.findall(pattern, modified)
        if matches:
            modified = re.sub(pattern, replacement, modified)
            changes_made.append(f"Replaced '{pattern}' → '{replacement}' ({len(matches)} occurrence(s))")
    
    # Write updated template
    if changes_made:
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(modified)
        
        print("✅ Template updated successfully!")
        print("\nChanges made:")
        for change in changes_made:
            print(f"  • {change}")
        return True
    else:
        print("ℹ️  No hardcoded company information found (may already be using variables)")
        return False

if __name__ == '__main__':
    update_template()
