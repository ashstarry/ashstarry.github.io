export const modelCollection = [
  {
    id: 'the-lode',
    name: 'The Lode',
    artwork: new URL('./assets/the-lode-paper.webp', import.meta.url).href,
    medium: 'Blender · 11 models',
    description: 'Deep-space mine',
    story: 'Follow a piece of ore from an asteroid pit, across a suspension bridge and into a waiting freighter. A passing gravity tide changes its flight.',
    url: 'https://ashstarry.github.io/the-lode/web/',
    action: 'Enter the mine',
    sourceUrl: 'https://github.com/ashstarry/ashstarry.github.io/tree/master/the-lode',
    note: 'Drag to orbit. Choose a viewpoint to follow the ore from the mine to the freighter.'
  }
];

export function exhibitCount(models) {
  return `${models.length} ${models.length === 1 ? 'exhibit' : 'exhibits'}`;
}
