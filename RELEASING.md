# Releasing the CrossGram clld app

```shell
git clone https://github.com/clld/crossgram
git clone --depth 1 https://github.com/crossgram/crossgram-internal
git clone --branch v1.1 --depth 1 https://github.com/clld/grammaticon-data
cd crossgram
pip install -e .[test]
```

```shell
clld initdb development.ini
```

```shell
pytest
```

Store the tested requirements:
```shell
pip freeze > requirements.txt
```

Store a db dump:
```shell
pg_dump -xO crossgram > crossgram.sql
zip crossgram.sql.zip crossgram.sql
rm crossgram.sql
```

