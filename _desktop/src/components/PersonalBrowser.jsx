import {useContext,useEffect,useState} from 'react';
import {createPortal} from 'react-dom';
import Draggable from 'react-draggable';
import UseContext from '../Context';
import {PERSONAL_PROJECT_EVENT,projectForName} from '../personalProjects';
import browserIcon from '../assets/ie.png';
import '../css/PersonalBrowser.css';

export default function PersonalBrowser(){
  const {maxZindexRef,handleSetFocusItemTrue,themeDragBar}=useContext(UseContext);
  const [entries,setEntries]=useState([]),[focused,setFocused]=useState(''),[taskHost,setTaskHost]=useState(null),[dragging,setDragging]=useState(false);
  const [viewport,setViewport]=useState({w:innerWidth,h:innerHeight});
  function focus(name){handleSetFocusItemTrue('Personal Browser');setFocused(name);const z=++maxZindexRef.current;setEntries(all=>all.map(e=>e.project.name===name?{...e,z,minimized:false}:e));}
  useEffect(()=>{
    setTaskHost(document.querySelector('.tap_container'));
    const open=e=>{const project=projectForName(e.detail?.name);if(!project)return;handleSetFocusItemTrue('Personal Browser');setFocused(project.name);const z=++maxZindexRef.current;setEntries(all=>{
      const old=all.find(x=>x.project.name===project.name);if(old)return all.map(x=>x===old?{...x,minimized:false,z}:x);
      const i=all.length,maxX=Math.max(0,innerWidth-Math.min(1100,innerWidth-32));return [...all,{project,z,minimized:false,maximized:innerWidth<=650,loaded:false,reload:0,position:{x:Math.min(30+i*20,maxX),y:Math.min(35+i*23,Math.max(12,innerHeight-400))}}];});};
    const resize=()=>{setViewport({w:innerWidth,h:innerHeight});const maxX=Math.max(0,innerWidth-Math.min(1100,innerWidth-32));setEntries(all=>all.map(e=>({...e,maximized:innerWidth<=650?true:e.maximized,position:{x:Math.max(0,Math.min(e.position.x,maxX)),y:Math.max(0,Math.min(e.position.y,innerHeight-100))}})));};
    const outside=e=>{if(!e.target.closest('.personal-browser-window,.personal-browser-task'))setFocused('');};
    const blur=()=>setTimeout(()=>{const el=document.activeElement;if(el?.tagName==='IFRAME'&&el.dataset.personalBrowser)focus(el.dataset.personalBrowser);},0);
    window.addEventListener(PERSONAL_PROJECT_EVENT,open);window.addEventListener('resize',resize);document.addEventListener('pointerdown',outside);window.addEventListener('blur',blur);
    return()=>{window.removeEventListener(PERSONAL_PROJECT_EVENT,open);window.removeEventListener('resize',resize);document.removeEventListener('pointerdown',outside);window.removeEventListener('blur',blur);};
  },[]);
  const change=(name,updates)=>setEntries(all=>all.map(e=>e.project.name===name?{...e,...updates}:e));
  const close=name=>setEntries(all=>all.filter(e=>e.project.name!==name));
  return <>{entries.map(entry=>{
    const {project}=entry,name=project.name,width=Math.min(1100,viewport.w-32),height=Math.min(750,viewport.h-90);
    return <Draggable key={name} handle=".personal-browser-title" disabled={entry.maximized||viewport.w<=650} position={entry.maximized?{x:0,y:0}:entry.position} bounds={{left:0,top:0,right:Math.max(0,viewport.w-width),bottom:Math.max(0,viewport.h-100)}} onStart={()=>{focus(name);setDragging(true);}} onStop={(_,d)=>{setDragging(false);change(name,{position:{x:d.x,y:d.y}});}}>
      <section className={`personal-browser-window ${entry.maximized?'is-maximized':''}`} aria-label={`${name} experience window`} style={{width,height,display:entry.minimized?'none':'flex',zIndex:focused===name?1100:entry.z}} onPointerDown={()=>focus(name)}>
        <header className="personal-browser-title" style={{background:focused===name?themeDragBar:'#757579'}} onDoubleClick={()=>change(name,{maximized:!entry.maximized})}><span><img src={browserIcon} alt=""/>{name} — Project browser</span><div className="personal-browser-controls"><button aria-label={`Minimize ${name}`} onClick={()=>change(name,{minimized:true})}>−</button><button aria-label={`Maximize ${name}`} onClick={()=>change(name,{maximized:!entry.maximized})}>□</button><button aria-label={`Close ${name}`} onClick={()=>close(name)}>×</button></div></header>
        <div className="personal-browser-toolbar"><button onClick={()=>change(name,{reload:entry.reload+1,loaded:false})} aria-label={`Reload ${name}`}>↻ Refresh</button><span className="browser-address-label">Address</span><input aria-label={`${name} URL`} value={project.url} readOnly/><a href={project.url} target="_blank" rel="noopener noreferrer">Open separately ↗</a></div>
        <div className="personal-browser-context"><strong>{project.description}</strong><span>{project.note||'Explore this project here.'}</span></div>
        <div className="personal-browser-page"><iframe key={`${name}-${entry.reload}`} title={`${name} live experience`} data-personal-browser={name} src={project.url} allow="microphone; clipboard-write; fullscreen" allowFullScreen sandbox="allow-scripts allow-same-origin allow-forms allow-downloads allow-popups allow-popups-to-escape-sandbox" referrerPolicy="strict-origin-when-cross-origin" onLoad={()=>change(name,{loaded:true})} onFocus={()=>focus(name)}/>{dragging&&<div className="browser-drag-guard"/>}</div>
        <footer className="personal-browser-status"><span>{entry.loaded?new URL(project.url).hostname:'Loading project…'}</span><span>Need more space or permissions? Open separately.</span></footer>
      </section>
    </Draggable>;
  })}{taskHost&&createPortal(entries.map(e=><button key={e.project.name} className={`start_tap personal-browser-task ${focused===e.project.name&&!e.minimized?'active':''}`} onClick={()=>focus(e.project.name)}><img src={browserIcon} alt=""/>{e.project.name}</button>),taskHost)}</>;
}
