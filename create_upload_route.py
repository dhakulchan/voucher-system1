#!/usr/bin/env python3
"""
Create temporary route to upload Thai test template
"""

def create_upload_route():
    upload_route = '''
@app.route('/admin/upload-thai-template', methods=['GET', 'POST'])
def upload_thai_template():
    """Admin route to upload Thai test template"""
    if request.method == 'GET':
        return """
        <html><head><title>Upload Thai Template</title></head>
        <body style="font-family: Arial; margin: 20px;">
        <h2>Upload Thai Test Template</h2>
        <form method="POST" enctype="multipart/form-data">
            <p>Upload quote_thai_test.html:</p>
            <input type="file" name="template_file" accept=".html" required>
            <br><br>
            <input type="submit" value="Upload Template">
        </form>
        </body></html>
        """
    
    if request.method == 'POST':
        try:
            uploaded_file = request.files['template_file']
            if uploaded_file.filename:
                import os
                template_dir = os.path.join('templates', 'pdf')
                os.makedirs(template_dir, exist_ok=True)
                
                file_path = os.path.join(template_dir, 'quote_thai_test.html')
                uploaded_file.save(file_path)
                
                return f"""
                <html><body style="font-family: Arial; margin: 20px;">
                <h2>✅ Template uploaded successfully!</h2>
                <p>File saved to: {file_path}</p>
                <p><a href="/booking/test-quote-pdf/3">Test PDF Generation</a></p>
                <p><b>Next:</b> Restart server with: sudo supervisorctl restart voucher_app</p>
                </body></html>
                """
        except Exception as e:
            return f"Upload error: {str(e)}", 500
'''
    
    print("Upload route code:")
    print("=" * 50)
    print(upload_route)
    print("=" * 50)
    print("\nAdd this to app.py, then access:")
    print("https://service.dhakulchan.net/admin/upload-thai-template")

if __name__ == '__main__':
    create_upload_route()