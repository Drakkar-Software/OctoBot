from flask import render_template

from interfaces.web import server_instance


@server_instance.route("/")
@server_instance.route("/home")
def home():
    return render_template('index.html')


@server_instance.route("/config")
def config():
    return render_template('config.html')


@server_instance.route("/portfolio")
def portfolio():
    return render_template('portfolio.html')
