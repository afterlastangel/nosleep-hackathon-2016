import logging
import uuid
from werkzeug import secure_filename
import cloudstorage as gcs
from search_api import (
    process_upload_dictionary, process_delete_index, query_index)

import random
from generator import generate
from image_processing import ImageProccessing
from flask import Flask, request, jsonify
from google.appengine.ext import ndb

"""`main` is the top level module for your Flask application."""
app = Flask(__name__)
BUCKET_NAME = "nosleep-1469844138323.appspot.com"


class PostModel(ndb.Model):
    filename = ndb.StringProperty()
    facebook_user_id = ndb.StringProperty()
    message = ndb.StringProperty()
    meta = ndb.JsonProperty()
    feeling = ndb.StringProperty()

    def get_public_url(self):
        return 'https://storage.googleapis.com/' + BUCKET_NAME + '/' + self.filename  # noqa


@app.route('/')
def hello():
    """Return a friendly HTTP greeting."""
    return 'Hello World! from Nosleep!!!'


def get_meta_from_image_url(image_url):
    ip = ImageProccessing(image_url)
    ip_result = ip.execute()
    result = {}
    keywords = ip_result['keywords']
    print keywords
    messages = query_index(
        'shakespeare', random.sample(keywords, 3))
    if len(messages) > 0:
        message = random.choice(messages)
    else:
        message = random.choice(generate(keywords, None, random.randint(2,4)))
    result['message'] = message
    result['feeling'] = ''
    result['place'] = ''
    result['keywords'] = keywords
    return result


@app.route('/v1/images', methods=['GET'])
def get_list_posted_image():
    facebook_user_id = request.args.get('user_id')
    facebook_token = request.args.get('token')
    # TODO: Check valid facebok_user_id token
    if facebook_user_id is None:
        return jsonify([])
    images = PostModel.query(
        PostModel.facebook_user_id==facebook_user_id).fetch()
    results = []
    for image in images:
        results += [
            {
                'image_url': image.get_public_url(),
                'message': image.message,
                'feeling': image.feeling,
            }]
    return jsonify(results)


@app.route('/v1/dictionary', methods=['POST'])
def upload_dictionary():
    index_name = request.args.get('index_name')
    if request.method == 'POST':
        file = request.files['file']
        process_upload_dictionary(index_name, file)
    return jsonify({'success': True})


@app.route('/v1/search', methods=['GET'])
def search():
    query = request.args.get('query')
    index_name = request.args.get('index_name')
    if request.method == 'GET':
        keywords = query.split(' ')
        results = query_index(index_name, keywords)
    return jsonify(results)

@app.route('/v1/dictionary', methods=['DELETE'])
def delete_dictionary():
    index_name = request.args.get('index_name')
    if request.method == 'DELETE':
        process_delete_index(index_name)
    return jsonify({'success': True})


@app.route('/v1/cognitive/image', methods=['POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        extension = secure_filename(file.filename).rsplit('.', 1)[1]
        options = {}
        options['retry_params'] = gcs.RetryParams(backoff_factor=1.1)
        options['content_type'] = 'image/' + extension
        bucket_name = BUCKET_NAME
        filename = file.filename
        """
        # image_id = uuid.uuid1()
        # filename = str(image_id) + '.' + extension
        """
        facebook_user_id = request.args.get('user_id')
        path = '/' + bucket_name + '/' + str(
            secure_filename(filename))
        if file:
            try:
                with gcs.open(path, 'w', **options) as f:
                    f.write(file.stream.read())  # instead of f.write(str(file))
                post = PostModel(
                    filename=filename,
                    facebook_user_id=facebook_user_id)
                post_key = post.put()

                result = get_meta_from_image_url(post.get_public_url())
                message = result['message']
                feeling = result['feeling']
                place = result['place']
                keywords = result['keywords']
                post.meta = result
                post.message = message
                post.put()
                return jsonify(
                    {"success": True,
                     "post_id": post_key.urlsafe(),
                     "image_url": post.get_public_url(),
                     "message": message,
                     "feeling": feeling,
                     "place": place,
                     "keywords": keywords}
                )
            except Exception as e:
                logging.exception(e)
                return jsonify({"success": False})


@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, Nothing at this URL.', 404


@app.errorhandler(500)
def application_error(e):
    """Return a custom 500 error."""
    return 'Sorry, unexpected error: {}'.format(e), 500
