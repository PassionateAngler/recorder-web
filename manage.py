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
    
def load_desks(desks):
    import yaml
    from pprint import pprint
    with open(desks) as f:
        desks_map = yaml.load(f)
    for desk in desks_map.values():
        print desk.get('name')
        print desk.get('desc')

if __name__ == "__main__":
    manager.run()
