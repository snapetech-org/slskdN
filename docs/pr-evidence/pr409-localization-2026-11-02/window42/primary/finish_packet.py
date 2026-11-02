from __future__ import annotations
import hashlib, json, re, subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

repo=Path('/mnt/disks/scratch/task-worktrees/localization-20261102/slskdn-pr409-w40-root')
bundle=Path('/mnt/disks/scratch/task-worktrees/localization-20261030/slskdn-populated-review-4c2b-20261101/bundle')
out=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window42-primary-20261102')
w41=repo/'docs/pr-evidence/pr409-localization-2026-11-02/window41'
formal_path=repo/'docs/pr-evidence/pr409-localization-2026-11-02/window36/primary/formal-cell-ids.jsonl'
head_expected='1b518a69d099032c497149102751271eddb0fa57'
tree_expected='c7f351a3507a3758a10369632feeb7a001e83aeb'
locales=['zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
all_locales=locales+['es']

def sha(b): return hashlib.sha256(b).hexdigest()
def shat(s): return sha(s.encode('utf-8'))
def jlines(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def writej(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def writejl(p,xs): p.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in xs),encoding='utf-8')
def git(*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def blob(path): return git('rev-parse',f'HEAD:{path}')
head=git('rev-parse','HEAD'); tree=git('rev-parse','HEAD^{tree}'); status=git('status','--porcelain')
if head!=head_expected or tree!=tree_expected or status: raise SystemExit(f'wrong or dirty review input {head} {tree} {status!r}')
source_tree=git('rev-parse','HEAD:src/web/src'); locale_tree=git('rev-parse','HEAD:src/web/public/locales')

# Read all catalogs and verify common ordered key set.
catalogs={}; catmeta={}; common_keys=None; keyset_hash=None
for loc in all_locales:
 p=f'src/web/public/locales/{loc}.json'; raw=(repo/p).read_bytes(); d=json.loads(raw); keys=list(d)
 if len(keys)!=6169: raise SystemExit(f'{loc}: expected 6169 keys, found {len(keys)}')
 if common_keys is None: common_keys=keys; keyset_hash=sha(json.dumps(keys,ensure_ascii=False,separators=(',',':')).encode())
 elif keys!=common_keys: raise SystemExit(f'catalog key order differs: {loc}')
 catalogs[loc]=d; catmeta[loc]={'locale':loc,'path':p,'gitBlobOid':blob(p),'fileSha256':sha(raw),'entryCount':len(d),'orderedKeySetSha256':keyset_hash}

source_rows=jlines(out/'source-slice.jsonl')
if len(source_rows)!=25 or [r['sourceOrdinal'] for r in source_rows]!=list(range(51,76)): raise SystemExit('source slice does not contain ordinals 51–75')
source_by_id={r['sourceId']:r for r in source_rows}

# Reproduce selection from checksummed W1–W41 inputs and frozen pending inventory.
order41=json.loads((w41/'primary/order-evidence.json').read_text()); previous_ids=set(); input_att=[]
for a in order41['w1Through39ReviewInputAttestations']:
 rawpath=a['path']
 p=(Path('/mnt/disks/scratch/task-scratch')/rawpath[len('scratch:'):]) if rawpath.startswith('scratch:') else (repo/rawpath)
 rows=jlines(p); digest=sha(p.read_bytes()); ids={r['sourceId'] for r in rows}
 if digest!=a['sha256'] or len(rows)!=a['rows']: raise SystemExit(f'prior input hash/count mismatch W{a["window"]}')
 previous_ids.update(ids); input_att.append({'window':a['window'],'path':str(p),'rows':len(rows),'sha256':digest,'uniqueSourceIds':len(ids),'verified':True})
for window,rel in [(40,'docs/pr-evidence/pr409-localization-2026-11-02/window40/primary/review-input.jsonl'),(41,'docs/pr-evidence/pr409-localization-2026-11-02/window41/primary/review-input.jsonl')]:
 p=repo/rel; rows=jlines(p); digest=sha(p.read_bytes()); ids={r['sourceId'] for r in rows}; previous_ids.update(ids)
 input_att.append({'window':window,'path':str(p),'rows':len(rows),'sha256':digest,'uniqueSourceIds':len(ids),'verified':True})
pending_ids=set()
for loc in locales:
 for r in jlines(bundle/'pending'/f'{loc}.jsonl'): pending_ids.add(r['sourceId'])
if len(previous_ids)!=1022: raise SystemExit(f'expected 1,022 prior source IDs, got {len(previous_ids)}')
remaining=sorted(pending_ids-previous_ids)
selected=[r['sourceId'] for r in source_rows]
if remaining[:25]!=selected: raise SystemExit('W42 next-25 source selection did not reproduce')
prior_hold_ids=set(order41['priorHoldSourceIds'])
if not prior_hold_ids.issubset(previous_ids): raise SystemExit('one of the historic hold sources is missing from prior windows')

# Source baseline rows, exact current targets, placeholders, markup, protected literals.
allrows={}
for loc in locales:
 for r in jlines(bundle/'all'/f'{loc}.jsonl'): allrows[(loc,r['sourceId'])]=r
for s in source_rows:
 if shat(s['source'])!=s['sourceSha256']: raise SystemExit(f'source hash failed: {s["sourceId"]}')
 for loc in locales:
  b=allrows.get((loc,s['sourceId']))
  if not b or b['sourceSha256']!=s['sourceSha256'] or b['source']!=s['source']: raise SystemExit(f'frozen row mismatch: {loc}:{s["sourceId"]}')

# Candidate proposals are pinned to source and current-target hashes below.
C={}
def add(ord,loc,kind,target,reason,confidence='moderate'):
 C[(ord,loc)]={'reviewDisposition':kind,'candidateTarget':target,'rationale':reason,'confidence':confidence}
# 51 route messages / target peers / dedup state.
add(51,'ko','propose-correction','메시지를 라우팅하고 대상 피어를 지정하며 중복 제거 상태를 검토합니다.','The Korean current text coordinates “message” and “target peers” awkwardly as objects of route; the caller describes three operations. This states them as routing messages, selecting destination peers, and reviewing deduplication state.','high')
add(51,'vi','propose-correction','Định tuyến tin nhắn, nhắm đến các nút ngang hàng và xem xét trạng thái loại bỏ trùng lặp.','The current phrase “mục tiêu ngang hàng” reads as a noun phrase (“peer goal”) rather than targeting peers. The caller describes message routing to peers; this uses the Vietnamese network term “nút ngang hàng”.','high')
# 52 report copy action.
add(52,'fr','propose-refinement','Copier le rapport d’organisation des tags pour {name}','In this playlist-tag context, “balises” can be read as markup tags. “Tags” is the clearer metadata term and retains the named playlist placeholder.','moderate')
add(52,'ja','propose-refinement','「{name}」のタグ整理レポートをコピー','The caller labels a button that copies a report for the named playlist. This makes the object and action explicit and preserves {name}; the current noun-style “copy of” can read as a report title.','moderate')
add(52,'ko','propose-refinement','{name}의 태그 정리 보고서를 복사','The caller labels an action button. This uses a direct action form and “tag organization” as tag cleanup/organization, while preserving {name}.','moderate')
# 53 matched status/count.
add(53,'de','propose-refinement','Zugeordnet','The source is a completed match state and a count label, not merely an item that is suitable. “Zugeordnet” better signals a track matched/assigned by the intake flow.','moderate')
add(53,'hi','propose-refinement','मिलान किए गए','The caller uses this as the matched-track state and before a matched count. This past-participle form is clearer than “मेल खाने वाले” (“matching ones”) for completed matches.','moderate')
add(53,'ja','propose-correction','一致','The caller uses the string as a compact status and before a count; the current “一致しました” is a full past-tense sentence. The concise noun/status fits both UI uses.','high')
add(53,'fr','propose-refinement','Correspondance','The key is a compact matched-state label and also precedes the number of matched playlist tracks. “Correspondance” names the match; current “Correspondant” means corresponding/correspondent.','moderate')
add(53,'pt-BR','propose-refinement','Correspondência','The same key labels a matched state and a matched-track count. The noun “Correspondência” fits both displays more naturally than a gendered participle without a following noun.','moderate')
add(53,'zh-Hans','propose-refinement','已匹配','The caller uses this as a completed status and before a count. “已匹配” expresses completed matching more naturally than the attributive “匹配的” in that count label.','moderate')
add(53,'zh-Hant','propose-refinement','已匹配','The caller uses this as a completed status and before a count. “已匹配” expresses completed matching more naturally than the attributive “匹配的” in that count label.','moderate')
# 56 Arabic visualizer.
add(56,'ar','propose-correction','إخفاء عارض MilkDrop','The current “مرئي” means “visible” and does not name the visualizer. Nearby Arabic visualizer controls use “عارض”/“متخيل”; “عارض MilkDrop” preserves the product name and identifies the control.','high')
# 59 Lidarr wanted albums and sync destination.
add(59,'zh-Hans','propose-refinement','预览 Lidarr 中标记为想要、且可同步到 slskdN 愿望清单的专辑。','The source describes albums wanted in Lidarr, rather than “Lidarr wanted albums” as a compound. This makes the relation explicit and preserves the protected slskdN name.','moderate')
add(59,'hi','propose-correction','उन एल्बमों का पूर्वावलोकन करें जिन्हें Lidarr चाहता है और जिन्हें slskdN विशलिस्ट में सिंक किया जा सकता है।','The current Hindi wording is a fragment with “preview” followed by an unclear Lidarr/albums sequence. This makes Lidarr the subject that wants the albums and keeps the sync destination explicit.','high')
add(59,'de','propose-refinement','Vorschau auf die von Lidarr als gewünscht markierten Alben, die mit der slskdN-Wunschliste synchronisiert werden können.','The caller is a preview tooltip for Lidarr’s wanted-album state. This avoids the ambiguous compound “Lidarr-Alben” and preserves slskdN.','moderate')
add(59,'ja','propose-refinement','Lidarrで希望されているアルバムのうち、slskdNのウィッシュリストに同期できるものをプレビューします。','The current “Lidarr の希望アルバム” is an awkward compound. This states that Lidarr wants the albums and keeps the sync destination explicit.','moderate')
add(59,'fr','propose-correction','Prévisualiser les albums que Lidarr souhaite obtenir et qui peuvent être synchronisés dans la liste de souhaits de slskdN.','The current “Aperçu Lidarr voulait des albums” reads as a broken clause (“Preview Lidarr wanted albums”). This expresses the intended relation, sync action, and protected product name.','high')
add(59,'pt-BR','propose-refinement','Pré-visualize os álbuns que o Lidarr deseja e que podem ser sincronizados com a lista de desejos do slskdN.','The source says Lidarr wants these albums; the current “álbuns desejados do Lidarr” is understandable but less explicit. This keeps the Wishlist destination and protected name.','moderate')
add(59,'ar','propose-correction','عاين الألبومات التي يريدها Lidarr ويمكن مزامنتها مع قائمة أمنيات slskdN.','The current word order does not clearly identify Lidarr as the source of the wanted status. This makes the relation explicit and preserves slskdN.','high')
add(59,'ko','propose-correction','Lidarr가 원하는 앨범 중 slskdN 위시리스트에 동기화할 수 있는 항목을 미리 봅니다.','The current Korean parses as “Preview Lidarr wanted...” in past tense. This makes Lidarr the subject and names the albums that can be synced.','high')
add(59,'zh-Hant','propose-refinement','預覽 Lidarr 中標記為想要、且可同步到 slskdN 願望清單的專輯。','The source describes albums wanted in Lidarr, rather than “Lidarr wanted albums” as a compound. This makes the relation explicit and preserves the protected slskdN name.','moderate')
add(59,'vi','propose-refinement','Xem trước các album mà Lidarr muốn có và có thể đồng bộ vào Danh sách mong muốn của slskdN.','The current translation is understandable, but this makes the intended Lidarr wanted status and the sync destination clearer. It preserves the product name.','moderate')
add(59,'id','propose-refinement','Pratinjau album yang diinginkan oleh Lidarr dan dapat disinkronkan ke Daftar Keinginan slskdN.','Adding “oleh” makes Lidarr the explicit source of the wanted status; the current is understandable but can be read as an album category.','moderate')
# 63 Wishlist policy.
add(63,'fr','propose-correction','Activé et autorisé au téléchargement automatique selon la politique de la liste de souhaits.','The source specifically names the Wishlist policy. The current “politique de la liste” omits the wish-list meaning and reads as an unspecified list.','high')
add(63,'pt-BR','propose-correction','Ativado e autorizado a baixar automaticamente pela política da lista de desejos.','The source specifically names the Wishlist policy. The current “política da lista” omits the wish-list meaning and reads as an unspecified list.','high')
# 64 message-storage counts.
add(64,'ko','propose-correction','정리나 유지 관리 전에 데이터베이스 사용량을 확인할 수 있도록 로컬 메시지 저장 건수를 불러옵니다.','The source asks to load counts of locally stored messages. The current “저장 횟수” means the number of save operations; “저장 건수” means the number of stored records.','high')
# 65 space after error icon.
add(65,'hi','propose-refinement','✗ अमान्य सामग्री आईडी','The current Hindi target attaches text directly to the error mark. A separating space improves the status heading without changing the meaning.','moderate')
# 67 standalone inbound links; only Vietnamese has a directional mistranslation.
add(67,'vi','propose-correction','liên kết đến','“trong nước” means domestic/in-country, which reverses the standalone direction “inbound”. With no direct caller context, “liên kết đến” is the narrow incoming-link rendering; verify the exact product usage before apply.','moderate')
# 70 metric label.
add(70,'de','propose-correction','Durchschnittliche Konfidenz:','The caller displays a fuzzy-matching confidence score. “Vertrauen” usually means trust; “Konfidenz” is the statistical/model confidence label.','high')
add(70,'hi','propose-refinement','औसत विश्वास:','The caller displays a numeric fuzzy-matching confidence score. “आत्मविश्वास” can mean personal self-confidence; “विश्वास” is more suitable for this metric.','moderate')
add(70,'ar','propose-refinement','متوسط الثقة:','The current Arabic heading contains an invisible formatting character between “متوسط” and “الثقة”. Removing it preserves the label and avoids a stray text-control character.','high')
# 73 surrounding card publishes membership records to the DHT.
add(73,'zh-Hans','propose-refinement','高级会员记录发布控制','The adjacent section publishes signed membership records; the current phrase can read as controls for publishing members. Adding “记录” matches the warning and form below.','moderate')
add(73,'hi','propose-refinement','सदस्यता रिकॉर्ड प्रकाशित करने के उन्नत नियंत्रण','The adjacent section publishes signed membership records; this makes the object being published explicit rather than suggesting publication of membership itself.','moderate')
add(73,'de','propose-refinement','Erweiterte Steuerung für die Veröffentlichung von Mitgliedschaftsdatensätzen','The adjacent section publishes signed membership records, not memberships as an abstract concept. This makes the controlled object explicit.','moderate')
add(73,'ja','propose-refinement','メンバーシップ記録の高度な公開設定','The adjacent section publishes signed membership records. This names those records and reads naturally as a settings disclosure summary.','moderate')
add(73,'fr','propose-refinement','Contrôles avancés de publication des enregistrements d’adhésion','The adjacent section publishes signed membership records. This avoids “publication des adhésions,” which can suggest publishing memberships themselves.','moderate')
add(73,'pt-BR','propose-refinement','Controles avançados para publicar registros de associação','The adjacent section publishes signed membership records. This names the records rather than implying publication of members.','moderate')
add(73,'ar','propose-refinement','عناصر التحكم المتقدمة في نشر سجلات العضوية','The adjacent section publishes signed membership records. This makes the published object explicit.','moderate')
add(73,'ko','propose-refinement','멤버십 기록 게시 고급 설정','The adjacent section publishes signed membership records. This names the record and reads as a heading for advanced controls.','moderate')
add(73,'zh-Hant','propose-refinement','進階會員記錄發布控制','The adjacent section publishes signed membership records; the current phrase can read as controls for publishing members. Adding “記錄” matches the warning and form below.','moderate')
add(73,'vi','propose-refinement','Kiểm soát nâng cao việc xuất bản hồ sơ thành viên','The adjacent section publishes signed membership records; the current wording can mean publishing members. This names the records being published.','moderate')
add(73,'id','propose-refinement','Kontrol lanjutan untuk menerbitkan catatan keanggotaan','The adjacent section publishes signed membership records. This names the record rather than membership as an abstract concept.','moderate')
# 75 native MilkDrop wave fragment.
add(75,'hi','propose-correction','मूल MilkDrop वेव अंश निर्यात करें','In the caller, “native” refers to the active native MilkDrop preset, not “domestic” (“देशी”). This keeps the product name in Latin script and retains the wave-fragment type.','high')
add(75,'ko','propose-refinement','MilkDrop 네이티브 웨이브 조각 내보내기','The caller distinguishes native MilkDrop preset fragments from other preset formats. “네이티브” expresses native-format provenance more clearly than “기본” (“default/basic”).','moderate')
add(75,'zh-Hans','propose-refinement','导出原生 MilkDrop 波形片段','The caller exports a custom MilkDrop wave from a native preset as a .wave fragment. “波形” is more precise than the current water-wave sense “波浪”.','moderate')
add(75,'zh-Hant','propose-refinement','匯出原生 MilkDrop 波形片段','The caller exports a custom MilkDrop wave from a native preset as a .wave fragment. “波形” is more precise than the current water-wave sense “波浪”.','moderate')

# Caller line/file pins and primary input/decision ledgers.
phre=re.compile(r'\{[A-Za-z_][A-Za-z0-9_]*\}')
markup=re.compile(r'</?([A-Za-z][A-Za-z0-9:_-]*)(?:\s[^<>]*?)?\s*/?>')
callers=[]; refs=set(); no_callers=[]; inputs=[]; decisions=[]; candidates=[]; structural=[]
for s in source_rows:
 sid=s['sourceId']; key=s['catalogKey']; ordinal=s['sourceOrdinal']
 for c in s['sourceCallsites']:
  raw=(repo/c['path']).read_bytes(); lines=(repo/c['path']).read_text(encoding='utf-8').splitlines(); actual_line=lines[c['line']-1].strip()
  if sha(raw)!=c['fileSha256'] or actual_line!=c['lineText'] or shat(actual_line)!=c['lineTextSha256']:
   raise SystemExit(f'caller pin mismatch {c["path"]}:{c["line"]}')
  refs.add((c['path'],c['line']))
  callers.append({'window':42,'sourceId':sid,'sourceOrdinal':ordinal,'sourceSha256':s['sourceSha256'],'path':c['path'],'line':c['line'],'lineText':actual_line,'lineTextSha256':c['lineTextSha256'],'fileSha256':c['fileSha256'],'currentFileSha256':sha(raw),'sourceSubtreeTree':source_tree,'verified':True})
 if not s['sourceCallsites']: no_callers.append({'sourceId':sid,'sourceOrdinal':ordinal,'source':s['source'],'sourceSha256':s['sourceSha256'],'contextScope':'standalone-text-only'})
 for loc in locales:
  b=allrows[(loc,sid)]; cur=catalogs[loc][key]; cursha=shat(cur); sourceph=sorted(phre.findall(s['source'])); curph=sorted(phre.findall(cur)); current_missing=[x for x in s['protectedLiterals'] if x not in cur]
  source_markup=sorted(markup.findall(s['source'])); current_markup=sorted(markup.findall(cur))
  if b['reviewDisposition'] not in ('pending','reused_prior_exact'): raise SystemExit(f'unexpected base disposition {loc}:{sid}')
  inp={'window':42,'exactHead':head,'exactTree':tree,'sourceSubtreeTree':source_tree,'localeCatalogSubtreeTree':locale_tree,'id':f'{loc}:{sid}','locale':loc,'sourceOrdinal':ordinal,'sourceId':sid,'source':s['source'],'sourceSha256':s['sourceSha256'],'sourceFingerprint':s['sourceFingerprint'],'catalogKey':key,'catalogPath':f'src/web/public/locales/{loc}.json','currentTarget':cur,'currentTargetSha256':cursha,'currentCatalogBlobOid':catmeta[loc]['gitBlobOid'],'currentCatalogFileSha256':catmeta[loc]['fileSha256'],'frozenBundleTarget':b['target'],'frozenBundleTargetSha256':b['targetSha256'],'frozenReviewDisposition':b['reviewDisposition'],'frozenPendingReason':b.get('pendingReason'),'priorExactReuse':b['reviewDisposition']=='reused_prior_exact','placeholders':s['placeholders'],'currentTargetPlaceholders':curph,'protectedLiterals':s['protectedLiterals'],'currentProtectedLiteralMismatches':current_missing,'sourceCallsites':s['sourceCallsites'],'sourceContexts':s['sourceContexts'],'sourceKind':s['sourceKind']}
  inputs.append(inp)
  structural.append({'id':inp['id'],'sourceOrdinal':ordinal,'sourceSha256':s['sourceSha256'],'currentTargetSha256':cursha,'placeholderMismatch':curph!=sourceph,'protectedLiteralMismatches':current_missing,'markupMismatch':current_markup!=source_markup})
  p=C.get((ordinal,loc)); prior=(loc=='fr' and sid=='src_0e570ca6fabe24f9'); noctx=not s['sourceCallsites']
  if p:
   tgt=p['candidateTarget']; tgtsha=shat(tgt); tph=sorted(phre.findall(tgt)); tmiss=[x for x in s['protectedLiterals'] if x not in tgt]; tmark=sorted(markup.findall(tgt))
   candidate={'window':42,'exactHead':head,'exactTree':tree,'id':inp['id'],'locale':loc,'sourceOrdinal':ordinal,'sourceId':sid,'source':s['source'],'sourceSha256':s['sourceSha256'],'catalogKey':key,'currentTarget':cur,'currentTargetSha256':cursha,'candidateTarget':tgt,'candidateTargetSha256':tgtsha,'reviewDisposition':p['reviewDisposition'],'confidence':p['confidence'],'rationale':p['rationale'],'placeholders':s['placeholders'],'candidatePlaceholders':tph,'protectedLiterals':s['protectedLiterals'],'candidateProtectedLiteralsPresent':not tmiss,'candidateProtectedLiteralMismatches':tmiss,'candidateMarkupMatchesSource':tmark==source_markup,'sourceCallsites':s['sourceCallsites'],'sourceContexts':s['sourceContexts']}
   candidates.append(candidate)
   decisions.append({'schemaVersion':1,'window':42,'exactHead':head,'exactTree':tree,'id':inp['id'],'locale':loc,'sourceOrdinal':ordinal,'sourceId':sid,'source':s['source'],'sourceSha256':s['sourceSha256'],'sourceFingerprint':s['sourceFingerprint'],'catalogKey':key,'catalogPath':inp['catalogPath'],'currentTarget':cur,'currentTargetSha256':cursha,'currentCatalogFileSha256':catmeta[loc]['fileSha256'],'placeholders':s['placeholders'],'currentTargetPlaceholders':curph,'protectedLiterals':s['protectedLiterals'],'currentProtectedLiteralMismatches':current_missing,'currentMarkupMatchesSource':current_markup==source_markup,'sourceCallsites':s['sourceCallsites'],'sourceContexts':s['sourceContexts'],'reviewDisposition':p['reviewDisposition'],'confidence':p['confidence'],'rationale':p['rationale'],'candidateTarget':tgt,'candidateTargetSha256':tgtsha,'candidatePlaceholders':tph,'candidateProtectedLiteralsPresent':not tmiss,'candidateProtectedLiteralMismatches':tmiss,'candidateMarkupMatchesSource':tmark==source_markup,'reviewerRequiredLiterals':s['protectedLiterals'],'priorExactReuse':False,'contextScope':'pinned-caller-context' if not noctx else 'standalone-text-only'})
  else:
   if noctx: rationale='Retain the current standalone rendering; it preserves the direction “incoming” in the source phrase. No direct caller was present in the frozen inventory, so this is a standalone-text judgment.'; confidence='moderate'
   elif prior: rationale='Retain the current French cognate “Source”; exact source and target hashes match the prior machine-reviewed keep, and the current contexts use it as a general source label.'; confidence='high'
   else: rationale='The current target preserves the source meaning in the pinned caller context and passes placeholder, markup, and protected-literal checks.'; confidence='high'
   decisions.append({'schemaVersion':1,'window':42,'exactHead':head,'exactTree':tree,'id':inp['id'],'locale':loc,'sourceOrdinal':ordinal,'sourceId':sid,'source':s['source'],'sourceSha256':s['sourceSha256'],'sourceFingerprint':s['sourceFingerprint'],'catalogKey':key,'catalogPath':inp['catalogPath'],'currentTarget':cur,'currentTargetSha256':cursha,'currentCatalogFileSha256':catmeta[loc]['fileSha256'],'placeholders':s['placeholders'],'currentTargetPlaceholders':curph,'protectedLiterals':s['protectedLiterals'],'currentProtectedLiteralMismatches':current_missing,'currentMarkupMatchesSource':current_markup==source_markup,'sourceCallsites':s['sourceCallsites'],'sourceContexts':s['sourceContexts'],'reviewDisposition':'accept-current','confidence':confidence,'rationale':rationale,'candidateTarget':None,'candidateTargetSha256':None,'reviewerRequiredLiterals':s['protectedLiterals'],'priorExactReuse':prior,'contextScope':'pinned-caller-context' if not noctx else 'standalone-text-only'})
if len(inputs)!=275 or len(decisions)!=275 or len(candidates)!=len(C): raise SystemExit('unexpected W42 cell/candidate count')
# Verify all candidate placeholder/protected-literal/markup integrity.
candidate_struct=[]
for c in candidates:
 s=source_by_id[c['sourceId']]; sourceph=sorted(phre.findall(s['source'])); cand=c['candidateTarget']; candph=sorted(phre.findall(cand)); miss=[x for x in s['protectedLiterals'] if x not in cand]
 cm=sorted(markup.findall(cand)); sm=sorted(markup.findall(s['source']))
 candidate_struct.append({'id':c['id'],'candidateTargetSha256':c['candidateTargetSha256'],'placeholderMismatch':candph!=sourceph,'protectedLiteralMismatches':miss,'markupMismatch':cm!=sm})
if any(r['placeholderMismatch'] or r['protectedLiteralMismatches'] or r['markupMismatch'] for r in candidate_struct): raise SystemExit('candidate structural validation failed')
writejl(out/'review-input.jsonl',inputs); writejl(out/'review-decisions.jsonl',decisions); writejl(out/'correction-candidates.jsonl',candidates); writejl(out/'caller-attestation.jsonl',callers); writejl(out/'source-without-callers.jsonl',no_callers); writejl(out/'structural-validation.jsonl',structural+candidate_struct); writejl(out/'holds.jsonl',[])

# W41 exact outcomes and history reattestation against W42 current catalog values.
w41_ledger=jlines(w41/'cross-review/cross-review-ledger.jsonl'); w41_apply=jlines(w41/'apply-plan.jsonl'); w41_readback=jlines(w41/'readback.jsonl')
apply_by={f"{r['locale']}:{r['sourceId']}":r for r in w41_apply}; readback_by={f"{r['locale']}:{r['sourceId']}":r for r in w41_readback}; w41_rows=[]
for r in w41_ledger:
 actual=catalogs[r['locale']][r['catalogKey']]; ah=shat(actual); exp=r.get('selectedTarget') or r['currentTarget']; eh=r.get('selectedTargetSha256') or r['currentTargetSha256']; rb=readback_by.get(r['id'])
 if actual!=exp or ah!=eh: raise SystemExit(f'W41 outcome mismatch at current head {r["id"]}')
 if rb and (not rb.get('matchesReviewedTarget') or rb.get('targetSha256')!=ah): raise SystemExit(f'W41 readback mismatch {r["id"]}')
 w41_rows.append({'windowReattested':41,'currentReviewWindow':42,'id':r['id'],'locale':r['locale'],'sourceOrdinal':r['sourceOrdinal'],'sourceId':r['sourceId'],'source':r['source'],'sourceSha256':r['sourceSha256'],'w41CrossReviewDisposition':r['crossReviewDisposition'],'w41PrimaryDisposition':r.get('primaryReviewDisposition'),'w41SelectedTarget':exp,'w41SelectedTargetSha256':eh,'currentTargetSha256':ah,'matchesW41SelectedOutcome':True,'appliedInW41':r['id'] in apply_by,'w41ReadbackSha256':rb.get('targetSha256') if rb else None})
writejl(out/'w41-cell-reattestation.jsonl',w41_rows)

old_holds=jlines(w41/'cross-review/preserved-holds-reattestation.jsonl'); preserved_holds=[]
for r in old_holds:
 rec=r['record']; loc=rec['locale']; key=rec.get('catalogKey',rec['source']); actual=catalogs[loc][key]; ah=shat(actual); expected=r.get('currentTargetSha256Reattested') or rec.get('currentTargetSha256AtW41') or rec.get('currentTargetSha256')
 if ah!=expected: raise SystemExit(f'historic hold changed: {rec["id"]}')
 preserved_holds.append({'window':42,'preservedFromWindow':41,'id':rec['id'],'locale':loc,'sourceId':rec['sourceId'],'source':rec['source'],'sourceSha256':rec['sourceSha256'],'catalogKey':key,'catalogPath':f'src/web/public/locales/{loc}.json','currentTarget':actual,'currentTargetSha256':ah,'w41TargetSha256':expected,'holdDisposition':rec.get('disposition') or rec.get('primaryVerdict') or r.get('independentResult'),'reason':rec.get('reason') or rec.get('crossReviewReason') or rec.get('crossReviewDisposition'),'unchanged':True,'sourceHoldLedgerPath':r.get('sourceHoldLedgerPath'),'sourceHoldLedgerSha256':r.get('sourceHoldLedgerSha256')})
writejl(out/'preserved-prior-holds.jsonl',preserved_holds)
old_es=jlines(w41/'cross-review/preserved-spanish-reattestation.jsonl'); old_es_rows=[]
for r in old_es:
 actual=catalogs['es'][r['catalogKey']]; ah=shat(actual)
 if ah!=r['currentTargetSha256Reattested']: raise SystemExit(f'W41 Spanish formal cell changed: {r["id"]}')
 old_es_rows.append({'windowReattested':41,'id':r['id'],'locale':'es','sourceOrdinal':r['sourceOrdinal'],'sourceId':r['sourceId'],'source':r['source'],'sourceSha256':r['sourceSha256'],'catalogKey':r['catalogKey'],'currentTarget':actual,'currentTargetSha256':ah,'w41TargetSha256':r['currentTargetSha256Reattested'],'formalCellIdPresent':r['formalCellIdPresent'],'preservationDisposition':r['preservationDisposition'],'unchanged':True})
writejl(out/'w41-spanish-formal-reattestation.jsonl',old_es_rows)
formal={r['id']:r for r in jlines(formal_path)}; w42_es=[]
for s in source_rows:
 cid='es:'+s['sourceId']; f=formal.get(cid)
 if not f: raise SystemExit(f'W42 cell missing from formal Spanish lane: {cid}')
 target=catalogs['es'][s['catalogKey']]
 w42_es.append({'window':42,'exactHead':head,'exactTree':tree,'id':cid,'locale':'es','sourceOrdinal':s['sourceOrdinal'],'sourceId':s['sourceId'],'source':s['source'],'sourceSha256':s['sourceSha256'],'catalogKey':s['catalogKey'],'catalogPath':'src/web/public/locales/es.json','currentTarget':target,'currentTargetSha256':shat(target),'currentCatalogBlobOid':catmeta['es']['gitBlobOid'],'currentCatalogFileSha256':catmeta['es']['fileSha256'],'formalCellId':f,'formalCellIdPresent':True,'preservationDisposition':'Spanish formal-lane cell preserved; no W42 language verdict emitted.'})
writejl(out/'preserved-spanish-formal.jsonl',w42_es)

# Keep exact prior reuse proof for French Source and ensure current target hash still matches.
reuse=jlines(out/'prior-exact-reuse-reattestation.jsonl')
for r in reuse:
 if r['sourceSha256']!=r['targetSha256'] or r['targetSha256']!=r['currentTargetSha256']: raise SystemExit('prior reuse is not exact source+target hash match')

# Live PR head at completion and exact input descriptor.
fields='state,isDraft,headRefOid,headRefName,url,title,body'
end=json.loads(subprocess.check_output(['gh','pr','view','409','--repo','snapetech-org/slskdN','--json',fields],text=True))
end_min={k:end[k] for k in ['state','isDraft','headRefOid','headRefName','url','title']}; end_min.update({'bodySha256':shat(end['body']),'verifiedAtUtc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')})
writej(out/'pr-snapshot-end.json',end_min)
advanced=end['headRefOid']!=head_expected
writej(out/'catalog-attestation.json',{'repository':'snapetech-org/slskdN','pullRequest':409,'headCommit':head,'tree':tree,'sourceSubtreeTree':source_tree,'localeCatalogSubtreeTree':locale_tree,'orderedKeyCountPerLocale':6169,'orderedKeySetSha256':keyset_hash,'catalogs':[catmeta[x] for x in all_locales],'allCatalogsHaveSameOrderedKeys':True})
writej(out/'exact-head.json',{'repository':'snapetech-org/slskdN','pullRequest':409,'url':'https://github.com/snapetech-org/slskdN/pull/409','stateAtStart':'OPEN','isDraftAtStart':True,'headCommit':head,'tree':tree,'sourceSubtreeTree':source_tree,'localeCatalogSubtreeTree':locale_tree,'liveHeadAtCompletion':end['headRefOid'],'reattestationRequiredAfterHeadChange':advanced,'worktreeStatusAtCompletion':git('status','--porcelain'),'worktreeStillAtPinnedHead':git('rev-parse','HEAD')==head_expected})
order={'window':42,'selectionRule':'next 25 lexicographically sorted non-Spanish pending source IDs after excluding all W1-W41 manual source IDs; preserve prior held sources','frozenBundleHead':json.loads((bundle/'manifest.json').read_text()).get('sourceHead'),'frozenBundleTree':json.loads((bundle/'manifest.json').read_text()).get('sourceTree'),'frozenBundleManifestSha256':sha((bundle/'manifest.json').read_bytes()),'frozenBundleBatchesSha256':sha((bundle/'batches.json').read_bytes()),'priorWindowInputAttestations':input_att,'w1Through41UniqueSourceIds':len(previous_ids),'frozenNonSpanishPendingSourceIdCount':len(pending_ids),'remainingSourceIdsBeforeW42':len(remaining),'priorHoldRowsPreserved':len(preserved_holds),'priorHoldSourceIds':sorted(prior_hold_ids),'selectedSourceIds':[{'ordinal':r['sourceOrdinal'],'sourceId':r['sourceId'],'sourceSha256':r['sourceSha256'],'source':r['source']} for r in source_rows],'selectionReproduced':True}
writej(out/'order-evidence.json',order)

# Structural checks: report each current cell and candidate; do not run tests/builds/scans.
current_fail=[r for r in structural if r['placeholderMismatch'] or r['protectedLiteralMismatches'] or r['markupMismatch']]
candidate_fail=[r for r in candidate_struct if r['placeholderMismatch'] or r['protectedLiteralMismatches'] or r['markupMismatch']]
unresolved=[r for r in current_fail if not any(d['id']==r['id'] and d['reviewDisposition'] in ('propose-correction','propose-refinement') for d in decisions)]
if candidate_fail or unresolved: raise SystemExit(f'structural validation needs review: candidate={candidate_fail[:2]} unresolved={unresolved[:2]}')
writej(out/'w41-evidence-attestation.json',{'window':41,'reviewInputHead':'ab6f8fd9fe94d222834f7e4720fd153af4e0649b','reviewInputTree':'bebc34f8806f57158140d8b831c7a17c1fc6f8f1','currentHeadAfterW41Application':head,'evidence':{rel:{'path':str(w41/rel),'sha256':sha((w41/rel).read_bytes()),'rows':len(jlines(w41/rel))} for rel in ['primary/review-input.jsonl','cross-review/cross-review-ledger.jsonl','apply-plan.jsonl','readback.jsonl','cross-review/preserved-holds-reattestation.jsonl','cross-review/preserved-spanish-reattestation.jsonl']},'currentCatalogReattestation':{'w41ReviewedCells':len(w41_rows),'mismatches':0,'w41AppliedReadbacks':sum(r['appliedInW41'] for r in w41_rows),'priorHolds':len(preserved_holds),'spanishFormalCells':len(old_es_rows)}})

counts=Counter(r['reviewDisposition'] for r in decisions)
per_locale={l:dict(Counter(r['reviewDisposition'] for r in decisions if r['locale']==l)) for l in locales}
summary={'result':'PRIMARY_REVIEW_COMPLETE_PENDING_CROSS_REVIEW_AND_NATIVE_SPEAKER_REVIEW','window':42,'pullRequest':409,'headCommit':head,'tree':tree,'sourceSubtreeTree':source_tree,'sourceOrdinals':[51,75],'sourceKeys':25,'nonSpanishReviewCells':len(decisions),'formalSpanishRowsPreserved':len(w42_es),'priorHoldsPreserved':len(preserved_holds),'priorExactRowsIndependentlyReattested':len(reuse),'candidateRows':len(candidates),'dispositions':dict(counts),'perLocaleVerdicts':per_locale,'directCallerReferences':len(refs),'sourcesWithoutDirectCaller':[r['sourceId'] for r in no_callers],'currentPlaceholderIntegrityFailures':sum(r['placeholderMismatch'] for r in structural),'currentProtectedLiteralIntegrityFailures':sum(bool(r['protectedLiteralMismatches']) for r in structural),'currentMarkupIntegrityFailures':sum(r['markupMismatch'] for r in structural),'candidatePlaceholderIntegrityFailures':sum(r['placeholderMismatch'] for r in candidate_struct),'candidateProtectedLiteralIntegrityFailures':sum(bool(r['protectedLiteralMismatches']) for r in candidate_struct),'candidateMarkupIntegrityFailures':sum(r['markupMismatch'] for r in candidate_struct),'w41CellRowsReattested':len(w41_rows),'w41CellMismatchCount':0,'w41AppliedReadbacksReattested':sum(r['appliedInW41'] for r in w41_rows),'w41PriorHoldsReattested':len(preserved_holds),'w41SpanishFormalCellsReattested':len(old_es_rows),'reattestationAfterHeadAdvanceRequired':advanced,'liveHeadAtCompletion':end['headRefOid'],'nativeSpeakerReview':'outstanding','readOnly':True,'notes':['No repo, catalog, PR, tests, builds, scans, CI, browser, workflow, release, or tag writes/actions were performed.','The Vietnamese “inbound links” target has no direct caller in the frozen source inventory; its proposal is standalone-text only.','The French “Source” target reuses one prior exact keep after exact source and current target hashes were reattested.']}
writej(out/'review-summary.json',summary)

prstart=json.loads((out/'pr-snapshot-start.json').read_text())
readme=f'''# slskdN PR #409 — W42 primary semantic review

- **Pinned input:** PR #409 was open/draft at head `{head}`, tree `{tree}`.
- **Scope:** source ordinals 51–75 (25 keys); 275 non-Spanish cells across 11 catalogs.
- **Output:** read-only evidence. No repository or PR changes were made.
- **W41 reattestation:** all {len(w41_rows)} W41 reviewed cells, {sum(r['appliedInW41'] for r in w41_rows)} applied readbacks, {len(preserved_holds)} historic holds, and {len(old_es_rows)} W41 Spanish formal cells match the current catalogs with zero hash mismatches.
- **Preservation:** {len(w42_es)} Spanish formal-lane cells recorded without Spanish verdicts; all {len(preserved_holds)} prior held rows remain unchanged.
- **W42 verdicts:** {counts.get('accept-current',0)} accept-current; {counts.get('propose-correction',0)} correction candidates; {counts.get('propose-refinement',0)} refinement candidates; {counts.get('hold',0)} W42 holds.
- **Prior exact reuse:** one French `Source` cell was reused after exact source and target hashes matched; see `prior-exact-reuse-reattestation.jsonl`.
- **Callers:** {len(refs)} exact caller references. `inbound links` has no direct caller in the frozen inventory, so its review is limited to standalone wording.
- **Validation:** all 12 catalogs have the same ordered 6,169-key set. Input/candidate hashes, placeholder, markup, protected-literal, and caller file/line checks are included. Candidate structural checks passed with zero mismatches.
- **Native-speaker review:** outstanding; machine-assisted review does not claim native-speaker approval.
- **Head movement:** PR head at completion was `{end['headRefOid']}`. Reattestation required after head advance: `{str(advanced).lower()}.

Key files: `order-evidence.json`, `exact-head.json`, `catalog-attestation.json`, `source-slice.jsonl`, `review-input.jsonl`, `caller-attestation.jsonl`, `review-decisions.jsonl`, `correction-candidates.jsonl`, `w41-cell-reattestation.jsonl`, `preserved-prior-holds.jsonl`, and `preserved-spanish-formal.jsonl`. `SHA256SUMS.txt` covers the packet files except itself.
'''
(out/'README.md').write_text(readme,encoding='utf-8')

# Final local state check and packet checksums.
if git('rev-parse','HEAD')!=head_expected or git('rev-parse','HEAD^{tree}')!=tree_expected or git('status','--porcelain'):
 raise SystemExit('repository changed during read-only packet generation')
files=sorted(p for p in out.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
(out/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(out).as_posix()}\n' for p in files),encoding='utf-8')
print(json.dumps({'output':str(out),'head':head,'tree':tree,'sources':len(source_rows),'cells':len(decisions),'candidates':len(candidates),'dispositions':dict(counts),'priorExactReuse':len(reuse),'priorHolds':len(preserved_holds),'w41Rows':len(w41_rows),'w41MismatchCount':0,'w41AppliedReadbacks':sum(r['appliedInW41'] for r in w41_rows),'w41Spanish':len(old_es_rows),'w42Spanish':len(w42_es),'callerRefs':len(refs),'sourcesWithoutCallers':[r['sourceId'] for r in no_callers],'candidateStructuralFailures':len(candidate_fail),'currentStructuralFindings':len(current_fail),'liveHeadAtCompletion':end['headRefOid'],'reattestationRequired':advanced,'packetFiles':len(files)+1,'packetSizeBytes':sum(p.stat().st_size for p in out.rglob('*') if p.is_file())},ensure_ascii=False,indent=2))
