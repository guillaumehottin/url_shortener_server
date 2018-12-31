from url_shortener import UrlShortener
from flask import Flask, redirect
from flask_restful import reqparse, abort, Api, Resource
import datetime
import os
from pymongo import MongoClient

application = Flask(__name__)
application.debug = True
api = Api(application)

API_KEY = os.environ.get('URL_SHORTENER_API_KEY')
MONGO_URI = os.environ.get('MONGO_URI')
MONGO_USER = os.environ.get('MONGO_USER')
MONGO_PASSWORD = os.environ.get('MONGO_PASSWORD')
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME')
SHORT_URL_LENGTH = int(os.environ.get('SHORT_URL_LENGTH'))
SHORT_URL_POSSIBLE_CHARACTERS = os.environ.get('SHORT_URL_POSSIBLE_CHARACTERS').split(',')


# MONGO CONNECTIONS
def connect_to_mongo(mongo_uri, mongo_user, mongo_password):
    return MongoClient(mongo_uri, username=mongo_user, password=mongo_password)


if API_KEY is None:
    print("No API key set")


mongo_client = connect_to_mongo(MONGO_URI, MONGO_USER, MONGO_PASSWORD)


def abort_if_short_url_doesnt_exist(url_shortener, short_url):
    if not url_shortener.db_url_entry_exists(short_url):
        abort(404, message="Short URL {0} doesn't exist".format(short_url))


def abort_if_url_not_provided(url):
    if url is None:
        abort(422, message="No URL was provided")


def abort_if_wrong_api_key(api_key):
    if api_key != API_KEY:
        abort(403, message="Wrong API key provided")


parser = reqparse.RequestParser()
parser.add_argument('url')
parser.add_argument('name')
parser.add_argument('expiry_date')
parser.add_argument('api_key')


class ShortUrl(Resource):

    def get(self, url_type, short_url):
        url_shortener = UrlShortener(mongo_client, MONGO_DB_NAME, url_type, SHORT_URL_POSSIBLE_CHARACTERS,
                                     SHORT_URL_LENGTH)
        abort_if_short_url_doesnt_exist(url_shortener, short_url)
        url_shortener.add_click_date(short_url)
        return redirect(url_shortener.get_db_url_entry(short_url)["url"], code=302)


class ManageShortUrlList(Resource):

    def get(self, url_type):
        args = parser.parse_args()
        api_key = args['api_key']
        abort_if_wrong_api_key(api_key)
        url_shortener = UrlShortener(mongo_client, MONGO_DB_NAME, url_type, SHORT_URL_POSSIBLE_CHARACTERS,
                                     SHORT_URL_LENGTH)
        return url_shortener.get_all_db_url_entry()

    def post(self, url_type):
        args = parser.parse_args()
        url = args['url']
        name = args['name']
        expiry_date = args['expiry_date']
        api_key = args['api_key']
        if expiry_date is not None:
            expiry_date = datetime.strptime("%Y-%m-%dT%H:%M:%S")
        abort_if_wrong_api_key(api_key)
        abort_if_url_not_provided(url)
        url_shortener = UrlShortener(mongo_client, MONGO_DB_NAME, url_type, SHORT_URL_POSSIBLE_CHARACTERS,
                                     SHORT_URL_LENGTH)
        short_url = url_shortener.generate_and_insert_short_url(url, name, expiry_date)
        return short_url, 201


class ManageShortUrl(Resource):

    def get(self, url_type, short_url):
        args = parser.parse_args()
        api_key = args['api_key']
        abort_if_wrong_api_key(api_key)
        url_shortener = UrlShortener(mongo_client, MONGO_DB_NAME, url_type, SHORT_URL_POSSIBLE_CHARACTERS,
                                     SHORT_URL_LENGTH)
        abort_if_short_url_doesnt_exist(url_shortener, short_url)
        return url_shortener.get_db_url_entry(short_url), 200

    def delete(self, url_type, short_url):
        args = parser.parse_args()
        api_key = args['api_key']
        abort_if_wrong_api_key(api_key)
        url_shortener = UrlShortener(mongo_client, MONGO_DB_NAME, url_type, SHORT_URL_POSSIBLE_CHARACTERS,
                                     SHORT_URL_LENGTH)
        abort_if_short_url_doesnt_exist(url_shortener, short_url)
        url_shortener.delete_db_url_entry(short_url)
        return '', 204


class ManageAllCategories(Resource):

    def get(self):
        args = parser.parse_args()
        api_key = args['api_key']
        abort_if_wrong_api_key(api_key)
        url_shortener = UrlShortener(mongo_client, MONGO_DB_NAME, '', SHORT_URL_POSSIBLE_CHARACTERS,
                                     SHORT_URL_LENGTH)
        return url_shortener.get_all_categories(), 200

##
## Actually setup the Api resource routing here
##
api.add_resource(ManageShortUrlList, '/manage/<url_type>')
api.add_resource(ShortUrl, '/<url_type>/<short_url>')
api.add_resource(ManageAllCategories, '/manage/categories')
api.add_resource(ManageShortUrl, '/manage/<url_type>/<short_url>')

if __name__ == '__main__':
    application.run(host='0.0.0.0')