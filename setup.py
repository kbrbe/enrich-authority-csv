import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "enrich_authority_csv",
    version = "0.3.0",
    author = "Sven Lieber",
    author_email = "Sven.Lieber@kbr.be",
    description = ("A python script that uses SRU APIs to complete a CSV file with missing data based on an available identifier column that can be looked up in the SRU API"),
    license = "AGPL-3.0",
    keywords = "csv authority-control isni authority-files enriching",
    packages=setuptools.find_packages(),
    long_description=read('README.md')
)
