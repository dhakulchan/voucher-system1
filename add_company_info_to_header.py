#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add Company Information to Quote Template Header
Inserts company details after logo using Jinja2 variables
"""

def add_company_info_to_header():
    template_path = 'templates/pdf/quote_template_final_v2_production.html'
    
    # Read template
    with open(template_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Company information HTML to insert
    company_info_html = '''        <div class="company-info" style="font-size: 9px; margin-top: 5px; line-height: 1.3;">
            <div style="font-weight: bold;">{{ company.name_en }}</div>
            <div>{{ company.name_th }}</div>
            <div>{{ company.address_en }}</div>
            <div>Tel. {{ company.tel }} | Fax {{ company.fax }}</div>
            <div>{{ company.website }} | {{ company.email }}</div>
            <div><strong>{{ company.license }}</strong></div>
        </div>
'''
    
    # Find the closing div of header-content (should be after logo and quote-label)
    # Look for the line with just "    </div>" after "QUOTE</div>"
    modified_lines = []
    inserted = False
    
    for i, line in enumerate(lines):
        modified_lines.append(line)
        
        # Look for the QUOTE label div, then insert before the next closing div
        if not inserted and '<div class="quote-label">QUOTE</div>' in line:
            # Insert company info before the closing div (which should be next non-empty line)
            modified_lines.append(company_info_html)
            inserted = True
            print(f"✅ Company information inserted after line {i+1}")
    
    if not inserted:
        print("⚠️  Could not find appropriate location to insert company info")
        return False
    
    # Write updated template
    with open(template_path, 'w', encoding='utf-8') as f:
        f.writelines(modified_lines)
    
    print("✅ Template updated successfully!")
    print("\nAdded company information section to header using:")
    print("  • {{ company.name_en }}")
    print("  • {{ company.name_th }}")
    print("  • {{ company.address_en }}")
    print("  • {{ company.tel }}")
    print("  • {{ company.fax }}")
    print("  • {{ company.website }}")
    print("  • {{ company.email }}")
    print("  • {{ company.license }}")
    
    return True

if __name__ == '__main__':
    add_company_info_to_header()
