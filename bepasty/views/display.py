# Copyright: 2013 Bastian Blank <bastian@waldi.eu.org>
# License: BSD 2-clause, see LICENSE for details.

import errno
import time

from flask import current_app, render_template, Markup, request, url_for, abort
from flask.views import MethodView
from werkzeug.exceptions import NotFound, Forbidden
from pygments import highlight
from pygments.lexers import get_lexer_for_mimetype
from pygments.formatters import HtmlFormatter


from ..utils.name import ItemName
from ..utils.permissions import *
from . import blueprint
from .filelist import file_infos


class DisplayView(MethodView):
    def get(self, name):
        if not may(READ):
            raise Forbidden()
        try:
            item = current_app.storage.openwrite(name)
        except (OSError, IOError) as e:
            if e.errno == errno.ENOENT:
                raise NotFound()
            raise

        with item as item:
            if not item.meta['complete']:
                error = 'Upload incomplete. Try again later.'
            else:
                error = None
            if error:
                return render_template('error.html', heading=item.meta['filename'], body=error), 409

            if item.meta['locked'] and not may(ADMIN):
                raise Forbidden()

            def read_data(item):
                # reading the item for rendering is registered like a download
                data = item.data.read(item.data.size, 0)
                item.meta['timestamp-download'] = int(time.time())
                return data

            ct = item.meta['type']
            if ct.startswith('text/x-bepasty-'):
                # special bepasty items
                if ct == 'text/x-bepasty-list':
                    names = read_data(item).splitlines()
                    files = sorted(file_infos(names), key=lambda f: f['filename'])
                    rendered_content = Markup(render_template('filelist_tableonly.html', files=files))
                else:
                    rendered_content = u"Can't render this content type."
            elif ct.startswith('text/'):
                code = read_data(item).decode('utf-8')  # TODO we don't have the coding in metadata
                lexer = get_lexer_for_mimetype(ct)
                formatter = HtmlFormatter(linenos='table', lineanchors="L", anchorlinenos=True)
                rendered_content = Markup(highlight(code, lexer, formatter))
            elif ct.startswith('image/'):
                src = url_for('bepasty.download', name=name)
                rendered_content = Markup(u'<img src="%s" width="800">' % src)
            elif ct.startswith('audio/'):
                src = url_for('bepasty.download', name=name)
                alt_msg = u'html5 audio element not supported by your browser.'
                rendered_content = Markup(u'<audio controls src="%s">%s</audio>' % (src, alt_msg))
            elif ct.startswith('video/'):
                src = url_for('bepasty.download', name=name)
                alt_msg = u'html5 video element not supported by your browser.'
                rendered_content = Markup(u'<video controls src="%s">%s</video>' % (src, alt_msg))
            elif ct == 'application/pdf':
                src = url_for('bepasty.inline', name=name)
                link_txt = u'Click to see PDF'
                rendered_content = Markup(u'<a href="%s">%s</a>' % (src, link_txt))
            else:
                rendered_content = u"Can't render this content type."
            return render_template('display.html', name=name, item=item,
                                   rendered_content=rendered_content)


blueprint.add_url_rule('/<itemname:name>', view_func=DisplayView.as_view('display'))
