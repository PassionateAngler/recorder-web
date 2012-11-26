# -*- coding: utf-8 -*-
import time
import pytz
from os import path, environ
from datetime import datetime
from flask import Flask, redirect, url_for, render_template, jsonify, request, \
    session, abort, current_app
from flask.ext.login import LoginManager, login_user, logout_user, \
    login_required, current_user
from flask_principal import Principal, Permission, RoleNeed, UserNeed, Identity, \
    AnonymousIdentity, identity_changed, identity_loaded
from flask.ext.bcrypt import Bcrypt
from flask.ext.redis import Redis

#from testapp import settings
#from recorder import settings
from recorder.decorators import templated
from recorder.forms import LoginForm, ChangePasswordForm, UserAddForm, \
    UserEditForm

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
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.setup_app(app)

principals = Principal(app)

@login_manager.user_loader
def load_user(email):
    from recorder.models import User
    return User.load(email)

@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    identity.user = current_user

    if hasattr(current_user, 'email'):
        identity.provides.add(UserNeed(current_user.email))

    if hasattr(current_user, 'roles'):
        for role in current_user.roles:
            identity.provides.add(RoleNeed(role))

def create_roles():
    from recorder.models import Role
    roles = [{'name': 'users', 'description': "Zarządzaj użytkownikami"},
             {'name': 'recorder', 'description': "Zarządzaj nagraniami"}]
    for role in roles:
        Role(**role).save()

def app_is_init():
    return True if redis.get('global:appStarted') != None else False 
      
def app_init():
    if app_is_init():
        return 
    if not path.isdir(app.config['RECORDINGS_DIR']):
        return "%s do not exists!" % app.config['RECORDINGS_DIR']

    create_roles()
    redis.set('global:nextRecordingId', 0)
    init_time = time.time()
    redis.set('global:appStarted', int(init_time))
    print init_time

permissions = { 'users': Permission(RoleNeed('users')),
                'recorder': Permission(RoleNeed('recorder')) }

def _default_response():
    return {'current_user': current_user,
            'permissions' : permissions}

@app.route('/')
def home():
    if not app_is_init(): 
        return app_init();
    else:
        if current_user.is_anonymous(): 
            return redirect(url_for('login'))
        else:
            return redirect(url_for('search'))

#Users login and managment
@app.route('/login', methods=('GET', 'POST'))
@templated()
def login():
    message = ""
    form = LoginForm()
    if form.validate_on_submit():
        from recorder.models import User
        user = User.load(form.email.data)
        if user and user.check_password(form.password.data):
            login_user(user)
            identity_changed.send(current_app._get_current_object(),
                                  identity=Identity(user.email))
            return redirect(url_for('search'))
        else:
            message = u"Zły użytkownik lub hasło"

    return {'form' : form, 'message' : message}

@app.route('/logout')
def logout():
    logout_user()
    identity_changed.send(current_app._get_current_object(),
                          identity=AnonymousIdentity())
    return redirect(url_for('login'))

@app.route('/users')
@templated()
def users():
    with permissions['users'].require():
        from recorder.models import Role, User
        ret = _default_response()
        ret['title'] =  u"Użytkownicy"
        ret['section_title'] = u"Użytkownicy"
        users = User.all()
        for u in users:
            u.roles = map(lambda r: Role.load(r).description, u.roles)
        ret['users'] = users
        return ret

@app.route('/user/add', methods=['GET', 'POST']) 
@templated() 
def user_add():
    with permissions['users'].require():
        from recorder.models import Role
        ret = _default_response()
        ret['form'] = UserAddForm()
        ret['form'].roles.choices = [(r.name, r.description) for r in Role.all()]
        ret['title'] =  u"Dodaj użytkownika"
        ret['section_title'] = u"Dodaj użytkownika"

        if ret['form'].validate_on_submit():
            if ret['form'].password.data == ret['form'].re_password.data:
                from recorder.models import User
                user = User(**{'email':ret['form'].email.data, 
                               'password' : ret['form'].password.data,
                               'roles' : ret['form'].roles.data })
                user.save()
            else:
                ret['error'] = u"Podano dwa różne hasła"
        return ret

@app.route('/user/edit/<string:email>', methods=['GET', 'POST']) 
@templated() 
def user_edit(email):
    with permissions['users'].require():
        from recorder.models import Role, User 
        user = User.load(email)
        if not user:
            return abort(404)

        ret = _default_response()
        ret['form'] = UserEditForm()
        ret['form'].roles.choices = [(r.name, r.description) for r in Role.all()]
        ret['user'] = user
        ret['title'] =  u"Edtuj konto"
        ret['roles'] = user.roles
        ret['section_title'] = u"Edytuj konto"

        if request.method == 'POST' and ret['form'].validate_on_submit():
            if ret['form'].password.data == ret['form'].re_password.data:
                if ret['form'].password.data:
                    user.password = ret['form'].password.data
                user.roles = ret['form'].roles.data
                user.save()
                return redirect('users')
            else:
                ret['error'] = u"Podano dwa różne hasła"

        return ret

@app.route('/user/delete/<string:email>', methods=['GET']) 
@templated() 
def user_delete(email):
    with permissions['users'].require():
        from recorder.models import Role, User 
        user = User.load(email)
        user.delete()
        return redirect('users')

@app.route('/user/change_password', methods=['GET', 'POST'])
@login_required
@templated()
def change_password():
    ret = _default_response()
    ret['form'] = ChangePasswordForm()
    ret['title'] =  u"Zmień hasło"
    ret['section_title'] = u"Zmień hasło"

    if ret['form'].validate_on_submit():
        from recorder.models import User
        if not current_user.check_password(ret['form'].current_password.data): 
            ret['error'] =  u"Podano błędne OBECNE hasło"
            return ret 

        if ret['form'].password.data != ret['form'].re_password.data:
            ret['error'] = u"Hasło i jego powtórzenie są różne"
            return ret 

        current_user.password = ret['form'].password.data
        if current_user.save():
            ret['success'] = u"Zmieniono hasło"
        else:
            ret['error'] = u"Coś poszło nie tak, nie można zmieńć hasła"
    
    return ret

#Recordings managment views and functions
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

@app.route('/_ajax_search')
@login_required
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
            session['recording-search-min'] = min_len
            session['recording-channel_id'] = channel_id
        else:
            start = session.get('recording-search-start')

        if(request.args.get('e', "")):
            end = request.args.get('e', "")
            session['recording-search-end'] = end 
            session['recording-search-min'] = min_len
            session['recording-channel_id'] = channel_id
        else:
            end = session.get('recording-search-end')

        if(min_len > 0):
            session['recording-search-min'] = min_len
        else:
            min_len = session.get('recording-search-min', 0)

        if(channel_id >= 0):
            session['recording-channel_id'] = channel_id
        else:
            channel_id = session.get('recording-channel_id', 0)

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
        session.pop('recording-search-start', "")
        session.pop('recording-search-end', "")
        ret['error'] = u"Wybrana wartość daty nie jest w formacie" + \
            " 'dd.mm.yyyy HH:MM'"

    return jsonify(ret);


@app.route('/search', methods=['GET', 'POST'])
@login_required
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
    session.pop('recording-search-min', 0)
    session.pop('recording-channel_id', -1)
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

    ret = _default_response()
    ret['title']=u"Wyszukiwanie proste"
    ret['section_title']=u"Wyszukiwanie proste"
    ret['default_date']=date
    ret['default_date_str']=date.strftime("%d.%m.%Y")
    ret['recordings_table']=recordings_table
    ret['num']=num
    ret['pagination']=pagination

    return ret

@app.route('/search/advanced')
@login_required
@templated()
def search_advanced():
    from recorder.models import Card, Desk
    desks = []
    for card in Card.all():
        for desk in card.all_desks():
            desks.append(desk)

    ret = _default_response()
    ret['title']=u"Wyszukiwanie zaawansowane"
    ret['section_title']=u"Wyszukiwanie zaawansowane"
    ret['desks'] = desks
    ret['recordings_table']= render_template('result-table.html', recordings = [])
    ret['num']= 0
    return ret

@app.route('/listen/<int:rid>', methods=['GET'])
@login_required
@templated()
def listen(rid):
   from recorder.models import Recording
   recording = Recording.load(rid)
   if recording != None:
        ret = _default_response()
        ret['title']=u"Odsłuchaj",
        ret['section_title']=u"Odsłuchaj",
        ret['recording']= recording 
        return ret
   else:
       abort(404)

def _can_edit():
    lock_id = redis.get("tmp:deskLockId")
    if(lock_id):
        lock_id = long(lock_id)
    else:
        lock_id = 0

    edit_ok = (lock_id == long(session.get("desk_edit_lock_id", -1)))

    return (edit_ok, lock_id)

@app.route('/_desks_update', methods=['POST'])
@login_required
def desks_update():
    with permissions['recorder'].require():
        import json
        from recorder.models import Desk

        edit_ok, lock_id = _can_edit()

        if(edit_ok):
            redis.expire("tmp:deskLockId", 120)
        else:
            #Somebody else is editing
            return {'error':u"Błąd, edycja zablokowana"}

        ret = dict()
        with redis.pipeline() as pipe:
            try:
                desks = json.loads(request.form.get('desks', ""))
                if(len(desks) != 8):
                    raise ValueError
                for ch_id, desk in enumerate(desks):
                    pipe.set(Desk.KEY_STRING % (0, ch_id),
                              json.dumps({'name': desk['name'],
                                         'description': desk['desc']})
                    )
                pipe.execute()
                ret["status"] = "OK"
            except ValueError, KeyError:
                ret['error'] = u"Błędne dane w POST"

        return jsonify(ret)

@app.route('/desks')
@login_required
@templated()
def desks():
    import time
    from recorder.models import Card, Desk

    edit_ok, lock_id = _can_edit()

    if(edit_ok):
        #Could edit, we started edition and continuing it
        redis.expire("tmp:deskLockId", 120)
    elif(lock_id == 0):
        #No one is editing
        session['desk_edit_lock_id'] = "%s" % long(time.time() * 1000)
        redis.set("tmp:deskLockId", session['desk_edit_lock_id'])
        redis.expire("tmp:deskLockId", 120)
        edit_ok = True

    desks = []
    for card in Card.all():
        for desk in card.all_desks():
            desks.append(desk)
    ret = _default_response()
    ret['title']= u"Stanowiska"
    ret['section_title']= u"Stanowiska"
    ret['user']=current_user
    ret['desks']= desks
    ret['edit_ok']= edit_ok
    return ret

@app.route('/desk/edit/<int:card_id>/<int:channel_id>', methods=('GET', 'POST'))
@login_required
@templated()
def edit_desk(card_id, channel_id):
    with permissions['recorder'].require():
        from models import Desk

        edit_ok, lock_id = _can_edit()
        if(edit_ok):
            redis.expire("tmp:deskLockId", 120)
        else:
           #Somebody else is editing
           return redirect(url_for('desks'))

        desk = Desk.load(card_id, channel_id)
        if not desk:
            abort(404)

        if(request.method == 'POST'):
           desk.name = request.form['name'] 
           desk.description = request.form['description'] 
           desk.save()
           return redirect(url_for('desks'))

        ret = _default_response()
        ret['title']= u"Edytuj stanowisko"
        ret['section_title']= u"Edytuj stanowisko"
        ret['desk']= desk
        ret['user']=current_user
        return ret

@app.route('/test')
@login_required
def test():
    ret = _default_response()
    ret['section_title'] = u"Przegląd możliwość templatki"
    return render_template(
        'overview.html', **ret
        ) 
