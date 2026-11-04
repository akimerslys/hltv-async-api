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
    python_requires='>=3.10',

    install_requires=[
        'aiohttp',
        'pytz',
        'lxml',
        'beautifulsoup4',
        'fake-useragent',
        'Brotli',
    ],

    extras_require={
        'sync': [
            'requests',
        ],
        'selenium': [
            'selenium>=4.0',
            'undetected-chromedriver>=3.5',
            'setuptools',  # undetected-chromedriver imports distutils, removed from Python 3.12+
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