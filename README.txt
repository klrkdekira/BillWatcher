billwatcher README
==================

The Billwatcher site is hosted at 

http://billwatcher.sinarproject.org

Getting Started
---------------

- cd <directory containing this file>

- $venv/bin/python bootstrap.py

- bin/buildout

- bin/pserve development.ini

Setting Up dependency
----------------------

- mongodb
-- we use upstream mongodb here because the one in ubuntu is a bit old
-- essentially we follow the instruction on http://docs.mongodb.org/manual/tutorial/install-mongodb-on-ubuntu/
- Elasticsearch
-- we use the upstream repo because the ubuntu version is old. 
-- We just follow the instruction at http://www.elastic.co/guide/en/elasticsearch/reference/current/setup-repositories.html


TODO
----
- i18n
- Search
- Error page
