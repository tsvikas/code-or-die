import datetime
import secrets

import mongoengine
from mongoengine import document, fields

mongoengine.connect("code-or-die")

# TODO: append -> push ?
# TODO: system_id -> reference ?


class DocumentFormatter(document.BaseDocument):
    """An helper abstract class to str() mongoengine documents"""

    def __repr__(self):
        return str(self)

    def __str__(self):
        # noinspection PyUnresolvedReferences
        return "{}({})".format(
            self._class_name,
            ", ".join(
                [
                    "{}={}".format(
                        f,
                        field.formatter(self[f])
                        if hasattr(field, "formatter")
                        else repr(self[f]),
                    )
                    for (f, field) in self._fields.items()
                    if f != "id"
                ]
            ),
        )


class BaseDocument(document.Document, DocumentFormatter):
    """An helper abstract class with common methods"""

    meta = {"abstract": True}
    _last_id = 0

    @classmethod
    def _new_id(cls):
        """return a sequencer for each subclass."""
        # TODO: use fields.SequenceField instead ?
        cls._last_id += 1
        return cls._last_id

    def to_dict(self):
        """convert the mongo document to a dict"""
        # noinspection PyUnresolvedReferences
        return {f: self[f] for f in self._fields if f != "id"}

    @property
    def time_created(self):
        """time of the first save of this document"""
        return self.id.generation_time


class Ship(document.EmbeddedDocument, DocumentFormatter):
    """
    Embedded document (in Team) that represent a ship.
    Visible only to the owner.

    Static params:
    :ship_id: the public id

    Dynamic params:
    :history: List of dict(action=., time=., ...)
              Represent the changes that affected this instance
    :alive: True if alive
    :location: current system_id
    """

    _class_name = NotImplemented
    _fields = NotImplemented

    # static data
    ship_id = fields.IntField(required=True, min_value=0)

    # dynamic data
    history = fields.ListField(
        fields.DictField(),
        required=True,
        formatter=lambda l: "<{}: {!r}>".format(len(l), l[-1]["action"]),
    )
    alive = fields.BooleanField(required=True, default=True)
    location = fields.IntField(required=True, help="system_id")
    # TODO: queue of ship orders + history

    # methods
    @classmethod
    def create_at_location(cls, **ship_fields):
        """
        create a new ship at specific system_id.
        does not save!

        :param ship_fields: fields to pass to the Ship constructor
        :return: the created Ship
        """
        location = ship_fields.pop("location")
        return cls(
            location=location,
            history=[
                dict(action="created", time=datetime.datetime.now(), system_id=location)
            ],
            **ship_fields
        )

    def died(self, reason):
        """
        set ship.alive to False and logs the reason
        does not save!

        :param reason: string to log
        :return: self
        """
        self.history.append(
            dict(action="died", time=datetime.datetime.now(), reason=reason)
        )
        self.alive = False
        return self

    def start_move(self, target):
        raise NotImplementedError

    def end_move(self, target):
        raise NotImplementedError


class Team(BaseDocument):
    """
    A player in the game. Have ships and control systems.

    Static params:
    :team_id: the public id of the instance. Public.
    :name: the name of the team. Fluff, Public.
    :token: secret token used to issue commands.
    :homeworld: system_id of starting location.
                Team loses the game if control of this system is lost.

    Dynamic params:
    :history: List of dict(action=., time=., ...)
              Represent the changes that affected this instance
    :eliminated: had the player lost? , Public.

    Dynamic params not in history:
    :ships: list of ships. saves separate history.
    """

    meta = {
        "indexes": [
            "team_id",
            ("team_id", "token"),
            ("team_id", "homeworld"),
            ("eliminated", "team_id"),
            "ships",
            "ships.ship_id",
            ("ships.location", "ships.alive", "ships.ship_id"),
        ]
    }

    # static data
    team_id = fields.IntField(
        min_value=0, default=lambda: Team._new_id(), required=True, unique=True
    )
    name = fields.StringField(required=True, unique=True, min_length=3)

    # secret data
    token = fields.StringField(
        required=True, unique=True, min_length=4, default=lambda: secrets.token_hex(4)
    )
    homeworld = fields.IntField(
        help="system_id", unique=True, required=False, sparse=True
    )

    # dynamic data
    history = fields.ListField(
        fields.DictField(),
        default=lambda: [dict(action="new", time=datetime.datetime.now())],
        formatter=lambda l: "<{}: {!r}>".format(len(l), l[-1]["action"]),
    )
    eliminated = fields.BooleanField(required=True, default=False)

    def lost(self, reason, save=True):
        """
        set team.eliminated to True and logs the reason

        :param reason: string to log
        :param save: saves db by default
        :return: self
        """

        # TODO: remove control from systems also
        for ship in self.ships:
            ship.died("lost")
        self.history.append(
            dict(action="lost", time=datetime.datetime.now(), reason=reason)
        )
        self.eliminated = True
        if save:
            self.save()
        return self

    # dynamic data (save history)
    ships = fields.EmbeddedDocumentListField(Ship, formatter=len)

    def append_ship(self, save=True, **ship_fields):
        """
        create a new ship at specific system_id.

        :param save: saves db by default
        :param ship_fields: fields to pass to the Ship constructor
        :return: the created Ship
        """
        ship = Ship.create_at_location(**ship_fields, ship_id=len(self.ships) + 1)
        self.ships.append(ship)
        if save:
            self.save()
        return ship


class Route(document.EmbeddedDocument):
    """Represent a route from the parent system to `destination` of `distance`"""

    destination = fields.IntField(required=True, help="system_id")
    distance = fields.FloatField(min_value=0.0, required=True, default=0.0)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "({}: {:.2})".format(self.destination, self.distance)


class System(BaseDocument):
    """
    A System on the board.
    Data is visible if you have ships in the system.

    Static params:
    system_id: the public id of the instance.
    name: the name of the system. Fluff.
    production: ships produced per time step.
    adjacent_systems: all possible routes (system_id & distance) from this system.
                      visible if you control the system.

    Dynamic params:
    history: List of dict(action=., time=., ...)
             Represent the changes that affected this instance
    controller: team_id of controlling team.

    Dynamic params not in history:
    ships_in_system: aggregated count of ships.
    """

    meta = {
        "indexes": [
            "system_id",
            ("controller", "system_id"),
            "adjacent_systems",
            "adjacent_systems.destination",
        ]
    }
    _controller_data = "adjacent_systems".split()
    _public_data = "system_id name production controller".split()
    _public_properties = "ships_in_system".split()

    # static public data
    system_id = fields.IntField(
        min_value=0, default=lambda: System._new_id(), required=True, unique=True
    )
    name = fields.StringField(required=True, unique=True)
    production = fields.FloatField(min_value=0.0, required=True, default=0.0)

    @property
    def ships_in_system(self):
        """
        Count ships of each team in this system
        only count alive ships
        only shows non-zero teams

        :return: dict(team_id: count)
        """
        ships_filter = dict(alive=True, location=self.system_id)
        return {
            team_id: Team.objects.get(team_id=team_id)
            .ships.filter(**ships_filter)
            .count()
            for team_id in Team.objects.filter(ships__match=ships_filter).distinct(
                "team_id"
            )
        }

    # static controller data
    adjacent_systems = fields.EmbeddedDocumentListField(Route, default=list)

    # static setup (without homeworlds - need to set separately
    @classmethod
    def setup_from_graph(cls, systems_graph):
        """
        sets a new Systems db from a networx graph
        :param systems_graph: graph to copy
        """
        cls.drop_collection()
        for system_id, system in systems_graph.nodes.items():
            system = cls(
                system_id=system_id,
                name=system["name"],
                production=system["production"],
            )
            for adj_system_id, adj_system in systems_graph[system_id].items():
                system.adjacent_systems.append(
                    Route(destination=adj_system_id, distance=adj_system["distance"])
                )
            system.save()
        cls._last_id = max(systems_graph)

    # dynamic public data
    history = fields.ListField(
        fields.DictField(),
        default=lambda: [dict(action="new", time=datetime.datetime.now())],
        formatter=lambda l: "<{}: {!r}>".format(len(l), l[-1]["action"]),
    )
    controller = fields.ReferenceField("Team")

    def change_control(self, team_id, save=True):
        """
        set system.controller to team_id

        :param team_id: use team_id=None to unset controller
        :param save: saves db by default
        :return: self
        """
        self.history.append(
            dict(action="control", time=datetime.datetime.now(), team_id=team_id)
        )
        self.controller = team_id
        if save:
            self.save()
        return self

    # helper function
    def to_dict(self, team_id=None, visibility=None):
        """
        convert the mongo document to a dict.
        adds the properties and shows only visible data

        :param team_id: controls visibility
               compares to system.controller and to team_ships
        :param visibility: overrides team_id visibility settings.
               'controller': view all data
               'guest': view some data
               False: view no data
        :return: dict(field: value)
        """
        if visibility is None:
            print(team_id)
            if team_id is None:
                visibility = False
            elif self.controller == team_id:
                visibility = "controller"
            elif (
                Team.objects.get(team_id=team_id)
                .ships.filter(alive=True, location=self.system_id)
                .count()
            ):
                visibility = "guest"
        if not visibility:
            return {}
        d = super().to_dict()
        for k in self._public_properties:
            d[k] = self.__getattribute__(k)
        keys = self._public_data + self._public_properties
        if visibility == "controller":
            keys.extend(self._controller_data)
        return {k: d[k] for k in keys}


if __name__ == "__main__":
    from board import setup_board

    def print_history(hist):
        for h in hist:
            h = dict(h)
            print("{}: [{}] {}".format(h.pop("time"), h.pop("action"), h))
        print()

    systems_g = setup_board()
    System.setup_from_graph(systems_g)

    Team.drop_collection()
    t1 = Team(name="red").save()
    t2 = Team(name="blue").save()
    t3 = Team(name="mars", token="AAAA").save()
    assert t2.token != t3.token

    ships = [t1.append_ship(location=2, save=False) for _ in range(3)]
    ships[-1].location = 1
    ships[-1].died("killed")
    t1.save()

    ships = [t2.append_ship(location=1, save=False) for _ in range(3)]
    ships[-1].died("killed")
    t2.save()

    ships = [t3.append_ship(location=1, save=False) for _ in range(3)]
    t3.save()

    print(System.objects[0])
    print(System.objects[1])
    assert System.objects[0].ships_in_system == {2: 2, 3: 3}
    print(System.objects[0].to_dict(visibility="guest"))
    print_history(System.objects[0].history)

    print(Team.objects[0])
    print(Team.objects[1])
    print_history(Team.objects[0].history)

    print(Team.objects[0].ships[0])
    print(Team.objects[0].ships[1])
    print_history(Team.objects[0].ships[0].history)
