import logging
import sys

import waitress

from core.app import get_app


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app = get_app()
    waitress.serve(app, host='0.0.0.0', port=5000, threads=150)
