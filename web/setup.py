from distutils.core import setup

from setuptools import find_packages

ldap_requires = [
    "twisted",
    "ldaptor==16.0.0",
    "service_identity",
    "txpostgres",
]

ldap_dependency_links = [
    "git+https://github.com/twisted/ldaptor.git@5f6cf0691cb4829429d9f2732fd0a1a0077f7075#egg=ldaptor-5f6cf0691cb4829429d9f2732fd0a1a0077f7075",
]

setup(name='p2k16',
      version='1.0',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      entry_points={
      },
      install_requires=[
          'blinker',
          'emails',
          'flask',
          'flask-bcrypt',
          'flask-bower',
          'flask-env',
          'flask_inputs>=0.2.0',
          'flask-login',
          'flask-sqlalchemy',
          'flask-testing',
          'gunicorn',
          'jsonschema',
          'ldif3',
          'nose',
          'paho-mqtt',
          'psycopg2-binary',
          'PyYAML',
          'sqlalchemy',
          'sqlalchemy-continuum',
          'stripe',
          'typing',
      ] + ldap_requires,
      dependency_links=[
          'git+https://github.com/nathancahill/flask-inputs.git@9d7d329#egg=Flask_Inputs-9d7d329',
      ] + ldap_dependency_links)
