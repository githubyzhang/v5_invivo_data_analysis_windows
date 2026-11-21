// Reusable Artifact Session callback. Uses the connected presentation, never creates a second deck.
export async function addReportSlides({presentation,input}) {
  function text(s,t,x,y,w,h,size=24,color='#334155',bold=false){
    const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
    a.text=t;a.text.style={fontFamily:'Arial',fontSize:size,color,bold};return a;
  }
  for(const spec of input.slides){
    const s=presentation.slides.add({width:1280,height:720});s.background.fill='#FFFFFF';
    text(s,spec.title,50,26,1180,68,34,'#123047',true);
    if(spec.image){
      s.images.add({path:input.root+'/figures/'+spec.image+'.png',fit:'contain',position:{left:45,top:100,width:1190,height:520},alt:spec.title});
      text(s,spec.caption,60,638,1160,65,20);
    }else if(spec.table){
      const values=spec.table;const t=s.tables.add({rows:values.length,columns:3,left:60,top:125,width:1160,height:385,columnWidths:[620,270,270],values});
      for(let r=0;r<values.length;r++)for(let c=0;c<3;c++){
        const cell=t.getCell(r,c);cell.fill=r===0?'#123047':(r%2?'#F1F5F9':'#FFFFFF');
        cell.text.style={fontFamily:'Arial',fontSize:24,color:r===0?'#FFFFFF':'#334155',bold:r===0};
      }
      t.borders.assign({fill:'#DCE3E9',width:1,style:'solid'});
      text(s,spec.caption,60,545,1160,120,24);
    }else{
      spec.paragraphs.forEach((p,i)=>text(s,p,70,135+i*118,1140,100,27));
    }
    s.speakerNotes.text=spec.notes+'\nAnalysis: analysis/activity_report.py. Source: results/spike_detection_ma50_adaptive/extra4/spikes.h5 and extra5/spikes.h5. Figures and numeric outputs: results/extra45_activity_report/. Nominal sampling 10,000 Hz; physical 10,080 Hz. Counts are candidate events, not sorted units. Source hashes and example selections are in manifest.json.';
  }
  return {slideCount:presentation.slides.items.length};
}
