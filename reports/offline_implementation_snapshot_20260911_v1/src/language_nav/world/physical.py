"""Research 3-owned passage worlds generated from one geometric specification."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import yaml


def geometry(index: int):
    # Deterministic geometric variation, independent of measured policy outcomes.
    half = 1.15 + 0.05 * (index % 3)
    doors = [4.0 + 0.15 * (index % 4), 7.5 + 0.2 * (index % 5)]
    end = doors[1] + 2.0
    depth, room_half, opening = 2.4, 1.3, 1.5
    walls = []
    def wall(name, x, y, sx, sy):
        walls.append(dict(name=name, x=x, y=y, sx=sx, sy=sy))
    wall('start_wall', 0, 0, .15, 2 * half)
    wall('end_wall', end, 0, .15, 2 * half)
    for side in (-1, 1):
        start = 0
        for number, x in enumerate(doors, 1):
            left, right = x - opening / 2, x + opening / 2
            wall(f'hall_{side}_{number}', (start + left) / 2, side * half, left - start, .15)
            start = right
            for edge in (-1, 1):
                wall(f'room_{side}_{number}_{edge}', x + edge * room_half,
                     side * (half + depth / 2), .15, depth)
            wall(f'room_end_{side}_{number}', x, side * (half + depth), 2 * room_half, .15)
            # Jamb strips connect room sides to the exact doorway opening.
            for edge in (-1, 1):
                wall(f'jamb_{side}_{number}_{edge}', x + edge * (room_half + opening / 2) / 2,
                     side * half, room_half - opening / 2, .15)
        wall(f'hall_end_{side}', (start + end) / 2, side * half, end - start, .15)
    return {'corridor_half_width': half, 'door_x': doors, 'end_x': end,
            'room_depth': depth, 'opening_width': opening, 'walls': walls}


def _box(world, name, x, y, z, sx, sy, sz, rgb, *, collide=True):
    model = ET.SubElement(world, 'model', name=name)
    ET.SubElement(model, 'static').text = 'true'
    ET.SubElement(model, 'pose').text = f'{x} {y} {z} 0 0 0'
    link = ET.SubElement(model, 'link', name='body')
    for kind in (('collision', 'visual') if collide else ('visual',)):
        item = ET.SubElement(link, kind, name=kind)
        box = ET.SubElement(ET.SubElement(item, 'geometry'), 'box')
        ET.SubElement(box, 'size').text = f'{sx} {sy} {sz}'
        if kind == 'visual':
            material = ET.SubElement(item, 'material')
            for prop in ('ambient', 'diffuse'):
                ET.SubElement(material, prop).text = ' '.join(str(v) for v in (*rgb, 1))


def build_world(destination: Path, instruction: dict, *, anchor_present=True):
    """Write SDF, occupancy map, independent gates and four candidate routes."""
    if type(anchor_present) is not bool:
        raise ValueError('anchor_present must be Boolean')
    if not anchor_present and instruction['partition'] not in {'development', 'validation'}:
        raise PermissionError('absence interventions are development/validation only')
    destination.mkdir(parents=True, exist_ok=False)
    index = int(instruction['base_instruction_id'].split('r')[-1])
    layout = geometry(index)
    half, doors = layout['corridor_half_width'], layout['door_x']
    partition = instruction['partition']
    map_id = 'r3geo_' + instruction['base_instruction_id'].replace('-', '_')
    root = ET.Element('sdf', version='1.9')
    world = ET.SubElement(root, 'world', name='default')
    for library, name in [('physics', 'Physics'), ('user-commands', 'UserCommands'),
                          ('sensors', 'Sensors'), ('imu', 'Imu'), ('contact', 'Contact')]:
        plugin = ET.SubElement(world, 'plugin', filename=f'gz-sim-{library}-system',
                               name=f'gz::sim::systems::{name}')
        if library == 'sensors':
            ET.SubElement(plugin, 'render_engine').text = 'ogre2'
    physics = ET.SubElement(world, 'physics', name='3ms', type='ode')
    ET.SubElement(physics, 'max_step_size').text = '0.003'
    ET.SubElement(physics, 'real_time_factor').text = '1'
    light = ET.SubElement(world, 'light', name='sun', type='directional')
    ET.SubElement(light, 'pose').text = '0 0 10 0 0 0'
    ET.SubElement(light, 'diffuse').text = '0.9 0.9 0.9 1'
    ET.SubElement(light, 'direction').text = '-0.5 0.1 -0.9'
    # Ground name matches the frozen support-contact filter.
    _box(world, 'ground_plane', layout['end_x']/2, 0, -.05, layout['end_x']+4, 12, .1, (.8,.8,.8))
    for w in layout['walls']:
        _box(world, w['name'], w['x'], w['y'], 1.1, w['sx'], w['sy'], 2.2, (.65,.68,.72))
    color = {'red': (0.86,.16,.16), 'blue': (.16,.27,.86),
             'green': (.16,.71,.27), 'yellow': (.9,.78,.16)}[instruction['anchor_attributes']['color']]
    chair_x, chair_y = 2.2, half - .4
    # Physical seat/back/legs, with matching conservative occupancy footprint.
    _box(world, 'chair_seat', chair_x, chair_y, .40, .42, .42, .08, color)
    _box(world, 'chair_back', chair_x, chair_y+.19, .67, .42, .05, .5, color)
    for dx in (-.16, .16):
        for dy in (-.16, .16):
            _box(world, f'chair_leg_{dx}_{dy}', chair_x+dx, chair_y+dy, .19, .04,.04,.38, (.2,.2,.2))
    if not anchor_present:
        for model in list(world.findall('model')):
            if model.attrib['name'].startswith('chair_'):
                world.remove(model)
    candidates, entities, door_entities = [], [], []
    expected_side = 1 if instruction['topology_side'] == 'left' else -1
    for side in (-1, 1):
        for ordinal, x in enumerate(doors, 1):
            route_id = f'{map_id}_{"left" if side == 1 else "right"}_{ordinal}'
            # Both same-side rooms have the same terminal category: ordinal matters.
            category = instruction['terminal_category'] if side == expected_side else (
                'office_entrance' if instruction['terminal_category'] == 'laboratory_entrance' else 'laboratory_entrance')
            rgb = (.84,.18,.57) if category == 'laboratory_entrance' else (.16,.80,.61)
            _box(world, f'{route_id}_lintel', x, side*half, 1.95, 1.5,.16,.25, (.6,.2,.75))
            _box(world, f'{route_id}_entrance_sign', x+.53, side*(half+.30), 1.05, .32,.08,.32, rgb, collide=False)
            terminal_id = route_id + '_entrance'
            candidates.append({'route_id': route_id, 'side': 'left' if side == 1 else 'right',
                               'ordinal': ordinal, 'goal': {'x': x, 'y': side*(half+.8), 'yaw': side*math.pi/2},
                               'terminal_entity_id': terminal_id})
            entities.append({'entity_id': terminal_id, 'region_id': terminal_id + '_region',
                             'category': category, 'pose': {'x': x+.53, 'y': side*(half+.30)}})
            door_entities.append({'entity_id': route_id+'_doorway', 'region_id': route_id+'_doorway_region',
                                  'category': 'doorway', 'pose': {'x':x,'y':side*half,'yaw':-side*math.pi/2},
                                  'attributes':{},'covariance':[.04,0.,0.,.04],
                                  'marker_rgb':[153,51,191],'route_ids':[route_id]})
    target = next(c for c in candidates if c['side'] == instruction['topology_side'] and c['ordinal'] == 2)
    # SDF and occupancy originate from exactly the same collision boxes.
    resolution = .05
    origin = [-1., -5., 0.]
    width, height = int(math.ceil((layout['end_x']+2)/resolution)), 200
    xx = origin[0] + (np.arange(width)+.5)*resolution
    yy = origin[1] + (np.arange(height)+.5)*resolution
    free = (xx[None,:] > 0) & (xx[None,:] < layout['end_x']) & (abs(yy[:,None]) < half)
    for x in doors:
        free |= (abs(xx[None,:]-x) < 1.3) & (abs(yy[:,None]) < half+layout['room_depth'])
    blocked = ~free
    boxes = layout['walls'] + ([dict(x=chair_x,y=chair_y,sx=.42,sy=.42)] if anchor_present else [])
    for w in boxes:
        blocked |= (abs(xx[None,:]-w['x']) <= w['sx']/2) & (abs(yy[:,None]-w['y']) <= w['sy']/2)
    pixels = np.where(blocked[::-1], 0, 254).astype('uint8')
    pgm = f'P5\n{width} {height}\n255\n'.encode()+pixels.tobytes()
    (destination/'map.pgm').write_bytes(pgm)
    map_digest = hashlib.sha256(pgm).hexdigest()
    (destination/'map.yaml').write_text(yaml.safe_dump({'image': 'map.pgm', 'resolution': resolution,
        'origin': origin, 'negate': 0, 'occupied_thresh': .65, 'free_thresh': .196}))
    ET.indent(root)
    ET.ElementTree(root).write(destination/'world.sdf', encoding='unicode')
    # A vertical gate is crossed eastward; a horizontal gate is crossed into the room.
    door_gate = {'gate_id': 'second_doorway', 'a': [doors[1]-.75, expected_side*half],
                 'b': [doors[1]+.75, expected_side*half], 'direction': expected_side}
    annotation = {'schema_version': 'ordered-instruction-geometry/v1',
        'base_instruction_id': instruction['base_instruction_id'], 'map_sha256': map_digest,
        'geometry_verified': False, 'geometry_evidence': 'pending independent occupancy/SDF audit',
        'required_gate_ids': ['corridor', 'past_chair', 'second_doorway'],
        'gates': [{'gate_id': 'corridor', 'a': [1.2,half], 'b': [1.2,-half], 'direction': 1},
                  {'gate_id': 'past_chair', 'a': [2.7,half], 'b': [2.7,-half], 'direction': 1}, door_gate]}
    annotation['forbidden_gate_ids'] = []
    for side in (-1, 1):
        for ordinal, x in enumerate(doors, 1):
            if side == expected_side and ordinal == 2:
                continue
            gate_id = f'wrong_doorway_{side}_{ordinal}'
            annotation['forbidden_gate_ids'].append(gate_id)
            annotation['gates'].append({'gate_id':gate_id, 'a':[x-.75,side*half],
                                       'b':[x+.75,side*half], 'direction':side})
    manifest = {'schema_version': 'research3-physical-world/v1', 'map_id': map_id,
        'partition': partition, 'base_instruction_id': instruction['base_instruction_id'],
        'canonical_instruction': instruction['canonical_text'], 'start': {'x': .6, 'y': 0, 'yaw': 0},
        'candidates': candidates, 'expected_route_id': target['route_id'], 'terminal_entities': entities,
        'anchor_entity_id': instruction['anchor_entity_id'], 'anchor_pose': [chair_x, chair_y],
        'layout': layout, 'map_sha256': map_digest,
        'world_sha256': hashlib.sha256((destination/'world.sdf').read_bytes()).hexdigest(),
        'map_metadata_sha256': hashlib.sha256((destination/'map.yaml').read_bytes()).hexdigest(),
        'claim_scope': 'new Research 3 geometry; no Research 1 clean-route claims inherited',
        'prior_protected_graph_access': True}
    for name, document in [('manifest.json', manifest), ('ordered_geometry.json', annotation)]:
        (destination/name).write_text(json.dumps(document, indent=2, sort_keys=True)+'\n')
    # Deployment catalogue has four alternatives and deliberately omits the answer.
    deployment = {'schema_version':'research3-physical-route-catalog/v1', 'map_id':map_id,
                  'partition':partition, 'start':manifest['start'], 'routes':candidates,
                  'map_sha256':map_digest,'world_sha256':manifest['world_sha256']}
    (destination/'execution_catalog.json').write_text(json.dumps(deployment,indent=2,sort_keys=True)+'\n')
    landmarks = [{'entity_id':instruction['anchor_entity_id'], 'region_id':map_id+'_chair_region',
                  'category':'chair','attributes':instruction['anchor_attributes'],
                  'pose':{'x':chair_x,'y':chair_y,'yaw':-math.pi/2},'covariance':[.04,0.,0.,.04],
                  'marker_rgb':[round(v*255) for v in color],'route_ids':[c['route_id'] for c in candidates]}]
    if not anchor_present:
        landmarks = []
    for entity,candidate in zip(entities,candidates):
        rgb=[214,46,145] if entity['category']=='laboratory_entrance' else [41,204,156]
        landmarks.append({**entity,'attributes':{},'covariance':[.04,0.,0.,.04],
                          'marker_rgb':rgb,'route_ids':[candidate['route_id']]})
    scene={'schema_version':'landmark-scene/v1','map_id':map_id,
           'partition':'test' if partition=='held_out' else partition,
           'map_hash':map_digest,'source':'research3-physical-world/v1',
           'entities':landmarks+door_entities}
    (destination/'landmark_scene.yaml').write_text(yaml.safe_dump(scene,sort_keys=False))
    return manifest
