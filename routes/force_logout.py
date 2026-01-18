"""
Add force logout route for non-admin users to refresh their sessions
"""

from flask import Blueprint, render_template_string, redirect, url_for, flash
from flask_login import logout_user, current_user, login_required

force_logout_bp = Blueprint('force_logout', __name__)

FORCE_LOGOUT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Session Update Required</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .card {
            max-width: 600px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="card-body p-5 text-center">
                <div class="mb-4">
                    <i class="fas fa-sync fa-spin fa-4x text-primary"></i>
                </div>
                <h2 class="mb-3">System Update Detected</h2>
                <p class="lead text-muted">
                    Your user permissions have been updated. Please log out and log back in to apply the changes.
                </p>
                
                <div class="alert alert-info mt-4">
                    <strong>Why do I need to do this?</strong><br>
                    Your account role has been modified. A fresh login is required to load your new permissions.
                </div>

                <div class="d-grid gap-2 mt-4">
                    <a href="{{ url_for('force_logout.do_logout') }}" class="btn btn-primary btn-lg">
                        <i class="fas fa-sign-out-alt me-2"></i>Log Out Now
                    </a>
                    <a href="{{ url_for('dashboard.index') }}" class="btn btn-outline-secondary">
                        Continue to Dashboard
                    </a>
                </div>

                <div class="mt-4">
                    <small class="text-muted">
                        Current Role: <strong>{{ current_user.role }}</strong>
                    </small>
                </div>
            </div>
        </div>
    </div>
    
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</body>
</html>
"""

@force_logout_bp.route('/force-logout-notice')
@login_required
def notice():
    """Show logout notice to users with outdated sessions"""
    return render_template_string(FORCE_LOGOUT_TEMPLATE)

@force_logout_bp.route('/do-logout')
@login_required
def do_logout():
    """Force logout the user"""
    logout_user()
    flash('You have been logged out. Please log in again to apply your updated permissions.', 'info')
    return redirect(url_for('auth.login'))
