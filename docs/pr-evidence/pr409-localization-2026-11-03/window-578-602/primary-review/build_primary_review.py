#!/usr/bin/env python3
import hashlib,json,re,subprocess,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
I=Path('/home/keith/Documents/code/task-scratch/slskdn-pr409-w68-ranks578-602-candidate-free-20261103/input')
O=Path(__file__).resolve().parent
REPO=Path('/home/keith/Documents/code/task-scratch/slskdn-pr409-w68-apply-20261103/repo')
HEAD='973a65312a475de4d8aa39aee837249553fd884e'; TREE='2a7b200dd1fe96f894bfdb663f656d6ffd48f487'
BRANCH='codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
BASE_KEYS=('placeholder','markup','numeric','protectedLiteral')
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode('utf-8')).hexdigest()
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def dumpjl(p,rs): p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rs),encoding='utf-8')
def ph(s): return sorted(set(re.findall(r'\{[^{}]+\}',s)))
def tags(s): return sorted(re.findall(r'</?[A-Za-z][^>]*>',s))
def nums(s): return re.findall(r'(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])',s)
def prot(s):
 found=set(re.findall(r'(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])',s))
 for x in ('Wishlist','Soulseek','Discogs','Pod'):
  if re.search(r'(?<![A-Za-z0-9])'+re.escape(x)+r'(?![A-Za-z0-9])',s): found.add(x)
 return sorted(found)
def tok(s): return {'placeholders':ph(s),'markup':tags(s),'numeric':nums(s),'protectedLiterals':prot(s)}
im=j(I/'manifest.json')
if (im['head'],im['tree'],im['continuationRankRange'],im['remainingQueueRankRange'])!=(HEAD,TREE,[578,602],[478,502]): raise SystemExit('candidate-free packet pin mismatch')
subprocess.run([sys.executable,str(I/'verify_input.py')],check=True,capture_output=True,text=True)
subprocess.run(['sha256sum','-c','PACKET-SHA256SUMS.txt'],cwd=I,check=True,capture_output=True,text=True)
cells=jl(I/'source-current-cells.jsonl'); contexts=jl(I/'caller-contexts.jsonl'); prior=jl(I/'prior-held-cell-reattestation.jsonl')
assert len(cells)==300 and len(contexts)==25 and len(prior)==128
cx={x['continuationRank']:x for x in contexts}
D={}
def add(rank,targets,disposition,rationale,confidence='high'):
 for locale,target in targets.items(): D[(rank,locale)]=(disposition,target,rationale,confidence)
add(580,{'id':'Hanya simulasi pemberian tag dan pengorganisasian; belum ada penulisan tag, penulisan sampul, proses ReplayGain, pemindahan file, pencarian penyedia, pencarian Soulseek, penelusuran peer, atau pengunduhan yang dimulai.','ko':'태그 지정과 정리의 시험 실행만 수행합니다. 태그 쓰기, 표지 아트 쓰기, ReplayGain 실행, 파일 이동, 제공자 조회, Soulseek 검색, 피어 탐색 또는 다운로드는 아직 시작되지 않았습니다.','zh-Hans':'仅进行标签与整理的试运行；尚未开始写入标签、写入封面、运行 ReplayGain、移动文件、查询服务提供方、搜索 Soulseek、浏览对等节点或下载。','zh-Hant':'僅進行標記與整理的試運行；尚未開始寫入標記、寫入封面、執行 ReplayGain、移動檔案、查詢服務提供者、搜尋 Soulseek、瀏覽對等節點或下載。'},'correction','The playlist-intake safety notice says the operation is a dry run and explicitly says none of the listed side effects has started. Fix the Korean polarity and make the Indonesian and Chinese negation/list construction unambiguous; use peer terminology for network peers.')
add(581,{'fr':'Type (facultatif)','id':'Jenis (opsional)'},'correction','This is a noun label for an optional Type field. The existing French Tapez and Indonesian Ketik are imperative verbs rather than the field name.')
add(582,{'zh-Hans':'消息去重','zh-Hant':'訊息去重'},'correction','This MediaCore settings heading names message deduplication. Use the established Chinese technical term for deduplication instead of wording that means deleting duplicate messages.')
add(585,{'es':'Importación de listas de reproducción'},'correction','This is the named Playlist Intake screen and navigation destination. Preserve the playlist scope in Spanish; listas alone can mean lists of any kind.')
add(589,{'hi':'रैंकिंग, डाउनलोड या स्थानीय फ़ाइलों में बदलाव किए बिना इस SongID प्रक्रिया की पूरी फोरेंसिक मैट्रिक्स JSON कॉपी करें।'},'correction','The exact SongID panel caller refers to this SongID run and a JSON forensic matrix. Keep the protected product literal SongID intact in Hindi and preserve the read-only promise and JSON token.')
add(600,{'ar':'مدة الاحتفاظ بالتنزيلات الفاشلة (بالدقائق)','de':'Aufbewahrungsdauer fehlgeschlagener Downloads (Minuten)','es':'Tiempo de retención de las descargas fallidas (minutos)','fr':'Durée de conservation des téléchargements en erreur (minutes)','hi':'विफल डाउनलोड रखने की अवधि (मिनट)','id':'Lama penyimpanan unduhan yang gagal (menit)','ko':'실패한 다운로드 보존 기간(분)','pt-BR':'Tempo de retenção de downloads com falha (minutos)','vi':'Thời gian lưu giữ các lượt tải xuống bị lỗi (phút)','zh-Hans':'失败下载的保留时长（分钟）','zh-Hant':'失敗下載的保留時間（分鐘）'},'correction','The Admin Policies caller binds this table field to retentionDownloadErrored under the Downloads heading. The value is the retention duration for failed downloads, expressed in minutes; it is not an action to download minutes or a number of faulty minutes.')
add(601,{'ar':'إدارة عضوية Pod','es':'Gestión de membresía de Pod','fr':'Gestion des membres de Pod','hi':'Pod सदस्यता प्रबंधन','ja':'Pod メンバーシップ管理','ko':'Pod 멤버십 관리','pt-BR':'Gerenciamento da associação ao Pod','vi':'Quản lý thành viên Pod'},'correction','MediaCore uses Pod as the exact product term for this membership system. Preserve the protected literal Pod in every locale rather than translating or changing its case.')
why={578:'Placeholder and title for the user-defined web service on the VPN gateway configuration screen.',579:'Health-check status explaining that the API key is optional and currently unconfigured.',580:'Playlist-intake dry-run safety statement enumerating effects that have not started.',581:'Optional Type field label in the MediaCore configuration form.',582:'MediaCore settings heading for message deduplication.',583:'Accessible filter label for including all networks.',584:'Confirmation before resetting MediaCore statistics, with irreversibility stated.',585:'Playlist Intake screen and primary-navigation destination.',586:'Tooltip for selecting every search within the active list filter.',587:'Verification report heading.',588:'Availability label for streaming from a Pod, with a dynamic status placeholder.',589:'SongID panel action to copy the forensic JSON matrix without changing rank, downloads, or local files.',590:'Playlist-intake heading for previewing track changes.',591:'Accessible action label for editing an item’s display metadata, with dynamic item placeholder.',592:'Mesh evidence-policy parse/validation error heading naming JSON.',593:'Share-group action to retry loading member data.',594:'System navigation label for diagnostics.',595:'Expired or unavailable radio-snapshot notice with refresh action.',596:'Table heading identifying who accepted an item.',597:'File-explorer tooltip that calculates directory sizes while leaving file data unopened and unchanged.',598:'Accessible execute action for a named automation recipe, with dynamic title placeholder.',599:'Contact-list action to retry loading contacts.',600:'Downloads policy table field bound to failed-download retention duration in minutes.',601:'MediaCore settings heading for Pod membership management.',602:'File-explorer action label for selecting a directory identified by a dynamic fullName placeholder.'}
if set(r for r,_ in D)!=set(range(578,603)) or any(k[0] not in why or k[1] not in LOCALES for k in D):
 if any(k[0] not in why or k[1] not in LOCALES for k in D): raise SystemExit('proposal outside W68 scope')
if O.exists() and any(p.name not in {'build_primary_review.py'} for p in O.iterdir()): raise SystemExit('primary output directory is not empty')
assert all(x['productionCallerCount']>0 and x['callers'] for x in contexts)
rows=[]
for c in cells:
 rank,loc=c['continuationRank'],c['locale']; dis,target,reason,conf=D.get((rank,loc),('accept-current',None,why[rank],'high'))
 reviewed=target if dis in ('correction','refinement') else c['currentTarget']
 if dis in ('correction','refinement') and reviewed==c['currentTarget']: raise SystemExit('proposal is a no-op')
 st,ct,rt=tok(c['source']),tok(c['currentTarget']),tok(reviewed)
 checks={'placeholdersPreserved':st['placeholders']==rt['placeholders'],'markupPreserved':st['markup']==rt['markup'],'numericTokensPreserved':st['numeric']==rt['numeric'],'protectedLiteralsPreserved':all(reviewed.count(z)>=c['source'].count(z) for z in st['protectedLiterals'])}
 if not all(checks.values()): raise SystemExit(f'token check failed {(rank,loc)}: {checks}; target={reviewed}')
 ctx=cx[rank]
 row={'schema':'slskdn-primary-cell-review/v1','repository':im['repository'],'pullRequest':im['pullRequest'],'window':'W68','head':HEAD,'tree':TREE,'continuationRank':rank,'remainingQueueRank':c['remainingQueueRank'],'sourceId':c['sourceId'],'source':c['source'],'sourceSha256':c['sourceSha256'],'locale':loc,'catalogKey':c['catalogKey'],'catalogPath':c['catalogPath'],'catalogFileSha256':c['catalogFileSha256'],'catalogGitBlob':c['catalogGitBlob'],'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'callerRefs':c['callerRefs'],'callerContextSourceId':ctx['sourceId'],'callerContextSourceSha256':ctx['sourceSha256'],'callerContexts':ctx['callers'],'containsCandidate':False,'verdict':None,'disposition':dis,'rationale':reason,'confidence':conf,'reviewedTargetSha256':sha(reviewed),'tokenAudit':{'source':st,'current':ct,'reviewed':rt,'checks':checks}}
 if dis in ('correction','refinement'): row['proposedTarget']=target
 rows.append(row)
assert len(rows)==300 and len({(x['continuationRank'],x['locale']) for x in rows})==300
assert set(D)=={(r['continuationRank'],r['locale']) for r in rows if r['disposition']!='accept-current'}
dumpjl(O/'primary-ledger.jsonl',rows)
counts=Counter(r['disposition'] for r in rows); base=Counter(); final=Counter()
for r in rows:
 st,ct=tok(r['source']),tok(r['currentTarget']); target=r.get('proposedTarget',r['currentTarget']); rt=tok(target)
 base['placeholder']+=st['placeholders']!=ct['placeholders']; base['markup']+=st['markup']!=ct['markup']; base['numeric']+=st['numeric']!=ct['numeric']; base['protectedLiteral']+=not all(r['currentTarget'].count(z)>=r['source'].count(z) for z in st['protectedLiterals'])
 final['placeholder']+=st['placeholders']!=rt['placeholders']; final['markup']+=st['markup']!=rt['markup']; final['numeric']+=st['numeric']!=rt['numeric']; final['protectedLiteral']+=not all(target.count(z)>=r['source'].count(z) for z in st['protectedLiterals'])
if dict(base)!=im['baselineTokenMismatchSummary']: raise SystemExit('baseline token mismatch summary differs from candidate-free input')
if any(final.values()): raise SystemExit('reviewed proposals retain token mismatches: '+str(dict(final)))
assert not any(r['productionCallerCount']==0 for r in contexts)
summary={'schemaVersion':1,'repository':im['repository'],'pullRequest':409,'window':'W68','head':HEAD,'tree':TREE,'sourceCount':25,'localeCount':12,'cellCount':300,'dispositionCounts':dict(counts),'proposalCount':sum(v in ('correction','refinement') for v in (r['disposition'] for r in rows)),'holdCount':counts.get('hold',0),'baselineTokenMismatches':dict(base),'reviewedTokenMismatches':dict(final),'priorHeldCellsReattested':128,'priorHeldCellsUnchanged':all(x['allTargetHashesMatchPrior'] for x in [j(I/'prior-held-cell-reattestation-summary.json')]),'callerlessSelectedRanks':[],'callerCountByRank':{str(x['continuationRank']):x['productionCallerCount'] for x in contexts},'candidateFreeInputVerified':True,'blindPacketAccessed':False,'repositoryOrPRFilesEdited':False,'nativeSpeakerReview':'not performed','browserReview':'not performed'}
dump(O/'summary.json',summary)
(O/'input-verification.txt').write_text('Candidate-free W68 input verifier ran before primary review.\n\n'+subprocess.check_output([sys.executable,str(I/'verify_input.py')],text=True),encoding='utf-8')
(O/'README.md').write_text('# slskdN PR #409 W68 primary semantic review\n\nThis packet records the primary review of 300 catalog cells across 25 sources, continuation ranks 578–602 (remaining-queue ranks 478–502), at PR head '+HEAD+' and tree '+TREE+'. It uses the separately sealed candidate-free packet and preserves all 128 prior holds. All selected sources have exact production callers.\n\nDisposition counts: '+', '.join(f'{k}: {v}' for k,v in sorted(counts.items()))+'. Proposed target rows: '+str(summary['proposalCount'])+'. The candidate-free baseline had nine protected-literal gaps; reviewed targets preserve placeholders, markup, numeric tokens, and protected product literals.\n\nNo blind packet was accessed and no repository or catalog files were edited. Native-speaker and headed-browser review were not performed. Run python3 verify_primary.py here to verify the ledger and checksums.\n',encoding='utf-8')
manifest={'schemaVersion':1,'artifact':'slskdN PR #409 W68 primary semantic review ledger','reviewType':'primary-semantic','sealed':True,'candidateFreeInput':True,'repository':im['repository'],'pullRequest':409,'branch':im['branch'],'window':'W68','head':HEAD,'tree':TREE,'sourceCount':25,'localeCount':12,'cellCount':300,'locales':LOCALES,'inputPath':str(I),'inputManifestSha256':sha((I/'manifest.json').read_bytes()),'inputChecksumListSha256':sha((I/'PACKET-SHA256SUMS.txt').read_bytes()),'inputLedgerSha256':sha((I/'source-current-cells.jsonl').read_bytes()),'priorHeldCellsReattested':128,'dispositionCounts':dict(counts),'proposalCount':summary['proposalCount'],'blindPacketAccessed':False,'nativeSpeakerReview':'not performed','browserReview':'not performed','createdAtUtc':datetime.now(timezone.utc).isoformat()}
manifest['files']=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(O.iterdir()) if p.is_file() and p.name not in ('manifest.json','SHA256SUMS.txt')]
dump(O/'manifest.json',manifest)
paths=sorted(p for p in O.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt')
(O/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.name}\n' for p in paths),encoding='utf-8')
print(json.dumps({'built':True,'head':HEAD,'tree':TREE,'rows':len(rows),'dispositions':dict(counts),'proposals':summary['proposalCount'],'baselineTokenMismatches':dict(base),'reviewedTokenMismatches':dict(final)},ensure_ascii=False,indent=2))
