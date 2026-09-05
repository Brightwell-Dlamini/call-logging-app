"""
Application entry point for local and Vercel.
"""
import os
import sys
import traceback

# Prefer production on Vercel when a real DB is configured
if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
    if os.environ.get('DATABASE_URL') and not os.environ.get('FLASK_ENV'):
        os.environ['FLASK_ENV'] = 'production'
    elif not os.environ.get('FLASK_ENV'):
        os.environ['FLASK_ENV'] = 'development'

try:
    from app import create_app, db
    from app.models import User, CallLog, CallActivity, Department

    app = create_app(os.environ.get('FLASK_ENV') or 'development')

    @app.shell_context_processor
    def make_shell_context():
        return {
            'db': db,
            'User': User,
            'CallLog': CallLog,
            'CallActivity': CallActivity,
            'Department': Department,
        }

except Exception:
    traceback.print_exc(file=sys.stderr)
    raise


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
