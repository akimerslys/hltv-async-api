from setuptools import setup, find_packages

setup(
    name='hltv_async_api',
    version='0.5.0',
    author='akimerslys',
    author_email='akimslys2003@gmail.com',
    description='Hltv-aio: An unofficial asynchronous HLTV API Wrapper for Python',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/akimerslys/aiohltv',
    packages=find_packages(),

    install_requires=[
        'aiohttp',
        'pytz',
        'lxml',
        'beautifulsoup4',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)