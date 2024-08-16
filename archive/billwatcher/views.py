import logging

from pyramid.view import view_config
from pyramid.i18n import TranslationStringFactory
from pyramid.response import Response
from pyramid.renderers import render_to_response
from pyramid.exceptions import HTTPNotFound

from webhelpers import feedgenerator, paginate
from bson.objectid import ObjectId

_ = TranslationStringFactory('billwatcher')

log = logging.getLogger(__name__)

def views_include(config):
    config.add_route('home', '/')

    config.add_route('bill.list', '/bill')
    config.add_route('bill.detail', 'bill/{bill_id}')
    config.add_route('bill.doc', '/bill/doc/{bill_id}')

    config.add_route('feed.list', '/feed')

    config.add_route('search', '/search')

class HomeView(object):
    def __init__(self, request):
        self.request = request
        self.db = request.db

    @view_config(route_name='home', renderer='home.html', accept='text/html')
    def home(self):
        latest_bills = (self.db.bills.find({}, {'name': 1, 'description': 1})
                        .sort([('year', -1), ('name', -1)])
                        .limit(5))
        return {'latest_bills': latest_bills}

class BillView(object):
    def __init__(self, request):
        self.request = request
        self.db = request.db
        self.params = request.params

    def _list(self):
        p = self.params
        year = p.get('year')
        status = p.get('status')

        spec = {}

        if year:
            spec['year'] = year

        if status:
            spec['status'] = status

        bills = self.db.bills.find(spec, {'name': 1,
                                          'year': 1,
                                          'description': 1,
                                          'status': 1}).sort([('year', -1),
                                                              ('name', -1)])
        return map(lambda bill: bill, bills)

    @view_config(route_name='home', renderer='json', accept='application/json')
    @view_config(route_name='bill.list', renderer='json', accept='application/json')
    def api_list(self):
        return {'bills': self._list()}

    @view_config(route_name='bill.list', renderer='bill/list.html', accept='text/html')
    def web_list(self):
        p = self.params
        page = p.get('page', '1')

        bills = self._list()
        page_url = paginate.PageURL_WebOb(self.request)
        data = paginate.Page(bills, page,
                             items_per_page=20,
                             url=page_url)

        years = (self.db.bills
                 .aggregate([{'$group': {"_id": "$year",
                                         "count": {"$sum": 1}}},
                             {'$sort': {'_id': -1}}]))
        statuses = (self.db.bills
                    .aggregate([{'$group': {"_id": "$status",
                                            "count": {"$sum": 1}}},
                                {'$sort': {'count': -1}}]))

        return {'data': data,
                'years': years['result'],
                'statuses': statuses['result']}

    def _get_bill(self, bill_id):
        bill = self.db.bills.find_one({'_id': ObjectId(bill_id)})
        if not bill:
            raise HTTPNotFound()
        return bill

    # @view_config(route_name='bill.detail', renderer='json', accept='application/json')
    # @view_config(route_name='bill.detail', renderer='bill/detail.html', accept='text/html')
    @view_config(route_name='bill.detail', renderer='bill/detail.html')
    def view(self):
        bill_id = self.request.matchdict['bill_id']
        bill = self._get_bill(bill_id)
        if self.request.accept == 'application/json':
            resp = render_to_response('json',
                                      {'bill': bill},
                                      request=self.request)
            resp.content_type = 'application/json'
        else:
            resp = render_to_response('bill/detail.html',
                                      {'bill': bill},
                                      request=self.request)
            resp.content_type = 'text/html'
        return resp

    @view_config(route_name='bill.doc')
    def doc(self):
        bill_id = self.request.matchdict['bill_id']
        bill = self._get_bill(bill_id)
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

class FeedView(object):
    def __init__(self, request):
        self.request = request
        self.db = request.db

    def _list(self):
        bill_view = BillView(self.request)
        return bill_view._list()

    @view_config(route_name='feed.list')
    def list(self):
        feed = feedgenerator.Rss201rev2Feed(title='Malaysian BillWatcher',
                                            link=self.request.route_url('bill.list'),
                                            description='Collection of bills debated in Malaysian Parliament')

        bills = self._list()
        for bill in bills:
            link_name = "%s - %s" % (bill['name'], bill['description'])
            feed.add_item(title=link_name,
                          link=self.request.route_url('bill.detail', bill_id=bill['_id']),
                          description=bill['description'])

        resp = Response()
        resp.content_type = 'application/rss+xml'
        feed.write(resp.body_file, 'utf-8')
        return resp

@view_config(route_name='search', renderer='search.html', accept='text/html')
def search(request):
    search_param = request.params.get('search', '')
    query_dsl = {"fuzzy_like_this": {"like_text": search_param,
                                     "fields": ['name', 'description']}}
    res = request.es.search(size=30,
                            body={"query": query_dsl})
    return {'bills': res['hits']['hits']}
