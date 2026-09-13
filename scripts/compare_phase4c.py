"""Compare actual equal-size Pilot crops; retain original screenshots and hashes."""
import json
from pathlib import Path
from PIL import Image,ImageDraw
from flyrendezvous.recording import sha256,write_json
OUT=Path('docs/evidence_phase4c')
canvas=Image.new('RGB',(1440,390),(22,27,35));draw=ImageDraw.Draw(canvas)
for i,name in enumerate(['C1','C2','C3']):
 image=Image.open(OUT/f'design_{name}.png').convert('RGB').resize((480,360))
 canvas.paste(image,(i*480,30));draw.text((i*480+15,10),'Variant '+name+(' (default)' if name=='C2' else ''),fill='white')
canvas.save(OUT/'design_comparison.png')
rect=(1325,945,1830,1370)
sources=[('Phase 4A | fixed external fly','docs/evidence_phase4a/demo_early.png'),('Phase 4B | procedural B + IK','docs/evidence_phase4b/demo_early.png'),('Phase 4C | semi-stylized C2 + same IK','docs/evidence_phase4c/demo_early.png')]
width=rect[2]-rect[0];height=rect[3]-rect[1]
canvas=Image.new('RGB',(3*width,height+32),(22,27,35));draw=ImageDraw.Draw(canvas)
meta=[]
for i,(label,path) in enumerate(sources):
 im=Image.open(path).convert('RGB');assert im.size==(2240,1400)
 canvas.paste(im.crop(rect),(i*width,32));draw.text((i*width+12,10),label,fill='white')
 meta.append(dict(source=path,sha256=sha256(path),crop=list(rect),resize=False,physical_time_s=20))
dest=OUT/'phase4a_vs_4b_vs_4c.png';canvas.save(dest)
write_json(OUT/'comparison.json',dict(file=str(dest),sha256=sha256(dest),sources=meta,note='Equal source pixel size, no re-rendering, same time and panel area'))
