from setuptools import setup, find_packages

setup(
    name='hltv_async_api',
    version='0.9.0b0',
    author='akimerslys',
    author_email='akimslys2003@gmail.com',
    description='An unofficial asynchronous HLTV API Wrapper for Python\nUse only in non-commercial purposes.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/akimerslys/hltv-async-api',
    packages=find_packages(),

    install_requires=[
        'aiohttp',
        'pytz',
        'lxml',
        'beautifulsoup4',
    ],

    extras_require={
        'sync': [
            'requests',
        ],
        'beta': [
            'uvloop',
        ]
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)