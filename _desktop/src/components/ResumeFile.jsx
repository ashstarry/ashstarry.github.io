import { portfolioStorage } from '../portfolioStorage.js';
import UseContext from '../Context'
import { useContext, useState } from "react";
import Draggable from 'react-draggable'
import { motion } from 'framer-motion';
import resumefile from '../assets/resume.png'
import '../css/ResumeFile.css'



function ResumeFile() {

  const { 
    themeDragBar,
    ResumeFileExpand, setResumeFileExpand,
    lastTapTime, setLastTapTime,
    StyleHide,
    isTouchDevice,
    handleSetFocusItemTrue,
    inlineStyleExpand,
    inlineStyle,
    deleteTap,

   } = useContext(UseContext);

   const [ downloadBox, setDownloadBox ] = useState(false)
   const [note, setNote] = useState(() => portfolioStorage.getItem('notepad') || '');

      function handleDragStop(event, data) {
        const positionX = data.x 
        const positionY = data.y
        setResumeFileExpand(prev => ({
          ...prev,
          x: positionX,
          y: positionY
        }))

      }

   function handleExpandStateToggle() {
    setResumeFileExpand(prevState => ({
      ...prevState,
      expand: !prevState.expand
    }));
  }

  function handleExpandStateToggleMobile() {
    const now = Date.now();
    if (now - lastTapTime < 300) {
        setResumeFileExpand(prevState => ({
            ...prevState,
            expand: !prevState.expand
        }));
    }
    setLastTapTime(now);
}

  return (
    <>
      <Draggable
        axis="both" 
        handle={'.folder_dragbar-resumefile'}
        grid={[1, 1]}
        scale={1}
        disabled={ResumeFileExpand.expand}
        bounds={{top: 0}}
        defaultPosition={{ 
          x: window.innerWidth <= 500 ? 5 : 80,
          y: window.innerWidth <= 500 ? 100 : 90,
        }}
        onStop={(event, data) => handleDragStop(event, data)}
        onStart={() => handleSetFocusItemTrue('NotePad')}
      >
        <div className='folder_folder-resumefile' 
            onClick={(e) => {
              e.stopPropagation();
              handleSetFocusItemTrue('NotePad');
            }}
            style={ ResumeFileExpand.expand ? inlineStyleExpand('NotePad') : inlineStyle('NotePad')}>
          <div className="folder_dragbar-resumefile"
              onDoubleClick={handleExpandStateToggle}
              onTouchStart={handleExpandStateToggleMobile}
             style={{ background: ResumeFileExpand.focusItem? themeDragBar : '#757579'}}
          >
            <div className="folder_barname-resumefile">
              <img src={resumefile} alt="resumefile" />
              <span>NotePad — saved in this browser</span>
            </div>
            <div className="folder_barbtn-resumefile">
              <div onClick={ !isTouchDevice? (e) => {
                e.stopPropagation()
                setResumeFileExpand(prev => ({...prev, hide: true, focusItem: false}))
                StyleHide('NotePad') 
              } : undefined
            }
                   onTouchEnd={(e) => {
                    e.stopPropagation()
                    setResumeFileExpand(prev => ({...prev, hide: true, focusItem: false}))
                    StyleHide('NotePad')
                  }}
                  onTouchStart={(e) => e.stopPropagation()}
              >
                <p className='dash-resumefile'></p>
              </div>
              <div
                onClick={ !isTouchDevice ? () => handleExpandStateToggle() : undefined}
                onTouchEnd={handleExpandStateToggle}
              >
                <motion.div className={`expand-resumefile ${ResumeFileExpand.expand ? 'full' : ''}`}>
                </motion.div>
                {ResumeFileExpand.expand ? 
                (
                <div className="expand_2-resumefile"></div>
                )
                :
                (null)}
              </div>
              <div>
                <p className='x-resumefile'
                 onClick={!isTouchDevice ? () => {
                  deleteTap('NotePad')
                  setDownloadBox(false)
                 }: undefined
                }
                onTouchEnd={() => {
                  deleteTap('NotePad')
                  setDownloadBox(false)
              }}
                >×</p>
              </div>
            </div>
          </div>

          <div className="folder_content-resumefile"
            style={ResumeFileExpand.expand ? 
              { height: 'calc(100svh - 72px)'} /// fullscreen btm nav
              : 
              {}
            }

          >
            <textarea className="personal-notepad" aria-label="Personal notepad" placeholder="Write a thought… Saved only in this browser." value={note} onChange={e => { setNote(e.target.value); portfolioStorage.setItem('notepad', e.target.value); }} />
            
          </div>
        </div>
      </Draggable>
    </>
  )
}          


export default ResumeFile
