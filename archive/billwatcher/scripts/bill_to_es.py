from gevent import monkey; monkey.patch_all()
import gevent
from gevent import queue
import os
import sys
import logging
import multiprocessing

from urlparse import urlparse
import pymongo

import elasticsearch

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

log = logging.getLogger(__name__)

def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)
    

def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)

    db_url = urlparse(settings['mongo_uri'])
    conn = pymongo.Connection(
        host=db_url.hostname,
        port=db_url.port
    )

    db = conn.billwatcher

    q = queue.JoinableQueue()

    es = elasticsearch.Elasticsearch(settings['es_uri'])
    def index_bill(bill):
        body = {'name': bill['name'],
                'description': bill['description'],
                'year': bill['year'],
                'status': bill['status']}

        document = bill.get('document')
        if document:
            content = document.get('content')
            if content:
                body['content'] = content

        res = es.index(index='billwatcher',
                       doc_type='bill',
                       id=bill['_id'],
                       body=body)
        log.info(res)

    def worker():
        while True:
            item = q.get()
            try:
                index_bill(item)
            except Exception as e:
                log.error(e)
            q.task_done()

    worker_count = multiprocessing.cpu_count() + 1
    log.info("Initialising {worker_count} workers...".format(worker_count=worker_count))
    for i in xrange(worker_count):
        gevent.spawn(worker)
    log.info("Workers started...")

    log.info("Inserting records to workers...")
    record_count = 0
    for bill in db.bills.find():
        q.put(bill)
        record_count += 1
    log.info("{record_count} inserted...".format(record_count=record_count))

    log.info("Processing...")
    q.join()
    log.info('Refreshing index...')
    es.indices.refresh(index='billwatcher')
    log.info('Done!')
    sys.exit(1)