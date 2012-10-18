from setuptools import setup, find_packages

setup(
    name='recorder-web',
    version='0.1-pre',
    long_description=__doc__,
    packages=['recorder'],
    include_package_data=True,
    zip_safe=False,
    install_requires=['Flask',
                      'Flask-And-Redis',
                      'Flask-Script',
                      'Jinja2',
                      'PyYAML',
                      'Werkzeug',
                      'argparse',
                      'pytz',
                      'redis',
                      'hiredis',
                      'wsgiref']
)
