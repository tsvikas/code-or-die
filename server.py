import logging
import random
import sys

from cheroot.wsgi import Server as WSGIServer, PathInfoDispatcher
from pymongo import MongoClient

from app import get_app
from board import setup_board

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


def get_column(collection, column='_id'):
    return [r[column] for r in collection.find({}, [column])]


##### init board #####
db = MongoClient('localhost', 27017)['code-or-die']

systems_graph = setup_board(12)

db['systems'].drop()
systems = db['systems']
systems.insert_many(
    [
        dict(
            _id=system_id,
            name=systems_graph.nodes[system_id]['name'],
            is_destroyed=False,
            production=systems_graph.nodes[system_id]['production'],
        )
        for system_id in systems_graph.nodes
    ]
)

systems_ids = list(systems_graph.nodes)

db['routes'].drop()
routes = db['routes']
routes.insert_many(
    [
        dict(
            system_ids=[system1_id, system2_id],
            distance=systems_graph[system1_id][system2_id]['distance'],
        )
        for system1_id in systems_graph
        for system2_id in systems_graph[system1_id]
    ]
)

# add a beam for each system
beams = db['beams']
beams.insert_many(
    [dict(system_id=system_id, is_repair_mode=False) for system_id in systems_ids]
)

# set random tuning for each beam
db['tuning_params'].drop()
tuning_params = db['tuning_params']
beam_ids = get_column(beams)
for beam_id in beam_ids:
    tuning_params.insert_one(dict(beam_id=beam_id, coord=random.randint(1, 2 ** 32)))

# set-up teams.
# TODO: how to add teams on the fly?
# TODO: secure tokens
db['teams'].drop()
teams = db['teams']
teams.insert_one(dict(_id=0, name='red', token='AAAA'))
teams.insert_one(dict(_id=1, name='blue', token='BBBB'))

# populate teams into systems
# creates new columns in teams & systems
# TODO: Make sure players are distant!
HOME_PLANET_PRODUCTION = 3
for team_id, system_id in zip(
    get_column(teams), random.sample(systems_ids, k=teams.count_documents({}))
):
    teams.update_one({'_id': team_id}, {'$set': dict(home_system=system_id)})
    systems.update_one(
        {'_id': system_id},
        {'$set': dict(controller_id=team_id, production=HOME_PLANET_PRODUCTION)},
    )

# set-up starting ships
INITIAL_SHIPS = 5
db['ships'].drop()
ships = db['ships']
for team_number, team_id in enumerate(get_column(teams)):
    system_id = teams.find_one({'_id': team_id})['home_system']
    ships.insert_many(
        [
            dict(
                _id=team_number * INITIAL_SHIPS + i,
                team_id=team_id,
                src_system_id=system_id,
                system_id=system_id,
                destroyed=False,
            )
            for i in range(INITIAL_SHIPS)
        ]
    )

# db['systems_names'].drop()
# systems_names = db['systems_names']

# db['ships_names'].drop()
# ships_names = db['ships_names']

db['systems_orders'].drop()
systems_orders = db['systems_orders']

db['ships_orders'].drop()
ships_orders = db['ships_orders']


if __name__ == '__main__':
    app_server = PathInfoDispatcher({'/': get_app(db)})
    server = WSGIServer(('0.0.0.0', 5000), app_server, numthreads=150)
    try:
        logger.info('starting server!')
        server.start()
    except KeyboardInterrupt:
        server.stop()
