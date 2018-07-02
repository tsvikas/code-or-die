import logging
import sys

import waitress
from pymongo import MongoClient

from app import get_app


if __name__ == '__main__':
    db = MongoClient('localhost', 27017)['code-or-die']
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app = get_app(db)
    waitress.serve(app, host='0.0.0.0', port=5000, threads=150)
