// These photographs include extra space around the render camera. Cropping them
// by focal length keeps the mine registered through different window shapes.
(() => {
  const shots = [
    { name: 'tall', bearing: .72, width: 1240, height: 2640, zoom: .85 },
    { name: 'tablet', bearing: .89, width: 1740, height: 1860, zoom: .82 },
    { name: 'square', bearing: 1.02, width: 1760, height: 1760, zoom: .84 },
    { name: 'book', bearing: 1.15, width: 1840, height: 1560, zoom: .83 },
    { name: 'wide', bearing: 1.27, width: 3024, height: 1440, zoom: .83 }
  ];
  function select(aspect, mode) {
    if (mode === 'tour') return aspect <= .8 ? shots[0] : shots[4];
    const i = [.835,.955,1.085,1.21].findIndex(limit => aspect < limit);
    return shots[i < 0 ? 4 : i];
  }
  function extent(shot, width, height) {
    const aspect = shot.width / shot.height;
    const f = Math.max(1,1.43 / aspect) / (shot.zoom * Math.max(1,1.43 * height / width));
    return {width: height * f * aspect, height: height * f};
  }
  function fit(image, shot, width, height) {
    const size = extent(shot,width,height);
    image.style.width = size.width + 'px'; image.style.height = size.height + 'px';
  }
  window.minePlates = { shots, select, extent, fit, url: shot => './assets/opening/plate-' + shot.name + '.webp?v=5' };
  const params = new URLSearchParams(location.search);
  window.minePlates.home = !['test','manual','ff','parts','cam','tgt'].some(k=>params.has(k)) &&
    (!params.has('focus') || params.get('focus') === 'home');
  if (window.minePlates.home) {
    const link = document.createElement('link');
    link.rel = 'preload'; link.as = 'image'; link.fetchPriority = 'high';
    link.href = window.minePlates.url(select(innerWidth / innerHeight, params.get('view')));
    document.head.append(link);
  }
})();
