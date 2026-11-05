#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,shutil
from pathlib import Path
OUT=Path(__file__).resolve().parent; ROOT=OUT.parent; CF=ROOT/'candidate-free'/'input'; PR=ROOT/'primary-review'; BL=ROOT/'blind-review'
def sha(b):return hashlib.sha256(b).hexdigest()
def j(name):return json.loads((OUT/name).read_text())
def wj(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
before=j('attestation/live-before.json'); after=j('attestation/live-after.json')
if before['headSha']!=after['headSha'] or before['headTree']!=after['headTree'] or before['apiBaseSha']!=after['apiBaseSha']:
 raise SystemExit('FAIL: PR head/tree/base changed during cross-review')
summary=j('summary.json')
summary['liveMainAtBefore']=before['liveMainSha'];summary['liveMainTreeAtBefore']=before['liveMainTree']
summary['liveMainAtAfter']=after['liveMainSha'];summary['liveMainTreeAtAfter']=after['liveMainTree']
summary['liveMainChangedDuringReview']=before['liveMainSha']!=after['liveMainSha']
summary['attestationBeforeSha256']=sha((OUT/'attestation/live-before.json').read_bytes())
summary['attestationAfterSha256']=sha((OUT/'attestation/live-after.json').read_bytes())
wj('summary.json',summary)
verifier_results={'portableVerifier':{'command':'python3 cross-review/verify_cross_review.py','result':'PASS','cells':300,'proposalsReconciled':177,'hashOnlyHolds':12},'exactWorktreeVerifier':{'command':'python3 cross-review/verify_cross_review.py /mnt/disks/scratch/task-worktrees/localization-20261105/slskdn-pr409-w928-952-pinned','result':'PASS','upstreamExactVerifiers':['candidate-free','primary','blind'],'exactHead':'fc8e42a06363ceee762ae084bbe716953d4a5d94','exactTree':'e04aa06b8cfb0ee41cae90aef601a0552b5e85bd'},'recordedAfterSuccessfulVerifierRuns':True}
wj('verifier-results.json',verifier_results)
tracked=['README.md','summary.json','input-pins.json','cross-review-ledger.jsonl','proposal-reconciliation.jsonl','holds-hash-only.jsonl','verify_cross_review.py','build_cross_review.py','finalize_cross_review.py','attestation/attest_live_refs.py','attestation/live-before.json','attestation/live-after.json','attestation/live-final.json','verifier-results.json']
manifest={'schemaVersion':1,'repository':'snapetech-org/slskdN','pullRequest':409,'branch':summary['branch'],'window':'W83','scope':{'continuationRanks':[953,977],'remainingQueueRanks':[853,877],'sourceIds':25,'locales':['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant'],'cells':300},'head':summary['head'],'tree':summary['tree'],'apiBase':summary['apiBase'],'liveMainBefore':before['liveMainSha'],'liveMainTreeBefore':before['liveMainTree'],'liveMainAfter':after['liveMainSha'],'liveMainTreeAfter':after['liveMainTree'],'liveMainChangedDuringReview':before['liveMainSha']!=after['liveMainSha'],'candidateFreeManifestSha256':sha((CF/'manifest.json').read_bytes()),'primaryManifestSha256':sha((PR/'manifest.json').read_bytes()),'blindManifestSha256':sha((BL/'manifest.json').read_bytes()),'recommendationCounts':summary['recommendationCounts'],'proposalRecordsReconciled':summary['proposalRecordsReconciled'],'hashOnlyHolds':summary['crossHoldCount'],'artifactPins':{name:{'path':name,'sha256':sha((OUT/name).read_bytes())} for name in tracked},'candidateFreeOnlySourceInputs':True,'nativeSpeakerSignoff':False,'repositoryOrPullRequestEdited':False,'applicationPerformed':False,'result':'PASS'}
wj('manifest.json',manifest)
# Make the final limitations and hold reason clear in the standalone reader guide.
(OUT/'README.md').write_text(f'''# slskdN PR #409 W953–W977 semantic cross-review

This cross-review covers continuation ranks 953–977 and remaining-queue ranks 853–877: 25 source IDs × 12 locales = 300 cells. It is pinned to open draft PR head `{summary['head']}` / tree `{summary['tree']}`, API base `{summary['apiBase']}`, and live main `{before['liveMainSha']}` at entry and `{after['liveMainSha']}` at exit. The PR head, tree, base, branch ref, pull ref, and clean exact-head worktree were unchanged.

The review reconciles the candidate-free source/current/caller packet with the primary and blind packets. The 300-row ledger binds source, current target, caller context, and candidate-free row hashes; every selected target and all 177 proposals passed placeholder, markup, numeric, and protected-literal checks. The proposal reconciliation accounts for all 111 primary corrections and 66 blind proposals. It recommends 114 changed targets, accepts 174 current targets, accepts eight identical primary/blind targets, and makes one explicit wording adjustment.

All 12 cells for source rank 966 (`left`) remain hash-only. Its 52 pinned production references are layout/alignment attributes, not demonstrated user-facing localization calls. The primary Arabic proposal is not accepted because the localization meaning is not established. The hold packet omits source, current-target, and proposal text.

`attestation/live-before.json` and `attestation/live-after.json` capture the live PR API state, base, branch/pull refs, main ref, Git trees, and clean worktree. `input-pins.json` binds the exact candidate-free, primary, and blind packet hashes. `verify_cross_review.py` checks the cross ledger and upstream packet seals; pass `--repo` as the exact-head worktree path to rerun all upstream exact-worktree verifiers.

No repository or PR content was edited; no translations were applied. No tests, builds, CI, browser review, or native-speaker signoff are claimed. Confidence is moderate because this is machine-assisted multilingual review.
''')
# Remove only Python bytecode generated by this task's local script compilation.
cache=OUT/'__pycache__'
if cache.exists():shutil.rmtree(cache)
files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
(OUT/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(OUT).as_posix()}\n' for p in files))
print(json.dumps({'files':len(files)+1,'manifestPins':len(manifest['artifactPins']),'head':manifest['head'],'tree':manifest['tree'],'liveMainBefore':manifest['liveMainBefore'],'liveMainAfter':manifest['liveMainAfter'],'result':manifest['result']},indent=2))
