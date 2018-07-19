from flask import Blueprint

api = Blueprint('api', __name__, url_prefix='/api', template_folder="")


def get_api_blueprint():
    return api
