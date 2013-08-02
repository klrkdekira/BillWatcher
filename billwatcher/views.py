from pyramid.view import view_config
from pyramid.i18n import TranslationStringFactory

from webhelpers import paginate

_ = TranslationStringFactory('billwatcher')

def views_include(config):
    config.add_route('bill.list', '/')
    config.add_route('bill.detail', '/detail/{rev_id}')

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
        
    @view_config(route_name='bill.list', renderer='bill/list.html')
    def web_list(self):
        page = self.request.params.get('page', '1')

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

    @view_config(route_name='bill.detail', renderer='bill/detail.html')
    @view_config(route_name='bill.detail', renderer='json', accept='application/json')
    def view(self):
        rev_id = self.request.matchdict['rev_id']
        bill = self.db.bills.find_one({'item.id': rev_id})
        return {'bill': bill}

@view_config(route_name='feeds')
def feeds(request):
    from pyramid.response import Response
    from webhelpers import feedgenerator

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
