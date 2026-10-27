"""Configuracao do Gunicorn lida automaticamente da pasta de trabalho.

A unit (infra/hostgator-vps/systemd/octobox-gunicorn.service) roda em
/srv/octobox/app, entao o deploy aplica este arquivo so com o restart.

O formato padrao grava a linha da requisicao inteira ("%(r)s") e o referer:
o token do link magico (/treinos/login?token=...) ia parar no journal.
"%(U)s" e o caminho sem query string; o referer sai do log.
"""

access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(m)s %(U)s %(H)s" %(s)s %(b)s "%(a)s"'
