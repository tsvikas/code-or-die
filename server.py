import random

import dataset
from flask import Flask

from board import setup_board


def get_column(table, column='id'):
    col = table.db.query(f"SELECT {column} FROM {table.name}")
    return [c[column] for c in col]


##### init board #####
db = dataset.connect('sqlite:///:memory:')


systems_graph = setup_board()

db['systems'].drop()
systems = db['systems']
for id in systems_graph:
    systems.insert(
        dict(
            # id=id,
            name=systems_graph.nodes[id]['name'],
            is_destroyed=False,
            production=systems_graph.nodes[id]['production'],
        )
    )
systems_ids = get_column(systems, 'id')

db['routes'].drop()
routes = db['routes']
for origin in systems_graph:
    for destination in systems_graph[origin]:
        routes.insert(
            dict(
                origin=origin,
                destination=destination,
                distance=systems_graph[origin][destination]['distance'],
            )
        )

# add a beam for each system
beams = db['beams']
for system_id in systems_ids:
    beams.insert(dict(system_id=system_id, is_repair_mode=False))

# set random tuning for each beam
db['tuning_params'].drop()
tuning_params = db['tuning_params']
for beam_id in get_column(beams):
    tuning_params.insert(dict(beam_id=beam_id, coord=random.randint(1, 2 ** 32)))

# set-up teams.
# TODO: how to add teams on the fly?
# TODO: secure tokens
db['teams'].drop()
teams = db.create_table('teams')
teams.insert(dict(name='red', token='AAAA'))
teams.insert(dict(name='blue', token='BBBB'))

# populate teams into systems
# creates new columns in teams & systems
HOME_PLANET_PRODUCTION = 3
for team_id, system_id in zip(
    get_column(teams), random.sample(systems_ids, k=len(teams))
):
    teams.update(dict(id=team_id, home_system=system_id), ['id'])
    systems.update(
        dict(controller_id=team_id, id=system_id, production=HOME_PLANET_PRODUCTION),
        ['id'],
    )

# set-up starting ships
INITIAL_SHIPS = 5
db['ships'].drop()
ships = db['ships']
for team_id in get_column(teams):
    system_id = teams.find_one(id=team_id)['home_system']
    for _ in range(INITIAL_SHIPS):
        ships.insert(
            dict(
                team_id=team_id,
                src_system_id=system_id,
                system_id=system_id,
                destroyed=False,
            )
        )

# db['systems_names'].drop()
# systems_names = db['systems_names']

# db['ships_names'].drop()
# ships_names = db['ships_names']

db['systems_orders'].drop()
systems_orders = db['systems_orders']

db['ships_orders'].drop()
ships_orders = db['ships_orders']

app = Flask(__name__)


# TODO: API token per team


def get_team_id(token):
    return  # team_id if found, False if not


from functools import wraps


def with_team_id(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        token = 0  # get from url
        team = teams.find_one(token=token)
        team_id = team['id'] if team else False
        if team_id:
            # how should i pass it to f ?
            f(*args, **kwargs)
        else:
            # invalid token
            pass

    return wrap


@app.route('/token/', methods=['POST'])
def new_team_token():
    """POST new team token."""
    pass


@app.route('/systems/', methods=['GET'])
@with_team_id
def get_systems():
    """GET all systems currently controlled by team"""
    pass


@app.route('/systems/names/', methods=['GET'])
@with_team_id
def get_systems_names():
    """GET all convenience names for all systems."""
    pass


@app.route('/system/<string:system>/', methods=['GET'])
@with_team_id
def get_system(system: str):
    """
    GET systems with given ID or name.

    If team does not control solar system outpost or has no ships stationed at system,
    returns unavailable result.

    Otherwise, if team has ships stationed at outpost, returns result including:
    * convenience name of solar system
    * current controller of solar system
    * all teams and number of ships stationed at system
      (NOTE: can only see total troop strength, not individual unit information,
      because who cares? all units identical)
    * the system's production capacity

    Additionally, if team controls solar system outpost, return:
    * all historical destination tuning parameters for this system's beam motivator
    * all tuning parameters for beam transits originating from this outpost
      (TODO: include this or not? these are historical tuning parameters and may be not be up-to-date)
    * IDs and names of all immediately adjacent systems, including FTL transit time
    * IDs and names of all beam destinations
      (TODO: include this or not? include transit history, too? how many ships transitted and at what time?)
    """


@app.route('/system/<string:system>/name/', methods=['PUT'])
@with_team_id
def set_system_name(system: str):
    """PUT a convenience name on an systems.
    Team does not have to control an systems to give it a convenience name."""
    pass


@app.route('/system/<string:system>/tuning', methods=['POST'])
@with_team_id
def set_system_tuning(system: str):
    """PUT a new set of tuning paramters on an systems.
    Payload may indicate to use specific parameters or to generate random parameters."""
    pass


@app.route('/system/<string:system>/orders', methods=['GET'])
@with_team_id
def get_system_orders(system: str):
    """GET a controlled system's order queue."""
    pass


@app.route('/system/<string:system>/orders', methods=['PUT'])
@with_team_id
def append_system_orders(system: str):
    """PUT an order onto the end of a controlled systems's order queue.
    Returns failure if team does not control systems."""
    pass


@app.route('/system/<string:system>/orders', methods=['DELETE'])
@with_team_id
def clear_system_orders(system: str):
    """DELETE (clear) all orders from systems's order queue."""
    pass


@app.route('/system/<string:system>/orders/<int:order>', methods=['DELETE'])
@with_team_id
def delete_from_system_orders(system: str, order: int):
    """DELETE specified order from systems's order queue."""
    pass


@app.route('/ships/', methods=['GET'])
@with_team_id
def get_ships():
    """GET all information for all units controlled by team."""
    pass


@app.route('/ships/names/', methods=['GET'])
@with_team_id
def get_ships_names():
    """GET all convenience names for all ships."""
    pass


@app.route('/ship/<string:ship>', methods=['GET'])
@with_team_id
def get_ship(ship: str):
    """
    GET all information for a given ship controlled by team.
    Information includes:
    * ship convenience name
    * ship location
    * queue of ship orders
    * ship status (live/destroyed)
    * all messages sent to this ship
    """


@app.route('/ship/<string:ship>/name', methods=['PUT'])
@with_team_id
def set_ship_name(ship: str):
    """PUT a convenience name on a ship.
    Ship does not have to be active to be given a convenience name."""
    pass


@app.route('/ship/<string:ship>/orders', methods=['GET'])
@with_team_id
def get_ship_orders(ship: str):
    """GET ship's order queue."""
    pass


@app.route('/ship/<string:ship>/orders', methods=['PUT'])
@with_team_id
def append_ship_order(ship: str):
    """PUT a new order into at the end of a ship's order queue."""
    pass


@app.route('/ship/<string:ship>/orders', methods=['DELETE'])
@with_team_id
def clear_ship_orders(ship: str):
    """DELETE (clear) all orders from ship's order queue."""
    pass


@app.route('/ship/<string:ship>/orders/<int:order>', methods=['DELETE'])
@with_team_id
def remove_ship_order(ship: str, order: int):
    """DELETE specified order from ship's order queue."""
    pass
