from pathlib import Path
import collections, hashlib, json
repo=Path('/home/keith/Documents/code/task-scratch/slskdn-pr409-w65-ranks503-527-primary-20261103/source-checkout')
e=repo/'docs/pr-evidence/pr409-localization-2026-11-03/window-503-527'
base='c64d57a0322897bbaac77fa88a1327dd2f687db7'
tree='51ebf25124fc6ba30c8d5d99298e78353a951f17'
cells=[json.loads(x) for x in (e/'candidate-free-input/source-current-cells.jsonl').read_text().splitlines() if x]
cross=[json.loads(x) for x in (e/'cross-audit/crossaudit-decisions.jsonl').read_text().splitlines() if x]
counts=collections.Counter(x['crossAudit']['disposition'] for x in cross)
paths=sorted({x['catalogPath'] for x in cells})
result={'repository':'snapetech-org/slskdN','pullRequest':409,'branch':'codex/slskdn-oidc-tooltip-localization-20261030','reviewedBaseHead':base,'reviewedBaseTree':tree,'status':'catalogs applied locally; commit pin recorded in application-verification.json','cells':300,'dispositions':dict(sorted(counts.items())),'updates':counts['correction']+counts['refinement'],'updatedCatalogs':len(paths),'catalogs':{p:hashlib.sha256((repo/p).read_bytes()).hexdigest() for p in paths},'nonTargetChanges':0,'keyOrderPreserved':True,'priorHoldsPreserved':98,'newHolds':6,'workflowFilesTouched':False,'testsBuildsScansCi':'not run','releaseTagMerge':'not performed'}
(e/'application-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
entries=[]
for p in sorted(e.rglob('*')):
 if p.is_file() and p.name!='SHA256SUMS.txt':
  entries.append(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(e).as_posix()}')
(e/'SHA256SUMS.txt').write_text('\n'.join(entries)+'\n')
print(json.dumps({'evidenceFiles':len(entries)+1,'evidenceBytes':sum(p.stat().st_size for p in e.rglob('*') if p.is_file()),'updatedCatalogs':len(paths),'dispositions':dict(counts)},indent=2))
