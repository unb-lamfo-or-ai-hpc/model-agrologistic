// Local inspection-workbook renderer; computational ingestion remains Python-only.
import fs from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const [directory, only] = process.argv.slice(2);
if (!directory) throw new Error('Pass the new local seed directory.');
const output = path.resolve(directory);
const workbooks = [
  ['baseline-workbook.json', 'agrologistic_effective_baseline_v1.xlsx'],
  ['registry-workbook.json', 'agrologistic_warehouse_registry_v1.xlsx'],
];
// Separate processes release artifact-engine memory between the two workbooks.
if (!only) {
  for (const [, filename] of workbooks) {
    const child = spawnSync(process.execPath,
      ['--max-old-space-size=8192', import.meta.filename, directory, filename],
      { stdio: 'inherit' });
    if (child.error) throw child.error;
    if (child.status !== 0) process.exit(child.status ?? 1);
  }
  process.exit(0);
}
if (!workbooks.some(([, filename]) => filename === only)) {
  throw new Error('Unknown workbook selection.');
}
for (const [payloadName, filename] of workbooks.filter(([, name]) => name === only)) {
  const payload = JSON.parse(await fs.readFile(path.join(output, payloadName), 'utf8'));
  const wb = Workbook.create();
  for (const { name, columns, rows } of payload.sheets) {
    const ws = wb.worksheets.add(name);
    ws.showGridLines = false;
    const width = columns.length;
    ws.getRangeByIndexes(0, 0, 1, width).values = [columns];
    for (let start = 0; start < rows.length; start += 2000) {
      const batch = rows.slice(start, start + 2000);
      ws.getRangeByIndexes(start + 1, 0, batch.length, width).values = batch;
    }
    const head = ws.getRangeByIndexes(0, 0, 1, width);
    head.format = {
      fill: '#26374A', font: { name: 'Arial', size: 10, color: '#FFFFFF', bold: true },
      rowHeight: 30, wrapText: true, verticalAlignment: 'center',
    };
    ws.getRangeByIndexes(0, 0, rows.length + 1, width).format.columnWidth = 22;
    if (rows.length) {
      ws.getRangeByIndexes(1, 0, Math.min(rows.length, 100), width).format.font = {
        name: 'Arial', size: 10, color: '#222222',
      };
    }
    if (columns.includes('key_json')) {
      ws.getRangeByIndexes(0, 0, rows.length + 1, 1).format.columnWidth = 37;
      ws.getRangeByIndexes(0, 1, rows.length + 1, 1).format.columnWidth = 105;
      ws.getRangeByIndexes(0, 2, rows.length + 1, 1).format.columnWidth = 24;
      ws.getRangeByIndexes(1, 2, Math.max(1, rows.length), 1).setNumberFormat('0.0##############');
      for (const [column, columnWidth] of [[4, 55], [5, 72], [6, 50], [7, 72], [8, 25]]) {
        ws.getRangeByIndexes(0, column, rows.length + 1, 1).format.columnWidth = columnWidth;
      }
    }
    if (name === 'Identification') {
      ws.getRange('A1:A10').format.columnWidth = 26;
      ws.getRange('B1:B10').format.columnWidth = 100;
      ws.getRange('B1:B10').format.wrapText = true;
      ws.getRange('A1:B10').format.rowHeight = 34;
    }
    if (name === 'Sources' || name === 'NetworkReferences') {
      ws.getRangeByIndexes(0, 1, rows.length + 1, 1).format.columnWidth = 75;
      if (columns.length > 2) ws.getRangeByIndexes(0, 2, rows.length + 1, 1).format.columnWidth = 110;
    }
    if (name === 'Dictionary' || name === 'Configurations') {
      ws.getRangeByIndexes(0, 0, rows.length + 1, 1).format.columnWidth = 42;
      ws.getRangeByIndexes(0, 1, rows.length + 1, 1).format.columnWidth = 42;
      ws.getRangeByIndexes(0, 2, rows.length + 1, 1).format.columnWidth = 100;
    }
    if (name === 'Transformations') {
      ws.getRangeByIndexes(0, 1, rows.length + 1, 2).format.columnWidth = 100;
    }
    if (name === 'ParameterTemplate') {
      ws.getRange('A1:A2').format.columnWidth = 105;
      ws.getRange('A2').format.wrapText = true;
      ws.getRange('A2').format.rowHeight = 70;
    }
    if (name === 'Registry') {
      ws.getRangeByIndexes(1, 0, rows.length, columns.length).format.rowHeight = 34;
      for (let column = 0; column < columns.length; column++) {
        if (/Armazenador|Razão|Nome|transformation/.test(columns[column])) {
          const values = ws.getRangeByIndexes(0, column, rows.length + 1, 1);
          values.format.columnWidth = 80;
          values.format.wrapText = true;
        }
      }
      ws.freezePanes.freezeColumns(1);
    }
    if (rows.length > 20) ws.freezePanes.freezeRows(1);
    console.log(JSON.stringify({ workbook: filename, sheet: name, rows: rows.length }));
  }
  wb.recalculate();
  const errors = await wb.inspect({ kind: 'match',
    searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',
    options: { useRegex: true, maxResults: 20 }, maxChars: 1200 });
  console.log(errors.ndjson);
  const check = await wb.inspect({ kind: 'table', range: 'Identification!A1:B8',
    include: 'values,formulas', tableMaxRows: 8, tableMaxCols: 2, maxChars: 1500 });
  console.log(check.ndjson);
  const artifact = await SpreadsheetFile.exportXlsx(wb);
  await artifact.save(path.join(output, filename));
  const previewDirectory = path.join(output, 'previews', filename.replace('.xlsx', ''));
  await fs.mkdir(previewDirectory, { recursive: true });
  for (const { name, columns, rows } of payload.sheets) {
    const endColumn = Math.min(columns.length, 5);
    const letter = String.fromCharCode(64 + endColumn);
    const image = await wb.render({ sheetName: name,
      range: `A1:${letter}${Math.min(rows.length + 1, 9)}`, scale: 1, format: 'png' });
    await fs.writeFile(path.join(previewDirectory, `${name}.png`),
      new Uint8Array(await image.arrayBuffer()));
  }
  console.log(JSON.stringify({ saved: filename }));
}
