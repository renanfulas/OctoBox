"""
ARQUIVO: namespace tecnico de relatorios e exportacoes.

POR QUE ELE EXISTE:
- Separa a entrega de exportacao HTTP e os builders puros de relatorio das camadas historicas do catalogo.

O QUE ESTE ARQUIVO FAZ:
1. Reserva a fronteira tecnica de reporting.
2. Permite reaproveitar exportacoes sem acoplar ao catalogo legado.

PONTOS CRITICOS:
- Nesta fase este pacote nao e um app Django; ele e uma fronteira tecnica de suporte.
"""