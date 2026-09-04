"""
Application entry point.
"""
import os
from app import create_app, db
from app.models import User, CallLog, CallActivity, Department

app = create_app(os.environ.get('FLASK_ENV') or 'development')


@app.shell_context_processor
def make_shell_context():
    """Shell context for flask shell."""
    return {
        'db': db,
        'User': User,
        'CallLog': CallLog,
        'CallActivity': CallActivity,
        'Department': Department
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
