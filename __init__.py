import time
from os import path
from flask import Flask, redirect, url_for
from flask.ext.redis import Redis

#from testapp import settings
from recorder import settings

# Initialize simple Flask application
app = Flask(__name__)
app.config.from_object(settings)

# Setup Redis conection
redis = Redis(app)

def app_is_init():
    return True if redis.get('global:appStarted') != None else False 
      
def app_init():
    if app_is_init():
        return 
    if path.isdir(app.config['RECORDINGS_DIR']):
        redis.set('global:recordingsDir', app.config['RECORDINGS_DIR']);
    else:
        return "%s do not exists!" % app.config['RECORDINGS_DIR']

    redis.set('global:nextRecordingId', 0)
    #redis.set('global:nextCardId', 0)
    #redis.set('global:nextDeskId', 0)
    redis.set('global:appStarted', int(time.time()))

@app.route('/')
def home():
    if not app_is_init(): 
        message = app_init();
    else:
        message = 'App running!'

    return message
        

