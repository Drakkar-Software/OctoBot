from flask import make_response


def get_rest_reply(json_message, code=200, content_type="application/json"):
    resp = make_response(json_message, code)
    resp.headers['Content-Type'] = content_type
    return resp
