from logging import getLogger, INFO
from functools import wraps

from flask import Flask, request, jsonify

logger = getLogger(__name__)
logger.setLevel(INFO)


def change_mongo_ids(dataset):
    for d in dataset:
        d.update({'id': d.pop('_id')})
    return dataset


def get_column(dicts, cloumn='_id'):
    return [d[cloumn] for d in dicts]


def get_app(db):
    app = Flask(__name__)
    teams = db['teams']
    systems = db['systems']
    ships = db['ships']
    routes = db['routes']

    def with_team_id(f):
        @wraps(f)
        def wrap(*args, **kwargs):
            token = request.args.get('token')
            team = teams.find_one({'token': token}, ['_id'])
            if team:
                # how should i pass it to f ?
                kwargs['team_id'] = team['_id']
                return f(*args, **kwargs)
            else:
                # invalid token
                return jsonify({'error': 'Invalid Team'}), 400

        return wrap

    @app.route('/token/', methods=['POST'])
    def new_team_token():
        """POST new team token."""
        pass

    @app.route('/systems/', methods=['GET'])
    @with_team_id
    def get_systems(team_id):
        """GET all systems currently controlled by team"""
        team_system_ids = get_column(systems.find({'controller_id': team_id}, ['_id']))
        ships_system_ids = get_column(ships.find({'team_id': team_id}, ['system_id']), 'system_id')
        route_system_ids = sum(get_column(routes.find({'system_ids': {'$in': team_system_ids}}), 'system_ids'), [])
        system_ids = sorted(set(team_system_ids + ships_system_ids + route_system_ids))
        visible_systems = systems.find({'_id': {'$in': system_ids}})
        return jsonify(change_mongo_ids(list(visible_systems)))

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

    return app
