# Campanha Gurobi/HiGHS em série — plano de execução

Data: 1 de novembro de 2026. Este plano organiza todas as células restantes
da campanha aprovada. É um desenho de dependências, ainda não um lançador
qualificado. Nenhum job foi submetido por este planejamento. Os PDFs do
artigo e dos apêndices continuam adiados por orientação do pesquisador.

## Escopo e situação atual

A grade mantém dois solvers, três populações (h300/h400/h500), cinco limites
de threads (1/2/4/8/16) e três repetições: 90 execuções. Os dois pilotos h300
com uma thread já foram coletados e validados; faltam 88 execuções, sendo
44 por solver. Não se repetem as células consumidas nem se incorporam as
observações históricas de outro protocolo como novas repetições.

As células restantes e todas as dependências estão enumeradas em
[JSON](../../experiments/pyomo_scaling_serial_schedule_v1.json) e
[CSV](../../experiments/pyomo_scaling_serial_schedule_v1.csv). O JSON preserva
também as duas âncoras já executadas e os índices do planejamento original.
O engine qualificado permanece no commit c493be8c; o código e os dados
científicos não são alterados para organizar a fila. A nova camada de
orquestração terá identidade e qualificação próprias.

## Limites efetivamente consultados

A consulta enviada pelo pesquisador informou QOS preempt, MaxJobsPU=10,
MaxSubmitJobsPU=100, fila pessoal vazia e associação à conta sxdsouza.
A partição intel-256 informou sete nós, 64 CPUs por nó, PreemptMode=CANCEL,
QOS de partição compute e MaxTime=20 dias. MaxWall da QOS preempt veio vazio.
Isso não estabelece o limite efetivo herdado da QOS de partição/associações.
O desenho mantém os 12 h já admitidos por job científico; não utiliza uma
suposta permissão nova para jobs de 20 dias ou precisa ocupar as 48 h antes
discutidas. O lançador deve validar o perfil exato no scheduler.

O df informou 12 T livres no filesystem compartilhado. Isso não comprova
quota pessoal. Com limite de evidência expandida de 4 GiB por execução,
os 88 casos podem somar até 352 GiB de membros arquiváveis, além dos próprios
arquivos comprimidos e temporários. O planejamento de armazenamento deve
considerar cópias e scratch; não se apagam originais para liberar espaço.

## Duas sequências e seis etapas

Cada sequência contém um solver. No máximo um Gurobi e um HiGHS executam
simultaneamente, em nós exclusivos distintos. Isso também evita introduzir
concorrência entre duas licenças Gurobi que não foi qualificada. Dentro de
cada etapa, os jobs de um solver dependem do sucesso do predecessor desse
solver. Entre etapas, ambos aguardam a coleta e a verificação conjunta.

| Etapa | Jobs de solução | Coleta/verificação | Condição para liberar a etapa seguinte |
| --- | ---: | ---: | --- |
| h300: pilotos de 16 threads, r1 | 2 | 1 | Quatro pilotos h300, incluindo os dois já aceitos, fechados e compatíveis |
| h300: demais células | 26 | 1 | Recibos e configurações das 30 células h300 conferidos |
| h400: pilotos de 1 e 16 threads, r1 | 4 | 1 | Quatro pilotos h400 fechados e compatíveis |
| h400: demais células | 26 | 1 | Recibos e configurações das 30 células h400 conferidos |
| h500: pilotos de 1 e 16 threads, r1 | 4 | 1 | Quatro pilotos h500 fechados e compatíveis |
| h500: demais células | 26 | 1 | Recibos e configurações das 30 células h500 conferidos |
| Consolidação final | 0 | 1 | Registrar todos os estados, inclusive células não executadas |
| **Total novo** | **88** | **7** | **95 jobs no grafo completo** |

A qualificação pública do controlador precede essa fila. A proposta cabe
no limite informado de 100 jobs, deixando cinco posições de margem, desde
que a fila total do usuário continue compatível no instante da submissão.
Limites herdados/compartilhados também devem ser respeitados. Uma job array
não elimina o limite: suas tarefas também contam como jobs para MaxSubmit.

Os controles de coleta por etapa evitam acrescentar um job coletor para cada
uma das 88 soluções. Os jobs científicos preservam a revisão dos próprios
produtos; o novo preflight verifica os pequenos recibos do predecessor antes
de permitir nova construção. As verificações completas de accounting,
arquivos, matrizes, bounds e recursos ocorrem nos seis controles de etapa.
Nenhuma etapa seguinte é liberada por um simples COMPLETED sem esses recibos.

## Recursos e duração

Cada solução mantém o perfil aprovado: limite nativo 28.800 s, alvo de gap
1%, memória solicitada 192 GiB, 24 CPUs lógicas solicitadas, pool comum de
16 CPUs lógicas no worker, nó exclusivo, Slurm 12 h, intel-256/preempt,
sem requeue. Threads do solver e CPUs do pool não são a mesma quantidade.
Alocação efetiva, topologia, pacote, fonte e input são registrados novamente.

Os seis controles de etapa terão orçamento proposto de 2 h, quatro CPUs e
32 GiB, sem nó exclusivo e sem otimização privada. O fechamento final terá
30 min, uma CPU e 2 GiB. Esses perfis novos ainda precisam de qualificação.
O coletor processará os casos sequencialmente para limitar memória e IO.

Uma sequência restante contém 44 soluções. Com dois nós disponíveis durante
toda a execução, o teto dos envelopes científicos é 44 × 12 h = 528 h:
22 dias. Os seis controles acrescentam até 12 h e o fechamento 30 min,
resultando em cerca de 22,5 dias, antes de filas e interrupções. São até
704 horas nativas de solver restantes, distribuídas entre as duas sequências.
Isso é orçamento de planejamento, não previsão estatística ou prazo garantido.
A preempção por CANCEL interrompe o ramo afetado e preserva seus recibos.

## Contrato científico preservado

Ambos os solvers usam a mesma formulação Pyomo/APPSI, entradas e arcos OSRM
congelados, cenários, limites derivados e validação independente. A seed do
modelo continua 42. Gurobi mantém métodos, presolve e cortes automáticos,
Heuristics=0.05 e os overrides declarados de tempo, threads, gap e tolerâncias;
não é uma execução integralmente default. HiGHS 1.15.1 mantém parallel=on,
inclusive no nível de uma thread. O limite configurado não comprova utilização
simultânea ou aceleração, sobretudo em uma execução dominada pelo LP da raiz.

As três execuções são repetições temporais com seed fixa. Não representam
três sementes ou a mesma solução inicial entre solvers. A ordem bloqueada por
população/repetição usa seed de agendamento 42031, distinta da seed dos solvers.
O novo plano é uma alteração prospectiva de ordem após observar os dois
pilotos; preserva o índice antigo e registrará o efetivamente executado.

Cada gate usa quatro pilotos originais (1 e 16 threads para ambos os solvers),
accounting e encerramento próprios, amostras oportunas e pico amostrado até
80% de 192 GiB: 153,6 GiB. Matriz ordenada, prova de bounds e classe de hardware
devem coincidir dentro da população. A passagem não garante pico não observado
nem autoriza ampliar memória automaticamente. Falha operacional, OOM, fonte
divergente ou solução rejeitada impedem o avanço.

Um retorno nativo regular no limite de tempo, inclusive sem incumbente,
permanece observação censurada. Não atingir gap de 1% não é, por si só,
motivo para descartar o caso ou selecionar apenas o solver vencedor. Dificuldade
matemática e falha de execução são classificadas separadamente.

## Submissão e pausa

O futuro lançador deve preparar o grafo finito no login, conferir fontes,
runtime, entradas, espaço/quota e slots, e submeter todos os novos jobs em
hold. Cada intenção e resposta sbatch é gravada antes de avançar. Somente
depois de conferir os 95 recibos e dependências haverá liberação explícita.
Submissão parcial ou resposta incerta mantém os jobs novos em hold; não
reexecuta start, não duplica claims e não libera um subconjunto silenciosamente.

Os nós de solução usam afterok; os coletores usam afterany para preservar
também falhas. Descendentes impossíveis são cancelados pelo scheduler com
kill-on-invalid-dep=yes. A consolidação roda após os controles terminais e
mantém todas as 90 linhas. Um job cancelado antes de executar não recebe
objetivo, gap ou rótulo de falha do solver. A ausência de batch/step para esse
estado deve ser tratada explicitamente pelo novo coletor, sem espera infinita.

Uma vez liberado o grafo qualificado, o pesquisador pode encerrar sua sessão:
as dependências ficam no Slurm. Nenhum processo permanente no login, cron,
submissão a partir de nó de compute ou escalonamento ilimitado é necessário.
Não há retry automático, fallback, aumento de recursos, novo warm start ou
publicação. Uma falha preserva a campanha para retomada e pode deixar células
não executadas; a pausa não converte essas células em resultados.

As âncoras antigas são verificadas por arquivos e hashes. Não se criam novas
dependências Slurm de jobs antigos possivelmente fora de MinJobAge. Se os
dois pilotos de 16 threads forem lançados antes do controlador, seus claims
serão reconciliados e anexados por recibos; nunca submetidos outra vez.

## Implementação e qualificação ainda necessárias

O driver atual exige login em start/collect, conta jobs pendentes no limite
de dois e só admite uma célula por chamada. Portanto, não basta acrescentar
--dependency ao código atual. A PR operacional precisa acrescentar uma camada
separada de preparação/liberação e coleta em compute, preservando o engine,
os claims originais, a identidade do worker e os limites de cada célula.

Antes do lote completo: implementar o controlador; testar grafo, limites,
submissão parcial, respostas incertas, cancelamento sem batch/step, atraso de
accounting, corrupção de evidência, drift, gates e estados censurados; qualificar
em job público curto no NPAD; incorporar recibos; solicitar merge; depois
fornecer o bloco de submissão/liberação para execução manual pelo pesquisador.
O plano estático aprovado localmente não equivale a esse lançador qualificado.

As tabelas finais distinguirão configuração, qualidade/limites, tempos,
recursos e resultados físicos. A grade completa inclui as não executadas,
falhas operacionais e censura; estatísticas usam denominadores explícitos.
Outras configurações h215 estão fora destas 90 células e não serão acrescentadas
silenciosamente. A revisão da PR144 continua separada; PDFs e publicação
dependem das próximas orientações e aprovações.

Documentação primária do mecanismo de dependências:
[sbatch](https://slurm.schedmd.com/sbatch.html),
[job arrays](https://slurm.schedmd.com/job_array.html) e
[limites sacctmgr](https://slurm.schedmd.com/sacctmgr.html).
