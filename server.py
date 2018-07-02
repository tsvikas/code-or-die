import logging
import sys

from cheroot.wsgi import Server as WSGIServer, PathInfoDispatcher
from pymongo import MongoClient

from app import get_app

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    db = MongoClient('localhost', 27017)['code-or-die']
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app_server = PathInfoDispatcher({'/': get_app(db)})
    server = WSGIServer(('0.0.0.0', 5000), app_server, numthreads=150)
    try:
        logger.info('starting server!')
        server.start()
    except KeyboardInterrupt:
        server.stop()
