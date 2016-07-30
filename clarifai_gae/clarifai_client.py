import sys
import base64, json, logging, os, time, urllib
from six import string_types
from google.appengine.api import urlfetch

try:
  from PIL import Image
  CAN_RESIZE = True
except ImportError:
  CAN_RESIZE = False
  print ('It is recommended to install PIL/Pillow with the desired image format support so that '
         'image resizing to the correct dimesions will be handled for you. '
         'If using pip, try "pip install Pillow"')

if sys.version_info >= (3,0):
  import urllib.request as urllib2
  from urllib.parse import urlencode
  from io import StringIO

  def iteritems(d):
    return iter(d.items())
else:
  import urllib2
  from urllib import urlencode
  from cStringIO import StringIO

  def iteritems(d):
    return d.iteritems()

import sys
from email.encoders import encode_noop
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from uuid import uuid4

if sys.version_info >= (3,0):
  from urllib.parse import urlparse
  from urllib.parse import quote

else:
  from urlparse import urlparse
  from urllib import quote

#logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


class ApiError(Exception):
  """Api error."""

  def __init__(self, msg):
    self.msg = msg

  def __str__(self):
    return repr(self.msg)

  def __repr__(self):
    return "Error: '%s'" % str(self.msg)


class ApiClientError(ApiError):
  """Thrown when client side validation fails"""
  pass

class ApiThrottledError(Exception):
  """The usage limit throttle was hit.  Client should wait for wait_seconds before retrying."""

  def __init__(self, msg, wait_seconds):
    self.msg = msg
    self.wait_seconds = wait_seconds

  def __str__(self):
    return repr(self.msg) + '  Wait for %d seconds before retrying.' % self.wait_seconds


class ApiBadRequestError(ApiError, ValueError):
  pass


IM_QUALITY = 95
IGNORE_RESIZE_FORMATS = ['GIF']  # these formats will not be resized.
API_VERSION = 'v1'


class ClarifaiApi(object):
  """
  The constructor for API access. You must sign up at developer.clarifai.com first and create an
  application in order to generate your credentials for API access.

  Args:
    app_id: the client_id for an application you've created in your Clarifai account.
    app_secret: the client_secret for the same application.
    base_url: Base URL of the API endpoints.
    model: Name of the recognition model to query. Defaults to None so that server side defaults
  in your app settings are used.
    wait_on_throttle: When the API returns a 429 throttled error, sleep for the amount of time
        reported in the X-Throttle-Wait-Seconds HTTP response header.
    language: set the default language using it's two letter (with options -XX variant) ISO 639-1
  code to use for all requests. Defaults to None so that server side defaults in your app settings
  are used.
  """

  def __init__(self, app_id=None, app_secret=None, base_url='https://api.clarifai.com',
               model=None, wait_on_throttle=True, language=None):
    if not app_id:
      self.CLIENT_ID = os.environ.get('CLARIFAI_APP_ID', None)
    else:
      self.CLIENT_ID = app_id
    if not app_secret:
      self.CLIENT_SECRET = os.environ.get('CLARIFAI_APP_SECRET', None)
    else:
      self.CLIENT_SECRET = app_secret
    self.wait_on_throttle = wait_on_throttle

    self._base_url = base_url
    self.set_model(model)
    self.language = language
    self._urls = {
      'tag': "/".join([self._base_url, '%s/tag/' % API_VERSION]),
      'embed': "/".join([self._base_url, '%s/embed/' % API_VERSION]),
      'multiop': "/".join([self._base_url, '%s/multiop/' % API_VERSION]),
      'feedback': "/".join([self._base_url, '%s/feedback/' % API_VERSION]),
      'token': "/".join([self._base_url, '%s/token/' % API_VERSION]),
      'info': "/".join([self._base_url, '%s/info/' % API_VERSION]),
      'languages': "/".join([self._base_url, '%s/info/languages' % API_VERSION])
      }
    self.access_token = None
    self.api_info = None

  def set_model(self, model):
    self._model = self._sanitize_param(model, 'default')

  @property
  def language(self):
    return self._language

  @language.setter
  def language(self, lang_code):
    self._language = self._sanitize_param(lang_code, default=None)

  def get_access_token(self, renew=False):
    """ Get an access token using your app_id and app_secret.

    You shouldn't need to call this method yourself. If there is no access token yet, this method
    will be called when a request is made. If a token expires, this method will also automatically
    be called to renew the token.

    Args:
      renew: if True, then force the client to get a new token (even if not expired). By default if
      there is already an access token in the client then this method is a no-op.
    """
    if self.access_token is None or renew:
      headers = {}  # don't use json here, juse urlencode.
      url = self._url_for_op('token')
      data = urlencode({'grant_type': 'client_credentials',
                               'client_id':self.CLIENT_ID,
                               'client_secret':self.CLIENT_SECRET})
      data = bytearray(data, 'utf-8')
      req = urllib2.Request(url, data, headers)
      try:
        # response = urllib2.urlopen(req).read()
        response = urlfetch.fetch(
            url=url, payload=data, headers=headers, validate_certificate=False)
        response = self._parse_response(response)
        pass
      except urllib2.HTTPError as e:
        raise ApiError(e.reason)
      except Exception as e:
        raise ApiError(e)
      self.access_token = response['access_token']
    return self.access_token

  def get_info(self):
    """ Get various information about the current state of the API.

    This provides general information such as the API version number, but also use specific
    information such as the limitations on your account. Some of this information is needed to
    ensure that your API calls will go through within your limits.
    """
    url = self._url_for_op('info')
    # This will be a GET request since data is None
    kwargs = {}
    response = self._get_raw_response(
        self._get_json_headers, self._get_json_response, url, kwargs)
    response = self._parse_response(response)
    self.api_info = response['results']
    return self.api_info

  def get_languages(self):
    response = self._parse_response(self._get_raw_response(
          self._get_json_headers,
          self._get_json_response,
          self._url_for_op('languages'),
          {}
        ))
    return response['languages']

  def _url_for_op(self, ops):
    if not isinstance(ops, list):
      ops = [ops]
    if len(ops) > 1:
      return self._urls.get('multiop')
    else:
      return self._urls.get(ops[0], self._urls.get('multiop'))

  def tag(self, files, model=None, local_ids=None, meta=None, select_classes=None,
          language=None):
    """ Autotag a single data file from an open file object or multiples data files from a list of
    open file objects.

    The only method used on the file object is read() to get the bytes of the compressed
    data representation. Ensure that all file objects are pointing to the beginning of a
    valid data file.

    Args:
      files: a single (file, name) tuple or a list of (file, name) tuples, where file is an
    open file-like object containing the encoded data bytes.
      model: specifies the desired model to use for processing of the data.
      local_ids: a single string identifier or list of string identifies that are useful client
    side. These will be returned in the request to match up results (even though results to come
    back in order).
      meta: a string of any extra information to accompany the request. This has to be a string, so
    if passing structured data, pass a json.dumps(meta) string.
      select_classes: to select only a subset of all possible classes, enter a comma separated list
    of classes you want to predict. Ex: "dog,cat,tree,car,boat"
      language: set the default language using it's two letter (with options -XX variant) ISO 639-1
    code to use for all requests.

    Returns:
      results: an API reponse including the generated tags. See the docs at
      https://developer.clarifai.com/docs/ for more detais.

    Example:
      from py.client import ClarifaiApi
      clarifai_api = ClarifaiApi()
      clarifai_api.tag([open('/path/to/local/image.jpeg'),
                        open('/path/to/local/image2.jpeg')])
    """
    return self._multi_data_op(files, ['tag'], model=model, local_ids=local_ids, meta=meta,
                               select_classes=select_classes,
                               language=language)

  tag_images = tag

  def embed(self, files, model=None, local_ids=None, meta=None):
    """ Embed a single data file from an open file object or multiples data files from a list of
    open file objects.

    The only method used on the file object is read() to get the bytes of the compressed
    data representation. Ensure that all file objects are pointing to the beginning of a
    valid data file.

    Args:
      files: a single (file, name) tuple or a list of (file, name) tuples, where file is an
    open file-like object containing the encoded data bytes.
      model: specifies the desired model to use for processing of the data.
      local_ids: a single string identifier or list of string identifies that are useful client
    side. These will be returned in the request to match up results (even though results to come
    back in order).
      meta: a string of any extra information to accompany the request. This has to be a string, so
    if passing structured data, pass a json.dumps(meta) string.

    Returns:
      results: an API reponse including the generated embeddings. See the docs at
      https://developer.clarifai.com/docs/ for more detais.

    Example:
      from py.client import ClarifaiApi
      clarifai_api = ClarifaiApi()
      clarifai_api.embed([open('/path/to/local/image.jpeg'),
                          open('/path/to/local/image2.jpeg')])
    """
    return self._multi_data_op(files, ['embed'], model=model, local_ids=local_ids, meta=meta)

  embed_images = embed

  def tag_and_embed(self, files, model=None, local_ids=None, meta=None, select_classes=None,
                    language=None):
    """ Tag AND embed data files in one request. Note: each operation is treated separate for
    billing purposes.

    The only method used on the file object is read() to get the bytes of the compressed
    data representation. Ensure that all file objects are pointing to the beginning of a
    valid data file.

    Args:
      files: a single (file, name) tuple or a list of (file, name) tuples, where file is an
    open file-like object containing the encoded data bytes.
      model: specifies the desired model to use for processing of the data.
      local_ids: a single string identifier or list of string identifies that are useful client
    side. These will be returned in the request to match up results (even though results to come
    back in order).
      meta: a string of any extra information to accompany the request. This has to be a string, so
    if passing structured data, pass a json.dumps(meta) string.
      select_classes: to select only a subset of all possible classes, enter a comma separated list
    of classes you want to predict. Ex: "dog,cat,tree,car,boat"
      language: set the default language using it's two letter (with options -XX variant) ISO 639-1
    code to use for all requests.

     Returns:
      results: an API reponse including the generated tags and embeddings. See the docs at
      https://developer.clarifai.com/docs/ for more detais.

    Example:
      from py.client import ClarifaiApi
      clarifai_api = ClarifaiApi()
      clarifai_api.tag_and_embed([open('/path/to/local/image.jpeg'),
                                         open('/path/to/local/image2.jpeg')])
    """
    return self._multi_data_op(files, ['tag','embed'], model=model, local_ids=local_ids, meta=meta,
                               select_classes=select_classes,
                               language=language)

  tag_and_embed_images = tag_and_embed

  def tag_urls(self, urls, model=None, local_ids=None, meta=None, select_classes=None,
               language=None):
    """ Tag data from a url or data from a list of urls.

    Args:
      urls: a single url for the input data to be processed or a list of urls for a set of
    data to be processed. Note: all urls must be publically accessible.
      model: specifies the desired model to use for processing of the data.
      local_ids: a single string identifier or list of string identifies that are useful client
    side. These will be returned in the request to match up results (even though results to come
    back in order).
      meta: a string of any extra information to accompany the request. This has to be a string, so
    if passing structured data, pass a json.dumps(meta) string.
      select_classes: to select only a subset of all possible classes, enter a comma separated list
    of classes you want to predict. Ex: "dog,cat,tree,car,boat"
      language: set the default language using it's two letter (with options -XX variant) ISO 639-1
    code to use for all requests.

    Returns:
      results: an API reponse including the generated tags. See the docs at
      https://developer.clarifai.com/docs/ for more detais.

    Example:
      from py.client import ClarifaiApi
      clarifai_api = ClarifaiApi()
      clarifai_api.tag_urls(['http://www.clarifai.com/img/metro-north.jpg',
                                  'http://www.clarifai.com/img/metro-north.jpg'])

    """
    return self._multi_dataurl_op(urls, ['tag'], model=model, local_ids=local_ids, meta=meta,
                                  select_classes=select_classes,
                                  language=language)

  tag_image_urls = tag_urls

  def embed_urls(self, urls, model=None, local_ids=None, meta=None):
    """ Embed an data from a url or data from a list of urls.

    Args:
      urls: a single url for the input data be processed or a list of urls for a set of
    data to be processed. Note: all urls must be publically accessible.
      model: specifies the desired model to use for processing of the data.
      local_ids: a single string identifier or list of string identifies that are useful client
    side. These will be returned in the request to match up results (even though results to come
    back in order).
      meta: a string of any extra information to accompany the request. This has to be a string, so
    if passing structured data, pass a json.dumps(meta) string.

    Returns:
      results: an API reponse including the generated embeddings. See the docs at
      https://developer.clarifai.com/docs/ for more detais.

    Example:
      from py.client import ClarifaiApi
      clarifai_api = ClarifaiApi()
      clarifai_api.embed_url(['http://www.clarifai.com/img/metro-north.jpg',
                                  'http://www.clarifai.com/img/metro-north.jpg'])

    """
    return self._multi_dataurl_op(urls, ['embed'], model=model, local_ids=local_ids, meta=meta)

  embed_image_urls = embed_urls

  def tag_and_embed_urls(self, urls, model=None, local_ids=None, meta=None, select_classes=None,
                         language=None):
    """ Tag AND Embed data from a url or data from a list of urls.

    Args:
      urls: a single url for the input data to be processed or a list of urls for a set of
    data to be processed. Note: all urls must be publically accessible.
      model: specifies the desired model to use for processing of the data.
      local_ids: a single string identifier or list of string identifies that are useful client
    side. These will be returned in the request to match up results (even though results to come
    back in order).
      meta: a string of any extra information to accompany the request. This has to be a string, so
    if passing structured data, pass a json.dumps(meta) string.
      select_classes: to select only a subset of all possible classes, enter a comma separated list
    of classes you want to predict. Ex: "dog,cat,tree,car,boat"
      language: set the default language using it's two letter (with options -XX variant) ISO 639-1
    code to use for all requests.

    Returns:
      results: an API reponse including the generated tags and embeddings. See the docs at
      https://developer.clarifai.com/docs/ for more detais.

    Example:
      from py.client import ClarifaiApi
      clarifai_api = ClarifaiApi()
      clarifai_api.tag_and_embed_url(['http://www.clarifai.com/img/metro-north.jpg',
                                            'http://www.clarifai.com/img/metro-north.jpg'])
    """
    return self._multi_dataurl_op(urls, ['tag','embed'], model=model, local_ids=local_ids,
                                  meta=meta, select_classes=select_classes,
                                  language=language)

  tag_and_embed_image_urls = tag_and_embed_urls

  def feedback(self, docids=None, urls=None, files=None, add_tags=None,
               remove_tags=None, similar_docids=None, dissimilar_docids=None,
               search_click=None):
    """ Tag AND Embed data from a url or data from a list of urls.

    Args:
      docids: list of docid strings for data already processed by the API.
      files: a single (file, name) tuple or a list of (file, name) tuples, where file is an
    open file-like object containing the encoded data bytes.
      urls: a single url for the input data to be processed or a list of urls for a set of
    data to be processed. Note: all urls must be publically accessible.
      add_tags: If the user believes additioal tags are relavent to the given data, they
    can be provided in the add_tags argument.
      remove_tags: If the user believes tags were are not relavent to the given data, they
    can be provided in the remove_tags argument.
      similar_docids: If there is a notion of similarity between data, this can be fed
    back to the system by providing an input set of docids and a list of docids that are similar to
    the input docids.
      dissimilar_docids: If there is a notion of similarity between data, this can be
    fed back to the system by providing an input set of docids and a list of docids that are
    dissimilar to the input docids.
      search_click: This is useful when showing search results and a user clicks on data
    when the "search_click" tags were used to generate the search results.

    Returns:
      results: OK if everything went well.

    Example:
      from py.client import ClarifaiApi
      clarifai_api = ClarifaiApi()
      clarifai_api.feedback(urls=['http://www.clarifai.com/img/metro-north.jpg',
                                  'http://www.clarifai.com/img/metro-north.jpg'],
                            add_tags='dog,tree',
                            remove_tags='fish')
    """
    if int(docids is not None) + int(urls is not None) + int(files is not None) != 1:
      raise ApiError("Must specify exactly one of docids, urls or files")
    if (int(add_tags is not None) + int(remove_tags is not None) +
        int(similar_docids is not None) + int(dissimilar_docids is not None) +
        int(search_click is not None)) == 0:
      raise ApiError(("Must specify one or more of add_tags, remove_tags, similar_docids, "
                      "dissimilar_docids, search_click."))
    payload = {}
    def add_comma_arg(payload, name, value):
      if not isinstance(value, list):
        value = [value]
      payload[name] = ','.join(value)
    if add_tags:
      add_comma_arg(payload, 'add_tags', add_tags)
    if remove_tags:
      add_comma_arg(payload, 'remove_tags', remove_tags)
    if similar_docids:
      add_comma_arg(payload, 'similar_docids', similar_docids)
    if dissimilar_docids:
      add_comma_arg(payload, 'dissimilar_docids', dissimilar_docids)
    if search_click:
      add_comma_arg(payload, 'search_click', search_click)
    if docids is not None:
      add_comma_arg(payload, 'docids', docids)
      return self._multi_dataurl_op(None, ['feedback'], payload=payload)
    elif urls is not None:
      return self._multi_dataurl_op(urls, ['feedback'], payload=payload)
    else: # must be files
      raise ApiError("Using encoded_data in feedback is not supported in Python client yet.")

  def _resize_image_tuple(self, image_tup):
    """ Resize the (image, name) so that it falls between MIN_SIZE and MAX_SIZE as the minimum
    dimension.
    """
    if self.api_info is None:
      self.get_info()  # sets the image size and other such info from server.
    try:
      MIN_SIZE = self.api_info['min_image_size']
      MAX_SIZE = self.api_info['max_image_size']
      # Will fail here if PIL does not work or is not an image.
      img = Image.open(image_tup[0])
      if img.format not in IGNORE_RESIZE_FORMATS:
        min_dimension = min(img.size)
        max_dimension = max(img.size)
        min_ratio = float(MIN_SIZE) / min_dimension
        max_ratio = float(MAX_SIZE) / max_dimension
        im_changed = False
        # Only resample if min size is > 512 or < 256
        if max_ratio < 1.0:  # downsample to MAX_SIZE
          newsize = (int(round(max_ratio * img.size[0])), int(round(max_ratio * img.size[1])))
          img = img.resize(newsize, Image.BILINEAR)
          im_changed = True
        elif min_ratio > 1.0:  # upsample to MIN_SIZE
          newsize = (int(round(min_ratio * img.size[0])), int(round(min_ratio * img.size[1])))
          img = img.resize(newsize, Image.BICUBIC)
          im_changed = True
        else:  # no changes needed so rewind file-object.
          img.verify()
          image_tup[0].seek(0)
          img = Image.open(image_tup[0])
        # Finally make sure we have RGB images.
        if img.mode != "RGB":
          img = img.convert("RGB")
          im_changed = True
        if im_changed:
          io = StringIO()
          img.save(io, 'jpeg', quality=IM_QUALITY)
          image_tup = (io, image_tup[1])
    except IOError as e:
      logger.warning('Could not open image file: %s, still sending to server.', image_tup[1])
    finally:
      image_tup[0].seek(0)  # rewind file-object to read() below is good to go.
    return image_tup

  def _process_files(self, input_files):
    """ Ensure consistent format for data files from local storage.
    """
    # Handle single file-object as arg.
    if not isinstance(input_files, list):
      input_files = [input_files]
    self._check_batch_size(input_files)
    # Handle unnames images as lists of file objects. Named by index in list.
    files = []
    for i, tup in enumerate(input_files):
      if not isinstance(tup, tuple):
        files.append((tup, str(i)))
        assert hasattr(files[i][0], 'read'), (
            'files[%d] has wrong type: %s. Must be file-object with read method.') % (
                i, type(files[i][0]))
      else:  # already tuples passed in.
        files.append(tup)
    # Resize any images such that the min dimension is in range.
    if CAN_RESIZE:
      for i, image_tup in enumerate(files):
        files[i] = self._resize_image_tuple(image_tup)
    # Return a list of (bytes, name) tuples of the encoded data bytes.
    data = []
    for data_file in files:
      data.append((bytes(data_file[0].read()), data_file[1]))
    return data

  def _check_batch_size(self, data_list):
    """ Ensure the maximum batch size is obeyed on the client side. """
    if self.api_info is None:
      self.get_info()  # sets the image size and other such info from server.
    MAX_BATCH_SIZE = self.api_info['max_batch_size']
    if len(data_list) > MAX_BATCH_SIZE:
      raise ApiError({'status_code':'ALL_ERROR',
                      'status_msg':"request with %d images exceeds max batch size of %d" % (
                        len(data_list), MAX_BATCH_SIZE)})

  def _sanitize_param(self, param, default=''):
    """Convert parameters into a form ready for the wire."""
    if param:
      # Can't send unicode. If it can't encode it as ascii something is wrong with this string
      try:
        param = param.encode('ascii')
      except UnicodeDecodeError:
        return default

      # convert it back to str
      param = param.decode('ascii')

    return param

  def _setup_multi_data(self, ops, num_cases, model=None, local_ids=None, meta=None, language=None,
                        **kwargs):
    """ Setup the data dict to POST to the server. """
    data =  {'op': ','.join(ops)}
    if model:  # use the variable passed into method
      data['model'] = self._sanitize_param(model, 'default')
    elif self._model:  # use the variable passed into __init__
      data['model'] = self._model
    if language:  # use the variable passed into method
      data['language'] = self._sanitize_param(language, default=None)
    elif self.language:  # use the variable passed into __init__
      data['language'] = self.language
    if local_ids:
      if not isinstance(local_ids, list):
        local_ids = [local_ids]
      assert isinstance(local_ids, list)
      assert isinstance(local_ids[0], string_types), "local_ids must each be strings"
      assert len(local_ids) == num_cases, "Number of local_ids must match data"
      data['local_id'] = ','.join(local_ids)
    if meta:
      if isinstance(meta, dict):
        meta_mapped_ascii = json.dumps(meta, ensure_ascii=True)
      else:
        assert isinstance(meta, string_types), "meta arg must be a string or json string"
        meta_mapped_ascii = self._sanitize_param(meta)
      data['meta'] = meta_mapped_ascii
    for (k, v) in iteritems(kwargs):
      if v is not None:
        data[k] = self._sanitize_param(v)
    return data

  def _multi_data_op(self, files, ops, model=None, local_ids=None, meta=None, **kwargs):
    """ Supports both list of tuples (data_file, name) or a list of files where a name will
    be created as the index into the list. """
    media = self._process_files(files)
    url = self._url_for_op(ops)
    data = self._setup_multi_data(ops, len(media), model, local_ids, meta, **kwargs)
    kwargs = {
      'media': media,
      'form_data': data,
    }
    raw_response = self._get_raw_response(
        self._get_multipart_headers, post_data_multipart, url, kwargs)
    return self._parse_response(raw_response)

  def _multi_dataurl_op(self, urls, ops, model=None, local_ids=None, meta=None,
                         payload=None, **kwargs):
    """ If sending image_url or image_file strings, then we can send as json directly instead of the
    multipart form. """
    if urls is not None: # for feedback, this might not be required.
      if not isinstance(urls, list):
        urls = [urls]
      self._check_batch_size(urls)
      if not isinstance(urls[0], string_types):
        raise Exception("urls must be strings")
    data = self._setup_multi_data(ops, len(urls), model, local_ids, meta, **kwargs)
    # Add some addition url specific stuff to data dict:
    if urls is not None:
      data['url'] = urls
    if payload:
      assert isinstance(payload, dict), "Addition payload must be a dict"
      for (k, v) in iteritems(payload):
        data[k] = v
    url = self._url_for_op(ops)
    kwargs = {'data': data}
    raw_response = self._get_raw_response(
        self._get_json_headers, self._get_json_response, url, kwargs)
    return self._parse_response(raw_response)

  def _parse_response(self, response):
    """ Get the raw response form the API and convert into nice Python objects. """
    response = response.decode('utf-8')
    try:
      parsed_response = json.loads(response)
    except Exception as e:
      raise ApiError(e)
    if 'error' in parsed_response:  # needed anymore?
      raise ApiError(parsed_response['error'])
    # Return the true API return value.
    return parsed_response

  def _get_authorization_headers(self):
    access_token = self.get_access_token()
    return {'Authorization': 'Bearer %s' % access_token}

  def _get_multipart_headers(self):
    return self._get_authorization_headers()

  def _get_json_headers(self):
    headers = self._get_authorization_headers()
    headers['Content-Type'] = 'application/json'
    return headers

  def _get_raw_response(self, header_func, request_func, url, kwargs):
    """ Get a raw_response from the API, retrying on TOKEN_EXPIRED errors.

    Args:
      header_func: function to generate dict of HTTP headers for this request, passed as kwarg to
                   request_func.
      request_func: function to make the request, using url and kwargs.
      url: where to send the request.
      kwargs: dict passed as **kwargs to request_func.
    """
    headers = header_func()
    attempts = 3
    while attempts > 0:
      attempts -= 1
      try:
        # Try the request.
        kwargs['headers'] = headers
        raw_response = request_func(url, **kwargs)
        return raw_response
      except urllib2.HTTPError as e:
        response = e.read()  # get error response
        if e.code == 429:
          # Throttled.  Wait for the specified number of seconds.
          wait_secs = e.info().get('X-Throttle-Wait-Seconds', 10)
          try:
            wait_secs = int(wait_secs)
          except ValueError as e:
            wait_secs = 10
          if self.wait_on_throttle:
            logger.error('Throttled. Waiting %d seconds.', wait_secs)
            time.sleep(wait_secs)
          raise ApiThrottledError(response, wait_secs)
        try:
          response = self._parse_response(response)
          if response['status_code'] == 'TOKEN_EXPIRED':
            logger.info('Getting new access token.')
            self.get_access_token(renew=True)
            headers = header_func()
          else:
            raise ApiError(response)  # raise original error
        except ValueError as e2:
          raise ApiError(response) # raise original error.
        except Exception as e2:
          raise ApiError(response) # raise original error.

  def _get_json_response(self, url, method=None, data=None, headers={}):
    """Get the response for sending json dumped data.

    Args:
      url: url of the request.
      data: optional request dict send as json-encoded request body.
      headers: optional dict of HTTP headers.
      method: HTTP request method, e.g. GET, POST, PUT, DELETE. Default (None) uses POST if data
              is present, otherwise GET.
    """
    if data:
      data = json.dumps(data)
      data = bytearray(data, 'utf-8')
    # req = RequestWithMethod(url, method, data, headers)
    # raw_response = urllib2.urlopen(req).read()
    raw_response = urlfetch.fetch(url=url, method=method, headers=headers, payload=data, validate_certificate=False)
    return raw_response

  def tag_image_base64(self, image_file):
    """ NOTE: If possible, you should use avoid this method and use tag_images, which is more
    efficient and supports single or multiple images.  This version base64-encodes the images.

    Autotag an image.

    Args:
      image_file: an open file-like object containing the encoded image bytes. The read
      method is called on this object to get the encoded bytes so it can be a file handle or
      StringIO buffer.

    Returns:
      results: A list of (tag, probability) tuples.

    Example:
      clarifai_api = ClarifaiApi()
      clarifai_api.tag_image_base64(open('/path/to/local/image.jpeg'))
    """
    data = {'encoded_data': base64.encodestring(image_file.read())}
    return self._base64_encoded_data_op(data, 'tag')

  def _base64_encoded_data_op(self, data, op):
    """NOTE: _multi_data_op is more efficient, it avoids the overhead of base64 encoding."""
    data['op'] =  op
    access_token = self.get_access_token()
    url = self._url_for_op(data['op'])
    headers = self._get_json_headers()
    response = self._get_json_response(url, data=data, headers=headers)
    return self._parse_response(response)

class RequestWithMethod(urllib2.Request):
  """Extend urllib2.Request to support methods beyond GET and POST."""
  def __init__(self, url, method, data=None, headers={},
               origin_req_host=None, unverifiable=False):
    self.url = url
    self._method = method
    urllib2.Request.__init__(self, url, data, headers, origin_req_host, unverifiable)

  def get_method(self):
    if self._method:
        return self._method
    else:
        return urllib2.Request.get_method(self)

  def __str__(self):
    return '%s %s' % (self.get_method(), self.url)


def post_data_multipart(url, media=[], form_data={}, headers={}):
  """POST a multipart MIME request with encoded media.

  Args:
    url: where to send the request.
    media: list of (encoded_data, filename) pairs.
    form_data: dict of API params.
    headers: dict of extra HTTP headers to send with the request.
  """
  message = multipart_form_message(media, form_data)
  response = post_multipart_request(url, message, headers=headers)
  return response

def parse_url(url):
  """Return a host, port, path tuple from a url."""
  parsed_url = urlparse(url)
  port = parsed_url.port or 80
  if url.startswith('https'):
    port = 443
  return parsed_url.hostname, port, parsed_url.path

def post_multipart_request(url, multipart_message, headers={}):
  data, headers = message_as_post_data(multipart_message, headers)
  req = RequestWithMethod(url, 'POST', data, headers)
  f = urllib2.urlopen(req)
  response = f.read()
  f.close()
  return response

def crlf_mixed_join(lines):
  """ This handles the mix of 'str' and 'unicode' in the data,
  encode 'unicode' lines into 'utf-8' so the lines will be joinable
  otherwise, the non-unicode lines will be auto converted into unicode
  and triggers exception because the MIME data is not unicode convertible

  Also, Python3 makes this even more complicated.
  """
  # set default encoding to 'utf-8'
  encoding = 'utf-8'

  post_data = bytearray()

  idx = 0
  for line in lines:
    if sys.version_info < (3,0):
      if isinstance(line, unicode):
        line = line.encode(encoding)
      # turn to bytearray
      line_bytes = bytearray(line)

    if sys.version_info >= (3,0):
      if isinstance(line, str):
        line_bytes = bytearray(line, encoding)
      else:
        line_bytes = bytearray(line)

    if idx > 0:
      post_data.extend(b'\r\n')

    post_data.extend(line_bytes)
    idx += 1

  return post_data

def form_data_media(encoded_data, filename, field_name='encoded_data', headers={}):
  """From raw encoded media return a MIME part for POSTing as form data."""
  message = MIMEApplication(encoded_data, 'application/octet-stream', encode_noop, **headers)

  disposition_headers = {
    'name': '%s' % field_name,
    'filename': quote(filename.encode('utf-8')),
  }
  message.add_header('Content-Disposition', 'form-data', **disposition_headers)
  # Django seems fussy and doesn't like the MIME-Version header in multipart POSTs.
  del message['MIME-Version']
  return message

def message_as_post_data(message, headers):
  """Return a string suitable for using as POST data, from a multipart MIME message."""
  # The built-in mail generator outputs broken POST data for several reasons:
  # * It breaks long header lines, and django doesn't like this. Can use Generator.
  # * It uses newlines, not CRLF.  There seems to be no easy fix in 2.7:
  #   http://stackoverflow.com/questions/3086860/how-do-i-generate-a-multipart-mime-message-with-correct-crlf-in-python
  # * It produces the outermost multipart MIME headers, which would need to get stripped off
  #   as form data because the HTTP headers are used instead.
  # So just generate what we need directly.
  assert message.is_multipart()
  # Simple way to get a boundary. urllib3 uses this approach.
  boundary = uuid4().hex
  lines = []
  for part in message.get_payload():
    lines.append('--' + boundary)
    for k, v in part.items():
      lines.append('%s: %s' % (k, v))
    lines.append('')
    data = part.get_payload(decode=True)
    lines.append(data)
  lines.append('--%s--' % boundary)
  post_data = crlf_mixed_join(lines)
  headers['Content-Length'] = str(len(post_data))
  headers['Content-Type'] = 'multipart/form-data; boundary=%s' % boundary
  return post_data, headers

def multipart_form_message(media, form_data={}):
  """Return a MIMEMultipart message to upload encoded media via an HTTP form POST request.

  Args:
    media: a list of (encoded_data, filename) tuples.
    form_data: dict of name, value form fields.
  """
  message = MIMEMultipart('form-data', None)
  if form_data:
    for (name, val) in iteritems(form_data):
      part = Message()
      part.add_header('Content-Disposition', 'form-data', name=name)
      part.set_payload(val)
      message.attach(part)

  for im, filename in media:
    message.attach(form_data_media(im, filename))

  return message

