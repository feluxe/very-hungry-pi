import pypandoc
from setuptools import setup, find_packages
from codecs import open
import ruamel.yaml as yaml

try:
    long_description = pypandoc.convert('README.md', 'rst')

except(IOError, ImportError):
    long_description = open('README.md').read()

config = {}

with open('Project', 'r') as stream:
    config = yaml.safe_load(stream.read())


setup(
    name=config['proj_pypi_name'],
    version=config['version'],
    author=config['author'],
    author_email=config['author_email'],
    maintainer=config['maintainer'],
    maintainer_email=config['maintainer_email'],
    url=config['url'],
    description=config['description'],
    long_description=long_description,
    download_url=config['url'] + '/tarball/' + config['version'],
    license=config['license'],
    keywords=config['keywords'],

    include_package_data=True,
    platforms=config['pypi']['platforms'],
    classifiers=config['pypi']['classifiers'],
    install_requires=config['pypi']['install_requires'],
    packages=find_packages(where='.', exclude=(
    'tests', 'tests.*', 'venv-vhpi', 'venv-vhpi.*')),
    package_dir=config['pypi']['package_dir'],
    package_data=config['pypi']['package_data'],
    data_files=config['pypi']['data_files'],
    entry_points=config['pypi']['entry_points'],
    tests_require=config['pypi']['tests_require']
)
