from setuptools import find_packages, setup

version='0.0'

setup(name='pluginspector',
      version=version,
      description="",
      author='',
      author_email='',
      url='',
      keywords='trac plugin',
      license="",
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests*']),
      include_package_data=True,
      package_data={ 'pluginspector': ['templates/*', 'htdocs/*'] },
      zip_safe=False,
      install_requires=["Tempita", "zope.dottedname"],
      entry_points = """
      [trac.plugins]
      pluginspector = pluginspector
      """,
      )

