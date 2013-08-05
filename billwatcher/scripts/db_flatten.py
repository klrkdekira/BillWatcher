import os
import re
import sys
import logging
import datetime

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


document_pattern = re.compile(".*\('(.*)','(.*)'\)")

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

    ENDPOINT = 'http://www.parlimen.gov.my'
    const_first_reading = 'Bacaan Pertama'
    const_second_reading = 'Bacaan Kedua'
    const_presented_by = 'Dibentang Oleh'
    const_passed_at = 'Diluluskan Pada'

    db = conn.billwatcher

    for bills in db.bills_archive.find():
        year = bills['id'].split('_')[-1]

        for bill in bills['item']:
            data = {'bill_reference_id': None,
                    'name': None,
                    'description': None,
                    'year': year,
                    'ducument': None,
                    'passed_at': None,
                    'presented_by': None,
                    'status': None,
                    'passed_at': None,
                    'first_reading': None,
                    'second_reading': None,
                    'presented_by': None,
                    'history': []}
        
            data['bill_reference_id'] = bill['id']
            data['description'] = bill['text']

            item = bill.get('item')
            if item:
                metadata = item.pop(0)
                data['name'] = metadata['text']
                userdata = metadata.get('userdata')
                if userdata:
                    content = userdata[0]['content']
                    document = document_pattern.findall(content)[0]
                    document_name = document[1]
                    document_url = ENDPOINT + document[0]
                    data['document'] = {'name': document_name,
                                        'url': document_url}

                for h in item:
                    text = h['text']
                    d = text.split(':')[-1]

                    if const_first_reading in text:
                        data['status'] = 'first reading'
                        if d:
                            d = datetime.datetime.strptime(d, '%M/%d/%Y')
                        data['first_reading'] = d
                        hitem = {'history_id': h['id'],
                                 'first_reading': d}
                        data['history'].append(hitem)

                    if const_second_reading in text:
                        data['status'] = 'second reading'
                        if d:
                            d = datetime.datetime.strptime(d, '%M/%d/%Y')
                        data['second_reading'] = d
                        hitem = {'history_id': h['id'],
                                 'second_reading': d}
                        data['history'].append(hitem)

                    if const_presented_by in text:
                        data['presented_by'] = d
                        hitem = {'history_id': h['id'],
                                 'presented_by': d}
                        data['history'].append(hitem)

                    if const_passed_at in text:
                        data['status'] = 'passed'
                        if d:
                            d = datetime.datetime.strptime(d, '%M/%d/%Y')
                        data['passed_at'] = d
                        hitem = {'history_id': h['id'],
                                 'passed_at': d}
                        data['history'].append(hitem)

            log.info('Saving record...')
            db.bills.insert(data)
    log.info('Done!')
    sys.exit(1)