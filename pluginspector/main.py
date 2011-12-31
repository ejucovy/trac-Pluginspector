"""
pluginspector:
a plugin for Trac
http://trac.edgewall.org
"""

import inspect
import re

from unzip import unzip

from trac.core import *
from trac.config import *

from trac.admin.api import IAdminCommandProvider

from zope.dottedname.resolve import resolve

class Pluginspector(Component):

    implements(IAdminCommandProvider)

    pkg_src_dir = Option("pluginspector", 'pkg_src_dir', './src', """Where I can find source files for Trac and plugins""")

    ### methods for IAdminCommandProvider

    """Extension point interface for adding commands to the console
    administration interface `trac-admin`.
    """

    def try_to_find_package(self, object):
        module = resolve(object.__module__)
        file = module.__file__
        assert file.startswith(self.pkg_src_dir)
        dir, path = file[len(self.pkg_src_dir):].split("/", 1)
        setup_py = os.path.join(self.pkg_src_dir, dir, "setup.py")
        assert os.path.exists(setup_py), "No file %s exists" % setup_py
        with open(setup_py) as f:
            contents = f.read()
        contents = contents.replace("setup(", "metadata=dict(")
        ctx = {}
        exec contents in ctx
        assert 'metadata' in ctx, "Problem running %s" % setup_py
        return ctx['metadata']['name']

    def get_data(self):
        packages = {}

        interfaces = {}
        for interface in Interface.__subclasses__():
            data = self._base_data(interface)
            data['implemented_by'] = []
            interfaces[data['name']] = data
            data['package'] = self.try_to_find_package(interface)
            packages.setdefault(data['package'], 
                                {'interfaces': [],
                                 'components': [],
                                 })['interfaces'].append(data['name'])

        components = {}
        for component in Component.__subclasses__():
            if hasattr(component, '_implements'):
                impl = [interfaces['%s.%s' % (i.__module__, i.__name__)]
                        for i in component._implements]
            else:
                impl = []
            data = self._base_data(component)
            data['_extension_points'] = self._extension_points(component)
            data['implements'] = [i['name'] for i in impl]
            for imp in impl:
                imp['implemented_by'].append(data['name'])
            components[data['name']] = data
            data['package'] = self.try_to_find_package(component)
            packages.setdefault(data['package'], 
                                {'interfaces': [],
                                 'components': [],
                                 })['components'].append(data['name'])

        return components, interfaces, packages

    def write_zipfile(self, dir):
        import os
        import tempfile
        from zipfile import ZipFile
        import tempita

        fd, zip_filename = tempfile.mkstemp(prefix="trac_pluginspector",
                                            suffix=".zip")
        zipfile = ZipFile(zip_filename, 'w')
        try:
            components, interfaces, packages = self.get_data()

            tmpl = """---
layout: main
title: {{name}}
---
<h1 class="name">{{name}}</h1>
<h2 class="package">In package <a href="packages/{{package}}/index.html">{{package}}</a></h2>

{{if doc}}
<pre class="doc">{{doc}}</pre>
{{else}}
<p><em>No documentation available</em></p>
{{endif}}
<h2>Implemented by:</h2>
<ul>
{{for component in implemented_by}}
  <li><a href="components/{{component}}/index.html">{{component}}</a></li>
{{endfor}}
</ul>
"""
            tmpl = tempita.HTMLTemplate(tmpl)
            for name in interfaces:
                html = tmpl.substitute(interfaces[name])
                zipfile.writestr("interfaces/%s/index.html" % name, html)

            tmpl = """---
layout: main
title: {{name}}
---
<h1 class="name">{{name}}</h1>
<h2 class="package">In package <a href="packages/{{package}}/index.html">{{package}}</a></h2>

<pre class="doc">{{doc}}</pre>

<h2>Implements:</h2>
<ul>
{{for interface in implements}}
  <li><a href="interfaces/{{interface}}/index.html">{{interface}}</a></li>
{{endfor}}
</ul>
"""
            tmpl = tempita.HTMLTemplate(tmpl)

            for name in components:
                html = tmpl.substitute(components[name])
                zipfile.writestr("components/%s/index.html" % name, html)

            tmpl = """---
layout: main
title: {{name}}
---
<h1 class="name">{{name}}</h1>

{{if doc}}
<pre class="doc">{{doc}}</pre>
{{else}}
<p><em>No documentation available</em></p>
{{endif}}
<h2>Interfaces Declared:</h2>
<ul>
{{for interface in interfaces}}
  <li><a href="interfaces/{{interface}}/index.html">{{interface}}</a></li>
{{endfor}}
</ul>
<h2>Components Provided:</h2>
<ul>
{{for component in components}}
  <li><a href="components/{{component}}/index.html">{{component}}</a></li>
{{endfor}}
</ul>
"""
            tmpl = tempita.HTMLTemplate(tmpl)
            for package in packages:
                ctx = dict(name=package,
                           interfaces=packages[package]['interfaces'],
                           components=packages[package]['components'],
                           doc=None,
                           )
                html = tmpl.substitute(ctx)
                zipfile.writestr("packages/%s/index.html" % package, html)

            tmpl = """---
layout: main
title: Index
---
<h1 class="name">Trac Docs</h1>

<h2>Packages</h2>
<ul>
{{for package in packages}}
  <li><a href="packages/{{package}}/index.html">{{package}}</a></li>
{{endfor}}
</ul>

<h2>Interfaces</h2>
<ul>
{{for interface in interfaces}}
  <li><a href="interfaces/{{interface}}/index.html">{{interface}}</a></li>
{{endfor}}
</ul>

<h2>Components</h2>
<ul>
{{for component in components}}
  <li><a href="components/{{component}}/index.html">{{component}}</a></li>
{{endfor}}
</ul>
"""
            tmpl = tempita.HTMLTemplate(tmpl)
            html = tmpl.substitute(locals())
            zipfile.writestr("index.html", html)

        finally:
            zipfile.close()

        unzipper = unzip()
        unzipper.verbose = False
        unzipper.extract(zip_filename, dir)
        
        os.unlink(zip_filename)

            

    # Internal methods

    def _base_data(self, cls):
        return {
            'name': '%s.%s' % (cls.__module__, cls.__name__),
            'type': '%s:%s' % (cls.__module__, cls.__name__),
            'doc': inspect.getdoc(cls)
        }


    def _extension_points(self, cls):
        xp = [(m, getattr(cls, m)) for m in dir(cls) if not m.startswith('_')]
        return [{'name': name,
                 'interface': self._base_data(m.interface)}
                for name, m in xp if isinstance(m, ExtensionPoint)]


    def get_admin_commands(self):
        """Return a list of available admin commands.
        
        The items returned by this function must be tuples of the form
        `(command, args, help, complete, execute)`, where `command` contains
        the space-separated command and sub-command names, `args` is a string
        describing the command arguments and `help` is the help text. The
        first paragraph of the help text is taken as a short help, shown in the
        list of commands.
        
        `complete` is called to auto-complete the command arguments, with the
        current list of arguments as its only argument. It should return a list
        of relevant values for the last argument in the list.
        
        `execute` is called to execute the command, with the command arguments
        passed as positional arguments.
        """
        return [
            ('pluginspector list', '', 'list data', None, self.get_data),
            ('pluginspector html', 'dir', 'generate html', None, self.write_zipfile),
            ]
