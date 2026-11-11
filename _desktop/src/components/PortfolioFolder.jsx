import {useContext, useEffect, useState} from 'react';
import Draggable from 'react-draggable';
import UseContext from '../Context';
import {personalProjects, openPersonalProject} from '../personalProjects';
import '../css/PortfolioFolder.css';

function ProjectArt({kind}) {
  if (kind === 'callay') return <div className="project-art art-callay" aria-hidden="true"><span className="art-caption">A WORD OPENS A DOOR</span><span className="word-key">moon<span>月亮</span></span><span className="book-spine"/><span className="book-page">The Moon<br/>& Sixpence</span><span className="art-line">词语 → 释义 → 文学</span></div>;
  if (kind === 'wonderline') return <div className="project-art art-wonderline" aria-hidden="true"><span className="art-caption">WORDS BECOME PICTURES</span><svg viewBox="0 0 200 100"><path d="M31 57Q48 21 99 39Q121 47 139 50L157 35L152 60Q129 89 79 81Q44 76 31 57Z" fill="#a0bfc4"/><path d="M31 57Q48 21 99 39Q121 47 139 50L157 35L152 60Q129 89 79 81Q44 76 31 57Z" fill="none" stroke="#4e7783" strokeWidth="2" strokeDasharray="3 2"/><circle cx="57" cy="52" r="3" fill="#3b5562"/><path d="M75 35q-2-17 8-19m-8 19q8-14 16-11M69 63q8 6 15 3" fill="none" stroke="#4e7783" strokeWidth="2" strokeLinecap="round"/><path d="m161 13 2 5 6 1-5 4 1 6-5-3-5 3 1-6-4-4 6-1Z" fill="#d5a553"/></svg><span className="art-line">说出来，画下来。</span></div>;
  return <div className="project-art art-koyoi" aria-hidden="true"><span className="art-caption">A LITTLE WORLD, ALIVE</span><div className="mini-moon"/><div className="mini-town"><span/><span/><span/></div><span className="art-line">今宵，想给小镇带来什么？</span></div>;
}

export default function PortfolioFolder() {
  const {ProjectExpand,setProjectExpand,ProjectFolderRef,themeDragBar,handleSetFocusItemTrue,inlineStyle,inlineStyleExpand,StyleHide,deleteTap,handleShow} = useContext(UseContext);
  const [page,setPage] = useState('works');
  const [position,setPosition] = useState({x:innerWidth<=650?8:Math.max(20,(innerWidth-Math.min(1040,innerWidth-40))/2),y:innerWidth<=650?12:24});
  useEffect(()=>{const resize=()=>setPosition(p=>innerWidth<=650?{x:8,y:12}:{x:Math.max(0,Math.min(p.x,innerWidth-Math.min(1040,innerWidth-40))),y:Math.max(0,Math.min(p.y,innerHeight-100))});window.addEventListener('resize',resize);return()=>window.removeEventListener('resize',resize);},[]);
  const toggleMax = () => setProjectExpand(p=>({...p,expand:!p.expand}));
  return <Draggable handle=".portfolio-titlebar" disabled={ProjectExpand.expand} bounds={{top:0}} position={ProjectExpand.expand?{x:0,y:0}:position} onStart={()=>handleSetFocusItemTrue('Project')} onStop={(_,d)=>{setPosition({x:d.x,y:d.y});setProjectExpand(p=>({...p,x:d.x,y:d.y}));}}>
    <section className="portfolio-window" ref={ProjectFolderRef} aria-label="ashstarry 的个人主页" style={ProjectExpand.expand?{...inlineStyleExpand('Project'),left:0,top:0}:inlineStyle('Project')} onClick={e=>{e.stopPropagation();handleSetFocusItemTrue('Project');}}>
      <header className="portfolio-titlebar" onDoubleClick={toggleMax} style={{background:ProjectExpand.focusItem?themeDragBar:'#757579'}}><span><span className="title-avatar">a</span>ashstarry — 个人主页</span><div className="portfolio-controls"><button aria-label="最小化个人主页" onClick={e=>{e.stopPropagation();setProjectExpand(p=>({...p,hide:true,focusItem:false}));StyleHide('Project');}}>−</button><button aria-label="放大个人主页" onClick={e=>{e.stopPropagation();toggleMax();}}>□</button><button aria-label="关闭个人主页" onClick={e=>{e.stopPropagation();deleteTap('Project');}}>×</button></div></header>
      <nav className="portfolio-menu" aria-label="作品档案菜单"><button aria-pressed={page==='works'} onClick={()=>setPage('works')}>我的作品</button><button aria-pressed={page==='about'} onClick={()=>setPage('about')}>关于我</button><button onClick={()=>openPersonalProject('Blog Archive')}>博客档案 ↗</button></nav>
      <div className="portfolio-scroll">
        <div className="portfolio-intro"><div className="creator-monogram" aria-hidden="true">a<span>★</span></div><div><div className="creator-kicker">A PERSONAL COLLECTION</div><h1>你好，我是 ashstarry。</h1><p>我把一些关于表达与创造的想法，做成了可以亲手体验的小作品。</p></div></div>
        {page==='works'?<><div className="portfolio-section-label"><span>我的三个项目</span><span>文字 · 画面 · 空间</span></div><div className="portfolio-projects">{personalProjects.map((p,i)=><article key={p.name} className="portfolio-project" onDoubleClick={()=>openPersonalProject(p.name)}><ProjectArt kind={p.kind}/><div className="project-story"><div className="project-file-label">0{i+1} / {p.category}</div><h2>{p.name}<span>{p.kind==='koyoi'?'今宵':p.kind==='wonderline'?'一笔奇境':'Mac 输入法'}</span></h2><h3>{p.summary}</h3><p>{p.detail}</p><p className="project-example">{p.example}</p><button className="retro-launch" onClick={()=>openPersonalProject(p.name)}>{p.action}<span aria-hidden="true"> →</span></button></div></article>)}</div><div className="portfolio-help">点击按钮会在桌面里的浏览器窗口打开项目。Callay 展示的是官网与演示，输入法本体需在 Mac 安装。</div></>:<div className="creator-document"><h2>一些被做出来的想法。</h2><p>这张桌面收着我的三个个人项目。它们分别从文字、画面和空间出发，尝试把想象变成可以使用、可以探索的东西。</p><p>你可以先看看项目介绍，再进入应用体验；也可以打开博客，看看以前留下的文章和记录。</p><div className="creator-links"><button className="retro-launch" onClick={()=>openPersonalProject('Blog Archive')}>以前的文章</button><a href="https://github.com/ashstarry" target="_blank" rel="noopener noreferrer">我的 GitHub ↗</a><button onClick={()=>handleShow('About')}>关于桌面与开源致谢</button></div><hr/><p className="creator-footnote">桌面的记事本、画图和小游戏是这个空间附带的小玩具。真正想与你分享的，是上面的三个作品。</p></div>}
      </div><footer className="portfolio-status"><span>ashstarry / 个人作品集</span><span>3 projects · 打开即探索</span></footer>
    </section>
  </Draggable>;
}
