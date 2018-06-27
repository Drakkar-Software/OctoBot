from flask import render_template, Blueprint

advanced = Blueprint('advanced', __name__, url_prefix='/advanced', template_folder="advanced_template")


def get_advanced_blueprint():
    return advanced


@advanced.route("/")
@advanced.route("/home")
def home():
    return render_template('advanced_index.html')

