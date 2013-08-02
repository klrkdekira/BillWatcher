import datetime

from pyramid.config import Configurator
from pyramid.renderers import JSON

from gridfs import GridFS
from urlparse import urlparse
import pymongo
import bson

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.add_translation_dirs('locale/')

    # Custom JSON renderer
    json_renderer = JSON()
    def datetime_adapter(obj, request):
        return obj.isoformat()
    json_renderer.add_adapter(datetime.datetime, datetime_adapter)

    def objectid_adapter(obj, request):
        return unicode(obj)
    json_renderer.add_adapter(bson.objectid.ObjectId, objectid_adapter)

    config.add_renderer('json', json_renderer)

    config.include('pyramid_jinja2')
    config.add_renderer('.html', 'pyramid_jinja2.renderer_factory')
    config.add_jinja2_search_path("billwatcher:templates")

    config.add_static_view('static', 'billwatcher:static',
                           cache_max_age=3600)

    db_url = urlparse(settings['mongo_uri'])
    config.registry.db = pymongo.Connection(
        host=db_url.hostname,
        port=db_url.port
    )

    def add_db(request):
        db = config.registry.db[db_url.path[1:]]
        if db_url.username and db_url.password:
            db.authenticate(db_url.username, db_url.password)
        return db

    def add_fs(request):
        return GridFS(request.db)

    config.add_request_method(add_db, 'db', reify=True)
    config.add_request_method(add_fs, 'fs', reify=True)
        
    config.include('billwatcher.views.views_include')
    config.scan()
    return config.make_wsgi_app()
