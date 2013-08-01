import os
import sys
import logging

from urlparse import urlparse
import pymongo

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
    for bill in db.bills.find():
        db.bills_archive.insert(bill)
    log.info('Archived records from billwatcher.bills to billwatcher.bills_archive')
    db.bills.remove()
    log.info('Removed records from billwatcher.bills')
