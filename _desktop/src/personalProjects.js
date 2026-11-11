export const personalProjects = [
  {
    "name": "Koyoi",
    "url": "https://koyoi.fun/",
    "description": "An interactive miniature town",
    "category": "WORLDS / INTERACTIVE",
    "summary": "A little world moved by your words.",
    "detail": "Explore a living paper-cut town, watch its residents, and send it a wish to change the scene.",
    "example": "Try bringing in snow or lighting up the night market.",
    "note": "Explore the town here. Maximize the window for a closer look.",
    "action": "Explore the town",
    "kind": "koyoi"
  },
  {
    "name": "Wonderline",
    "url": "https://wonderline.fun/",
    "description": "Voice-driven drawing",
    "category": "DRAWING / CREATIVE TOOL",
    "summary": "Keep talking. Watch your ideas take shape.",
    "detail": "Turn spoken descriptions into drawings, choose crayon, pencil, or watercolor, and save your pictures and stories.",
    "example": "Try: “a whale in a spacesuit.”",
    "note": "The live canvas runs here. Your browser will ask for microphone permission when you start speaking.",
    "action": "Try the drawing board",
    "kind": "wonderline"
  },
  {
    "name": "Callay",
    "url": "https://ashstarry.github.io/callay-site/",
    "description": "Mac input method · Website & demo",
    "category": "WRITING / MAC APP",
    "summary": "Discover more behind the words you type.",
    "detail": "An English-first Mac input method that brings meanings and literary connections alongside your writing.",
    "example": "Type “moon” and find a path to The Moon and Sixpence.",
    "note": "This is the website and demo. The input method itself needs to be installed on a Mac.",
    "action": "Explore the input method",
    "kind": "callay"
  }
];

export const PERSONAL_PROJECT_EVENT = 'ashstarry:open-project';

export function projectForName(name) {
  const normalized = String(name || '').replace(/\.url$/i, '').toLowerCase();
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
