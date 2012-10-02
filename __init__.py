# -*- coding: utf-8 -*-
import time
import pytz
from os import path
from datetime import datetime
from flask import Flask, redirect, url_for, render_template, jsonify, request, \
                    session
from flask.ext.redis import Redis

#from testapp import settings
from recorder import settings
from recorder.decorators import templated

# Initialize simple Flask application
app = Flask(__name__)

if not app.debug:
    import logging
    from logging.handlers import RotatingFileHandler 
    logfile = path.join(settings.RECORDER_LOG_DIR, 'recorder.log') 
    file_handler = RotatingFileHandler(logfile)
    file_handler.setLevel(logging.ERROR)
    app.logger.addHandler(file_handler)

app.config.from_object(settings)
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

def _perform_search(start, page):
    from recorder.models import Recording
    start = datetime.strptime(start, "%d.%m.%Y %H:%M")
    start = pytz.timezone(settings.APP_TZ).localize(start)
    start = time.mktime(start.utctimetuple()) 
    recordings, num = Recording.search(
                            start, 
                            start+(3600*3), 
                            True,
                            True,
                            page)
    num_pages = int(num/settings.RECORDS_PER_PAGE)
    return (recordings, num, num_pages)

@app.route('/')
def home():
    if not app_is_init(): 
        message = app_init();
    else:
        message = 'App running!'

    return message

@app.route('/_search_simple', methods=['GET'])
def _search_simple():
    import jsonpickle
    ret = dict()
    page = request.args.get('p', 1, type=int)
    try:
        if(request.args.get('s', "")):
            start = request.args.get('s', "")
            session['recording-search-start'] = start
        else:
            start = session.get('recording-search-start')

        recordings, num, num_pages = _perform_search(start, page)

        ret['recordings_table'] = render_template('result-table.html',
                                                  recordings=recordings)
        if(num_pages > 1):
            #TODO poprawić tą PAGINCJĘ!!
            pages = range(1, num_pages + 1)
            ret['pagination'] = render_template('_table_pagination.html',
                                                pages=pages,
                                                page=page)
        ret['num'] = num
    except ValueError:
        session.pop('recording-search-start')
        ret['error'] = u"Wybrana wartość daty nie jest w formacie" + \
            " 'dd.mm.yyyy HH:MM'"

    return jsonify(ret);

@app.route('/search', methods=['GET', 'POST'])
@templated()
def search():
    from recorder.models import Recording
    date = datetime.fromtimestamp(Recording.last().timestamp)
    date = pytz.timezone("UTC").localize(date)
    date = date.astimezone(pytz.timezone(settings.APP_TZ))

    recordings_table = "" 
    num = 0
    pagination = ""
    start = session.get('recording-search-start')
    if(start):
        try:
            recordings, num, num_pages = _perform_search(start, 1)
            recordings_table = render_template('result-table.html',
                                               recordings=recordings)
            if(num_pages > 1):
                page = 1
                #pages = range(page, min(num_pages, page + 2) + 1)
                pages = range(page, num_pages + 1)
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

@app.route('/test')
def test():
    return render_template('overview.html', section_title = u"Przegląd możliwość templatki") 

