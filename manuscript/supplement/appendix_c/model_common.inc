$onText
Reviewable translation of the approved daily-factors/scalable scalar contract.
Rosa (2026) mathematical foundation; Python source pinned in Appendix C.
This file is NOT evidence of compiled or numerical GAMS equivalence.
Native indicators are mandatory: no arbitrary finite slack Big-M is introduced.
Input is a generated GAMS include plus a hash-bound symbol/identifier manifest.
No NPAD submission command exists here. Large solves are intentionally blocked.
$offText
$if not set data $abort Supply --data=absolute/path/data.inc
$if not set backend $setglobal backend gurobi
$if not set execute_small $setglobal execute_small 0
Sets o origins, w warehouses, c destinations, p products, t ordered_periods,
     s scenarios, n(w) candidates, old(w) existing, ex(w) expansion_eligible,
     bulk(w) conversion_eligible, dom(c) domestic, exportDest(c) export,
     firstPeriod(t);
Alias(w,v);
Alias(t,tp);
Sets ow(o,w,p), wd(w,c,p), ww(w,v,p), direct(o,c,p), predecessor(t,tp);
Parameters pi(s), supply(s,o,p,t), demand(s,c,p,t), exportCap(s,c,p,t),
     initial(w,p), stock0(w), receive0(w), ship0(w), days(t),
     maxNew(w), maxExp(w), maxBulk(w), fixedNew(w), unitNew(w),
     fixedExp(w), unitExp(w), fixedBulk(w), unitBulk(w),
     costOW(o,w,p), costWD(w,c,p), costWW(w,v,p), costOD(o,c,p),
     hold(w,p), penaltyD(c,p), penaltyK(w), penaltyR(w);
Scalars rhoNew, rhoExp, rhoBulk, etaNew, etaExp, etaBulk;
$include %data%
abort$(abs(sum(s,pi(s))-1)>1e-12 or smin(s,pi(s))<=0)
    'Invalid probability vector';
abort$(card(old)+card(n)<>card(w) or sum(w$(old(w) and n(w)),1)>0)
    'Warehouse partition differs';
$ifthenI %formulation% == det
abort$(card(s)<>1 or not s('deterministic'))
    'DET requires the original deterministic singleton';
$endif
Binary Variables y(w) candidate_open_or_existing_active,
                 z(w) expansion_active, g(w) conversion_active;
Positive Variables k(w) candidate_tonnes, e(w) expansion_tonnes,
     b(w) conversion_tonnes, xOW(s,o,w,p,t), xWD(s,w,c,p,t),
     xWW(s,w,v,p,t), xOD(s,o,c,p,t), stock(s,w,p,t),
     unmet(s,c,p,t), qK(s,w,t), qR(s,w,t);
Variable total penalized_BRL;

* D11/S9: only the eligible first-stage variables may be nonzero.
y.fx(w)$old(w)=1;
k.fx(w)$(not n(w))=0;
z.fx(w)$(not ex(w))=0; e.fx(w)$(not ex(w))=0;
g.fx(w)$(not bulk(w))=0; b.fx(w)$(not bulk(w))=0;
unmet.fx(s,c,p,t)$(not dom(c))=0;
Equations objective, newBound(w), expBound(w), bulkBound(w),
     expActive(w), bulkActive(w), exclusion(w),
     supplyBalance(s,o,p,t), inventoryBalance(s,w,p,t),
     domesticBalance(s,c,p,t), exportBound(s,c,p,t),
     stockBound(s,w,t), receiveBound(s,w,t), shipBound(s,w,t),
     closedStock(s,w,t), closedReception(s,w,t);

* D1/S1: investment BRL once; recourse and three penalties weighted once.
* Python _build_investment_costs/_build_scenario_costs; all flows in tonnes.
objective.. total =e=
 sum(w$n(w),fixedNew(w)*y(w)+unitNew(w)*k(w))
 +sum(w$ex(w),fixedExp(w)*z(w)+unitExp(w)*e(w))
 +sum(w$bulk(w),fixedBulk(w)*g(w)+unitBulk(w)*b(w))
 +sum(s,pi(s)*(
    sum((o,w,p,t)$ow(o,w,p),costOW(o,w,p)*xOW(s,o,w,p,t))
   +sum((w,c,p,t)$wd(w,c,p),costWD(w,c,p)*xWD(s,w,c,p,t))
   +sum((w,v,p,t)$ww(w,v,p),costWW(w,v,p)*xWW(s,w,v,p,t))
   +sum((o,c,p,t)$direct(o,c,p),costOD(o,c,p)*xOD(s,o,c,p,t))
   +sum((w,p,t),hold(w,p)*stock(s,w,p,t))
   +sum((c,p,t)$dom(c),penaltyD(c,p)*unmet(s,c,p,t))
   +sum((w,t),penaltyK(w)*qK(s,w,t)+penaltyR(w)*qR(s,w,t))));

* D2: quantity tonnes <= valid physical investment maximum x binary.
* Python _add_first_stage_constraints; no arbitrary epsilon or budget added.
newBound(w)$n(w).. k(w) =l= maxNew(w)*y(w);
expBound(w)$ex(w).. e(w) =l= maxExp(w)*z(w);
bulkBound(w)$bulk(w).. b(w) =l= maxBulk(w)*g(w);
expActive(w)$ex(w).. z(w) =l= y(w);
bulkActive(w)$bulk(w).. g(w) =l= y(w);
exclusion(w)$(ex(w) and bulk(w)).. z(w)+g(w) =l= y(w);

* D4/S2: all origin supply leaves, in tonnes per period and scenario.
supplyBalance(s,o,p,t)..
 sum(w$ow(o,w,p),xOW(s,o,w,p,t))
 +sum(c$direct(o,c,p),xOD(s,o,c,p,t)) =e= supply(s,o,p,t);
* D5/D6/S3/S4: initial stock at first period, predecessor thereafter.
* Python _add_scenario_constraints/solve_model_scip; no terminal-stock fix.
inventoryBalance(s,w,p,t).. stock(s,w,p,t) =e=
 initial(w,p)$firstPeriod(t)
 +sum(tp$predecessor(t,tp),stock(s,w,p,tp))
 +sum(o$ow(o,w,p),xOW(s,o,w,p,t))
 +sum(v$ww(v,w,p),xWW(s,v,w,p,t))
 -sum(c$wd(w,c,p),xWD(s,w,c,p,t))
 -sum(v$ww(w,v,p),xWW(s,w,v,p,t));
* D7/S5 and D8/S6: direct+mediated deliveries, not separately bounded copies.
domesticBalance(s,c,p,t)$dom(c)..
 sum(w$wd(w,c,p),xWD(s,w,c,p,t))
 +sum(o$direct(o,c,p),xOD(s,o,c,p,t))+unmet(s,c,p,t)
 =e= demand(s,c,p,t);
* Infinite original export upper bounds are unrestricted, not finite Big-M.
exportBound(s,c,p,t)$(exportDest(c) and exportCap(s,c,p,t)<inf)..
 sum(w$wd(w,c,p),xWD(s,w,c,p,t))
 +sum(o$direct(o,c,p),xOD(s,o,c,p,t)) =l= exportCap(s,c,p,t);

* D3/D9/S7: storage tonnes; daily handling x days -> period tonnes.
* Python _effective_*_capacity_expr; conversion adds handling, NOT storage.
stockBound(s,w,t).. sum(p,stock(s,w,p,t))
 =l= stock0(w)+k(w)+e(w)+qK(s,w,t);
receiveBound(s,w,t)..
 sum((o,p)$ow(o,w,p),xOW(s,o,w,p,t))
 +sum((v,p)$ww(v,w,p),xWW(s,v,w,p,t))
 =l= days(t)*(receive0(w)+rhoNew*k(w)+rhoExp*e(w)+rhoBulk*b(w))
 +qR(s,w,t);
shipBound(s,w,t)..
 sum((c,p)$wd(w,c,p),xWD(s,w,c,p,t))
 +sum((v,p)$ww(w,v,p),xWW(s,w,v,p,t))
 =l= days(t)*(ship0(w)+etaNew*k(w)+etaExp*e(w)+etaBulk*b(w));

* D10/S8: rows below become indicators active only when candidate y=0.
* Nonnegative q <= 0 is equivalent to q=0. Never solve without the mapping.
closedStock(s,w,t)$n(w).. qK(s,w,t) =l= 0;
closedReception(s,w,t)$n(w).. qR(s,w,t) =l= 0;
Model grain /all/;
File indicatorFile /grain.indic/, optionFile /%backend%.opt/;
putclose indicatorFile
 'indic closedStock(s,w,t)$y(w) 0' /
 'indic closedReception(s,w,t)$y(w) 0' /;
$ifthenI %backend% == gurobi
putclose optionFile
 'indic closedStock(s,w,t)$y(w) 0' /
 'indic closedReception(s,w,t)$y(w) 0' /;
option mip=gurobi;
$elseifI %backend% == scip
putclose optionFile 'gams/indicatorfile=grain.indic' /;
option mip=scip;
$else
$abort Only native-indicator Gurobi or SCIP interfaces are in this translation
$endif
grain.optfile=1;

* Default is source inspection only. Large numerical parity is NOT admitted.
$ifthen %execute_small% == 1
abort$(card(w)>10 or card(o)>10 or card(c)>10 or card(t)>6 or card(s)>9)
 'Only separately reviewed tiny local validation is permitted';
option reslim=60, optcr=0;
solve grain using mip minimizing total;
Scalars returnedModelStatus, returnedSolveStatus, incumbent, bestBound;
returnedModelStatus=grain.modelstat; returnedSolveStatus=grain.solvestat;
incumbent=grain.objval; bestBound=grain.objest;
execute_unload 'grain_results.gdx', returnedModelStatus, returnedSolveStatus,
 incumbent, bestBound, y,z,g,k,e,b,xOW,xWD,xWW,xOD,stock,unmet,qK,qR;
display returnedModelStatus, returnedSolveStatus, incumbent, bestBound;
$else
display 'STRUCTURAL TRANSLATION ONLY; NO SOLVE PERFORMED';
$endif
