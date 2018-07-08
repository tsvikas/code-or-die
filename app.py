import random
from functools import wraps
from logging import getLogger, INFO

from flask import Flask, request, jsonify

from board import setup_board

logger = getLogger(__name__)
logger.setLevel(INFO)


def init_db(db):
    # init board (routes & routes)
    def get_column(collection, column='_id'):
        return [r[column] for r in collection.find({}, [column])]

    systems_graph = setup_board()

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
        tuning_params.insert_one(
            dict(beam_id=beam_id, coord=random.randint(1, 2 ** 32))
        )

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
        get_column(teams), random.sample(systems_ids, k=teams.count())
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


def get_app(db):
    def get_column(dicts, column='_id'):
        return [d[column] for d in dicts]

    def change_mongo_ids(dataset):
        for d in dataset:
            d.update({'id': d.pop('_id')})
        return dataset

    app = Flask(__name__)
    init_db(db)

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
        ships_system_ids = get_column(
            ships.find({'team_id': team_id}, ['system_id']), 'system_id'
        )
        route_system_ids = sum(
            get_column(
                routes.find({'system_ids': {'$in': team_system_ids}}), 'system_ids'
            ),
            [],
        )
        system_ids = sorted(set(team_system_ids + ships_system_ids + route_system_ids))
        visible_systems = systems.find({'_id': {'$in': system_ids}})
        return jsonify(change_mongo_ids(list(visible_systems)))

    @app.route('/systems/names/', methods=['GET'])
    @with_team_id
    def get_systems_names():
        """GET all convenience names for all systems."""
        pass

    @app.route('/systems/<int:system_id>/', methods=['GET'])
    @with_team_id
    def get_system(system_id: int, team_id: int):
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
          (TODO: include this or not? include transit history, too? how many ships transmitted and at what time?)
        """

    @app.route('/systems/<int:system_id>/name/', methods=['PUT'])
    @with_team_id
    def set_system_name(system: str):
        """PUT a convenience name on an systems.
        Team does not have to control an systems to give it a convenience name."""
        pass

    @app.route('/systems/<int:system_id>/tuning', methods=['POST'])
    @with_team_id
    def set_system_tuning(system_id: int):
        """PUT a new set of tuning parameters on an systems.
        Payload may indicate to use specific parameters or to generate random parameters."""
        pass

    @app.route('/systems/<int:system_id>/orders', methods=['GET'])
    @with_team_id
    def get_system_orders(system_id: int):
        """GET a controlled system's order queue."""
        pass

    @app.route('/systems/<int:system_id>/orders', methods=['PUT'])
    @with_team_id
    def append_system_orders(system_id: int):
        """PUT an order onto the end of a controlled systems's order queue.
        Returns failure if team does not control systems."""
        pass

    @app.route('/systems/<int:system_id>/orders', methods=['DELETE'])
    @with_team_id
    def clear_system_orders(system_id: int):
        """DELETE (clear) all orders from systems's order queue."""
        pass

    @app.route('/systems/<int:system_id>/orders/<int:order>', methods=['DELETE'])
    @with_team_id
    def delete_from_system_orders(system_id: int, order: int):
        """DELETE specified order from systems's order queue."""
        pass

    @app.route('/ships/', methods=['GET'])
    @with_team_id
    def get_ships():
        """GET all information for all units controlled by team."""
        pass

    @app.route('/ships/<int:ship_id>', methods=['GET'])
    @with_team_id
    def get_ship(ship_id: int):
        """
        GET all information for a given ship controlled by team.
        Information includes:
        * ship convenience name
        * ship location
        * queue of ship orders
        * ship status (live/destroyed)
        * all messages sent to this ship
        """

    @app.route('/ships/<int:ship_id>/orders', methods=['GET'])
    @with_team_id
    def get_ship_orders(ship_id: int):
        """GET ship's order queue."""
        pass

    @app.route('/ships/<int:ship_id>/orders', methods=['PUT'])
    @with_team_id
    def append_ship_order(ship_id: int):
        """PUT a new order into at the end of a ship's order queue."""
        pass

    @app.route('/ships/<int:ship_id>/orders', methods=['DELETE'])
    @with_team_id
    def clear_ship_orders(ship_id: int):
        """DELETE (clear) all orders from ship's order queue."""
        pass

    @app.route('/ships/<int:ship_id>/orders/<int:order>', methods=['DELETE'])
    @with_team_id
    def remove_ship_order(ship_id: int, order: int):
        """DELETE specified order from ship's order queue."""
        pass

    return app
