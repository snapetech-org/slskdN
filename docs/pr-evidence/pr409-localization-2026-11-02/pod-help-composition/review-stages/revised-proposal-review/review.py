import hashlib,json,pathlib,subprocess
IN_DIR=pathlib.Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-pod-help-composition-crossreview-20261102')
INPUT=IN_DIR/'cell-crossreview.jsonl'
OUT=pathlib.Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-pod-help-revised-proposal-review-20261102')
WORK=pathlib.Path('/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn')
REPO='snapetech-org/slskdN'; PR=409
HEAD='490983c336d4958f11518c73268de2788c8858cb'; TREE='01ca1bcdd5f74fd1adf6151dda441e8a77a811da'
BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
SOURCE='Enable {feature} in the server configuration to use Pod rooms and discover other Pods.'
CODE='feature.Pods'; CODE_NODE='<code dir="ltr">feature.Pods</code>'
REFINEMENTS={
 'ar':'فعّل {feature} في إعدادات الخادم لاستخدام غرف Pod واكتشاف Pods أخرى.',
 'de':'Aktiviere {feature} in der Serverkonfiguration, um Pod-Räume zu nutzen und andere Pods zu entdecken.',
 'hi':'Pod रूमों का उपयोग करने और अन्य Pods खोजने के लिए सर्वर कॉन्फ़िगरेशन में {feature} सक्षम करें।',
 'fr':'Activez {feature} dans la configuration du serveur pour utiliser les salons Pod et découvrir d’autres Pods.',
 'vi':'Bật {feature} trong cấu hình máy chủ để sử dụng các phòng Pod và tìm các Pod khác.',
 'zh-Hant':'在伺服器設定中啟用 {feature}，即可使用 Pod 房間並發現其他 Pod。',
}
REASONS={
 'ar':'The proposal says “more Pods” rather than “other Pods”; this refinement preserves the source distinction.',
 'de':'The input sentence omitted the explicit “other” sense; this refinement adds andere to match the source.',
 'fr':'Capitalize Pods to preserve the source term’s casing in both mentions.',
 'hi':'Use the oblique plural रूमों to represent multiple Pod rooms.',
 'vi':'Use các phòng Pod to mark the room plural present in the source.',
 'zh-Hant':'發現 is the closer match for discover; 尋找 is closer to search/look for.'
}

def sha(b): return hashlib.sha256(b).hexdigest()
def sha_text(s): return sha(s.encode())
def run(args,text=True,cwd=None): return subprocess.check_output(args,text=text,cwd=cwd)
def git(*args,text=True): return run(['git','-C',str(WORK),*args],text=text)
def live():
 pr=json.loads(run(['gh','pr','view',str(PR),'--repo',REPO,'--json','state,isDraft,headRefOid,headRefName,baseRefOid,url']))
 tree=run(['gh','api',f'repos/{REPO}/commits/{pr["headRefOid"]}','--jq','.commit.tree.sha']).strip()
 remote=run(['git','ls-remote',f'https://github.com/{REPO}.git',f'refs/heads/{pr["headRefName"]}']).split()[0]
 return pr,tree,remote
def verify_sums(d):
 for line in (d/'SHA256SUMS').read_text().splitlines():
  digest,name=line.split('  ',1)
  assert sha((d/name).read_bytes())==digest,name
 return sha((d/'SHA256SUMS').read_bytes())
# Validate the prior packet, candidate input, exact open PR and pinned clean worktree.
input_sums=verify_sums(IN_DIR)
prior_manifest=json.loads((IN_DIR/'manifest.json').read_text())
prior_review=json.loads((IN_DIR/'cross-review.json').read_text())
assert sha(INPUT.read_bytes())==next(x['sha256'] for x in prior_manifest['files'] if x['path']=='cell-crossreview.jsonl')
assert (prior_review['head'],prior_review['tree'])==(HEAD,TREE)
pr,tree,remote=live()
assert pr['state']=='OPEN' and pr['isDraft'] and pr['headRefOid']==HEAD and pr['headRefName']==BRANCH and tree==TREE and remote==HEAD
assert git('rev-parse','HEAD').strip()==HEAD and git('rev-parse','HEAD^{tree}').strip()==TREE and not git('status','--porcelain').strip()
rows=[json.loads(x) for x in INPUT.read_text().splitlines()]
assert len(rows)==12 and len({x['locale'] for x in rows})==12
# Caller pin: exact original UI composition in the provided task worktree.
caller_path='src/web/src/components/Messaging/MessagingV2.jsx'; caller_line=1716
caller_raw=(WORK/caller_path).read_bytes(); caller_lines=caller_raw.decode().splitlines(); caller_text=caller_lines[caller_line-1].strip()
caller_blob=git('rev-parse',f'HEAD:{caller_path}').strip()
assert caller_blob=='ab5a672ca6e1242e45da3f93247593780221eadc'
assert 'LocalizedText source={"Enable"}' in caller_text and '<code>feature.Pods</code>' in caller_text
assert 'in the server configuration to use pod rooms and discovery.' in caller_text
# Independently review all 12 candidate strings and reattest the locale files that supplied them.
OTHER_TERMS={'ar':'Pods أخرى','de':'andere Pods','es':'otros Pods','fr':'d’autres Pods','hi':'अन्य Pods','id':'Pod lainnya','ja':'他の Pod','ko':'다른 Pod','pt-BR':'outros Pods','vi':'các Pod khác','zh-Hans':'其他 Pod','zh-Hant':'其他 Pod'}
reviews=[]
for row in rows:
 loc=row['locale']; candidate=row['independentRecommendedFullSentence']
 assert candidate.count('{feature}')==1 and 'feature.Pods' not in candidate
 locale_raw=(WORK/row['localeFile']).read_bytes()
 locale_blob=git('rev-parse',f'HEAD:{row["localeFile"]}').strip()
 assert sha(locale_raw)==row['localeFileSha256'] and locale_blob==row['localeBlob']
 recommended=REFINEMENTS.get(loc,candidate)
 assert recommended.count('{feature}')==1 and 'feature.Pods' not in recommended
 rendered= recommended.replace('{feature}',CODE_NODE)
 assert rendered.count(CODE)==1 and rendered.count(CODE_NODE)==1
 assert rendered.count('{feature}')==0
 verdict='revise-proposal' if loc in REFINEMENTS else 'accept-proposal'
 reason=REASONS.get(loc,'The full sentence is grammatical and preserves the source meaning, exact Pod terminology, and a single feature placeholder in the caller context.')
 reviews.append({'locale':loc,'candidateFile':row['localeFile'],'candidateFileBlob':locale_blob,'candidateFileSha256':sha(locale_raw),'inputProposal':candidate,'inputProposalSha256':sha_text(candidate),'inputRenderedComposition':candidate.replace('{feature}',CODE_NODE),'independentVerdict':verdict,'independentRecommendedFullSentence':recommended,'independentRecommendedSha256':sha_text(recommended),'independentRenderedComposition':rendered,'reason':reason,'checks':{'placeholderCountExactlyOne':recommended.count('{feature}')==1,'featureCodeTokenExactlyOnceAfterComposition':rendered.count(CODE)==1,'exactCodeNodePreserved':rendered.count(CODE_NODE)==1,'noPlaceholderLeftUnresolved':'{feature}' not in rendered,'podRoomMeaningPresent':'Pod' in recommended,'otherPodsMeaningPresent':OTHER_TERMS[loc] in recommended,'sentencePunctuationPresent':recommended.rstrip()[-1:] in '.。؟۔!।','sourceCallerMatchesPinnedHead':True},'confidence':'moderate','nativeSpeakerApproval':False})
assert len(reviews)==12 and all(all(v for v in r['checks'].values()) for r in reviews)
# Reattest live PR/ref/tree/worktree once more after completing all judgments.
pr2,tree2,remote2=live(); state={'head':git('rev-parse','HEAD').strip(),'tree':git('rev-parse','HEAD^{tree}').strip(),'status':git('status','--porcelain').strip()}
assert pr2['state']=='OPEN' and pr2['isDraft'] and pr2['headRefOid']==HEAD and pr2['headRefName']==BRANCH and tree2==TREE and remote2==HEAD
assert state=={'head':HEAD,'tree':TREE,'status':''}
source_hash=sha_text(SOURCE)
source_pin={'sentence':SOURCE,'sha256':source_hash,'callerPath':caller_path,'callerLine':caller_line,'callerLineText':caller_text,'callerLineSha256':sha_text(caller_text),'callerFileBlob':caller_blob,'callerFileSha256':sha(caller_raw),'tree':TREE,'head':HEAD}
(OUT/'source-caller-pins.json').write_text(json.dumps({'source':source_pin,'livePullRequest':pr2,'remoteBranchHead':remote2,'worktree':state,'inputPacket':{'path':str(INPUT),'sha256':sha(INPUT.read_bytes()),'manifestSha256':sha((IN_DIR/'manifest.json').read_bytes()),'sha256sumsFileSha256':input_sums}},ensure_ascii=False,indent=2,sort_keys=True)+'\n')
(OUT/'per-locale-review.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in reviews))
summary={'schemaVersion':1,'repository':REPO,'pullRequest':PR,'head':HEAD,'tree':TREE,'sourceSha256':source_hash,'inputPath':str(INPUT),'inputSha256':sha(INPUT.read_bytes()),'inputChecksumsSha256':input_sums,'localeCount':12,'verdictCounts':{'accept-proposal':sum(r['independentVerdict']=='accept-proposal' for r in reviews),'revise-proposal':sum(r['independentVerdict']=='revise-proposal' for r in reviews),'hold':0},'placeholderPerSentence':1,'codeToken':'feature.Pods','codeTokenOccurrencesAfterComposition':1,'allLocaleFilesReattested':True,'callerPinReattested':True,'cleanWorktree':True,'nativeSpeakerApproval':False,'repositoryModified':False,'testsBuildsCiRun':False,'browserReview':False}
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
(OUT/'README.md').write_text(f'''# slskdN PR #409 revised Pod-help proposal review

Independent review of 12 full-sentence translations for:

`{SOURCE}`

PR #409 is OPEN/DRAFT at `{HEAD}` / tree `{TREE}`. Input packet checksums, the caller line at `{caller_path}:{caller_line}`, all 12 locale blobs, remote branch head, and clean worktree were reattested.

Each sentence has exactly one `{{feature}}` placeholder. Replacing it with `{CODE_NODE}` yields exactly one correctly cased `feature.Pods` token. I accepted {summary['verdictCounts']['accept-proposal']} proposals and recommend refinements to {summary['verdictCounts']['revise-proposal']}; there are no holds. The six refinements preserve “other Pods”, Pod casing, and Pod-room plurality. Japanese and Korean do not morphologically mark plural number, which is natural for those languages.

This is a machine cross-review, not native-speaker approval. No repository files were modified; no tests, builds, CI, or browser actions were run.
''')
manifest={'schemaVersion':1,'repository':REPO,'pullRequest':PR,'head':HEAD,'tree':TREE,'scope':'12 locale full-sentence candidates','input':{'path':str(INPUT),'sha256':sha(INPUT.read_bytes())},'sourceSha256':source_hash,'localeCount':12,'verdictCounts':summary['verdictCounts'],'files':[]}
for f in sorted(OUT.iterdir()):
 if f.is_file() and f.name not in ('manifest.json','SHA256SUMS'):
  manifest['files'].append({'path':f.name,'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())})
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
names=sorted(x.name for x in OUT.iterdir() if x.is_file() and x.name!='SHA256SUMS')
(OUT/'SHA256SUMS').write_text(''.join(f'{sha((OUT/n).read_bytes())}  {n}\n' for n in names))
print(json.dumps({'output':str(OUT),'head':HEAD,'tree':TREE,'verdictCounts':summary['verdictCounts'],'inputSha256':sha(INPUT.read_bytes()),'sourceCallerPin':caller_blob,'allTokensExact':all(r['checks']['featureCodeTokenExactlyOnceAfterComposition'] for r in reviews),'cleanWorktree':True},ensure_ascii=False,indent=2))
