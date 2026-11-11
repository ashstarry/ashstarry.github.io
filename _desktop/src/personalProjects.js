export const personalProjects = [
  {name: 'Callay', url: 'https://ashstarry.github.io/callay-site/', description: 'Mac 输入法 · 官网与演示', category: '文字 / INPUT', summary: '输入一个词，也能遇见另一个世界。', detail: '一款 Mac 输入法，把词语释义和文学联想放在输入过程旁边。', example: '比如输入 moon，沿着一个词发现《月亮和六便士》。', note: '此处体验官网演示；真正的输入法需要在 Mac 上安装。', action: '看看输入法', kind: 'callay'},
  {name: 'Wonderline', url: 'https://wonderline.fun/', description: '语音画板 · 一笔奇境', category: '画面 / DRAWING', summary: '一边说，想象一边变成画。', detail: '把描述逐笔变成图画，在蜡笔、彩铅和水彩之间选择，保存自己的画面与故事。', example: '试着描述：a whale in a spacesuit。', note: '画板在这个窗口中运行；开始说话时，浏览器会询问麦克风权限。', action: '打开画板', kind: 'wonderline'},
  {name: 'Koyoi', url: 'https://koyoi.fun/', description: '今宵 · 微缩小镇', category: '空间 / LITTLE WORLD', summary: '用一句话，改变小镇的一个夜晚。', detail: '一个有居民、天气和日常生活的剪纸风微缩小镇，会回应你带来的心愿。', example: '送来一场雪，或让夜晚的市场亮起灯。', note: '可以在窗口中探索小镇；放大窗口能看见更多细节。', action: '走进小镇', kind: 'koyoi'},
];

export const PERSONAL_PROJECT_EVENT = 'ashstarry:open-project';

export function projectForName(name) {
  const normalized = String(name || '').replace(/\.url$/i, '').toLowerCase();
  if (normalized === 'blog archive') return { name: 'Blog Archive', url: 'https://ashstarry.github.io/blog/', description: '以前的文章与记录', note: '原来的博客和文章仍保留在这里。' };
  return personalProjects.find(project => project.name.toLowerCase() === normalized);
}

export function openPersonalProject(name) {
  const project = projectForName(name);
  if (!project) return false;
  window.dispatchEvent(new CustomEvent(PERSONAL_PROJECT_EVENT, {detail: {name: project.name}}));
  return true;
}

// These upstream apps need the original author's services or personal content.
export const disabledApps = new Set(['msn', 'mail', 'bitcoin', 'news', 'webresume', 'resumefile', 'resume', 'nft', 'note', 'aiagent', '3dobject', 'fortune', 'pixelpic', 'ie', 'internet', 'cat', 'patch']);
