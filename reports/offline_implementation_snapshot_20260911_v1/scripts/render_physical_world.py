#!/usr/bin/env python3
"""Render the actual collision layout and verified passage route for review."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--world',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():
        raise SystemExit('refusing to overwrite diagram')
    m=json.loads((args.world/'manifest.json').read_text())
    audit=json.loads((args.world/'geometry_audit.json').read_text())
    annotation=json.loads((args.world/'verified_ordered_geometry.json').read_text())
    fig,ax=plt.subplots(figsize=(12,8))
    for wall in m['layout']['walls']:
        ax.add_patch(Rectangle((wall['x']-wall['sx']/2,wall['y']-wall['sy']/2),
                               wall['sx'],wall['sy'],color='#586474'))
    ax.add_patch(Rectangle((m['anchor_pose'][0]-.21,m['anchor_pose'][1]-.21),.42,.42,color='royalblue'))
    ax.annotate('Chair',m['anchor_pose'],xytext=(1.6,.1),arrowprops={'arrowstyle':'->'})
    for c in m['candidates']:
        goal=c['goal']
        expected=c['route_id']==m['expected_route_id']
        ax.scatter(goal['x'],goal['y'],s=85,marker='*' if expected else 'o',color='#13845b' if expected else '#9e4444')
        ax.text(goal['x'],goal['y']+(0.6 if goal['y']>0 else -.65),
                f"{c['side'].title()} doorway {c['ordinal']}"+('\nRequested entrance' if expected else '\nAlternative room'),
                ha='center',va='center',fontsize=10)
    path=next(p['positions'] for p in audit['paths'] if p['expected'])
    ax.plot([p[0] for p in path],[p[1] for p in path],color='#13845b',lw=2,label='Verified reference path (grid)')
    for gate in annotation['gates']:
        ax.plot([gate['a'][0],gate['b'][0]],[gate['a'][1],gate['b'][1]],'--',color='#eb9b21',lw=2)
    ax.scatter(m['start']['x'],m['start']['y'],color='black',s=40)
    ax.text(m['start']['x'],m['start']['y']-.45,'Start',ha='center')
    ax.set(xlim=(-.5,m['layout']['end_x']+.5),ylim=(-4.1,4.1),xlabel='x (metres)',ylabel='y (metres)',
           title='Research 3: physical doorway choices\n'+m['canonical_instruction'])
    ax.set_aspect('equal')
    ax.legend(loc='lower left')
    fig.tight_layout()
    fig.savefig(args.output,dpi=160)
    plt.close(fig)


if __name__=='__main__':
    main()
