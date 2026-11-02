# Retomada: campanha seriada e PDFs adiados

O pesquisador adiou explicitamente os PDFs e priorizou planejar a campanha
Gurobi/HiGHS para permitir uma pausa após a submissão. A PR144 permanece em
313f3af8, com as duas observações h300 de uma thread aceitas. Originais e
planilha/grafo/matriz/cenários permanecem preservados. develop não foi alterada.

O plano enumera 95 jobs novos: 88 soluções, seis coletas/gates e fechamento.
As sequências contêm 44 soluções por solver, no máximo duas simultâneas.
Os quatro pilotos por população liberam as etapas, com headroom amostrado
de 20%, sem selecionar sucesso apenas pelo gap. São dez pilotos ainda não
executados e 78 outras soluções. Duas células consumidas ficam fora da nova
submissão. A verificação estática conferiu cobertura, parâmetros, topologia
do grafo e ordenação total por solver.

O NPAD informou MaxSubmitJobsPU=100, MaxJobsPU=10 e fila vazia; a proposta
reserva cinco posições e não substitui limites herdados nem quota pessoal.
Mantêm-se os jobs científicos de 12 h. O teto de planejamento para os dois
encadeamentos e controles é cerca de 22,5 dias, sem espera em fila. Preempção
ou falha operacional interrompe o ramo e preserva evidências; não há retry.

O novo controlador ainda precisa ser implementado e qualificado antes de
submeter essa fila. Não se alterou o driver c493be8c, que continua sujeito à
admissão manual de uma célula e não aceita esse grafo por simples parâmetro.
Os dois pilotos h300 de 16 threads já são a próxima ação admitida pelo driver
atual; comandos separados podem usá-lo sem novo merge. Seus eventuais recibos
serão anexados ao plano em vez de repetir os starts no futuro controlador.

Não houve nova execução, qualificação nativa, submissão, merge, geração de
PDF ou depósito. Próxima etapa: qualificar os pilotos de 16 threads e construir
o controlador finito, testar estados adversos, executar qualificação pública,
pedir aprovação para merge e fornecer a submissão integral ao pesquisador.
