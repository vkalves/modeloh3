import importlib.util,sys,types,json,unittest
from pathlib import Path
from unittest.mock import patch
import torch
ROOT=Path(__file__).resolve().parents[1]
sys.modules['folder_paths']=types.ModuleType('folder_paths')
p=ROOT/'custom_nodes/H3-Teste-Mascara-V1'
spec=importlib.util.spec_from_file_location('trial',p/'__init__.py',submodule_search_locations=[str(p)])
t=importlib.util.module_from_spec(spec);sys.modules['trial']=t;spec.loader.exec_module(t)
from trial.guards import validate_mask

class Checks(unittest.TestCase):
    def test_protection_removes_everything(self):
        frames=torch.full((5,64,64,3),.2)
        person=torch.ones(5,64,64);face=torch.zeros_like(person);face[:,16:32,16:32]=1
        class Track:
            @staticmethod
            def execute(images,model,conditioning,**kw):
                return ({'packed_masks':{'person':person,'face':face,'hands':face}[conditioning][:,None]},)
        class Mask:
            @staticmethod
            def execute(data,object_indices):return (data['packed_masks'][:,0],)
        sam=types.ModuleType('comfy_extras.nodes_sam3');sam.SAM3_VideoTrack=Track;sam.SAM3_TrackToMask=Mask
        clip=types.SimpleNamespace(tokenize=lambda x:x,encode_from_tokens_scheduled=lambda x:x)
        with patch.dict(sys.modules,{'comfy_extras':types.ModuleType('comfy_extras'),'comfy_extras.nodes_sam3':sam}):
            with self.assertRaisesRegex(ValueError,'protecao removeu toda'):
                t.v2.H3SmartMaskV2().run(frames,None,clip,{'person':'person','edit_regions':'face','protect_objects':'hands'},.5,12,4)
            g,b,preview=t.v2.H3SmartMaskV2().run(frames,None,clip,{'person':'person','edit_regions':'face','protect_objects':''},.5,12,4)
            self.assertTrue(bool(g.any()))
            self.assertTrue(torch.all(preview[g==1,0]>.2))

    def test_empty_frames_allowed_but_not_empty_clip(self):
        im=torch.zeros(5,64,64,3);m=torch.zeros(5,64,64);m[2,10:20,10:20]=1
        validate_mask(m,im,'test')
        with self.assertRaisesRegex(ValueError,'vazia'):validate_mask(m*0,im,'test')
        m[0,0,0]=float('nan')
        with self.assertRaisesRegex(ValueError,'NaN'):validate_mask(m,im,'test')

    def test_reference_sanitized_and_empty_blocks_before_model(self):
        im=torch.full((5,64,64,3),.2);m=torch.zeros(5,64,64);m[:,16:48,16:48]=1
        captured={}
        class Native:
            @staticmethod
            def execute(**kw):captured.update(kw);return ('positive','latent')
        native=types.ModuleType('comfy_extras.nodes_minimax_h3');native.MiniMaxH3ReferenceToVideo=Native
        with patch.dict(sys.modules,{'comfy_extras':types.ModuleType('comfy_extras'),'comfy_extras.nodes_minimax_h3':native}):
            args=(None,None,None,im,{'audio':None,'width':64,'height':64,'padded_count':5},{'prompt':'Edit @Video1 with @Image1'},'match')
            result=t.v2.H3ManualReferencesV2().run(*args,m,ref_1={'image':im[:1]})
            self.assertTrue(torch.all(result[3][m==1]==.5))
            self.assertTrue(torch.all(result[3][m==0]==.2))
            captured.clear()
            with self.assertRaisesRegex(ValueError,'vazia'):
                t.v2.H3ManualReferencesV2().run(*args,m*0,ref_1={'image':im[:1]})
            self.assertEqual(captured,{})

    def test_final_composition_preserves_generated(self):
        im=torch.full((5,64,64,3),.2);generated=torch.full_like(im,.8)
        m=torch.zeros(5,64,64);m[:,16:48,16:48]=1
        out=t.base.composite_frames(generated,m,im)
        self.assertTrue(torch.all(out[m==1]==.8));self.assertTrue(torch.all(out[m==0]==.2))

    def test_workflow_and_unique_nodes(self):
        w=json.loads((ROOT/'workflows/H3_PROMPT_UNICO_V2.json').read_text());nodes={n['id']:n for n in w['nodes']}
        for ident,src,slot,dst,inp,kind in w['links']:
            self.assertIn(ident,nodes[src]['outputs'][slot]['links'])
            self.assertEqual(nodes[dst]['inputs'][inp]['link'],ident)
        for n in w['nodes']:
            if n['type'].startswith('H3'):self.assertIn(n['type'],t.NODE_CLASS_MAPPINGS)
            self.assertEqual(n['mode'],0)
        self.assertEqual(nodes[27]['widgets_values'],['normal',20,1.0])
        self.assertEqual(nodes[22]['widgets_values'],['match'])

if __name__=='__main__':unittest.main(verbosity=2)
