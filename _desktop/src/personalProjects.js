export const personalProjects = [
  {name: 'Callay', url: 'https://ashstarry.github.io/callay-site/', description: 'Mac 输入法 · 官网与演示'},
  {name: 'Wonderline', url: 'https://wonderline.fun/', description: '语音画板 · 一笔奇境'},
  {name: 'Koyoi', url: 'https://koyoi.fun/', description: '今宵 · 微缩小镇'},
];

export function projectForName(name) {
  const normalized = String(name || '').replace(/\.url$/i, '').toLowerCase();
  if (normalized === 'blog archive') return { name: 'Blog Archive', url: 'https://ashstarry.github.io/blog/' };
  return personalProjects.find(project => project.name.toLowerCase() === normalized);
}

export function openPersonalProject(name) {
  const project = projectForName(name);
  if (!project) return false;
  window.open(project.url, '_blank', 'noopener,noreferrer');
  return true;
}

// These upstream apps need the original author's services or personal content.
export const disabledApps = new Set(['msn', 'mail', 'bitcoin', 'news', 'webresume', 'resumefile', 'resume', 'nft', 'note', 'aiagent', '3dobject', 'fortune', 'pixelpic', 'ie', 'internet', 'cat', 'patch']);
