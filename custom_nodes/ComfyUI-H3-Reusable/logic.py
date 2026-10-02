"""Pure prompt/timing utilities, independent of ComfyUI and GPU."""
import math
import re

SECTIONS = ('subject_definitions', 'summary', 'retention_analysis', 'detailed_description', 'overall_soundscape', 'non_diegetic_music')

def timing(duration):
    frames = max(1, int(math.floor(duration * 24 + 1e-6)))
    internal = max(5, frames)
    internal += (5 - internal) % 17
    return frames, internal

def canvas(width, height, long_edge):
    scale = min(1.0, long_edge / max(width, height))
    return max(32, round(width * scale / 32) * 32), max(32, round(height * scale / 32) * 32)

def reference_items(slots):
    result = []
    for slot in slots:
        if slot and slot.get('image') is not None:
            result.append(slot)
    if not result:
        raise ValueError('Carregue pelo menos uma imagem de referencia. Os slots VAZIO sao ignorados.')
    return result

def build_prompt(brief, roles, duration, has_audio):
    # The loaded slots, not their visual positions, determine Picture numbering.
    if not roles:
        raise ValueError('Nenhuma referencia carregada.')
    for value in list(brief.values()) + list(roles):
        if re.search(r'<(?:Picture|Video|Audio|Subject)\s+\d+>|@(?:Image|Video)\d+', str(value)):
            raise ValueError('Os rotulos de referencia sao automaticos: remova @Image/@Video e <Picture N> dos campos de texto.')
    sources = '; '.join(f'<Picture {i}> provides {role.strip() or "additional visual identity details of the replacement person"}' for i, role in enumerate(roles, 1))
    definitions = [
        '<Subject 1> is the original target person in <Video 1>: ' + brief['target'] + '.',
        '<Subject 2> is the replacement person defined by the loaded appearance references: ' + sources + '.',
        '<Video 1> is the already-trimmed source clip. It defines the scene, every shot and cut, camera, framing, perspective, scale, positions, movement, action timing, lighting, occlusions, visible text and recording texture.'
    ]
    if has_audio:
        definitions.append('<Audio 1> is the synchronized original soundtrack of <Video 1>.')
    summary = '[video editing + reference generation' + (' + audio reuse' if has_audio else '') + '] The target video is an edited version of <Video 1>. Replace the entire visible <Subject 1> with <Subject 2>, while retaining the source action and the rest of the recorded scene.'
    retention = [
        '<Subject 1> (wherever visible in the source timeline): partially_preserved - retain only the original position, scale, pose, movement and interaction timing; replace the original visible identity, body, hair and clothing.',
        '<Subject 2> (at the target person\'s location throughout the source timeline): attribute_transfer - transfer the referenced face, body, hair, skin, glasses, tattoos, clothes and footwear as applicable. Keep these attributes consistent across frames.',
        '<Video 1> (all source shots and transitions): partially_preserved - replace only the target person. Preserve all other people, objects, background, camera motion, lighting, occlusion order and shot timing.'
    ]
    if has_audio:
        retention.append('<Audio 1>: fully_copy - reuse the source soundtrack as the complete final audio track, without adding or replacing sounds.')
    details = (
        f'From 00:00.000 to {duration:.3f} seconds, follow the source timeline of <Video 1>, including every existing shot boundary; introduce no new shots. '
        'At each appearance of <Subject 1>, show <Subject 2> in the same screen position and at the same scale, following the recorded head motion, gaze, mouth motion, body motion, hand motion and finger placement. '
        'Replace the entire visible person: face, head, hair, glasses, neck, skin, torso, arms, hands, fingers, waist, hips, legs, tattoos, clothing and visible footwear. '
        'Every visible part belongs consistently to the replacement identity; retain natural anatomy and the source lighting on the new person. '
        + brief['action'].strip() + '\n' + brief['preserve'].strip() + '\n' + brief['appearance'].strip()
    )
    values = ['\n'.join(definitions), summary, '\n'.join(retention), details,
              'Reuse <Audio 1> unchanged and synchronized with the recorded action. No additional sound effects.' if has_audio else 'The source clip has no audio. Export a silent video.',
              'Preserve only music already present in <Audio 1>; add no music.' if has_audio else 'N/A']
    return '\n\n'.join(f'{key}:\n{value}' for key, value in zip(SECTIONS, values))
