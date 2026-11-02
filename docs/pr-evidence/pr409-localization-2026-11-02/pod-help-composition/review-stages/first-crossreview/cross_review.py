import hashlib,json,pathlib,re,subprocess
IN=pathlib.Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-pod-help-composition-review-20261102/composition-review-input.json')
IN_DIR=IN.parent
OUT=pathlib.Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-pod-help-composition-crossreview-20261102')
WORK=pathlib.Path('/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn')
REPO='snapetech-org/slskdN'; PR=409
EXPECTED_HEAD='490983c336d4958f11518c73268de2788c8858cb'; EXPECTED_TREE='01ca1bcdd5f74fd1adf6151dda441e8a77a811da'
CODE='<code dir="ltr">feature.Pods</code>'
REVISED_SOURCE='Enable {feature} in the server configuration to use Pod rooms and discover other Pods.'
REFINEMENTS={
'ar':'فعّل {feature} في إعدادات الخادم لاستخدام غرف Pod واكتشاف المزيد من Pods.',
'de':'Aktiviere {feature} in der Serverkonfiguration, um Pod-Räume zu nutzen und Pods zu entdecken.',
'es':'Activa {feature} en la configuración del servidor para usar las salas de Pod y descubrir otros Pods.',
'fr':'Activez {feature} dans la configuration du serveur pour utiliser les salons Pod et découvrir d’autres pods.',
'hi':'Pod रूम इस्तेमाल करने और अन्य Pods खोजने के लिए सर्वर कॉन्फ़िगरेशन में {feature} सक्षम करें।',
'id':'Aktifkan {feature} di konfigurasi server untuk menggunakan ruang Pod dan menemukan Pod lainnya.',
'ja':'Pod ルームを利用して他の Pod を見つけるには、サーバー設定で {feature} を有効にしてください。',
'ko':'Pod 대화방을 사용하고 다른 Pod를 찾으려면 서버 설정에서 {feature}를 활성화하세요.',
'pt-BR':'Ative {feature} na configuração do servidor para usar salas de Pod e descobrir outros Pods.',
'vi':'Bật {feature} trong cấu hình máy chủ để sử dụng phòng Pod và tìm các Pod khác.',
'zh-Hans':'在服务器配置中启用 {feature}，即可使用 Pod 房间并发现其他 Pod。',
'zh-Hant':'在伺服器設定中啟用 {feature}，即可使用 Pod 房間並尋找其他 Pod。'
}
REASONS={
'ar':'تعبير «ميزة الاستكشاف» عام؛ الصياغة المقترحة توضّح أن المقصود اكتشاف Pods أخرى.',
'de':'„Discovery-Funktion“ bleibt abstrakt; die vorgeschlagene Verbform nennt ausdrücklich das Entdecken anderer Pods.',
'es':'«La función de descubrimiento» no indica qué se descubre; la propuesta lo aclara con «descubrir otros Pods».',
'fr':'«La découverte» est trop abstrait ici; la proposition précise qu’il s’agit de découvrir d’autres pods.',
'hi':'«खोज सुविधा» सामान्य खोज का अर्थ दे सकता है; प्रस्ताव स्पष्ट करता है कि उपयोगकर्ता अन्य Pods खोजते हैं।',
'id':'«Fitur penemuan» tidak menyebut apa yang ditemukan; usulan menyatakan secara langsung bahwa pengguna menemukan Pod lain.',
'ja':'「検出機能」は障害物などの検知とも読めます。提案は他の Pod を見つける意味を明確にします。',
'ko':'“검색 기능”은 일반 검색을 뜻할 수 있습니다. 제안은 다른 Pod를 찾는 기능임을 분명히 합니다.',
'pt-BR':'«A descoberta» fica abstrata; a proposta deixa claro que a função permite descobrir outros Pods.',
'vi':'“Tính năng khám phá” chưa nêu rõ đối tượng; đề xuất nói cụ thể là tìm các Pod khác.',
'zh-Hans':'“发现功能”没有说明发现什么；建议明确为发现其他 Pod。',
'zh-Hant':'「探索功能」未說明探索對象；建議明確寫出尋找其他 Pod。'
}

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_text(s): return sha_bytes(s.encode())
def run(args,text=True,cwd=None): return subprocess.check_output(args,text=text,cwd=cwd)
def git(*args,text=True): return run(['git','-C',str(WORK),*args],text=text)
def live_pr():
 p=json.loads(run(['gh','pr','view',str(PR),'--repo',REPO,'--json','state,isDraft,headRefOid,headRefName,baseRefOid,url']))
 tree=run(['gh','api',f'repos/{REPO}/commits/{p["headRefOid"]}','--jq','.commit.tree.sha']).strip()
 remote=run(['git','ls-remote',f'https://github.com/{REPO}.git',f'refs/heads/{p["headRefName"]}']).split()[0]
 return p,tree,remote
def checksums_valid(d):
 for line in (d/'SHA256SUMS').read_text().splitlines():
  digest,name=line.split('  ',1)
  assert sha_bytes((d/name).read_bytes())==digest,(name,digest)
 return sha_bytes((d/'SHA256SUMS').read_bytes())
def line_at(path,n):
 raw=(WORK/path).read_bytes(); lines=raw.decode().splitlines()
 assert 1<=n<=len(lines)
 return raw,lines[n-1]
# Verify frozen input and live object before any review judgment is written.
input_sums_hash=checksums_valid(IN_DIR)
manifest=json.loads((IN_DIR/'manifest.json').read_text()); data=json.loads(IN.read_text())
assert manifest['files']['composition-review-input.json']==sha_bytes(IN.read_bytes())
assert (manifest['inputHead'],manifest['inputTree'])==(EXPECTED_HEAD,EXPECTED_TREE)
assert (data['head'],data['tree'],data['pr'],data['repository'],data['state'],data['draft'])==(EXPECTED_HEAD,EXPECTED_TREE,PR,REPO,'OPEN',True)
pr,api_tree,remote=live_pr()
assert pr['state']=='OPEN' and pr['isDraft'] and pr['headRefOid']==EXPECTED_HEAD and api_tree==EXPECTED_TREE and remote==EXPECTED_HEAD
assert git('rev-parse','HEAD').strip()==EXPECTED_HEAD and git('rev-parse','HEAD^{tree}').strip()==EXPECTED_TREE and not git('status','--porcelain').strip()
# Reattest caller bytes/line and exact locale blobs, sizes, key values, and current fragments.
caller=data['caller']; caller_raw,caller_line=line_at(caller['path'],caller['line'])
assert sha_bytes(caller_raw)==caller['fileSha256'] and git('rev-parse',f'HEAD:{caller["path"]}').strip()==caller['blob']
assert caller_line.strip()==caller['lineText']
localized_rich_path='src/web/src/components/Shared/LocalizedText.jsx'
rich_raw=(WORK/localized_rich_path).read_bytes(); rich_text=rich_raw.decode()
rich_blob=git('rev-parse',f'HEAD:{localized_rich_path}').strip()
assert sha_bytes(rich_raw)==sha_bytes(git('show',f'{EXPECTED_HEAD}:{localized_rich_path}',text=False))
assert 'export const LocalizedRichText = ({ source, values = {} })' in rich_text
assert 'return typeof value === \'string\' || typeof value === \'number\'' in rich_text
assert ' : <Fragment key={index}>{value}</Fragment>' in rich_text
assert 'LocalizedRichText' not in caller_line
product_context=[]
for path,lines_wanted in [
 ('src/web/src/components/Pods/Pods.jsx',[660,663,669]),
 ('src/web/src/components/Messaging/MessagingV2.jsx',[1527]),
]:
 raw=(WORK/path).read_bytes(); lines=raw.decode().splitlines(); blob=git('rev-parse',f'HEAD:{path}').strip()
 refs=[]
 for number in lines_wanted:
  text=lines[number-1].strip()
  refs.append({'line':number,'lineText':text,'lineSha256':sha_text(text)})
 product_context.append({'path':path,'blob':blob,'fileSha256':sha_bytes(raw),'references':refs})
locale_rows=[]
for loc in data['locales']:
 raw=(WORK/loc['path']).read_bytes(); obj=json.loads(raw)
 blob=git('rev-parse',f'HEAD:{loc["path"]}').strip()
 assert sha_bytes(raw)==loc['fileSha256'] and blob==loc['blob'],loc['locale']
 assert len(obj)==loc['keyCount'] and obj['Enable']==loc['enable'] and obj[data['currentSourceKey']]==loc['fragment'],loc['locale']
 source=data['newEnglishSource']; candidate=data['translationCandidates'][loc['locale']]
 revised=REFINEMENTS[loc['locale']]
 assert candidate==loc['proposedFullSentence']
 assert candidate.count('{feature}')==1 and revised.count('{feature}')==1
 assert CODE.count('feature.Pods')==1
 old_comp=f"{loc['enable']} {CODE} {loc['fragment']}"
 primary_render=candidate.replace('{feature}',CODE)
 revised_render=revised.replace('{feature}',CODE)
 reason=REASONS[loc['locale']]
 locale_rows.append({
  'locale':loc['locale'],'localeFile':loc['path'],'localeBlob':blob,'localeFileSha256':sha_bytes(raw),'localeKeyCount':len(obj),
  'currentEnableTranslation':loc['enable'],'currentFragmentTranslation':loc['fragment'],'currentComposedSentenceWithCode':old_comp,
  'proposedFullSentence':candidate,'proposedFullSentenceSha256':sha_text(candidate),'renderedProposedSentenceWithCode':primary_render,
  'independentVerdict':'revise-proposal','independentRecommendedFullSentence':revised,'independentRecommendedSha256':sha_text(revised),'renderedRecommendedSentenceWithCode':revised_render,
  'reason':reason,'checks':{'featurePlaceholderExactlyOnce':True,'codeTokenExactlyOnceAfterReactComposition':revised_render.count('feature.Pods')==1,'codeTokenExactCaseAndSpelling':'<code dir="ltr">feature.Pods</code>' in revised_render,'ReactNodeSupportedByPinnedLocalizedRichText':True,'PodRoomsTermPresent':'Pod' in revised_render,'discoveryMeaningExplicit':True,'sentenceFinalPunctuation':revised.strip()[-1:] in '。.!؟،۔','noUnescapedMarkupInTranslationText':'<code' not in revised,'currentLocaleCatalogValueAttested':True},
  'confidence':'moderate','nativeSpeakerApproval':False
 })
assert len(locale_rows)==12 and {x['locale'] for x in locale_rows}=={x['locale'] for x in data['locales']}
# Current source itself uses fragmented strings around a code node; assess exact baseline composition.
expected_old=' '.join([])
assert caller_line.strip()==data['caller']['lineText']
# The caller sentence is currently split into two localization keys and a React code element.
assert 'LocalizedText source={"Enable"}' in caller_line and '<code>feature.Pods</code>' in caller_line and data['currentSourceKey'] in caller_line
# Final PR/head/tree/ref and clean worktree reattestation before writing the packet summary.
pr2,api_tree2,remote2=live_pr(); repo_state={'head':git('rev-parse','HEAD').strip(),'tree':git('rev-parse','HEAD^{tree}').strip(),'status':git('status','--porcelain').strip()}
assert pr2['state']=='OPEN' and pr2['isDraft'] and pr2['headRefOid']==EXPECTED_HEAD and api_tree2==EXPECTED_TREE and remote2==EXPECTED_HEAD
assert repo_state=={'head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'status':''}
review={'schemaVersion':1,'reviewType':'independent full-sentence composition review','repository':REPO,'pullRequest':PR,'head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'inputPath':str(IN),'inputSha256':sha_bytes(IN.read_bytes()),'inputManifestSha256':sha_bytes((IN_DIR/'manifest.json').read_bytes()),'inputChecksumsSha256':input_sums_hash,'livePullRequest':pr2,'remoteBranchHead':remote2,'worktree':repo_state,'caller':{'path':caller['path'],'blob':caller['blob'],'fileSha256':caller['fileSha256'],'line':caller['line'],'lineSha256':sha_text(caller_line.strip()),'importsCurrentlyIncludeLocalizedRichText':False},'localizedRichTextImplementation':{'path':localized_rich_path,'blob':rich_blob,'fileSha256':sha_bytes(rich_raw),'supportsReactNodeValues':True,'codeTokenRecommendedAs':'<code dir="ltr">feature.Pods</code>'},'productContextEvidence':product_context,'source':{'currentEnglishKey':data['newEnglishSource'],'recommendedClarification':REVISED_SOURCE,'sourceDesignIssue':'“pod rooms and discovery” leaves discovery as an abstract noun without naming what is discovered. The pinned Pod UI identifies a pod discovery index and discovered pods, so wording “discover other Pods” is clearer and supports consistent translations. This is a terminology clarification recommendation, not a source edit.'},'localeCount':len(locale_rows),'verdictCounts':{'revise-proposal':len(locale_rows),'accept-proposal':0,'hold':0},'localeReviews':locale_rows,'limitations':['Machine cross-review is not native-speaker approval.','The wording “other Pods” is inferred from the pinned Pod discovery index and discovered-pods UI text; product owner should confirm this intended meaning.'],'repositoryModified':False,'testsBuildsCiRun':False,'browserReview':False,'nativeSpeakerApproval':False}
(OUT/'live-reattestation.json').write_text(json.dumps({'passed':True,'head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'livePullRequest':pr2,'remoteBranchHead':remote2,'worktree':repo_state,'inputChecksumSha256':input_sums_hash,'callerPinVerified':True,'localeFilePinsVerified':len(locale_rows),'localizedRichTextBlob':rich_blob,'productContextRefs':sum(len(x['references']) for x in product_context)},ensure_ascii=False,indent=2,sort_keys=True)+'\n')
(OUT/'product-context-reattestation.json').write_text(json.dumps(product_context,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
(OUT/'cell-crossreview.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in locale_rows))
(OUT/'cross-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
summary={'schemaVersion':1,'repository':REPO,'pullRequest':PR,'head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'scope':'12 target phrases evaluated with the React code placeholder in full-sentence context','localeCount':len(locale_rows),'verdictCounts':review['verdictCounts'],'candidateRefinements':len(locale_rows),'placeholderOccurrencesPerCandidate':1,'codeToken':'feature.Pods','codeNode':'<code dir="ltr">feature.Pods</code>','callerBlob':caller['blob'],'localizedRichTextBlob':rich_blob,'sourceDesignIssue':review['source']['sourceDesignIssue'],'recommendedEnglishSource':REVISED_SOURCE,'liveReattestationPassed':True,'worktreeClean':True,'nativeSpeakerApproval':False,'testsBuildsCiRun':False,'browserReview':False,'repositoryModified':False}
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
README=f'''# slskdN PR #409 Pod-help composition cross-review

This read-only review evaluates all 12 proposed translations in the actual UI composition with the exact React node `<code dir="ltr">feature.Pods</code>`.

## Pin and evidence

PR #409 is OPEN/DRAFT at `{EXPECTED_HEAD}` / tree `{EXPECTED_TREE}`. The remote PR branch, API tree, exact-head task worktree, caller line, all 12 locale files, and `LocalizedRichText` implementation were reattested. Input packet checksums validate. The worktree is clean.

The caller currently concatenates localized “Enable”, the code element, and a localized fragment. `LocalizedRichText` accepts React nodes as placeholder values and preserves them as React children, so the full-sentence approach is supported. The caller needs to import `LocalizedRichText`; the inline code element should set `dir="ltr"` to preserve the exact configuration key in RTL text.

## Review

All 12 primary proposals were revised to express discovering other Pods as an action, instead of leaving “discovery” as an abstract feature name. This matches the pinned UI text about the Pod discovery index and discovered Pods. The packet records the prior candidate, independently recommended full sentence, rendered composition, placeholder/code checks, rationale, and exact locale file hashes for each locale.

The English source also has a design ambiguity: “Pod rooms and discovery” does not say what discovery refers to. Recommended clarification: `{REVISED_SOURCE}`. This follows the pinned pod discovery-index context. Confirm that interpretation before application if product semantics differ.

No repository or PR files were changed; no tests, builds, CI, or browser actions were run. This machine cross-review is not native-speaker approval.
'''
(OUT/'README.md').write_text(README)
manifest_out={'schemaVersion':1,'repository':REPO,'pullRequest':PR,'head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'sourceInput':{'path':str(IN),'sha256':sha_bytes(IN.read_bytes())},'localeCount':len(locale_rows),'verdictCounts':review['verdictCounts'],'files':[]}
for f in sorted(OUT.iterdir()):
 if f.is_file() and f.name not in ('manifest.json','SHA256SUMS'):
  manifest_out['files'].append({'path':f.name,'bytes':f.stat().st_size,'sha256':sha_bytes(f.read_bytes())})
(OUT/'manifest.json').write_text(json.dumps(manifest_out,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
names=sorted(f.name for f in OUT.iterdir() if f.is_file() and f.name!='SHA256SUMS')
(OUT/'SHA256SUMS').write_text(''.join(f'{sha_bytes((OUT/n).read_bytes())}  {n}\n' for n in names))
print(json.dumps({'output':str(OUT),'head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'verdicts':review['verdictCounts'],'inputChecksum':input_sums_hash,'localeRows':len(locale_rows),'codeTokenPreserved':all(x['checks']['codeTokenExactlyOnceAfterReactComposition'] for x in locale_rows),'cleanWorktree':True,'sourceIssue':review['source']['sourceDesignIssue']},ensure_ascii=False,indent=2))
