// Versioned inspection workbooks. Computational ingestion stays in the existing Python pipeline.
import fs from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const [directory, kind] = process.argv.slice(2);
if (!directory) throw new Error('Pass the payload/output directory.');
if (!kind) {
  for (const name of ['baseline','registry']) {
    const c=spawnSync(process.execPath,['--max-old-space-size=8192',import.meta.filename,directory,name],{stdio:'inherit'});
    if (c.error) throw c.error;
    if(c.status!==0) process.exit(c.status??1);
  }
  process.exit(0);
}
if(!['baseline','registry'].includes(kind))throw new Error('Unknown workbook.');
const output=path.resolve(directory);
const payload=JSON.parse(await fs.readFile(path.join(output,`${kind}-workbook-v2.json`),'utf8'));
const wb=Workbook.create();
const previews=path.join(output,'previews',kind);
await fs.mkdir(previews,{recursive:true});
for(const {name,columns,rows,formulas={}} of payload.sheets){
 const ws=wb.worksheets.add(name);ws.showGridLines=false;
 ws.getRangeByIndexes(0,0,1,columns.length).values=[columns];
 for(let start=0;start<rows.length;start+=2000){const batch=rows.slice(start,start+2000);ws.getRangeByIndexes(start+1,0,batch.length,columns.length).values=batch;}
 for(const [cell,formula]of Object.entries(formulas))ws.getRange(cell).formulas=[[formula]];
 ws.getRangeByIndexes(0,0,rows.length+1,columns.length).format.columnWidth=23;
 ws.getRangeByIndexes(0,0,1,columns.length).format={fill:'#26374A',font:{name:'Arial',size:11,color:'#FFFFFF',bold:true},rowHeight:42,wrapText:true,verticalAlignment:'center'};
 if(rows.length)ws.getRangeByIndexes(1,0,Math.min(rows.length,100),columns.length).format.font={name:'Arial',size:11,color:'#222222'};
 const widths={Identification:[32,105],Controls:[32,55,20,100,45],InvestmentLimits:[28,20,25,18,25,25,22,92],Dictionary:[43,27,110,40,65,60],Transformations:[28,78,115],NetworkReferences:[30,78,90],Sources:[50,78,110],ParameterTemplate:[110,95]};
 if(columns.includes('key_json')){widths[name]=[40,95,25,30,70,80,72,65,30];if(rows.length)ws.getRangeByIndexes(1,2,rows.length,1).setNumberFormat('0.0##############');}
 for(const [i,width]of(widths[name]??[]).entries())ws.getRangeByIndexes(0,i,rows.length+1,1).format.columnWidth=width;
 if(['Identification','Controls','Dictionary','Transformations','ParameterTemplate'].includes(name)){
  ws.getRangeByIndexes(1,0,Math.max(rows.length,1),columns.length).format.wrapText=true;
  ws.getRangeByIndexes(1,0,Math.max(rows.length,1),columns.length).format.rowHeight=name==='Controls'?62:58;
 }
 if(name==='Controls'){
  ws.getRange('B2:B8').format.fill='#E9F3FA';ws.getRange('B2:B8').format.font.color='#15639A';
  ws.getRange('B5').setNumberFormat('0.0%');ws.getRange('B7').setNumberFormat('0.0%');ws.getRange('B9').setNumberFormat('0.0%');
 }
 if(name==='InvestmentLimits'&&rows.length){ws.getRangeByIndexes(1,2,rows.length,3).setNumberFormat('#,##0.00');ws.getRangeByIndexes(1,5,rows.length,2).setNumberFormat('"BRL "#,##0.00');}
 if(name==='Registry'){
  ws.freezePanes.freezeColumns(1);
  ws.getRangeByIndexes(1,0,rows.length,columns.length).format.rowHeight=32;
  for(let i=0;i<columns.length;i++){
   if(/Armazenador|transformation/.test(columns[i])){const range=ws.getRangeByIndexes(0,i,rows.length+1,1);range.format.columnWidth=95;range.format.wrapText=true;}
   else if(/Latitude|Longitude/.test(columns[i]))ws.getRangeByIndexes(1,i,rows.length,1).setNumberFormat('0.00000000000000');
   else if(/BRL|capacity|_t$|_day|Cap\./.test(columns[i])){ws.getRangeByIndexes(0,i,1,1).format.columnWidth=30;ws.getRangeByIndexes(1,i,rows.length,1).setNumberFormat('#,##0.00');}
  }
 }
 ws.freezePanes.freezeRows(1);
 console.log(JSON.stringify({sheet:name,rows:rows.length,workbook:kind}));
}
// Verify the same formula build reacts to K, then restore the delivered neutral case.
if(kind==='baseline'){
 wb.worksheets.getItem('Controls').getRange('B3').values=[[2]];wb.recalculate();
 const changed=await wb.inspect({kind:'table',range:'InvestmentLimits!A1:G4',include:'values,formulas',tableMaxRows:4,tableMaxCols:7,maxChars:3000});
 await fs.writeFile(path.join(previews,'K2-recalculation.ndjson'),changed.ndjson);
 wb.worksheets.getItem('Controls').getRange('B3').values=[[1]];
}
wb.recalculate();
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:50},maxChars:3000});
await fs.writeFile(path.join(previews,'formula-errors.ndjson'),errors.ndjson);
for(const {name,columns,rows}of payload.sheets){
 const last=String.fromCharCode(64+Math.min(columns.length,3));
 const image=await wb.render({sheetName:name,range:`A1:${last}${Math.min(rows.length+1,7)}`,scale:1,format:'png'});
 await fs.writeFile(path.join(previews,`${name}.png`),new Uint8Array(await image.arrayBuffer()));
}
if(kind==='registry'){
 const image=await wb.render({sheetName:'Registry',range:'V1:AF5',scale:1,format:'png'});
 await fs.writeFile(path.join(previews,'Registry-effective.png'),new Uint8Array(await image.arrayBuffer()));
}
const filename=kind==='baseline'?'agrologistic_effective_baseline_v2.xlsx':'agrologistic_warehouse_registry_v2.xlsx';
await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(output,filename));
console.log(JSON.stringify({saved:filename}));
