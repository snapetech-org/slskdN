from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import hashlib, json, subprocess

ROOT=Path(__file__).resolve().parent
CF=ROOT/'candidate-free'
WT=Path('/mnt/disks/scratch/task-worktrees/localization-20261104/slskdn-pr409-w76-778-802-source')
OUT=ROOT/'blind-review'; OUT.mkdir(exist_ok=True)
REPO='snapetech-org/slskdN'; BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
HEAD='674156749ee86021ef91d896b1824be62cff9a93'; TREE='86483dbf9227130cade6a3f4c9dc9ef5cf232450'

def run_json(args): return json.loads(subprocess.run(args,check=True,text=True,capture_output=True).stdout)
def git(*args): return subprocess.run(['git','-C',str(WT),*args],check=True,text=True,capture_output=True).stdout.strip()
def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def readjl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x]

pr=run_json(['gh','api',f'repos/{REPO}/pulls/409'])
branch=run_json(['gh','api',f'repos/{REPO}/branches/{BRANCH}'])
pullref=run_json(['gh','api',f'repos/{REPO}/git/ref/pull/409/head'])
base=run_json(['gh','api',f"repos/{REPO}/git/commits/{pr['base']['sha']}"])
main=run_json(['gh','api',f'repos/{REPO}/branches/main'])
wt_head=git('rev-parse','HEAD'); wt_tree=git('rev-parse','HEAD^{tree}'); wt_status=git('status','--porcelain')
assert pr['number']==409 and pr['state']=='open' and pr['head']['sha']==HEAD and pr['head']['ref']==BRANCH
assert pr['base']['sha']=='f25d263a2a7cdb2c8f76c40c346cb10f749a9356'
assert branch['commit']['sha']==HEAD and pullref['object']['sha']==HEAD
assert wt_head==HEAD and wt_tree==TREE and not wt_status
pre={
 'attestedAtUtc':datetime.now(timezone.utc).isoformat(),'repo':REPO,
 'pullRequest':{'number':409,'state':pr['state'],'draft':pr['draft'],'headRef':pr['head']['ref'],'headSha':pr['head']['sha'],'headTree':wt_tree,'baseRef':pr['base']['ref'],'baseSha':pr['base']['sha'],'baseTree':base['tree']['sha']},
 'branchRef':{'name':branch['name'],'sha':branch['commit']['sha'],'tree':branch['commit']['commit']['tree']['sha']},
 'pullRef':{'ref':pullref['ref'],'sha':pullref['object']['sha']},
 'liveMain':{'name':main['name'],'sha':main['commit']['sha'],'tree':main['commit']['commit']['tree']['sha']},
 'sourceWorktree':{'path':str(WT),'head':wt_head,'tree':wt_tree,'clean':True},
 'candidateFree':{'copiedPath':str(CF),'manifestSha256':hashlib.sha256((CF/'manifest.json').read_bytes()).hexdigest(),'checksumsSha256':hashlib.sha256((CF/'PACKET-SHA256SUMS.txt').read_bytes()).hexdigest()},
 'baseDriftNote':'PR base f25d263a2a7cdb2c8f76c40c346cb10f749a9356 differs from live main bc6251ff4ea5a7e59f2d86e2400c90520601f46e. Root cross-review reported four intervening commits affecting workflows, AGENTS.md, docs, and policy scripts, with no localization source/catalog changes.'}
(ROOT/'live-attestation-before-review.json').write_text(json.dumps(pre,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

manifest=readj(CF/'manifest.json')
selected=readjl(CF/'source-inventory-selection.jsonl')
contexts={x['sourceId']:x for x in readjl(CF/'caller-contexts.jsonl')}
cells=readjl(CF/'source-current-cells.jsonl')
assert manifest['window']=='W76' and manifest['head']==HEAD and manifest['tree']==TREE
assert manifest['sourceCount']==25 and manifest['cellCount']==300 and len(selected)==25 and len(cells)==300

proposals={}
def prop(rank,loc,target,reason): proposals[(rank,loc)]=(target,reason)
release={
'ar':'اسم الفنان في Release Radar','de':'Künstlername für Release Radar','es':'Nombre del artista para Release Radar','fr':'Nom de l’artiste pour Release Radar','hi':'Release Radar के लिए कलाकार का नाम','id':'Nama artis untuk Release Radar','ja':'Release Radar のアーティスト名','ko':'Release Radar 아티스트 이름','pt-BR':'Nome do artista para o Release Radar','vi':'Tên nghệ sĩ cho Release Radar','zh-Hans':'Release Radar 艺人姓名','zh-Hant':'Release Radar 藝人姓名'}
for loc,t in release.items(): prop(779,loc,t,'The current wording reads as releasing, publishing, or publicizing an artist name. The caller is an artist-name input in the Release Radar panel; this names the field and retains the feature name.')
job={'ar':'المهام','es':'Tareas','fr':'Tâches','hi':'कार्य','id':'Tugas','ja':'ジョブ','ko':'작업','pt-BR':'Tarefas','vi':'Tác vụ','zh-Hans':'任务','zh-Hant':'任務'}
for loc,t in job.items(): prop(781,loc,t,'The callers show a system Jobs menu and a health check over runtime job states. This means background jobs/tasks, while the current locale wording denotes employment or vacancies.')
notfound={'ar':'لم يتم العثور على مهام','es':'No se encontraron tareas','fr':'Aucune tâche trouvée','hi':'कोई कार्य नहीं मिला','id':'Tidak ada tugas yang ditemukan','ja':'ジョブが見つかりませんでした','ko':'작업을 찾을 수 없습니다','pt-BR':'Nenhuma tarefa encontrada','vi':'Không tìm thấy tác vụ nào','zh-Hans':'未找到任务','zh-Hant':'找不到任務'}
for loc,t in notfound.items(): prop(786,loc,t,'The caller is the empty state in the system jobs list, and another caller reads failed job states. The current wording in this locale denotes employment or vacancies rather than background tasks.')
route={'ar':'أرسل إلى المحلفين','de':'An die Geschworenen senden','es':'Enviar a los jurados','fr':'Envoyer aux jurés','hi':'जूरी सदस्यों को भेजें','id':'Kirim ke juri','ja':'陪審員に送信','pt-BR':'Enviar aos jurados','vi':'Gửi đến bồi thẩm đoàn','zh-Hans':'发送给陪审员','zh-Hant':'傳送給陪審員'}
for loc,t in route.items(): prop(788,loc,t,'The caller is a paper-plane action button; its nearby tooltip says the request is sent only to listed target jurors. The current wording describes a route or path rather than the action.')
prop(791,'hi','localhost:{localPort} पर अग्रेषण बंद करें और स्थानीय मार्ग की आवश्यकता न रहने पर यह टनल बंद कर दें।','The caller is tunnel guidance. Keep {localPort} attached directly to localhost as a host:port token; the current Hindi placement puts it after the verb instead.')
prop(794,'id','Penerusan Port','Callers use this for network port forwarding through VPN tunnels. The current Indonesian “Pelabuhan” means a harbor; use the network term “Port”.')
prop(798,'vi','URL cơ sở đã được cấu hình','The callers use this as a readiness status label. The current Vietnamese wording is an imperative; this proposal expresses the configured state and retains the protected literal URL.')
prop(798,'zh-Hans','基本 URL 已配置','The callers use this as a readiness status label. The current wording is an imperative; this proposal expresses the configured state and retains the protected literal URL.')
prop(798,'zh-Hant','基本 URL 已設定','The callers use this as a readiness status label. The current wording is an imperative; this proposal expresses the configured state and retains the protected literal URL.')
prop(800,'es','16 pulsos','The caller identifies a Native MilkDrop beats-per-preset value, so this means musical beats rather than heartbeats. The proposal keeps the exact numeric token.')
prop(801,'ko','라이브러리 상태 검사 경로','The caller is a path field for the Library Health scan recipe. Current Korean “검색” means search; use a term for a status scan or inspection.')

keep={
778:'Checkbox label in Metadata Settings enabling Chromaprint; current imperative is accurate and preserves the product name.',
780:'MediaCore card header for publishing a Content Descriptor to the DHT; current wording preserves the technical term and action.',
781:'System menu and health-check callers identify background jobs; German “Jobs” is established software terminology and fits this context.',
782:'Automation cooldown/cadence value; current target preserves the 15-minute duration.',
784:'Popup explanation for clearing imported native presets from this browser; current target preserves action and browser scope.',
785:'Chat input placeholder and log/table label; current target is the appropriate generic noun.',
786:'Empty state in the system jobs list; German “Jobs” is established software terminology and fits this context.',
787:'Description of the signing workflow; current target preserves signing, signature verification, and key-pair generation.',
788:'The caller is a paper-plane action button; Korean wording conveys delivering the request to the jurors.',
789:'Last-updated time display; current wording preserves the update state and {time} placeholder.',
790:'Graph-reason text; current target preserves the connection, evidence edges, and {count} meaning.',
791:'Tunnel-management tooltip; current wording preserves localhost port, stopping action, and tunnel closure.',
792:'Error fallback when a native visualizer parameter edit fails; current target reports that failure accurately.',
794:'Network port forwarding in a VPN tunnel panel; current translation names the correct network function.',
797:'DHT policy explanation; current target preserves private/local discovery and the public-bootstrap-router warning.',
798:'Readiness status label; current target expresses that the base URL is configured and retains URL.',
799:'Channel-name input; current target is a concise field label.',
800:'Native MilkDrop beats-per-preset option; current target preserves the numeric value and musical-unit meaning.',
801:'Path field for the Library Health scan recipe; current target accurately names its path setting.'}

rows=[]
for c in cells:
    rank,loc,sid=c['continuationRank'],c['locale'],c['sourceId']; ctx=contexts[sid]; callerless=ctx['productionCallerCount']==0
    d={'schema':'slskdn-blind-cell-v1','continuationRank':rank,'remainingQueueRank':c['remainingQueueRank'],'sourceId':sid,'locale':loc,
       'sourceSha256':c['sourceSha256'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'productionCallerCount':ctx['productionCallerCount'],
       'catalogPath':c['catalogPath'],'catalogFileSha256':c['catalogFileSha256'],'catalogGitBlob':c['catalogGitBlob']}
    if callerless:
        d.update(disposition='hold',sourceTextIncluded=False,currentTargetIncluded=False,proposalIncluded=False,
         rationale='The pinned caller scan found no production caller for this key, so its intended meaning cannot be confirmed. Preserve this cell as a text-free hold until caller context is available.')
    elif rank==783:
        d.update(disposition='hold',sourceText=c['source'],sourceTextIncluded=True,currentTarget=c['currentTarget'],currentTargetIncluded=True,proposalIncluded=False,
         sourceProtectedLiterals=c['sourceProtectedLiterals'],currentProtectedLiterals=c['currentProtectedLiterals'],placeholderEvidence=c['placeholderEvidence'],markupEvidence=c['markupEvidence'],
         rationale='The caller is the minimum-source input in the Federated Taste Recommendations panel, but it does not settle whether “taste sources” is a product term to preserve or should be rephrased as recommendation sources. Hold for domain clarification.')
    elif (rank,loc) in proposals:
        target,reason=proposals[(rank,loc)]
        d.update(disposition='propose',sourceText=c['source'],sourceTextIncluded=True,currentTarget=c['currentTarget'],currentTargetIncluded=True,proposal=target,proposalSha256=sha(target),proposalIncluded=True,
         sourceProtectedLiterals=c['sourceProtectedLiterals'],currentProtectedLiterals=c['currentProtectedLiterals'],placeholderEvidence=c['placeholderEvidence'],markupEvidence=c['markupEvidence'],sourceNumericTokens=c['sourceNumericTokens'],rationale=reason)
    else:
        assert rank in keep,(rank,loc)
        d.update(disposition='keep',sourceText=c['source'],sourceTextIncluded=True,currentTarget=c['currentTarget'],currentTargetIncluded=True,recommendedTarget=c['currentTarget'],recommendedTargetSha256=c['currentTargetSha256'],proposalIncluded=False,
         sourceProtectedLiterals=c['sourceProtectedLiterals'],currentProtectedLiterals=c['currentProtectedLiterals'],placeholderEvidence=c['placeholderEvidence'],markupEvidence=c['markupEvidence'],sourceNumericTokens=c['sourceNumericTokens'],rationale=f'{keep[rank]} Keep the current {loc} translation.')
    rows.append(d)

sources=[]
for s in selected:
    sid=s['sourceId']; ctx=contexts[sid]; c=next(x for x in cells if x['sourceId']==sid); callerless=ctx['productionCallerCount']==0
    r={'continuationRank':s['continuationRank'],'remainingQueueRank':s['remainingQueueRank'],'sourceId':sid,'sourceSha256':s['sourceSha256'],'callerContextSha256':c['callerContextSha256'],
       'productionCallerCount':ctx['productionCallerCount'],'callerEvidenceSha256':sha(canon(ctx)),'sourceTextIncluded':not callerless,'callerRefsIncluded':not callerless}
    if not callerless: r.update(sourceText=s['source'],callers=ctx['callers'])
    sources.append(r)

(OUT/'review-cells.jsonl').write_text(''.join(canon(r)+'\n' for r in rows),encoding='utf-8')
(OUT/'review-sources.jsonl').write_text(''.join(canon(r)+'\n' for r in sources),encoding='utf-8')
prior=(CF/'prior-held-cell-reattestation-hash-only.jsonl').read_bytes()
(OUT/'prior-held-cells-hash-only.jsonl').write_bytes(prior)
counts=Counter(r['disposition'] for r in rows)
meta={'schema':'slskdn-blind-review-packet-v1','repo':REPO,'pullRequest':409,'window':'W76','continuationRanks':[778,802],'remainingQueueRanks':[678,702],
 'sourceCount':25,'cellCount':300,'localeOrder':manifest['locales'],'inputHead':HEAD,'inputTree':TREE,'prBaseSha':pr['base']['sha'],'prBaseTree':base['tree']['sha'],
 'liveMainSha':main['commit']['sha'],'liveMainTree':main['commit']['commit']['tree']['sha'],'candidateFreeManifestSha256':pre['candidateFree']['manifestSha256'],'candidateFreeChecksumsSha256':pre['candidateFree']['checksumsSha256'],
 'reviewMethod':'Independent cell-by-cell review against pinned source, locale target, exact production callers, and placeholder/numeric/protected-literal evidence; primary-review material was not opened.',
 'counts':dict(counts),'callerlessTextFreeHolds':sum(r['disposition']=='hold' and r.get('sourceTextIncluded') is False for r in rows),
 'contextualHolds':sum(r['disposition']=='hold' and r.get('sourceTextIncluded') is True for r in rows),'priorHeldCellsPreserved':len(prior.decode().splitlines()),
 'baselineProtectedLiteralMismatchCells':manifest['baselineTokenMismatchSummary']['protectedLiteral'],'baselineMismatchDisposition':'All baseline protected-literal mismatch cells are callerless and remain text-free holds.',
 'nativeSpeakerReview':'Not claimed.'}
(OUT/'review-packet.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

verifier=r'''#!/usr/bin/env python3
import argparse,hashlib,json,re
from pathlib import Path

def digest(b): return hashlib.sha256(b).hexdigest()
def textsha(s): return digest(s.encode('utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x]
def fail(s): raise SystemExit('FAIL: '+s)
def sums(folder,path):
 for line in path.read_text(encoding='utf-8').splitlines():
  if not line.strip(): continue
  h,rel=line.split('  ',1); f=folder/rel
  if not f.is_file() or digest(f.read_bytes())!=h: fail('checksum mismatch: '+str(f))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--packet-root',type=Path,default=Path(__file__).resolve().parent.parent);root=ap.parse_args().packet_root.resolve();cf=root/'candidate-free';out=root/'blind-review'
 sums(root,root/'SHA256SUMS.txt');sums(out,out/'SHA256SUMS.txt')
 manifest=json.loads((cf/'manifest.json').read_text());meta=json.loads((out/'review-packet.json').read_text());inputs=jl(cf/'source-current-cells.jsonl');dec=jl(out/'review-cells.jsonl');callers={x['sourceId']:x for x in jl(cf/'caller-contexts.jsonl')}
 if len(inputs)!=300 or len(dec)!=300:fail('expected exactly 300 cells')
 ix={(x['sourceId'],x['locale']):x for x in inputs};seen=set();counts={'keep':0,'propose':0,'hold':0}
 for d in dec:
  k=(d['sourceId'],d['locale'])
  if k in seen or k not in ix:fail('duplicate/unmatched cell '+str(k))
  seen.add(k);c=ix[k];ctx=callers[d['sourceId']]
  for f in ('continuationRank','remainingQueueRank','sourceSha256','currentTargetSha256','callerContextSha256','catalogPath','catalogFileSha256','catalogGitBlob'):
   if d.get(f)!=c.get(f):fail('binding mismatch '+str(k)+' '+f)
  if d['sourceSha256']!=textsha(c['source']) or d['currentTargetSha256']!=textsha(c['currentTarget']):fail('source/target hash mismatch '+str(k))
  cl=ctx['productionCallerCount']==0
  if d.get('productionCallerCount')!=ctx['productionCallerCount']:fail('caller count mismatch '+str(k))
  if cl:
   if d.get('disposition')!='hold' or d.get('sourceTextIncluded') is not False or d.get('currentTargetIncluded') is not False or d.get('proposalIncluded') is not False:fail('callerless cell is not text-free hold '+str(k))
   if any(f in d for f in ('sourceText','currentTarget','proposal','recommendedTarget')):fail('callerless text leaked '+str(k))
  else:
   if d.get('sourceTextIncluded') is not True or d.get('currentTargetIncluded') is not True or d.get('sourceText')!=c['source'] or d.get('currentTarget')!=c['currentTarget']:fail('cell text mismatch '+str(k))
   disp=d.get('disposition')
   if disp=='keep':
    if d.get('recommendedTarget')!=c['currentTarget'] or d.get('recommendedTargetSha256')!=c['currentTargetSha256'] or 'proposal' in d:fail('keep mismatch '+str(k))
   elif disp=='propose':
    p=d.get('proposal')
    if not isinstance(p,str) or not p or d.get('proposalSha256')!=textsha(p) or d.get('proposalIncluded') is not True:fail('bad proposal '+str(k))
    if d.get('sourceProtectedLiterals')!=c['sourceProtectedLiterals']:fail('protected-literal binding missing '+str(k))
    for lit in c['sourceProtectedLiterals']:
     if lit not in p:fail('proposal lost protected literal '+str(k))
    if sorted(re.findall(r'\{[^{}]+\}|%[^%]+%|<[^>]+>',p))!=sorted(c['placeholderEvidence']['sourceTokens']):fail('placeholder mismatch '+str(k))
    for tok in c['sourceNumericTokens']:
     if not re.search(r'(?<!\d)'+re.escape(tok)+r'(?!\d)',p):fail('numeric token mismatch '+str(k))
   elif disp!='hold':fail('bad disposition '+str(k))
  if not d.get('rationale'):fail('missing rationale '+str(k))
  counts[d['disposition']]+=1
 if seen!=set(ix):fail('incomplete cell coverage')
 if counts!=meta['counts']:fail('count mismatch')
 src=jl(out/'review-sources.jsonl')
 if len(src)!=25:fail('expected 25 source rows')
 for s in src:
  ctx=callers[s['sourceId']]
  if ctx['productionCallerCount']==0:
   if s.get('sourceTextIncluded') is not False or s.get('callerRefsIncluded') is not False or 'sourceText' in s or 'callers' in s:fail('callerless source text leaked')
  elif s.get('sourceText')!=ctx['source'] or s.get('callers')!=ctx['callers']:fail('caller evidence mismatch '+s['sourceId'])
 inp=(cf/'prior-held-cell-reattestation-hash-only.jsonl').read_bytes();outp=(out/'prior-held-cells-hash-only.jsonl').read_bytes()
 if inp!=outp or len(outp.splitlines())!=meta['priorHeldCellsPreserved']:fail('prior holds not preserved')
 for line in outp.decode().splitlines():
  r=json.loads(line)
  if r.get('sourceTextIncluded') is not False or r.get('targetTextIncluded') is not False:fail('prior hold is not text-free')
 if manifest.get('head')!=meta['inputHead'] or manifest.get('tree')!=meta['inputTree']:fail('head/tree mismatch')
 print('PASS: 300/300 cells, source/current/caller/catalog bindings, callerless text-free holds, proposal hashes and tokens, prior holds, and SHA256 manifests verified.')
 print('counts='+json.dumps(counts,sort_keys=True))
if __name__=='__main__':main()
'''
(OUT/'verify_blind_packet.py').write_text(verifier,encoding='utf-8'); (OUT/'verify_blind_packet.py').chmod(0o755)

readme=f'''# slskdN PR #409 W76 blind review

Independent blind dispositions for continuation ranks 778–802 (remaining-queue ranks 678–702), covering 300 cells across 12 locales.

## Pins and boundary

- Candidate-free input copy: `../candidate-free/` (copied from `/home/keith/Documents/code/task-scratch/slskdn-pr409-w76-778-802-primary-20261104/candidate-free/input/`).
- Primary review/proposals were not opened before this packet was written.
- PR API, branch ref, and pull ref agree at head `{HEAD}`; tree `{TREE}`.
- PR API base `{pr['base']['sha']}` (tree `{base['tree']['sha']}`); live main `{main['commit']['sha']}` (tree `{main['commit']['commit']['tree']['sha']}`). Root cross-review reports four intervening commits affecting workflows, AGENTS.md, docs and policy scripts, with no localization source/catalog changes.
- Exact source worktree `{WT}` was clean at the pinned head/tree.
- No product edits, tests, builds, scans, or CI were run. Native-speaker review is not claimed.

## Counts

- Keep: {counts['keep']}
- Propose: {counts['propose']}
- Hold: {counts['hold']} ({meta['callerlessTextFreeHolds']} callerless text-free cells; {meta['contextualHolds']} context-dependent cells)
- Prior held cells re-attested and preserved hash-only: {meta['priorHeldCellsPreserved']}
- Baseline protected-literal mismatch cells: {meta['baselineProtectedLiteralMismatchCells']}; all remain text-free holds because they are within callerless keys.

Exact dispositions and rationales are in `review-cells.jsonl`; source and caller evidence is in `review-sources.jsonl`. The previous held-cell record is preserved byte-for-byte as `prior-held-cells-hash-only.jsonl`.

## Verification

Run from any directory with Python 3:

```sh
python3 verify_blind_packet.py --packet-root {ROOT}
```

The stdlib-only verifier checks both checksum manifests, all 300 source/current/caller/catalog bindings, text-free callerless holds, proposal hashes and protected literals/placeholders/numeric tokens, and byte-for-byte prior-hold preservation. The candidate-free verifier is rerun at seal against the pinned source worktree.
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')
print('Created',len(rows),'cell decisions:',dict(counts),'callerless text-free holds',meta['callerlessTextFreeHolds'],'contextual holds',meta['contextualHolds'])
