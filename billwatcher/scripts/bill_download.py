from gevent import monkey; monkey.patch_all()
import gevent
from gevent import queue
import os
import sys
import logging

from urlparse import urlparse
import requests
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

    def flatten_data(bill):
        document = bill.get('document')

        if document:
            filename = document['name']

            if not fs.exists(filename=filename):
                log.info('Downloading file...')
                # Retry 5 times if error
                url = document['url']
                retries = 0
                while retries < 6:
                    f = requests.get(url)
                    if f.status_code == 200:
                        log.info(f.headers['content-type'])
                        log.info('Saving record...')
                        fs.put(f.content, filename=filename)
                        break
                    else:
                        log.info('File download error. Code %d' % f.status_code)
                    retries += 1

    def worker():
        while True:
            item = q.get()
            try:
                flatten_data(item)
            finally:
                q.task_done()

    for i in xrange(20):
        gevent.spawn(worker)
    
    for bill in db.bills.find():
        q.put(bill)

    q.join()
    log.info('Done')
    sys.exit(1)