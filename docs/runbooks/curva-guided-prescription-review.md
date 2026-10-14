# Curva: revisão de séries guiadas em programas ativos

## Fluxo do treinador

1. No admin, abra **Assinaturas Curva**, selecione uma conta ativa com `plan_slug` exclusivo e use **Criar rascunho guiado do programa ativo**.
2. Abra o rascunho pelo link da confirmação. A versão publicada continua servindo o treino até a aprovação.
3. Confira **cada movimento** e os alertas de restrições físicas da anamnese, sobretudo contagem mínima/máxima, reps, RIR, descanso e regra de carga. A proposta interpreta apenas o texto reconhecível; os percentuais Prep 40–55% e Feeder 60–80% e o descanso de 90 segundos são sugestões para o treinador decidir, não dados inferidos do aluno.
4. Movimentos ambíguos permanecem com o texto original. O aluno ainda pode fazer registro livre. Para torná-los guiados, preencha `guided_prescription` manualmente e valide o JSON.
5. Use **Aprovar e publicar** no rascunho somente após revisão. Isso cria uma nova versão; a versão anterior permanece guardada. A publicação pode enfileirar avisos ao aluno conforme as inscrições existentes.

O rascunho guarda `base_program`. Se outro programa for ativado antes da aprovação, a aprovação é recusada. Rejeite o rascunho antigo e crie outro a partir da versão ativa. O sistema também recusa a cópia quando o mesmo `plan_slug` pertence a mais de uma assinatura: resolva a vinculação antes de publicar para não atingir outra conta.

## Homologação operacional

Comece por uma conta de teste, confira o payload e a prévia no admin, publique uma única versão aprovada e conclua um treino no PWA instalado. Compare a sessão e as séries realizadas com o analytics e a outbox de conclusão. Uma sugestão de kg ou uma série planejada nunca conta como série realizada. Para histórico já publicado, a revisão é individual; não há migração automática em massa.
