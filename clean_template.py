#!/usr/bin/env python3
"""
Clean up orphaned JavaScript from the booking template
"""

def clean_template():
    file_path = '/Applications/python/voucher-ro_v1.0/templates/booking/view_en.html'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the start and end of orphaned JavaScript
    # Look for the orphaned '}' after the modal div
    start_line = None
    end_line = None
    
    for i, line in enumerate(lines):
        # Find the orphaned JavaScript start
        if line.strip() == '}' and i > 2300 and lines[i-1].strip() == '':
            start_line = i
            print(f"Found orphaned JavaScript start at line {i+1}")
            break
    
    # Find the script end tag
    if start_line:
        for i in range(start_line, len(lines)):
            if '</script>' in lines[i]:
                end_line = i + 1
                print(f"Found script end at line {i+1}")
                break
    
    if start_line is not None and end_line is not None:
        # Remove the orphaned JavaScript
        print(f"Removing lines {start_line+1} to {end_line}")
        new_lines = lines[:start_line] + lines[end_line:]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        print(f"✅ Removed {end_line - start_line} lines of orphaned JavaScript")
        print(f"File reduced from {len(lines)} to {len(new_lines)} lines")
    else:
        print("❌ Could not find orphaned JavaScript boundaries")

if __name__ == '__main__':
    clean_template()