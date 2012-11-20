# -*- coding: utf-8 -*-
import json
import os
from time import time
from datetime import datetime 
from pytz import timezone

from recorder import app,redis

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

    def all_desks(self):
        return map(lambda channel: Desk.load(self.card_id, channel), 
                   xrange(self.num_of_channels))

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
        return int(self._num_of_channels)

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

    @staticmethod
    def all(load = True):
        if load:
            return map(lambda rid: Recording.load(rid), Recording.all(False))
        else:
            return redis.zrangebyscore(Recording.TIMESTAMPS_KEY, 0, 2**32-1)

    @property
    def key(self):
        return self.KEY_STRING % (self.card_id, self._channel_id) 

    def __str__(self):
        return u"<Desk card_id: %s, channel: %s>" \
                    % (self.card_id, self._channel_id)

    def __repr__(self):
        return self.__str__()

class Recording(RedisBase, CardId, ChannelId):
    KEY_STRING = app.config['RECORDING_KEY_STRING']
    INDEX_KEY = app.config['RECORDING_INDEX_KEY']
    TIMESTAMPS_KEY = app.config['RECORDING_TIMESTAMPS_KEY']

    def __init__(self, **kwargs):
        self._is_new = True
        self._rid = None

        #path relative to app.config['RECORDINGS_DIR']
        self._path = kwargs.get('path')
        #timestamp (in seconds GMT)  
        self._timestamp = int(kwargs.get('timestamp'))
        #duratrion of recording
        self._duration = int(kwargs.get('duration'))
        self._card_id = int(kwargs.get('card_id'))
        self._channel_id = int(kwargs.get('channel_id'))
        #moved to archive = 1
        self._status = int(kwargs.get('status'))
        #all information from LCD
        self._display = kwargs.get('display')
        #json description of used desk
        self._desk = json.loads(kwargs.get('desk'))

    def __str__(self):
        return u"<Recording id:%s, timestamp:%s, duration:%s, path:%s>" \
                    % (self._rid, self._timestamp, self._duration, self._path)

    def __repr__(self):
        return self.__str__()

    @property
    def key(self):
        return self.KEY_STRING % (self._rid) 

    @property
    def index_key(self):
        return self.INDEX_KEY % (self._card_id, self._channel_id)

    @property
    def rid(self):
        return self._rid

    @property
    def channel_id(self):
        return self._channel_id

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

    def hr_timestamp(self):
        import pytz
        utc = pytz.timezone("UTC")
        app_tz = pytz.timezone(app.config['APP_TZ'])
        date = utc.localize(datetime.utcfromtimestamp(self.timestamp))
        date = date.astimezone(app_tz) 
        return date.strftime("%d-%m-%Y %H:%M")

    def path_url(self):
        return "/".join((app.config['RECORDINGS_URL'], self.path))

    def path_real(self):
        return os.path.join(app.config['RECORDINGS_DIR'], self.path)

    @staticmethod
    def load(rid):
        r_db = redis.hgetall(Recording.KEY_STRING % rid)
        if len(r_db): 
            rec = Recording(**r_db)
            rec._is_new = False 
            rec._rid = rid 
            return rec
        else:
            return None

    @staticmethod
    def last():
        return Recording.load(redis.get("global:nextRecordingId"));

    @staticmethod
    def find_by_timestamp(start, end, sort_len = False, page = 0, min_len = 0,
            channel = -1):

        if(page > 0):
            start_limit = app.config['RECORDS_PER_PAGE'] * (page - 1)
        else:
            start_limit = 0

        #Search key : recording:tmp:search:<ch_id>:<min_len>:<start>:<end>
        search_key = "recording:tmp:search:%s:%s:%s:%s" % (int(channel),
                                                       int(min_len), 
                                                       int(start), 
                                                       int(end))
        if not redis.exists(search_key):
            recordings = redis.zrangebyscore(Recording.TIMESTAMPS_KEY, start, end)
            #filter recordings by lenght and channel_id
            if(min_len > 0 or channel >= 0):
                recordings_filtered = []
                for r_id in recordings:
                    recording = Recording.load(r_id)
                    if(min_len > recording.duration):
                        continue;
                    if(channel >= 0 and channel != recording.channel_id):
                        continue;
                    recordings_filtered.append(r_id)
                recordings = recordings_filtered

            pipe = redis.pipeline()
            map(lambda r: pipe.sadd(search_key, r), recordings)
            pipe.execute()

        #Set expiration time
        redis.expire(search_key, 3600);

        if(sort_len):
            #Return all records
            recordings = redis.sort(search_key, 
                                    None, 
                                    None, 
                                    "recording:*->duration",
                                    None,
                                    True) 
        else:
            recordings = redis.smembers(search_key)

        lenght = len(recordings)

        if(page > 0):
            recordings = recordings[start_limit :
                                    start_limit + app.config['RECORDS_PER_PAGE']]

        return (map(lambda r_id: Recording.load(r_id), recordings), lenght)

    @staticmethod
    def count_all():
        return redis.zcard(Recording.TIMESTAMPS_KEY)

    @staticmethod
    def all(load = True):
        if load:
            return map(lambda rid: Recording.load(rid), Recording.all(False))
        else:
            return redis.zrangebyscore(Recording.TIMESTAMPS_KEY, 0, 2**32-1)
