# birthday/middleware.py
from django.http import HttpResponse

class HttpCatMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get the response from the view
        response = self.get_response(request)

        # Define "bad" status codes
        bad_status_codes = {400, 403, 404, 500, 501, 502, 503, 504}

        # Only modify HTML responses with bad status codes
        if (isinstance(response, HttpResponse) and
            'text/html' in response.get('Content-Type', '') and
            response.status_code in bad_status_codes):

            status_code = response.status_code
            image_url = f"https://http.cat/{status_code}"

            # Replace content with full-screen cat image
            new_content = f'''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>HTTP Error {status_code}</title>
                    <style>
                        body, html {{
                            margin: 0;
                            padding: 0;
                            height: 100%;
                            overflow: hidden;
                        }}
                        img {{
                            width: 100%;
                            height: 100%;
                        }}
                    </style>
                </head>
                <body>
                    <img src="{image_url}" alt="HTTP Cat for status {status_code}">
                </body>
                </html>
            '''
            response = HttpResponse(new_content, status=status_code)

        return response
