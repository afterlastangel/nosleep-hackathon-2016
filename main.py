import logging
from werkzeug import secure_filename
import cloudstorage as gcs


from flask import Flask, request, jsonify
from google.appengine.ext import ndb

"""`main` is the top level module for your Flask application."""
app = Flask(__name__)
BUCKET_NAME = "nosleep-1469844138323.appspot.com"


class PostModel(ndb.Model):
    filename = ndb.StringProperty()
    facebook_user_id = ndb.StringProperty()
    meta = ndb.JsonProperty()

    def get_public_url(self):
        return 'https://storage.googleapis.com/' + BUCKET_NAME + '/' + self.filename  # noqa


@app.route('/')
def hello():
    """Return a friendly HTTP greeting."""
    return 'Hello World! from Nosleep!!!'


def get_meta_from_image_url(image_url):
    result = {}
    result['message'] = 'this is demo config'
    result['feeling'] = ''
    result['place'] = ''
    result['keywords'] = ['']
    return result


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
