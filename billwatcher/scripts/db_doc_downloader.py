import os
import sys
import logging
import datetime

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

    for bill in db.bills.find():
        document = bill.get('document')
        if document:
            filename = document['name']
            url = document['url']
            f = requests.get(url)
            if f.status_code == 200:
                log.info('Saving record...')
                fs.put(f.content, filename=filename)
    log.info('Done')