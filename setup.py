from setuptools import setup, find_packages

setup(
    name='hltv-aio',
    version='0.1.0',
    author='Akim Slys',
    author_email='akimslys2003@gmail.com',
    description='Hltv-aio: An unofficial asynchronous HLTV API Wrapper for Python',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/akimerslys/aiohltv',
    packages=find_packages(),
    install_requires=[
        'aiohttp==3.9.3',
        'aiosignal==1.3.1',
        'attrs==23.2.0',
        'beautifulsoup4==4.12.3',
        'frozenlist==1.4.1',
        'idna==3.6',
        'multidict==6.0.5',
        'lxml==5.2.0',
        'soupsieve==2.5',
        'yarl==1.9.4',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)