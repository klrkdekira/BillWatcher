import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'pyramid',
    'pyramid_jinja2',
    'SQLAlchemy',
    'transaction',
    'pyramid_tm',
    'zope.sqlalchemy',
    'waitress',
    'gunicorn',
    'webhelpers',
    'simplejson',
    'Babel',
    'lingua',
    'ipython',
    'requests',
    'gevent',
    'pymongo',
    'slate',
    'pdfminer',
    ]

setup(name='billwatcher',
      version='0.0',
      description='billwatcher',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web wsgi bfg pylons pyramid',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='billwatcher',
      install_requires=requires,
      entry_points="""\
      [paste.app_factory]
      main = billwatcher:main
      [console_scripts]
      db_doc_downloader = billwatcher.scripts.db_doc_downloader:main
      pdf_parse = billwatcher.scripts.pdf_parse:main
      """,
      )
