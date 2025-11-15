#!/usr/bin/env python3
# Minimal Flask app to test basic functionality
from flask import Flask

app = Flask(__name__)

@app.route('/test')
def test():
    return "Test OK"

@app.route('/hello/<name>')
def hello(name):
    return f"Hello {name}"

if __name__ == '__main__':
    print("Starting minimal test server...")
    app.run(host='0.0.0.0', port=5003, debug=True)