from flask import Blueprint

advanced = Blueprint('advanced', __name__, url_prefix='/advanced', template_folder="../advanced_templates")


def get_advanced_blueprint():
    return advanced
