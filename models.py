import json
from time import time
from datetime import datetime 
from pytz import timezone

import settings
from recorder import redis

class RedisBase(object):
    KEY_STRING = ""

    def delete(self):
        redis.delete(self.key)
        self = None

    @property
    def is_new(self):
        return self._is_new

    @property
    def key(self):
        return self.KEY_STRING

class CardId(object):
    @property
    def card_id(self):
        return self._card_id

class ChannelId(object):
    @property
    def channel_id(self):
        return self._channel_id

class Card(RedisBase, CardId):
    KEY_STRING = "card:%s"
    INDEX_KEY = "cards"

    def __init__(self, **kwargs):
        super(Card, self).__init__()
        self._is_new = True
        self._card_id = kwargs.get("card_id")
        self._num_of_channels = kwargs.get("num_of_channels")

    def __str__(self):
        return "<Card id: %s num_of_channles: %s>" \
                    % (self.card_id, self.num_of_channels)

    def __repr__(self):
        return self.__str__()

    def save(self):
        if self._is_new and redis.exists(self.key):
            print "Save failed. Key '%s' exists." % self.key
            return False
        else:
            redis.hset(
                self.key, 
                "num_of_channels", self.num_of_channels
            )
            redis.sadd(self.INDEX_KEY, self.card_id)
            self._is_new = False
            return True

    def delete(self):
        super(Card, self).delete()
        redis.srem(self.INDEX_KEY, self.card_id)

    @staticmethod
    def load(card_id):
        n = redis.hgetall(Card.KEY_STRING % card_id)
        if n != None: 
            n["card_id"] = card_id
            c = Card(**n)
            c._is_new = False
            return c
        else:
            return None

    @staticmethod
    def all(load = True):
        if load:
            return map(lambda cid: Card.load(cid), Card.all(False))
        else:
            return redis.smembers(Card.INDEX_KEY)

    @property
    def num_of_channels(self):
        return self._num_of_channels 

    @property
    def key(self):
        return self.KEY_STRING % (self.card_id) 


class Desk(RedisBase, CardId, ChannelId):
    KEY_STRING = "desk:%s:%s"
    name = None
    description = None
    
    def __init__(self, **kwargs):
        self._is_new = True
        self._card_id = kwargs.get("card_id")
        self._channel_id = kwargs.get("channel_id")
        self.name = kwargs.get("name")
        self.description = kwargs.get("description")

    def save(self):
        if self._is_new and redis.exists(self.key):
            print "Save failed. Key '%s' exists." % self.key
            return False
        else:
            redis.set(
                self.key, 
                json.dumps({'name':self.name,'description':self.description})
            )
            self._is_new = False
            return True

    def switch_channel(self, new_channel):
        target = self.search(self._card_id, new_channel)
        if target != None:
            target._channel_id = self.channel_id
        else:
            redis.delete(self.key)
        self._channel_id = new_channel
        self.save()
        target.save()

    @staticmethod
    def load(card_id, channel_id):
        desk_json = redis.get(Desk.KEY_STRING % (card_id, channel_id))
        if desk_json == None:
            return None
        desk_json = json.loads(desk_json)
        desk_json["card_id"] = card_id
        desk_json["channel_id"] = channel_id
        desk = Desk(**desk_json)
        desk._is_new = False
        return desk

    @property
    def key(self):
        return self.KEY_STRING % (self.card_id, self._channel_id) 


class Recording(RedisBase, CardId, ChannelId):
    KEY_STRING = "recording:%s"
    INDEX_KEY = "recordings:%s:%s"
    TIMESTAMPS_KEY = "recordings:timestamps"

    def __init__(self, card_id, channel_id,
                 path, timestamp, duration,
                 display, desk):
        super(Card, self).__init__()
        self._is_new = True
        self._rid = None

        #path relative to settings.RECORDINGS_DIR 
        self._path = path
        #timestamp (in seconds GMT)  
        self._timestamp = timestamp 
        #duratrion of recording
        self._duration = duration 
        self._card_id = card_id
        self._channel_id = channel_id
        #moved to archive = 1
        self._status = 0
        #all information from LCD
        self._display = display
        #json description of used desk
        self._desk = desk

    def __str__(self):
        return "<Recording id:%s, timestamp:%s, duration:%s, path:%>" \
                    % (self._id, self._timestamp, self._duration, self._path)

    def __repr__(self):
        return self.__str__()

    @property
    def key(self):
        return self.KEY_STRING % (self._rid) 

    @property
    def index_key(self):
        return self.INDEX_KEY % (self._card_id, self._channel_id)

    @property
    def path(self):
        return self._path

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def duration(self):
        return self._duration

    @property
    def status(self):
        return self._status

    @property
    def display(self):
        return self._display

    @property
    def desk(self):
        return self._desk

    @staticmethod
    def load(rid):
        recording = redis.hget(Recording.KEY_STRING % rid)
        if n != None: 
            c = Recording(card_id, int(n) )
            return c
        else:
            return None

    #TODO dopisać funkcje obsługujące wyszukiwanie po timestampach
    @staticmethod
    def all(load = True):
        if load:
            return map(lambda rid: Recording.load(rid), Recording.all(False))
        else:
            return redis.zrange(Recording.INDEX_KEY, 0, 2**32-1)

