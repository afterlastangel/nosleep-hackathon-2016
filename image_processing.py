import os
import json
from google.appengine.api import urlfetch

# export CLARIFAI_APP_ID=sTqW-xHoMnvCcxyJAXWXbZxe3XOxtzYfsik4A218
# export CLARIFAI_APP_SECRET=0OACpD2GFomsFNVzO80uFqQDvXzSX2nVAExCe-d_
os.environ['CLARIFAI_APP_ID'] = 'sTqW-xHoMnvCcxyJAXWXbZxe3XOxtzYfsik4A218'
os.environ['CLARIFAI_APP_SECRET'] = '0OACpD2GFomsFNVzO80uFqQDvXzSX2nVAExCe-d_'


class ImageProccessing(object):

    def __init__(self, image_url):
        self.image_url = image_url

    def parse_result(self, result):
        if len(result['results']) > 0:
            keywords = result['results'][0]['result']['tag']['classes']
        return {'keywords': keywords}

    def execute(self):
        url = "http://104.199.150.188?image_url=%s" % self.image_url
        res = urlfetch.fetch(url=url)
        result = json.loads(res.content)
        parsed_result = self.parse_result(result)
        return parsed_result
