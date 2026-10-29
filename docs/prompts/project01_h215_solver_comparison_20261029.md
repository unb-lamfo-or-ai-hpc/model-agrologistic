# Prompt para Projeto 01 — avaliação independente de complexidade e comparação de solvers

Copiar o conteúdo abaixo para o chat escolhido do Projeto01. Este documento não foi enviado automaticamente a outro chat.

---

Atue como pesquisador sênior em programação inteira mista, programação estocástica e HPC. Precisamos de uma avaliação crítica e independente para o artigo Model Agrologistic. O objetivo é explicar os resultados observados e propor a comparação mínima cientificamente defensável, sem partir da premissa de que software livre é incapaz de resolver o problema.

## Fontes que devem ser lidas primeiro

PR139, ainda draft: https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/139.
Base congelada da evidência antes desta reavaliação: b4cf4715b61b840b7c0487bdf1c14e90a2900016. Distinguir essa revisão, develop e main. Na PR139, ler também docs/h215_solver_comparison_reassessment_20261029.md, que registra a reavaliação e o plano atual.

Fontes primárias do repositório:
- [Evidência Gurobi](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/b4cf4715b61b840b7c0487bdf1c14e90a2900016/manuscript/scalar_evidence.json), selecionar scalar_h215_sto.
- [SCIP4h original](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/b4cf4715b61b840b7c0487bdf1c14e90a2900016/docs/evidence/scalar_scip_h215_w_2225638_review.json).
- [SCIP ampliado interrompido](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/b4cf4715b61b840b7c0487bdf1c14e90a2900016/docs/evidence/scalar_scip_h215_2226388_inspection.json).
- [HiGHS validado](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/b4cf4715b61b840b7c0487bdf1c14e90a2900016/docs/evidence/scalar_highs_h215_2226536_inspection.json).
- [Identidade da entrada/OSRM](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/b4cf4715b61b840b7c0487bdf1c14e90a2900016/docs/evidence/scalar_h215_input_20261020.json).
- [Contrato matemático e hash do grafo](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/b4cf4715b61b840b7c0487bdf1c14e90a2900016/src/logic/mathematical_contract.py).
- [Gate do SCIP](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/b4cf4715b61b840b7c0487bdf1c14e90a2900016/scripts/mvp2_scalar_scip_h215_8h.py) e [gate do HiGHS](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/b4cf4715b61b840b7c0487bdf1c14e90a2900016/scripts/mvp2_scalar_highs_h215_8h_startup.py).
- [Prova e limites da reformulação](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/b4cf4715b61b840b7c0487bdf1c14e90a2900016/docs/pyomo_multisolver.md).
- [Resultados atuais para leitores](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/b4cf4715b61b840b7c0487bdf1c14e90a2900016/manuscript/scip_results.qmd), AppendixC e formulação na mesma revisão.
- Conferir no repositório a bibliografia atual, docs/literature_claims_reconciliation_20261028.md e docs/literature_disposition_20261028.json. Não assumir que todos os textos completos já foram acessados. Consultar fontes primárias adicionais e informar limites de acesso.

## Fatos e distinções já estabelecidos

A comparação open-source executou o mesmo problema científico STO h215 W do Gurobi:215warehouses incluídos(146existentes/69candidatos),60períodos,2produtos,9cenários equiprováveis, mesmíssima planilha processada SHA25640edb66585daca9cc393cab1f86bde6d4528a5f34b6afc57260cc1684396da4e, política de rotas, população e penalidades90,000/45,000/45,000. W exclui ligação direta origem/cliente e permite transbordo entre warehouses. Arestas selecionadas são3,182OD,3,440DC,18,490DD,0OC, já indexadas por produto. Há igualdade do contrato que inclui selected_network_sha256; igualdade de contagens sozinha não provaria isso. A planilha/materialização completa contém63,289registrosOSRM, que não devem ser confundidos com as25,112rotas/produto efetivamente selecionadas. Mesma lista de warehouses/arestas admissíveis não exige a mesma solução ótima ou as mesmas arestas com fluxo positivo.

Isso NÃO significa matrizes nativas idênticas:
- Gurobi/gurobipy:14,054,654variáveis,307binárias,661,057linhas e74,520restrições gerais.
- SCIP/PySCIPOpt10.0.2/SoPlex8.0.2:14,129,174variáveis,307binárias,810,097restrições nativas.
- HiGHS1.15.1/Pyomo6.10.1/APPSI:14,054,654variáveis,307binárias,735,577linhas,52,217,866não zeros.
O HiGHS usa bounded_scalar_slacks_v1, equivalente na projeção física/investimento e valor ótimo escalar, sob as hipóteses documentadas; não é identidade de toda região redundante das folgas nem das relaxações. SCIP foi implementado nativamente, sem Pyomo. Hoje o adaptador Pyomo cobre HiGHS/CBC, não Gurobi/SCIP.

Resultados:
1. Gurobi2217990STO: validado; UB13,071,396,953,900.23BRL; LB12,974,647,770,396.824BRL; gap comum0.740159478%;2,445.517971s nativos.
2. SCIP2225638: retorno nativo timelimit em14,410.764462s, limite14,400s;zero soluções,1nó;presolve608.24s. Depois do presolve12,708,003variáveis,92binárias,626,547restrições. Conclusão da LPraiz não demonstrada. Não há incumbent nem gap calculável. Bound nativo-1.7794577021226982e15BRL não é custo ou prova de inviabilidade.
3. SCIP2226388: allowance28,800s,mas jobFAILED/stepCANCELLED0:15, controlador emitiuTERM;registro de conclusão ainda running,sem resultado/terminal nativo/validação. ValueError operacional e KeyError na revisão;gatilho original não identificado. Alocação30,042s não equivale a retorno nativo normal de8h. Log termina após565s de presolve. Observação censurada.
4. HiGHS2226536: validado,zero checks rejeitados;UB12,974,673,141,227.254BRL;LB12,974,647,770,396.836BRL;gap comum1.9554119122548442e-6 na forma fracionária,isto é0.000195541%;25,601.980820s nativos;1nó e2,901,682iteraçõesLP. Meta configurada também1%,não meta mais estrita. Log registra parallel search off/1maxworker,apesar de threads4.

O HiGHS tem incumbent cerca0.739965% menor que o do Gurobi,compatível com o intervalo certificado anterior. Seus indicadores físicos:econômico393.331bilhõesBRL,serviço92.3284%,51.991milhões de toneladas não atendidas,penalidades96.9685% do objetivo. Gap do total penalizado não certifica isoladamente custo financeiro,adequação de serviço ou calibração econômica.

Auditoria local confirmou hashes/inventários/fontes/recebimentos das entradas e certificados originais. O result.jsonHiGHS de70.77MB foi integralmente hashado,mas não interpretado em memória;não houve recálculo novo dos resíduos das decisões nem reprodução operacional integral. Preservar esse limite. A primeira execuçãoSCIP tem grande lacuna de amostragem de recursos; não atribuir sua duração ao observador como causalidade demonstrada.

O projeto completo também inclui GurobiDET/D e h300/h400/h500. Não generalizar o resultadoh215 para essas instâncias.

## Perguntas e entregas

1. Separar fatos, inferências sustentadas, hipóteses e lacunas. O que realmente explica a dificuldade do SCIP? O que falta para distinguir custo de LPraiz,degenerescência,escala numérica,tratamento de indicadores,paralelismo e interrupção do controlador? Não escolher uma causa sem evidência.
2. Explicar didaticamente por que215warehouses não descrevem o tamanho:25,112*60*9=13,560,480variáveis de fluxo antes das demais famílias. Distinguir dimensão,complexidade teórica e dificuldade empírica; não usar contagem ou falha de um solver como prova de NP-dificuldade da instância.
3. Auditar convenções de gap,alvo1% versus gap efetivamente atingido,retorno optimal sujeito a tolerâncias e dominância das penalidades. Propor tabela deUB/LB/gap absoluto/gap comum/gap nativo/validação,com valores ausentes explícitos.
4. Avaliar o que já pode ser publicado como comparação descritiva de implementações e o que exigiria benchmark controlado. Evitar quociente de runtimes apresentado como speedup causal,qualidade igual por ambos cumprirem1%,ou impossibilidade geral de solvers livres.
5. Propor o desenho MÍNIMO de eventual contraste adicional:matriz comum auditada versus APIs nativas,mesmas entradas/limites/alvos,tempos até incumbent validado e gaps comuns,presolve/LPraiz/crossover,memória com mesmo escopo,CPU/NUMA/SMT/carga compartilhada,efeito de seeds/replicações e censura. Estabelecer critérios para dispensar novos jobs se o artigo só fizer alegações descritivas. Não recomendar grade ampla antes dessa decisão.
6. Produzir uma matriz afirmação–evidência–limitação e textos sugeridos em inglês para Methods,Results,Discussion e AppendixC/D,voltados aos leitores da revista. Não introduzir orientações a coautores no artigo.
7. Confrontar as referências já citadas com literatura primária de benchmarkingMILP,LPs de grande porte,formas extensivas,reformulações e confiabilidade numérica. Fornecer links/DOIs e suporte específico para cada recomendação; não inventar leituras completas nem extrapolar de outros benchmarks.
8. Encerrar com prioridades:evidência recuperável sem novo solve;correções de documentação/software;experimentos estritamente opcionais e sua contribuição científica.

Não executar jobs,reiniciar claims,alterar pacotes originais,instalar software ou realizar merge. Entregar avaliação e recomendações; qualquer experimento posterior depende de pacote qualificado e CLI manual do pesquisador.
