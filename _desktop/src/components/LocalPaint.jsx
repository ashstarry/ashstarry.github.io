import { useEffect, useRef, useState } from 'react';

export default function LocalPaint() {
  const canvas = useRef(null);
  const drawing = useRef(false);
  const previous = useRef(null);
  const [colour, setColour] = useState('#164f75');
  const [width, setWidth] = useState(5);
  const [canUndo, setCanUndo] = useState(false);
  useEffect(() => { const c = canvas.current; c.width = 1000; c.height = 650; const ctx = c.getContext('2d'); ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, c.width, c.height); }, []);
  const point = e => { const c = canvas.current, r = c.getBoundingClientRect(); return {x: (e.clientX-r.left)*c.width/r.width, y: (e.clientY-r.top)*c.height/r.height}; };
  function begin(e) { e.preventDefault(); drawing.current = true; e.currentTarget.setPointerCapture(e.pointerId); const p=point(e),ctx=canvas.current.getContext('2d');ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(p.x+.01,p.y+.01);ctx.strokeStyle=colour;ctx.lineWidth=width;ctx.lineCap='round';ctx.lineJoin='round';ctx.stroke(); }
  function move(e) { if(!drawing.current)return; const p=point(e),ctx=canvas.current.getContext('2d');ctx.lineTo(p.x,p.y);ctx.stroke(); }
  function clear() { const c=canvas.current,ctx=c.getContext('2d');previous.current=ctx.getImageData(0,0,c.width,c.height);ctx.fillStyle='#fff';ctx.fillRect(0,0,c.width,c.height);setCanUndo(true); }
  function undo() { if(previous.current){canvas.current.getContext('2d').putImageData(previous.current,0,0);previous.current=null;setCanUndo(false);} }
  function download() { canvas.current.toBlob(blob=>{if(!blob)return;const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='my-painting.png';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}); }
  return <div style={{height:'calc(100% - 25px)',display:'flex',flexDirection:'column',background:'#c0c0c0',minHeight:260}}>
    <div style={{display:'flex',flexWrap:'wrap',alignItems:'center',gap:8,padding:7,borderBottom:'2px solid #808080',fontSize:12}}>
      <label>Color <input aria-label="Paint colour" type="color" value={colour} onChange={e=>setColour(e.target.value)} /></label>
      <label>Brush <input aria-label="Brush size" type="range" min="1" max="30" value={width} onChange={e=>setWidth(Number(e.target.value))} style={{width:65}} /></label>
      <button onClick={clear}>Clear</button><button onClick={undo} disabled={!canUndo}>Undo clear</button><button onClick={download}>Save PNG</button>
    </div>
    <canvas ref={canvas} aria-label="Drawing canvas" onPointerDown={begin} onPointerMove={move} onPointerUp={()=>drawing.current=false} onPointerCancel={()=>drawing.current=false} style={{display:'block',width:'100%',height:0,flex:'1 1 auto',minHeight:180,background:'#fff',touchAction:'none',cursor:'crosshair'}} />
  </div>;
}
