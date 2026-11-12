# Fechamento da E2 h400 e revisão do manuscrito

12 de novembro de 2026, America/Fortaleza.

A [PR #154](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/154)
já estava integrada a develop no commit `f35ef4f29ed98118778a6e38487e33dd6a2dd005`.
A execução está encerrada. Os seis solves e os seis gates E2,
jobs 2250119 a 2250130, terminaram com saída Slurm `0:0`.
Os seis gates aceitaram seus recibos operacionais.

O [registro de verificação](../evidence/h400_e1_e2_final_20261112/verification.json)
confere os SHA-256 dos 52 arquivos transferidos, a sequência dos gates,
as identidades dos jobs e os vínculos de entrada, matriz, limites e
hardware. O manifesto recebido tem SHA-256
`da8762022a36b59610c210e92615517a9d562910609faf2058be246ba4a4eae1`.
O diretório local de transferência conserva os recibos recebidos.
Os arquivos completos de evidência permanecem nas claims originais do NPAD.

A [grade h400 E1–E2](../evidence/h400_e1_e2_final_20261112/h400-e1-e2.csv)
contém uma execução por solver e por limite de 1, 2, 4, 8 e 16 threads.
O Gurobi atingiu o alvo de 1% nas cinco execuções, com gap comum de
0,836784% arredondado. Duas threads tiveram o menor tempo observado
(80,03 min nativos e 154,83 min ponta a ponta). Os speedups descritivos
frente a uma thread foram 1,092× e 1,050×. O HiGHS atingiu o limite
nativo nas cinco execuções, sem incumbente utilizável. O maior pico
amostrado do worker foi 162,99 GiB, abaixo do teto de 163,20 GiB.
O maior pico do cgroup foi 163,45 GiB, abaixo do teto de 172,80 GiB.

O artigo e os Apêndices C e E incorporam a grade validada a partir de
[`645d98b`](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/commit/645d98bfe81e575ac19858c24baa40931adef462).
A [PR #151](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/151)
continua em rascunho para revisão editorial. A exportação mantém o
trecho anterior a Results do LaTeX autoral e a bibliografia entregue
com SHA-256 `d4215c0fdcb0ce75d7fa8092d6b088b1e1d1f7d957689230064eee01d941daa6`.

A grade permite comparações descritivas. A variabilidade em h400
depende de repetições comparáveis. A extensão common-Pyomo para h500
depende de qualificação própria de recursos.
