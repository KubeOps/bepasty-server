from flask import current_app, render_template, request
from flask.views import MethodView

from ..utils.name import ItemName
from . import blueprint


class DisplayView(MethodView):
    def get(self, name):
        n = ItemName.parse(name)

        with current_app.storage.open(n) as item:
            return render_template('display.html', item=item)


blueprint.add_url_rule('/<name>', view_func=DisplayView.as_view('display'))