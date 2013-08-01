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

@view_config(route_name='bill.list', renderer='bill/list.html')
def bill_list(request):
    page = request.params.get('page', '1')

    records = request.db.bills.find().sort([['id', -1]])
    bills = []

    import pprint
    for bill in records:
        pprint.pprint(bill)
        # year = bill['id'].split('_')[-1]
        bills.extend(bill['item'])

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
def bill_detail(request):
    rev_id = request.matchdict['rev_id']
    bill = request.db.bills.find_one({'item.id': rev_id})
    import pprint
    pprint.pprint(bill)
    return {}

@view_config(route_name='feeds')
def feeds(request):
    from pyramid.response import Response
    from webhelpers import feedgenerator

    feed = feedgenerator.Rss201rev2Feed(title='test',
                                        link=request.route_url('bill.list'),
                                        description='test message')
    feed.add_item(title='Hello',
                  link=request.route_url('bill.list'),
                  description='test')

    resp = Response()
    resp.content_type = 'application/rss+xml'
    feed.write(resp.body_file, 'utf-8')
    return resp

@view_config(route_name='about', renderer='about.html')
def about(request):
    return {}
