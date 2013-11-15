import logging
from pprint import pformat

import requests
import simplejson 

from pyramid.view import view_config
from pyramid.i18n import TranslationStringFactory
from pyramid.response import Response
from pyramid.exceptions import HTTPNotFound

from webhelpers import feedgenerator, paginate
from bson.objectid import ObjectId

_ = TranslationStringFactory('billwatcher')

log = logging.getLogger(__name__)

def views_include(config):
    config.add_route('bill.list', '/')
    config.add_route('bill.detail', '/detail/{rev_id}')
    config.add_route('bill.doc', '/doc/{rev_id}')

    config.add_route('feeds', '/feeds')
    config.add_route('search', '/search')
    config.add_route('about', '/about')

class BillView(object):
    def __init__(self, request):
        self.request = request
        self.db = request.db

    def _list(self):
        bills = self.db.bills.find().sort([['bill_reference_id', -1]])
        return map(lambda bill: bill, bills)
        
    @view_config(route_name='bill.list', renderer='json', accept='application/json')
    def api_list(self):
        return {'bills': self._list()}
        
    @view_config(route_name='bill.list', renderer='bill/list.html', accept='text/html')
    def web_list(self):
        p = self.request.params
        page = p.get('page', '1')
        search_param = p.get('search')

        if search_param:
            results = search(self.request)
            bills = results['bills']
        else:
            bills = self._list()

        data = paginate.Page(bills, page,
                             items_per_page=20)

        # Quick hack for pager
        start = data.page - 2
        end = data.page + 3
        if start <= 0:
            start = 1
            end = 6

        if end >= data.page_count:
            end = data.page_count + 1
            start = end - 5

        return {'data': data,
                'start': start,
                'end': end}

    def _get_bill(self, rev_id):
        bill = self.db.bills.find_one({'_id': ObjectId(rev_id)})
        if not bill:
            raise HTTPNotFound()
        return bill

    @view_config(route_name='bill.detail', renderer='bill/detail.html', accept='text/html')
    @view_config(route_name='bill.detail', renderer='json', accept='application/json')
    def view(self):
        rev_id = self.request.matchdict['rev_id']
        bill = self._get_bill(rev_id)
        log.info(pformat(bill))
        return {'bill': bill}

    @view_config(route_name='bill.doc')
    def doc(self):
        rev_id = self.request.matchdict['rev_id']
        bill = self._get_bill(rev_id)
        document = bill.get('document')
        if not document:
            raise HTTPNotFound()

        pdf_doc = self.request.fs.get_last_version(filename=document['name'])
        if not pdf_doc:
            raise HTTPNotFound()

        resp = Response()
        resp.content_disposition = 'filename={filename}'.format(filename=document['name'])
        resp.content_type = pdf_doc.content_type
        resp.body_file.write(pdf_doc.read())
        return resp            
            
@view_config(route_name='feeds')
def feeds(request):

    feed = feedgenerator.Rss201rev2Feed(title='Malaysian Bill Watcher',
                                        link=request.route_url('bill.list'),
                                        description='Collection of bills debated in Malaysian Parliament')

    bills = request.db.bills.find().sort([['bill_reference_id', -1]])
    for bill in bills:
        feed.add_item(title=bill['name'],
                      link=request.route_url('bill.detail', rev_id=bill['_id']),
                      description=bill['description'])

    resp = Response()
    resp.content_type = 'application/rss+xml'
    feed.write(resp.body_file, 'utf-8')
    return resp

@view_config(route_name='about', renderer='about.html')
def about(request):
    return {}

ES_ENDPOINT = 'http://localhost:9200/mongoindex/_search'

def search(request):
    search_param = request.params.get('search')
    params = {"q": search_param}
    resp = requests.get(ES_ENDPOINT, params=params)
    if resp.status_code != 200:
        # TODO, implement session factory
        # request.session.flash('Sorry. Search engine is down at the moment. Please try again')
        # return HTTPFound(request.route_url('bill.list'))
        return {}
    results = simplejson.loads(resp.text)
    hits = results['hits']
    bills = hits['hits']
    return {'bills': map(lambda bill: bill['_source'], bills)}
