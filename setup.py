# -*- encoding:utf-8 -*-
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

version = '0.2.1'

setuptools.setup(
    name="pubmed_download",
    version=version,
    author="lin.li",
    author_email="lilinxr@gmail.com",
    description="download pdf by pmid",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/decouples/pubmed_download",
    packages=setuptools.find_packages(),
    install_requires=['setuptools',
                      'pandas',
                      'lxml',
                      'requests',
                      'PyPDF2',
                      'bs4'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
