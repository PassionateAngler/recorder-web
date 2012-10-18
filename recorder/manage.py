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

if __name__ == "__main__":
    manager.run()
