from functools import wraps

import mongoengine
from flask import Flask, request, jsonify

from models import System, Team


def get_app(db):
    app = Flask(__name__)

    def with_team_id(f):
        @wraps(f)
        def wrap(*args, **kwargs):
            token = request.args.get('token')
            try:
                team = Team.objects.get(token=token)
            except mongoengine.DoesNotExist:
                return jsonify({'error': 'Invalid Team'}), 400
            else:
                kwargs['team_id'] = team['team_id']
                return f(*args, **kwargs)

        return wrap

    @app.route('/token/', methods=['POST'])
    def new_team_token():
        """POST new team token."""
        pass

    @app.route('/systems/', methods=['GET'])
    @with_team_id
    def get_systems(team_id):
        """GET all systems currently controlled by team"""
        system_ids = set(
            System.objects(controller=Team.mongo_id(team_id=team_id)).distinct('system_id')
        ) | set(Team.objects(team_id=team_id).distinct('ships.location'))
        return jsonify([System.objects.get(system_id=s).to_dict(team_id) for s in system_ids])

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
        return jsonify(System.objects.get(system_id=system_id).to_dict(team_id=team_id))

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
