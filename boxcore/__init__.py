"""
ARQUIVO: marcador do pacote legado boxcore.

POR QUE ELE EXISTE:
- Mantem a pasta boxcore como pacote Python da ancora historica de estado do Django.

O QUE ESTE ARQUIVO FAZ:
1. Preserva o namespace historico exigido por app_label, admin e migrations antigas.

PONTOS CRITICOS:
- Nao deve voltar a ser tratado como namespace padrao de runtime para codigo novo.
"""
