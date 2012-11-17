# -*- coding: utf-8 -*-
import time
import pytz
from os import path, environ
from datetime import datetime
from flask import Flask, redirect, url_for, render_template, jsonify, request, \
                    session, abort
from flask.ext.redis import Redis

#from testapp import settings
#from recorder import settings
from recorder.decorators import templated

# Initialize simple Flask application
app = Flask(__name__)
app.config.from_envvar('RECORDER_CONFIG')

if not app.debug:
    import logging
    from logging.handlers import RotatingFileHandler 
    logfile = path.join(app.config['RECORDER_LOG_DIR'], 'recorder.log') 
    file_handler = RotatingFileHandler(logfile)
    file_handler.setLevel(logging.ERROR)
    app.logger.addHandler(file_handler)

#app.config.from_object(config.)
app.secret_key = '\xc3G\x1e\x16\xca\xed\x02\x01T\xc9\xe9?t\xc6\xa7\x1f\xf5\x17\x04\x94\xc0`\xad\xfa'

# Setup Redis conection
redis = Redis(app)

def app_is_init():
    return True if redis.get('global:appStarted') != None else False 
      
def app_init():
    if app_is_init():
        return 
    if not path.isdir(app.config['RECORDINGS_DIR']):
        return "%s do not exists!" % app.config['RECORDINGS_DIR']
    redis.set('global:nextRecordingId', 0)
    #redis.set('global:nextCardId', 0)
    #redis.set('global:nextDeskId', 0)
    init_time = time.time()
    redis.set('global:appStarted', int(init_time))
    print init_time

def _to_timestamp(time_string):
    import calendar
    utc = pytz.timezone("UTC")
    time = datetime.strptime(time_string, "%d.%m.%Y %H:%M")
    time = pytz.timezone(app.config['APP_TZ']).localize(time)
    time = utc.normalize(time.astimezone(utc))
    return calendar.timegm(time.utctimetuple()) 

def _perform_search(start, end = None, page = 1, min_len = 0, channel = -1):
    from recorder.models import Recording
    import calendar

    start = _to_timestamp(start)

    if end:
        end = _to_timestamp(end)
    else:
        end = start+(3600*3)
        
    recordings, num = Recording.find_by_timestamp(
                            start, 
                            end,  
                            True,
                            page,
                            min_len,
                            channel)
    num_pages = int(num/app.config['RECORDS_PER_PAGE'])
    return (recordings, num, num_pages)

@app.route('/')
def home():
    if not app_is_init(): 
        message = app_init();
    else:
        message = 'App running!'

    return message

@app.route('/_ajax_search', methods=['GET'])
def _ajax_search():
    ret = dict()
    page = request.args.get('p', 1, type=int)
    min_len = request.args.get('m', 0, type=int)
    
    try:
        card_id, channel_id = request.args.get('d', "-1:-1").split(':')
        card_id = int(card_id)
        channel_id = int(channel_id)
    except ValueError:
        ret['error'] = u"Zła wartość parametru d=card_id:channel_id"
        return ret

    try:
        if(request.args.get('s', "")):
            start = request.args.get('s', "")
            session['recording-search-start'] = start
        else:
            start = session.get('recording-search-start')

        if(request.args.get('e', "")):
            end = request.args.get('e', "")
            session['recording-search-end'] = end 
        else:
            end = session.get('recording-search-end')

        #if(min_len > 0):
        #    session['recording-search-min'] = min_len
        #else:
        #    min_len = session.get('recording-search-min', 0)

        recordings, num, num_pages = _perform_search(start, 
                                                     end, 
                                                     page, 
                                                     min_len,
                                                     channel_id)

        ret['recordings_table'] = render_template('result-table.html',
                                                  recordings=recordings)
        if(num > app.config['RECORDS_PER_PAGE']):
            pages = range(1, num_pages + 2)
            ret['pagination'] = render_template('_table_pagination.html',
                                                pages=pages,
                                                page=page)
        ret['num'] = num
    except ValueError:
        session.pop('recording-search-start')
        session.pop('recording-search-end')
        ret['error'] = u"Wybrana wartość daty nie jest w formacie" + \
            " 'dd.mm.yyyy HH:MM'"

    return jsonify(ret);


@app.route('/search', methods=['GET', 'POST'])
@templated()
def search():
    from recorder.models import Recording
    last = Recording.last()
    date = datetime.utcfromtimestamp(last.timestamp)
    date = pytz.timezone("UTC").localize(date)
    date = date.astimezone(pytz.timezone(app.config['APP_TZ']))

    recordings_table = "" 
    num = 0
    pagination = ""
    start = session.get('recording-search-start')
    #Reset min_len session value
    session.pop('recording-search-min')
    if(start):
        try:
            recordings, num, num_pages = _perform_search(start)
            recordings_table = render_template('result-table.html',
                                               recordings=recordings)
            if(num > app.config['RECORDS_PER_PAGE']):
                page = 1
                pages = range(1, num_pages + 2)
                pagination = render_template('_table_pagination.html',
                                             pages=pages,
                                             page=page)

        except ValueError:
            session.pop('recording-search-start')

    return dict(
            section_title=u"Wyszukiwanie proste",
            default_date=date,
            default_date_str=date.strftime("%d.%m.%Y"),
            recordings_table=recordings_table,
            num=num,
            pagination=pagination
    )

@app.route('/search/advanced')
@templated()
def search_advanced():
    from recorder.models import Card, Desk
    desks = []
    for card in Card.all():
        for desk in card.all_desks():
            desks.append(desk)

    return dict(
        desks = desks,
        recordings_table = render_template('result-table.html',
                                           recordings = []),
        num = 0,
    )

@app.route('/listen/<int:rid>', methods=['GET'])
@templated()
def listen(rid):
   from recorder.models import Recording
   recording = Recording.load(rid)
   if recording != None:
       return dict( recording = recording )
   else:
       abort(404)

@app.route('/test')
def test():
    return render_template('overview.html', section_title = u"Przegląd możliwość templatki") 

