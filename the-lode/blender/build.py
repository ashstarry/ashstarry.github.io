import sys
from pathlib import Path
import bpy,importlib
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root));out=root.parent/'web/assets';out.mkdir(parents=True,exist_ok=True)
parts=['textures','terrain','habitat','rail','plant','pit','bwe','port','fleet','rocks','fill','watchcrew']
names=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['all']
for name in (parts if names==['all'] else names):
    if name not in parts:raise ValueError(name)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    module=importlib.import_module('lib.terrain' if name=='terrain' else 'parts.'+name)
    module.build(out,lambda msg:print('[mine]',msg,flush=True))
