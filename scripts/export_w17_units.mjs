import fs from 'node:fs/promises';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const [input,output]=process.argv.slice(2);
const records=JSON.parse(await fs.readFile(`${input}/units.json`,'utf8'));
const definitions=JSON.parse(await fs.readFile(`${input}/column_definitions.json`,'utf8'));
const wb=Workbook.create();
const sheet=wb.worksheets.add('Accepted units');
const fields=Object.keys(records[0]);
sheet.getRangeByIndexes(0,0,42,fields.length).values=[fields,...records.map(r=>fields.map(k=>r[k]))];
sheet.showGridLines=false;
sheet.getRangeByIndexes(0,0,42,fields.length).format.font={name:'Arial',size:10};
sheet.getRangeByIndexes(0,0,42,fields.length).format.rowHeight=22;
sheet.getRangeByIndexes(0,0,1,fields.length).format={fill:'#254552',font:{bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:55};
for(let j=0;j<fields.length;j++){
 const col=sheet.getRangeByIndexes(0,j,42,1);col.format.columnWidth=Math.max(22,fields[j].length+3);
 if(fields[j]==='unit_id')col.format.columnWidth=65;
 if(fields[j]==='run_id'||fields[j]==='policy_id')col.format.columnWidth=48;
 if(typeof records[0][fields[j]]==='number')sheet.getRangeByIndexes(1,j,41,1).setNumberFormat(Number.isInteger(records[0][fields[j]])&&!fields[j].includes('rate')&&!fields[j].includes('duration')?'#,##0':'0.0000');
}
sheet.freezePanes.freezeRows(1);sheet.freezePanes.freezeColumns(2);
const last=(()=>{let n=fields.length,s='';while(n){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26)}return s})();
sheet.tables.add(`A1:${last}42`,true,'AcceptedUnits');
const notes=wb.worksheets.add('Definitions');notes.showGridLines=false;
const info=[['Field','Definition'],...Object.entries(definitions),['Sources','Frozen W17 release tables and original sorter labels; corrected table counts are recomputed from the retained event annotations.'],['Interpretation','All quality event counts refer to retained analysis events. Zero is a count, not proof of clean data. not_assessed means unavailable.'],['Release','Presentation revision 2 only. 41 accepted putative units and 62,048 events unchanged.']];
notes.getRangeByIndexes(0,0,info.length,2).values=info;
notes.getRangeByIndexes(0,0,info.length,2).format.font={name:'Arial',size:10};
notes.getRangeByIndexes(0,0,info.length,1).format.columnWidth=38;
notes.getRangeByIndexes(0,1,info.length,1).format.columnWidth=110;
notes.getRangeByIndexes(0,0,info.length,2).format.rowHeight=34;
notes.getRangeByIndexes(0,0,info.length,2).format.wrapText=true;
notes.getRange('A1:B1').format={fill:'#254552',font:{bold:true,color:'#FFFFFF'}};
notes.freezePanes.freezeRows(1);
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Accepted units!A1:H5',include:'values',tableMaxRows:5,tableMaxCols:8,maxChars:1500})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:10},maxChars:500})).ndjson);
for(const [name,range,file] of [['Accepted units','A1:B8','units-preview.png'],['Definitions','A1:B9','definitions-preview.png']]){
 const image=await wb.render({sheetName:name,range,scale:1,format:'png'});await fs.writeFile(`${output}/${file}`,new Uint8Array(await image.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(wb)).save(`${output}/units.xlsx`);
