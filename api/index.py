import os
import sys

# Add project root to system path
path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path not in sys.path:
    sys.path.append(path)

try:
    from django.core.wsgi import get_wsgi_application

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

    application = get_wsgi_application()

    app = application
except Exception:
    import traceback
    # Capture the full traceback string immediately because 'e' is deleted after except block
    error_details = traceback.format_exc()
    
    def error_app(environ, start_response):
        status = '500 Internal Server Error'
        response_headers = [('Content-type', 'text/plain; charset=utf-8')]
        start_response(status, response_headers)
        return [f"Startup Error:\n{error_details}".encode('utf-8')]
    app = error_app
