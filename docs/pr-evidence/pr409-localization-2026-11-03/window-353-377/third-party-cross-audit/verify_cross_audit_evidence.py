#!/usr/bin/env python3
"""Verify the sealed W59 cross-audit artifacts against pinned review packets and Git."""
from __future__ import annotations
import argparse, collections, hashlib, json, re, subprocess
from pathlib import Path

OUT=Path(__file__).resolve().parent
INPUT=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w59-ranks353-377-primary-20261103/input')
PRIMARY=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w59-ranks353-377-primary-20261103')
BLIND=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w59-independent-blind-20261103')
REPO_DEFAULT=Path('/home/keith/Documents/code/slskdn')
HEAD='fd6bf5c72a668eecac8cc57e4587bced7e4d9aad'
TREE='01c4bb4ea231e6ba72c3087d133b6e3e669853d9'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PH=re.compile(r'\{[^{}]+\}')
MARKUP=re.compile(r'</?[A-Za-z][^>]*>')
NUMBER=re.compile(r'(?<![A-Za-z])\d+(?:[.,]\d+)?%?(?![A-Za-z])')

def sha(data):
    if isinstance(data,str): data=data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def read_jsonl(p): return [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args])
def verify_manifest(p):
    entries=[]
    for line in p.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        expected,rel=line.split(None,1); rel=rel.strip().lstrip('*')
        relpath=Path(rel)
        assert not relpath.is_absolute() and '..' not in relpath.parts,(p,rel)
        actual=sha((p.parent/relpath).read_bytes())
        entries.append((rel,expected,actual))
    assert entries and all(expected==actual for _,expected,actual in entries),(p,entries)
    return entries

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',type=Path,default=REPO_DEFAULT)
    args=ap.parse_args(); repo=args.repo.resolve()
    # Verify all four packet checksum layers before reading any candidate decisions.
    packet_files=verify_manifest(INPUT/'PACKET-SHA256SUMS.txt')
    primary_review_files=verify_manifest(PRIMARY/'review/AGENT-SHA256SUMS.txt')
    primary_task_files=verify_manifest(PRIMARY/'TASK-SHA256SUMS.txt')
    blind_files=verify_manifest(BLIND/'SHA256SUMS.txt')
    audit_files=verify_manifest(OUT/'SHA256SUMS.txt')
    assert git(repo,'rev-parse',f'{HEAD}^{{tree}}').decode().strip()==TREE
    manifest=json.loads((INPUT/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['head']==HEAD and manifest['tree']==TREE and manifest['cellCount']==300
    assert sorted(manifest['locales'])==sorted(LOCALES)
    inp=read_jsonl(INPUT/'source-current-cells.jsonl')
    primary=read_jsonl(PRIMARY/'review/primary-ledger.jsonl')
    blind=read_jsonl(BLIND/'blind-decisions.jsonl')
    final=read_jsonl(OUT/'cross-audit-ledger.jsonl')
    key=lambda x:(x['continuationRank'],x['locale'])
    I={key(x):x for x in inp}; P={key(x):x for x in primary}; B={key(x):x for x in blind}; F={key(x):x for x in final}
    assert len(I)==len(P)==len(B)==len(F)==300 and set(I)==set(P)==set(B)==set(F)
    catalogs={}; blobs={}
    for locale in LOCALES:
        path=f'src/web/public/locales/{locale}.json'
        raw=git(repo,'show',f'{HEAD}:{path}')
        digest=sha(raw); blob=git(repo,'rev-parse',f'{HEAD}:{path}').decode().strip()
        exemplar=next(x for x in inp if x['locale']==locale)
        assert digest==exemplar['catalogFileSha256'] and blob==exemplar['catalogGitBlob']
        catalogs[locale]=json.loads(raw); blobs[locale]=blob
    counts=collections.Counter(); changes=0; disposition_pairs=collections.Counter(); disp_diff=0; target_diff=0; same_disp_target_diff=0
    for k,i in I.items():
        p=P[k]; b=B[k]; f=F[k]
        assert (f['head'],f['tree'],f['sourceId'],f['source'],f['sourceSha256'],f['locale'],f['catalogFileSha256'],f['catalogGitBlob'],f['currentTarget'],f['currentTargetSha256'])==(HEAD,TREE,i['sourceId'],i['source'],i['sourceSha256'],i['locale'],i['catalogFileSha256'],i['catalogGitBlob'],i['currentTarget'],i['currentTargetSha256']),k
        assert catalogs[i['locale']].get(i['source'])==i['currentTarget'],k
        assert f['primaryReview']['ledgerRowSha256']==sha(canon(p))
        p_selected=p['proposedTarget'] if p.get('proposedTarget') is not None else i['currentTarget']
        assert f['primaryReview']['selectedTarget']==p_selected and f['primaryReview']['selectedTargetSha256']==sha(p_selected)
        assert f['blindReview']['ledgerRowSha256']==sha(canon(b))
        assert f['primaryReview']['callerContextSha256']==i['callerContextSha256'] and f['blindReview']['callerCount']==len(i['callerRefs'])
        assert f['callerEvidence']['references']==i['callerRefs'] and f['callerEvidence']['callerCount']==len(i['callerRefs'])
        assert f['currentTargetSha256']==sha(i['currentTarget']) and f['selectedTargetSha256']==sha(f['selectedTarget'])
        assert f['changeFromCurrent']==(f['selectedTarget']!=i['currentTarget'])
        counts[f['disposition']]+=1; changes+=int(f['changeFromCurrent'])
        disposition_pairs[(p['verdict'],b['disposition'])]+=1
        disp_diff+=int(p['verdict']!=b['disposition'])
        p_target=p.get('proposedTarget') if p.get('proposedTarget') is not None else i['currentTarget']
        td=p_target!=b['selectedTarget']; target_diff+=int(td)
        same_disp_target_diff+=int(td and p['verdict']==b['disposition'])
        assert collections.Counter(PH.findall(i['source']))==collections.Counter(PH.findall(f['selectedTarget'])),k
        assert MARKUP.findall(i['source'])==MARKUP.findall(f['selectedTarget']),k
        assert NUMBER.findall(i['source'])==NUMBER.findall(f['selectedTarget']),k
        assert all(lit in f['selectedTarget'] for lit in p.get('structuralChecks',{}).get('protectedLiterals',{}).get('expected',[])),k
        assert (len(i['source'])-len(i['source'].lstrip(' ')),len(i['source'])-len(i['source'].rstrip(' ')))==(len(f['selectedTarget'])-len(f['selectedTarget'].lstrip(' ')),len(f['selectedTarget'])-len(f['selectedTarget'].rstrip(' '))),k
        if i['continuationRank'] in (356,366):
            assert len(i['callerRefs'])==0 and p['verdict']==b['disposition']=='hold'
            assert f['disposition']=='hold' and f['selectedTarget']==i['currentTarget']
    assert counts=={'accept-current':207,'correction':54,'refinement':15,'hold':24}
    assert changes==69 and disp_diff==39 and target_diff==53 and same_disp_target_diff==15
    supplement=json.loads((OUT/'supplemental-catalog-context.json').read_text(encoding='utf-8'))
    for source_key,locale_map in supplement['catalogKeyEvidence'].items():
        for locale,e in locale_map.items():
            assert catalogs[locale][source_key]==e['translatedValue']
            assert sha(e['translatedValue'])==e['valueSha256']
            assert blobs[locale]==e['catalogGitBlob']
    ds=json.loads((OUT/'disagreement-and-hold-summary.json').read_text(encoding='utf-8'))
    assert len(ds['dispositionDisagreementCells'])==disp_diff and len(ds['selectedTargetDisagreementCells'])==target_diff
    assert len(ds['sameDispositionDifferentTargetCells'])==same_disp_target_diff and len(ds['callerlessHolds'])==24
    summary=json.loads((OUT/'summary.json').read_text(encoding='utf-8'))
    assert summary['dispositions']==dict(sorted(counts.items()))
    assert summary['selectedCatalogChanges']==changes
    assert summary['primaryBlindDispositionDisagreements']==disp_diff
    assert summary['primaryBlindSelectedTargetDisagreements']==target_diff
    assert summary['sameDispositionDifferentTargetCells']==same_disp_target_diff
    assert summary['nativeSpeakerApproval'] is False and summary['releaseApprovedByThisCrossAudit'] is False
    att=json.loads((OUT/'attestation.json').read_text(encoding='utf-8'))
    assert att['head']==HEAD and att['tree']==TREE and att['rowCount']==300 and att['selectedChangeCount']==69
    assert att['nativeSpeakerApproval'] is False and att['releaseApproved'] is False
    print(json.dumps({'status':'verified','repository':str(repo),'head':HEAD,'tree':TREE,'rows':len(F),'dispositions':dict(sorted(counts.items())),'selectedChanges':changes,'dispositionDisagreements':disp_diff,'selectedTargetDisagreements':target_diff,'sameDispositionDifferentTargetCells':same_disp_target_diff,'callerlessHolds':len(ds['callerlessHolds']),'packetManifestFilesVerified':len(packet_files)+len(primary_review_files)+len(primary_task_files)+len(blind_files),'auditArtifactFilesVerified':len(audit_files)},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
