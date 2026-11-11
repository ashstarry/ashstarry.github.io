import {useContext, useLayoutEffect, useState} from 'react';
import Draggable from 'react-draggable';
import UseContext from '../Context';
import {personalProjects, openPersonalProject} from '../personalProjects';
import '../css/PortfolioFolder.css';

function ProjectArt({kind}) {
  if (kind === 'callay') return <div className="project-art art-callay" aria-hidden="true"><span className="art-caption">A WORD OPENS A DOOR</span><span className="word-key">moon<span>a word</span></span><span className="book-spine"/><span className="book-page">The Moon<br/>& Sixpence</span><span className="art-line">Words → meanings → literature</span></div>;
  if (kind === 'wonderline') return <div className="project-art art-wonderline" aria-hidden="true"><span className="art-caption">WORDS BECOME PICTURES</span><svg viewBox="0 0 200 100"><path d="M31 57Q48 21 99 39Q121 47 139 50L157 35L152 60Q129 89 79 81Q44 76 31 57Z" fill="#a0bfc4"/><path d="M31 57Q48 21 99 39Q121 47 139 50L157 35L152 60Q129 89 79 81Q44 76 31 57Z" fill="none" stroke="#4e7783" strokeWidth="2" strokeDasharray="3 2"/><circle cx="57" cy="52" r="3" fill="#3b5562"/><path d="M75 35q-2-17 8-19m-8 19q8-14 16-11M69 63q8 6 15 3" fill="none" stroke="#4e7783" strokeWidth="2" strokeLinecap="round"/><path d="m161 13 2 5 6 1-5 4 1 6-5-3-5 3 1-6-4-4 6-1Z" fill="#d5a553"/></svg><span className="art-line">Say it. Draw it.</span></div>;
  return <div className="project-art art-koyoi" aria-hidden="true"><span className="art-caption">A LITTLE WORLD, ALIVE</span><div className="mini-moon"/><div className="mini-town"><span/><span/><span/></div><span className="art-line">Give this little town a wish.</span></div>;
}

export default function PortfolioFolder() {
  const {ProjectExpand,setProjectExpand,ProjectFolderRef,DesktopRef,desktopIcon,iconScreenSize,themeDragBar,handleSetFocusItemTrue,inlineStyle,inlineStyleExpand,StyleHide,deleteTap,handleShow} = useContext(UseContext);
  const [page,setPage] = useState('works');
  const [gutter,setGutter] = useState(innerWidth<=650?0:176);
  const [position,setPosition] = useState({x:innerWidth<=650?8:176,y:8});
  const desktopCount=desktopIcon.filter(icon=>icon.folderId==='Desktop').length;
  useLayoutEffect(()=>{
    const arrange=()=>{
      if(innerWidth<=650){setGutter(0);setPosition({x:8,y:8});return;}
      const icons=[...(DesktopRef.current?.querySelectorAll('.icon')||[])];
      const edges=icons.map(icon=>icon.getBoundingClientRect()).filter(r=>r.width>0&&r.left<innerWidth*.4).map(r=>r.right);
      const edge=edges.length?Math.max(...edges):160;
      const left=Math.min(Math.max(96,Math.ceil(edge+16)),Math.max(96,innerWidth-420));
      setGutter(left);setPosition({x:left,y:8});
    };
    arrange();const frame=requestAnimationFrame(arrange);window.addEventListener('resize',arrange);
    return()=>{cancelAnimationFrame(frame);window.removeEventListener('resize',arrange);};
  },[DesktopRef,desktopCount,iconScreenSize]);
  const toggleMax = () => setProjectExpand(p=>({...p,expand:!p.expand}));
  return <Draggable handle=".portfolio-titlebar" disabled={ProjectExpand.expand} bounds={{top:0}} position={ProjectExpand.expand?{x:gutter,y:0}:position} onStart={()=>handleSetFocusItemTrue('Project')} onStop={(_,d)=>{setPosition({x:d.x,y:d.y});setProjectExpand(p=>({...p,x:d.x,y:d.y}));}}>
    <section className="portfolio-window" ref={ProjectFolderRef} aria-label="ashstarry’s personal homepage" style={{'--portfolio-gutter':`${gutter}px`,...(ProjectExpand.expand?{...inlineStyleExpand('Project'),left:0,top:0,width:`calc(100vw - ${gutter}px)`,height:'calc(100svh - 35px)'}:inlineStyle('Project'))}} onClick={e=>{e.stopPropagation();handleSetFocusItemTrue('Project');}}>
      <header className="portfolio-titlebar" onDoubleClick={toggleMax} style={{background:ProjectExpand.focusItem?themeDragBar:'#757579'}}><span><span className="title-avatar">a</span>ashstarry — Personal homepage</span><div className="portfolio-controls"><button aria-label="Minimize homepage" onClick={e=>{e.stopPropagation();setProjectExpand(p=>({...p,hide:true,focusItem:false}));StyleHide('Project');}}>−</button><button aria-label="Maximize homepage" onClick={e=>{e.stopPropagation();toggleMax();}}>□</button><button aria-label="Close homepage" onClick={e=>{e.stopPropagation();deleteTap('Project');}}>×</button></div></header>
      <nav className="portfolio-menu" aria-label="Portfolio navigation"><button aria-pressed={page==='works'} onClick={()=>setPage('works')}>My projects</button><button aria-pressed={page==='about'} onClick={()=>setPage('about')}>About me</button><button aria-pressed={page==='blog'} onClick={()=>setPage('blog')}>Blog</button></nav>
      <div className="portfolio-scroll">
        <div className="portfolio-intro"><div className="creator-monogram" aria-hidden="true">a<span>★</span></div><div><div className="creator-kicker">A PERSONAL COLLECTION</div><h1>Hi, I'm ashstarry.</h1><p>I make small tools and playful experiences. Here are three of them.</p></div></div>
        {page==='works'?<><div className="portfolio-section-label"><span>Three personal projects</span><span>Worlds · Drawing · Writing</span></div><div className="portfolio-projects">{personalProjects.map((p,i)=><article key={p.name} className="portfolio-project" onDoubleClick={()=>openPersonalProject(p.name)}><ProjectArt kind={p.kind}/><div className="project-story"><div className="project-file-label">0{i+1} / {p.category}</div><h2>{p.name}<span>{p.kind==='koyoi'?'Miniature world':p.kind==='wonderline'?'Voice drawing':'Mac input method'}</span></h2><h3>{p.summary}</h3><p>{p.detail}</p><p className="project-example">{p.example}</p><button className="retro-launch" onClick={()=>openPersonalProject(p.name)}>{p.action}<span aria-hidden="true"> →</span></button></div></article>)}</div><div className="portfolio-help">Open a project to try it in a desktop window. Callay shows its website and demo; the input method itself needs a Mac installation.</div></>:page==='about'?<div className="creator-document"><h2>A few things I've made.</h2><p>This desktop brings together three personal projects exploring small worlds, drawing, and writing.</p><p>Read a short introduction, then open whichever project sparks your curiosity. The blog is still empty, waiting for future notes.</p><div className="creator-links"><button className="retro-launch" onClick={()=>setPage('blog')}>Blog · Coming later</button><a href="https://github.com/ashstarry" target="_blank" rel="noopener noreferrer">My GitHub ↗</a><button onClick={()=>handleShow('About')}>About this desktop & credits</button></div><hr/><p className="creator-footnote">The notepad, paint tool, and games are little extras to play with. The three projects above are the work I am here to share.</p></div>:<div className="creator-document blog-placeholder"><div className="blog-empty-icon" aria-hidden="true">✎</div><div className="creator-kicker">BLOG / COMING LATER</div><h2>No posts yet.</h2><p>This space is reserved for future ideas, project notes, and stories from the creative process.</p><button className="retro-launch" onClick={()=>setPage('works')}>Explore my projects →</button></div>}
      </div><footer className="portfolio-status"><span>ashstarry / Personal projects</span><span>3 projects · Click to explore</span></footer>
    </section>
  </Draggable>;
}
