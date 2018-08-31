from flask import Blueprint

advanced = Blueprint('advanced', __name__, url_prefix='/advanced', template_folder="../advanced_templates")

from . import home
from . import configuration
