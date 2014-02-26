from gevent import monkey; monkey.patch_all()
import gevent
from gevent import queue

import os
import sys
import logging

from urlparse import urlparse
import slate
import pymongo
import gridfs

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
    fs = gridfs.GridFS(db)

    q = queue.JoinableQueue()

    def pdf_to_text(bill):
        document = bill.get('document')
        if document:
            doc_content = document.get('content')
            if not doc_content:
                filename = document['name']
                log.info('Processing pdf file...')

                if fs.exists(filename=filename):
                    try:
                        pdf_doc = fs.get_last_version(filename)
                    except:
                        pdf_doc = None

                    if pdf_doc:
                        pdf_text = slate.PDF(pdf_doc)
                        document['content'] = ''.join(pdf_text)
                        db.bills.update({'_id': bill['_id']},
                                        {'$set': {'document': document}},
                                        upsert=False)
                        log.info('Record updated!')
                else:
                    log.info('Skipped!')
            else:
                if isinstance(doc_content, list):
                    log.info('Merging content list to text')
                    document['content'] = ''.join(doc_content)
                    db.bills.update({'_id': bill['_id']},
                                    {'$set': {'document': document}},
                                    upsert=False)
                    log.info('Record updated!')
                else:
                    log.info('Skipped!')

    def worker():
        while True:
            item = q.get()
            try:
                pdf_to_text(item)
            finally:
                q.task_done()

    for i in xrange(4):
        gevent.spawn(worker)
    
    for bill in db.bills.find():
        q.put(bill)

    q.join()
    log.info('Done')
    sys.exit(1)
