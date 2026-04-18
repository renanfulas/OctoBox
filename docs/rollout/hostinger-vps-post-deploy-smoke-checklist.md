<!--
ARQUIVO: checklist de smoke pos-deploy da Hostinger VPS.

TIPO DE DOCUMENTO:
- checklist operacional

AUTORIDADE:
- alta para liberar o primeiro cliente

DOCUMENTO PAI:
- [hostinger-vps-production-deploy.md](hostinger-vps-production-deploy.md)

QUANDO USAR:
- logo apos cada deploy em VPS
- antes do go-live do primeiro cliente
-->

# Checklist de smoke pos-deploy na Hostinger VPS

## Objetivo

Confirmar que o deploy nao apenas subiu, mas ficou operacional.

## HTTP e health

- [ ] `/api/v1/health/` responde `200`
- [ ] `runtime_slug` do health esta coerente
- [ ] `runtime_namespace` do health esta coerente

## Fluxos centrais

- [ ] `/login/` responde sem `500`
- [ ] login funciona com usuario valido
- [ ] `/dashboard/` abre
- [ ] `/alunos/` abre
- [ ] `/operacao/` abre
- [ ] `/grade-aulas/` abre

## Front-end

- [ ] CSS carregou
- [ ] JS carregou
- [ ] nao ha erro visivel de asset

## Admin e seguranca

- [ ] admin responde apenas pelo caminho privado
- [ ] `/admin/` nao e o caminho real
- [ ] Cloudflare esta ativo na frente do dominio
- [ ] cabecalhos de proxy nao quebraram POST nem login
- [ ] respostas trazem `cf-ray` quando o proxy estiver ativo
- [ ] HTML autenticado nao esta vindo de cache indevido

## Runtime e servicos

- [ ] `systemctl status octobox-gunicorn` verde
- [ ] `systemctl status nginx` verde
- [ ] `systemctl status postgresql` verde
- [ ] `systemctl status redis-server` verde

## Logs e saude da maquina

- [ ] `journalctl -u octobox-gunicorn -n 100` sem erro recorrente
- [ ] `journalctl -u nginx -n 100` sem erro recorrente
- [ ] disco com folga
- [ ] memoria com folga

## Backup e rollback

- [ ] backup mais recente existe
- [ ] caminho do backup esta registrado
- [ ] restore ja foi ensaiado em banco isolado

## Gate final

So liberar para o primeiro cliente se todos os blocos acima estiverem verdes ao mesmo tempo.

## Regua de performance depois do proxy

- [ ] repetir a medicao autenticada de `/financeiro/`
- [ ] repetir a medicao autenticada de `/alunos/`
- [ ] comparar `elapsed_ms`, `req-total` e `view_total_ms`
- [ ] confirmar que o gap do primeiro hit caiu ou, no minimo, nao piorou
