from setuptools import setup, find_packages


setup(
    name='crossgram',
    version='0.0',
    description='crossgram',
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author='',
    author_email='',
    url='',
    keywords='web pyramid pylons',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # shut up pip
        'sqlalchemy<2.0',
        'cldfcatalog',
        'clld>=11.3',
        'clldmpg>=4.2',
        'clld-glottologfamily-plugin',
        'gitpython',
        'psycopg2',
        'pyglottolog',
    ],
    extras_require={
        'dev': ['flake8', 'waitress', 'cldfzenodo'],
        'test': [
            'mock',
            'pytest>=3.1',
            'pytest-clld',
            'pytest-mock',
            'pytest-cov',
            'coverage>=4.2',
            'selenium',
            'zope.component>=3.11.0',
        ],
    },
    test_suite="crossgram",
    entry_points="""\
    [paste.app_factory]
    main = crossgram:main
""")
