import {useEffect, useRef, useState} from 'react';
import {exhibitCount} from '../modelCollection';
import {openPersonalProject} from '../personalProjects';
import '../css/ModelCabinet.css';

function ModelLink({model, children, onOpen, ...props}) {
  function open(event) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    if (openPersonalProject(model.name)) {
      event.preventDefault();
      onOpen?.();
    }
  }
  return <a href={model.url} onClick={open} {...props}>{children}</a>;
}

function MountedModel({model}) {
  return (
    <span className="cabinet-mount" aria-hidden="true">
      <img src={model.artwork} alt="" draggable="false" />
    </span>
  );
}

export function CabinetPreview({models}) {
  const featured = models[0];
  return (
    <section className="cabinet-preview" aria-labelledby="modeling-heading">
      <div className="cabinet-preview-copy">
        <h2 id="modeling-heading">My 3D Modeling</h2>
        <p>{exhibitCount(models)} on display</p>
        <a href="#model-cabinet" className="retro-launch cabinet-open">Open cabinet</a>
      </div>
      {featured && (
        <ModelLink model={featured} className="cabinet-miniature"
          aria-label={`Open ${featured.name}`} title={`Open ${featured.name}`}>
          <MountedModel model={featured} />
          <span className="cabinet-plaque">{featured.name}</span>
        </ModelLink>
      )}
    </section>
  );
}

export function ModelCabinet({models}) {
  const [selectedId, setSelectedId] = useState(models[0]?.id);
  const heading = useRef(null);
  const selected = models.find(model => model.id === selectedId) ?? models[0];
  useEffect(() => {
    heading.current?.focus({preventScroll: true});
  }, []);

  return (
    <section className="model-cabinet" aria-labelledby="cabinet-heading">
      <header className="cabinet-header">
        <h1 id="cabinet-heading" ref={heading} tabIndex={-1}>Model Cabinet</h1>
        <span>{exhibitCount(models)} on display</span>
      </header>
      {models.length > 1 && <p className="cabinet-guide" id="shelf-guide">Select a nameplate for details. Open a model to explore it.</p>}
      {selected ? (
        <div className="cabinet-layout">
          <div className="cabinet-case">
            <ul className="cabinet-shelves" aria-label="Models on display"
              aria-describedby={models.length > 1 ? 'shelf-guide' : undefined}>
              {models.map(model => (
                <li key={model.id} className="cabinet-specimen">
                  <ModelLink model={model} className="cabinet-object-link" aria-label={`Open ${model.name}`}
                    title={`Open ${model.name}`} onOpen={() => setSelectedId(model.id)}>
                    <MountedModel model={model} />
                  </ModelLink>
                  <button type="button" className="cabinet-plaque" aria-label={`Read the label for ${model.name}`}
                    aria-pressed={selected.id === model.id} aria-controls="exhibit-record"
                    onClick={() => setSelectedId(model.id)}>{model.name}</button>
                </li>
              ))}
            </ul>
          </div>
          <article id="exhibit-record" className="cabinet-record" aria-labelledby="exhibit-name">
            <div aria-live="polite" aria-atomic="true">
              <h2 id="exhibit-name">{selected.name}</h2>
              <p className="cabinet-medium">{selected.medium}</p>
              <p className="cabinet-story">{selected.story}</p>
            </div>
            <div className="cabinet-record-actions">
              <ModelLink model={selected} className="retro-launch">{selected.action}</ModelLink>
              {selected.sourceUrl && <a className="cabinet-source" href={selected.sourceUrl}
                target="_blank" rel="noopener noreferrer">Source &amp; models</a>}
            </div>
          </article>
        </div>
      ) : <p className="cabinet-empty">The shelves are empty.</p>}
    </section>
  );
}
