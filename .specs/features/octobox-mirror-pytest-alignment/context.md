# Contexto

O `pytest.ini` raiz aponta para `config.settings.test`.

O espelho `OctoBox/` ainda funciona como segundo projeto Django detectavel, mas nao possui `config/settings/test.py`, o que quebra a inicializacao do `pytest-django` quando a descoberta cai dentro dele.
