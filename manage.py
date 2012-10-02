import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask.ext.script import Server, Manager
from recorder import app, app_is_init, app_init

manager = Manager(app)
manager.add_command("runserver", Server())

@manager.command
def init():
    if not app_is_init():
        print app_init();
    else:
        print "App initialized."
    
@manager.command
def load_test(test_yaml):
    import yaml
    from pprint import pprint
    from recorder.models import Card, Desk
    with open(test_yaml) as f:
        tests_map = yaml.load(f)
    for key, values in tests_map.iteritems():
        if key == 'card0':
            Card(**values).save() 
        else:
            Desk(**values).save()

@manager.command
def run_fapws3(port):
    import fapws._evwsgi as evwsgi
    from fapws import base
    from fapws.contrib import views, log

    from recorder import app
    
    evwsgi.start('0.0.0.0', port) 
    evwsgi.set_base_module(base)
    
    staticfile = views.Staticfile('static', maxage=2629000)
    evwsgi.wsgi_cb(('/static', staticfile))
    evwsgi.wsgi_cb(('/', app))
    evwsgi.set_debug(0)
    evwsgi.run()

if __name__ == "__main__":
    manager.run()
