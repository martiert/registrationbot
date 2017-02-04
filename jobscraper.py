#!/usr/bin/env python

import pymongo
import argparse
from urllib.request import urlopen
from html.parser import HTMLParser


class Parser(HTMLParser):
    def __init__(self, baseurl):
        super(Parser, self).__init__()

        self._baseurl = baseurl
        self.jobs = []
        self._processing = None
        self._next_is_title = False
        self._next_is_location = False
        self._next_is_department = False
        self._next_is_date = False
        self._next_is_jobtype = False

    def handle_starttag(self, tag, attrs):
        if self._processing:
            self.process(tag, attrs)
            return

        if tag != 'td':
            return

        if not ('class', 'colTitle') in attrs:
            return

        self._processing = {'dummy': True}

    def handle_endtag(self, tag):
        if not self._processing:
            return

        if tag == 'td':
            del self._processing['dummy']
            self.jobs.append(self._processing)
            self._processing = None

    def handle_data(self, data):
        if self._processing:
            self.process_data(data.strip())

    def process(self, tag, attrs):
        if tag == 'a' and ('class', 'jobTitle-link') in attrs:
            for attr in attrs:
                if attr[0] == 'href':
                    self._processing['url'] = '{}/{}'.format(self._baseurl, attr[1])
                    self._next_is_title = True
        elif tag == 'span':
            if ('class', 'jobLocation') in attrs:
                self._next_is_location = True
            elif ('class', 'jobDate') in attrs:
                self._next_is_date = True
            elif ('class', 'jobDepartment') in attrs:
                self._next_is_department = True
            elif ('class', 'jobShifttype') in attrs:
                self._next_is_jobtype = True

    def process_data(self, data):
        if self._next_is_title:
            self._processing['title'] = data
            self._next_is_title = False
        elif self._next_is_location:
            self._processing['location'] = data
            self._next_is_location = False
        elif self._next_is_date:
            self._processing['date'] = data
            self._next_is_date = False
        elif self._next_is_department:
            self._processing['department'] = data
            self._next_is_department = False
        elif self._next_is_jobtype:
            self._processing['jobtype'] = data
            self._next_is_jobtype = False


baseurl = 'https://jobs.cisco.com'
url = '{}/search/?q=Norway&locationsearch&startrow=0&sortcolumn=referencedate&sortdirection=desc&advanced=true&location=Oslo,%20Norway'.format(baseurl)
response = urlopen(url)
data = response.read().decode()

html = Parser(baseurl)
html.feed(data)

parser = argparse.ArgumentParser()
parser.add_argument(
    '--database',
    '-d',
    required=True,
)
parser.add_argument(
    '--username',
    '-u',
    required=True,
)
parser.add_argument(
    '--password',
    required=True,
)

args = parser.parse_args()

mongodb = pymongo.MongoClient()
db = mongodb[args.database]
db.authenticate(args.username, args.password)
db.jobs.remove({})
for job in html.jobs:
    db.jobs.update_one({'url': job['url']}, {'$set': job}, upsert=True)
