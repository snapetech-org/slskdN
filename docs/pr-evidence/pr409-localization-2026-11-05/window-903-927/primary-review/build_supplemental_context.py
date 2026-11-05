#!/usr/bin/env python3
"""Capture extra exact-head context for rank 910, 925, and 926 review."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
INPUT=ROOT.parent.parent/'candidate-free'/'input'
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261105/slskdn-pr409-w903-927-source')
HEAD='91da6fff5d5b628ade7ee556386e3db1db6878fa'
INV='docs/pr-evidence/pr409-localization-2026-11-03/window49/primary/source-inventory.jsonl'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def git(*a): return subprocess.check_output(['git','-C',str(REPO),*a],text=True).strip()
def context(path,first,last):
    p=REPO/path; data=p.read_bytes(); lines=data.decode('utf-8').splitlines()
    return {'path':path,'fileBytes':len(data),'fileSha256':sha(data),'gitBlob':blob(data),
            'lineStart':first,'lineEnd':last,'lines':[{'line':n,'text':lines[n-1],'sha256':sha(lines[n-1].encode())} for n in range(first,last+1)]}
def main():
    if git('rev-parse','HEAD')!=HEAD or git('rev-parse','HEAD^{tree}')!='56930b73d10a4c419edf68f0d951ceedaa63c990': raise SystemExit('REFUSED: exact head/tree')
    inv=[json.loads(x) for x in subprocess.check_output(['git','-C',str(REPO),'show',f'{HEAD}:{INV}'],text=True).splitlines() if x.strip()]
    bysource={x['source']:x for x in inv}; catpins={x['locale']:x for x in (json.loads(y) for y in (INPUT/'catalog-structure.jsonl').read_text().splitlines() if y.strip())}
    related=[]
    for source,role in [('format over the canonical join/leave payload and the supplied public key.','rank-910 following fragment'),('file','rank-925 dynamic type'),('directory','rank-925 dynamic type'),('Enter true fullscreen.','rank-926 adjacent tooltip; outside W81')]:
        r=bysource[source]; targets={}
        for loc in LOCALES:
            val=json.loads((REPO/f'src/web/public/locales/{loc}.json').read_text())[source]
            targets[loc]={'text':val,'sha256':sha(val.encode())}
        related.append({'role':role,'source':source,'sourceId':r['sourceId'],'sourceSha256':r['sourceSha256'],
          'continuationRank':r['continuationRank'],'remainingQueueRank':r['remainingQueueRank'],'outsideCurrentWindow':not 903<=r['continuationRank']<=927,
          'localeTargets':targets})
    filepins=[]
    for path,first,last in [('src/web/src/components/System/MediaCore/MediaCorePods.jsx',2858,2866),
                            ('src/web/src/components/System/Files/Explorer.jsx',30,47),
                            ('src/web/src/components/Player/Visualizer.jsx',2409,2420)]:
        filepins.append(context(path,first,last))
    catalogs=[]
    for loc in LOCALES:
        p=REPO/f'src/web/public/locales/{loc}.json'; data=p.read_bytes()
        catalogs.append({'locale':loc,'path':p.relative_to(REPO).as_posix(),'bytes':len(data),'sha256':sha(data),'gitBlob':blob(data)})
    data={'artifact':'W81 primary supplemental exact-head context','head':HEAD,'tree':'56930b73d10a4c419edf68f0d951ceedaa63c990',
          'sourceInventoryPath':INV,'sourceInventorySha256':sha(subprocess.check_output(['git','-C',str(REPO),'show',f'{HEAD}:{INV}'])),
          'relatedFragments':related,'callerFilePins':filepins,'catalogFilePins':catalogs,
          'scopeNote':'Rank 1999 Enter true fullscreen. is adjacent to a selected caller but outside W81; its translations are supplied only as context and receive no W81 disposition.'}
    (ROOT/'supplemental-context.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'result':'CAPTURED','supplementalFragments':len(related),'callerFiles':len(filepins),'catalogFiles':len(catalogs),'outsideWindowRows':sum(x['outsideCurrentWindow'] for x in related)},indent=2))
if __name__=='__main__': main()
