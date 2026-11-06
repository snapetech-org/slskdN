from __future__ import annotations
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path('/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn')
OUT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window44-primary-reconstructed-20261102')
W43 = REPO / 'docs/pr-evidence/pr409-localization-2026-11-02/window43'
W42 = REPO / 'docs/pr-evidence/pr409-localization-2026-11-02/window42'
W43_PRIOR_INPUTS = W43 / 'primary/prior-window-input-reattestation.jsonl'
W43_ORDER = W43 / 'primary/order-and-boundary.json'
W43_DECISIONS = W43 / 'primary/review-decisions.jsonl'
W43_RUNTIME_GAPS = W43 / 'primary/source-runtime-gaps.jsonl'
W42_SOURCE_SLICE = W42 / 'primary/source-slice.jsonl'
FORMAL_IDS = REPO / 'docs/pr-evidence/pr409-localization-2026-11-02/window36/primary/formal-cell-ids.jsonl'
FORMAL_IDS_SHA256 = '7bd9c90a1176403feb36daadfecb7822616a818d15e9980c99c0bf5dc9d6f856'
EXPECTED_HEAD = 'f3fbd3f8db10f78768b9951a67b4b9de8581a408'
EXPECTED_TREE = '9495c35a540ef2d2e845c833acb709365e0e26ac'
EXPECTED_BRANCH = 'codex/slskdn-localization-apply-20261102'
PR_BRANCH = 'codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
REPO_NAMES = [
    ('snapetech-org/chaptarrng',190), ('snapetech-org/seerrng',418),
    ('snapetech-org/slskr',204), ('snapetech-org/QuestarrNG',155),
    ('snapetech-org/TorrentNG',243), ('snapetech-org/slskdN',409),
    ('snapetech-org/ROMarrNG',70),
]
EXPECTED_RECONSTRUCTED_IDS = [
'src_00584470b901894c','src_00f8edd8bfb7a769','src_01a6f87c38cf6f9a','src_0220040a680c679a',
'src_026741b287567ba3','src_028c91844b3f88b4','src_02fcb11878038bda','src_033ac3db37df2036',
'src_043275f676ad0f53','src_043a718774c572bd','src_043d027f96d30249','src_049c287ed3e2d554',
'src_050080a4fb0dda17','src_056c3431d4ad33cc','src_05afc66a51f62542','src_05e19370e89dff1c',
'src_05f82d0f2d002090','src_068263d796c6603a','src_0722d01d337955a0','src_072d70f68f12345d',
'src_07340fd83dfc3c75','src_0808910517813eb3','src_0879b91621242969','src_08822f8abe8a3424',
'src_088256c96f272851'
]
HOLD_SOURCE_IDS = {'src_049c287ed3e2d554','src_07340fd83dfc3c75'}
W98_ID = 'src_0f34b6ede09f66e5'

# Exact reviewed target, disposition kind, rationale, and confidence for each candidate cell.
CANDIDATES = {
 ('limited download history','de'): ('Eingeschränkter Downloadverlauf','propose-correction','The current word order is unidiomatic; this is the compact German compound for limited download history.','moderate'),
 ('limited download history','es'): ('Historial de descargas limitado','propose-refinement','The current singular Historia de descarga is less natural here; Historial de descargas is the usual label for download history.','moderate'),
 ('limited download history','id'): ('Riwayat unduhan terbatas','propose-correction','The current target leaves download in English; unduhan is the standard Indonesian UI term.','moderate'),
 ('limited download history','ja'): ('ダウンロード履歴が限られている','propose-correction','The current phrase is an unnatural compound; this states that download history is limited.','moderate'),
 ('limited download history','ko'): ('제한된 다운로드 기록','propose-refinement','기록 is the more natural Korean term for a usage history than 역사 in this UI reason.','moderate'),
 ('limited download history','pt-BR'): ('Histórico de downloads limitado','propose-refinement','Histórico de downloads is the natural UI phrase; the current História de download reads as a history/story about downloading.','moderate'),
 ('limited download history','vi'): ('Lịch sử tải xuống bị giới hạn','propose-correction','The current target leaves download in English; tải xuống is the localized action.','moderate'),
 ('limited download history','zh-Hans'): ('下载记录有限','propose-refinement','记录有限 reads naturally as a concise status; the current 历史 is a less idiomatic label here.','moderate'),
 ('limited download history','zh-Hant'): ('下載記錄有限','propose-refinement','記錄有限 reads naturally as a concise status; the current 歷史 is a less idiomatic label here.','moderate'),

 ('Readiness: {readiness}','es'): ('Estado de preparación: {readiness}','propose-refinement','Adds estado so the label identifies readiness as a status value, matching the runtime readiness token.','moderate'),
 ('Readiness: {readiness}','fr'): ('État de préparation : {readiness}','propose-refinement','Adds état to identify the runtime token as a readiness status, rather than the process of preparing.','moderate'),
 ('Readiness: {readiness}','hi'): ('तैयारी की स्थिति: {readiness}','propose-refinement','Adds स्थिति so the runtime value reads as a readiness status, not as preparation activity.','moderate'),
 ('Readiness: {readiness}','ja'): ('準備状況: {readiness}','propose-correction','準備状況 is the status label for the readiness result; 準備 alone describes preparation.','moderate'),
 ('Readiness: {readiness}','ko'): ('준비 상태: {readiness}','propose-refinement','Adds 상태 to identify the interpolated value as readiness status.','moderate'),
 ('Readiness: {readiness}','pt-BR'): ('Estado de prontidão: {readiness}','propose-refinement','Adds estado and uses prontidão for the readiness result shown by the caller.','moderate'),

 ('Album title: {title}','de'): ('Albumtitel: {title}','propose-correction','German compounds Albumtitel as one word; the current split compound is incorrect.','high'),
 ('Album title: {title}','id'): ('Judul album: {title}','propose-refinement','Judul matches the source field title more closely than Nama while retaining the album context.','moderate'),
 ('Album title: {title}','zh-Hans'): ('专辑名称：{title}','propose-refinement','Uses Chinese full-width colon punctuation for this compact field label.','moderate'),
 ('Album title: {title}','zh-Hant'): ('專輯名稱：{title}','propose-refinement','Uses Chinese full-width colon punctuation for this compact field label.','moderate'),

 ('Minimum weight: {percent}%','hi'): ('न्यूनतम भार: {percent}%','propose-correction','भार names an abstract graph weight; वजन can mean physical weight.','moderate'),
 ('Minimum weight: {percent}%','id'): ('Bobot minimum: {percent}%','propose-correction','Bobot is the Indonesian term for a graph or scoring weight; berat more often means physical weight.','moderate'),
 ('Minimum weight: {percent}%','ja'): ('最小重み: {percent}%','propose-correction','重み names an abstract graph weight; 重量 means physical weight.','moderate'),
 ('Minimum weight: {percent}%','ko'): ('최소 가중치: {percent}%','propose-correction','가중치 is the scoring/graph weight; 무게 means physical weight.','moderate'),
 ('Minimum weight: {percent}%','vi'): ('Trọng số tối thiểu: {percent}%','propose-correction','Trọng số names an abstract graph/scoring weight; trọng lượng means physical weight.','moderate'),
 ('Minimum weight: {percent}%','zh-Hans'): ('最低权重：{percent}%','propose-correction','权重 names an abstract graph/scoring weight; 重量 means physical weight.','moderate'),
 ('Minimum weight: {percent}%','zh-Hant'): ('最低權重：{percent}%','propose-correction','權重 names an abstract graph/scoring weight; 重量 means physical weight.','moderate'),

 ('Local quality signals are ignored by reviewer override','de'): ('Eine manuelle Übersteuerung durch die prüfende Person ignoriert lokale Qualitätssignale.','propose-correction','Prüferausnahme means a reviewer exception; Übersteuerung expresses an override of local quality signals.','moderate'),
 ('Local quality signals are ignored by reviewer override','fr'): ('La décision du réviseur prévaut sur les signaux de qualité locaux.','propose-refinement','Makes the override relation clear: the reviewer decision takes precedence over local quality signals.','moderate'),
 ('Local quality signals are ignored by reviewer override','pt-BR'): ('A decisão manual do revisor prevalece sobre os sinais locais de qualidade.','propose-refinement','States that the reviewer’s manual decision overrides local quality signals; substituição can read as replacement.','moderate'),

 ('Spectral bandwidth {bandwidth}kHz suggests {bitrate}kbps lossy source','vi'): ('Băng thông phổ {bandwidth}kHz gợi ý đây là nguồn âm thanh nén mất dữ liệu với tốc độ bit {bitrate}kbps.','propose-refinement','Clarifies that the spectral bandwidth suggests a lossy-compressed audio source encoded at the interpolated bitrate.','moderate'),

 ('slskdN media-server sync review','ar'): ('مراجعة مزامنة خادم الوسائط في slskdN','propose-correction','The current Arabic word order is awkward for a heading; this makes slskdN media-server synchronization the subject of the review.','moderate'),
}
CONTEXT_NOTES = {
 ' | Issue {id}':'Library health report appends this localized suffix after each issue title; preserve the leading separator and issue ID.',
 'limited download history':'Search candidate ranking maps a reason code to this localized reason label.',
 'Lidarr':'The label is used in the Lidarr view, integration card, and metadata settings navigation; retain the product name.',
 'Readiness: {readiness}':'Setup health check formats a readiness result value after this label.',
 'Expire candidates: {count}':'Discovery shelf preview labels the number of candidates that will expire.',
 'Album title: {title}':'Playlist intake displays the album title option and its interpolated value.',
 'Minimum weight: {percent}%':'Discovery graph settings display the minimum relationship weight percentage.',
 '0/{length}':'Wishlist progress counter shows current index over list length.',
 'Trusted jurors reached a supermajority recommendation.':'Quarantine jury displays this outcome when trusted jurors reach the configured supermajority.',
 's':'Used as the seconds unit beside durations and time values.',
 'Local quality signals are ignored by reviewer override':'Search action preview warning explains that reviewer override bypasses local quality signals.',
 'pods':'No exact production localization caller was found; the string appears as a feature-gate key only.',
 'ReplayGain will not run.':'Playlist intake displays this explanation when ReplayGain will not run.',
 '  {description}':'Media-server integration report uses this indented description line.',
 'AcoustID':'Song identification score and metadata settings display the AcoustID product label.',
 'untrusted provenance tier: {tier}':'Mesh evidence reason source is rendered through the dynamic localized reason formatter.',
 'Spectral bandwidth {bandwidth}kHz suggests {bitrate}kbps lossy source':'Library health report flags a spectral signature suggesting a lossy source and bitrate.',
 '- [{severity}] {area}: {summary}':'Network health report formats a finding bullet with severity, area, and summary.',
 'the selected port':'Port-forwarding rich tooltip substitutes this label when no local port is selected.',
 '{artist} - {title}':'Song identification result displays a localized artist-title accessibility label.',
 'Private Message from {username}':'No production caller was found; the only exact reference is a pending-source ledger test.',
 'slskdN media-server sync review':'Media-server integration report uses this heading.',
 'Evidence: {evidence}':'Setup health check includes formatted evidence after this label.',
 ' | {severity}':'Library health report appends localized severity after an issue title.',
 'Search seeds:':'Library health report labels the initial search queries used for diagnostics.',
}
PROTECTED_BY_SOURCE = {
 'Lidarr':['Lidarr'],
 'ReplayGain will not run.':['ReplayGain'],
 'AcoustID':['AcoustID'],
 'Spectral bandwidth {bandwidth}kHz suggests {bitrate}kbps lossy source':['kHz','kbps'],
 'slskdN media-server sync review':['slskdN'],
}
MANUAL_SOURCE_TEXT = {
 'pods':'Pod is a slskdN service/community node in this repository, not a physical pod.',
 'Private Message from {username}':'Private Message is a chat message, not a physical private-message label.',
}
W98_REASON = 'Prior W43 hold remains outstanding: MediaCore concatenates the separate localized fragments Message, has been/has not been, and seen in pod, then appends podId. The English composition prevents locale-specific word order and current translations often read pod as a physical pod/capsule. Replace the caller with complete positive/negative localized receipt-result strings before translating.'
EXPECTED_W40_BUNDLE_PATHS = [
 '/mnt/disks/scratch/task-worktrees/localization-20261102/slskdn-pr409-w40-root/bundle',
 '/mnt/disks/scratch/task-worktrees/localization-20261030/slskdn-w40-frozen-bundle'
]

def sha_bytes(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def sha_text(s: str) -> str: return sha_bytes(s.encode('utf-8'))
def run(*args: str, cwd: Path = REPO) -> str:
    return subprocess.check_output(list(args), cwd=cwd, text=True, stderr=subprocess.STDOUT).strip()
def read_json(p: Path): return json.loads(p.read_text(encoding='utf-8'))
def read_jsonl(p: Path): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def write_json(p: Path, x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_jsonl(p: Path, xs): p.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in xs),encoding='utf-8')
def catalog_path(loc): return f'src/web/public/locales/{loc}.json'
def pr_snapshot(repo_slug, number):
    raw=run('gh','pr','view',str(number),'--repo',repo_slug,'--json','number,state,isDraft,headRefOid,headRefName,baseRefOid,baseRefName,url')
    return {'repository':repo_slug,**json.loads(raw)}
def verify_manifest(root: Path, manifest: Path):
    bad=[]; count=0
    for line in manifest.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        digest, rel=line.split(None,1); rel=rel.lstrip('* '); count+=1
        p=root/rel
        if not p.is_file() or sha_bytes(p.read_bytes())!=digest: bad.append(rel)
    return {'path':str(manifest),'sha256':sha_bytes(manifest.read_bytes()),'entries':count,'failures':bad,'verified':not bad}

def main():
    if not OUT.is_dir(): raise SystemExit(f'Expected task scratch folder is absent: {OUT}')
    existing=[p.name for p in OUT.iterdir() if p.name!='build_w44_primary.py']
    if existing: raise SystemExit(f'Output folder already contains packet files; refusing overwrite: {existing}')
    if OUT/'SHA256SUMS.txt' in OUT.iterdir(): raise SystemExit('Existing checksum manifest; refusing overwrite')

    # Freshly query all seven current localization PR heads before using any window evidence.
    prs_start=[pr_snapshot(slug,num) for slug,num in REPO_NAMES]
    pr409_start=next(x for x in prs_start if x['number']==409)
    head=run('git','rev-parse','HEAD'); tree=run('git','rev-parse','HEAD^{tree}')
    branch=run('git','branch','--show-current')
    dirty=run('git','status','--porcelain=v1')
    if (head,tree,branch,dirty)!=(EXPECTED_HEAD,EXPECTED_TREE,EXPECTED_BRANCH,''):
        raise SystemExit(f'Worktree changed or dirty: {head} {tree} {branch} {dirty!r}')
    if pr409_start['state']!='OPEN' or not pr409_start['isDraft'] or pr409_start['headRefOid']!=EXPECTED_HEAD:
        raise SystemExit(f'Live slskdN #409 is not the pinned OPEN/DRAFT head: {pr409_start}')
    remote_line=run('git','ls-remote','taskgithub',f'refs/heads/{PR_BRANCH}')
    remote_head=remote_line.split()[0] if remote_line else None
    if remote_head!=EXPECTED_HEAD: raise SystemExit(f'PR branch remote head differs: {remote_head}')
    source_tree=run('git','rev-parse','HEAD:src/web/src')
    locale_tree=run('git','rev-parse','HEAD:src/web/public/locales')

    # Verify W43 retained evidence and record precisely what boundary it pins.
    w43_integrity=verify_manifest(W43,W43/'SHA256SUMS.txt')
    if not w43_integrity['verified']: raise SystemExit(f'W43 evidence checksum failure: {w43_integrity["failures"]}')
    w43_exact=read_json(W43/'primary/exact-head.json')
    w43_order=read_json(W43_ORDER)
    if w43_order['sourceOrdinalRange']!=[76,100] or len(w43_order['sourceIdsByOrdinal'])!=25:
        raise SystemExit('W43 retained order evidence does not exactly pin source ordinals 76-100.')
    if (REPO/'docs/pr-evidence/pr409-localization-2026-11-02/window44').exists():
        raise SystemExit('A W44 repo evidence directory exists; inspect it for a boundary before reconstructing.')
    w44_matches=[]
    for root in [W42,W43]:
        for p in root.rglob('*'):
            if p.is_file() and p.suffix in ('.json','.jsonl','.md','.txt'):
                if re.search(r'\bW44\b|window44|101\s*[-–]\s*125',p.read_text(encoding='utf-8',errors='ignore'),re.I):
                    w44_matches.append(str(p))
    if w44_matches: raise SystemExit(f'Unexpected W44 boundary references found in W42/W43 evidence: {w44_matches[:5]}')
    w42_primary=REPO/'docs/pr-evidence/pr409-localization-2026-11-02/window42/primary'
    w42_cross=REPO/'docs/pr-evidence/pr409-localization-2026-11-02/window42/crossreview'
    w42_app=REPO/'docs/pr-evidence/pr409-localization-2026-11-02/window42/application'
    w42_manifests=[verify_manifest(p,p/'SHA256SUMS.txt') for p in [w42_primary,w42_cross,w42_app]]
    if not all(m['verified'] for m in w42_manifests): raise SystemExit('A W42 repo evidence manifest failed verification.')
    w42_primary_external=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window42-primary-20261102')
    w42_cross_external=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window42-crossreview-independent-20261102')
    w40_primary_external=Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window40-primary-20261102')
    external_manifests=[verify_manifest(p,p/'SHA256SUMS.txt') for p in [w42_primary_external,w42_cross_external,w40_primary_external]]
    if not all(m['verified'] for m in external_manifests): raise SystemExit('A retained W40/W42 scratch packet checksum failed.')
    w42_future=W42/'crossreview/w43-future-boundary-reattestation.jsonl'
    w42_future_rows=read_jsonl(w42_future)
    if not w42_future_rows or {r.get('window') for r in w42_future_rows}!={43}:
        raise SystemExit('W42 future boundary does not pin only W43.')
    w40_bundle_status=[{'path':p,'exists':Path(p).exists()} for p in EXPECTED_W40_BUNDLE_PATHS]
    if any(x['exists'] for x in w40_bundle_status):
        raise SystemExit('A previously missing W40 frozen-bundle path now exists; inspect it before selection.')

    # Reattest all W1-W41 source-input files and source IDs from W43's retained exact-pin list.
    prior_file_rows=[]; w1_w41_id_rows={}; file_errors=[]
    for item in read_jsonl(W43_PRIOR_INPUTS):
        p=Path(item['path'])
        if not p.is_absolute(): p=REPO/p
        if not p.is_file():
            file_errors.append({'path':item['path'],'window':item['window'],'error':'pinned input file is missing'}); continue
        raw=p.read_bytes(); digest=sha_bytes(raw); rows=read_jsonl(p)
        ids=set()
        for r in rows:
            src=r.get('source') or r.get('catalogKey')
            sid=r.get('sourceId')
            if not sid and isinstance(r.get('id'),str) and ':' in r['id']: sid=r['id'].split(':',1)[1]
            if not src or not sid:
                file_errors.append({'path':item['path'],'window':item['window'],'error':'input row lacks source or sourceId'}); continue
            sh=sha_text(src); expected='src_'+sh[:16]
            if sid!=expected or (r.get('sourceSha256') and r['sourceSha256']!=sh):
                file_errors.append({'path':item['path'],'window':item['window'],'error':f'source ID/hash mismatch for {sid}'}); continue
            ids.add(sid)
            rec=w1_w41_id_rows.setdefault(sid,{'sourceId':sid,'source':src,'sourceSha256':sh,'windows':[],'inputPaths':[]})
            if rec['source']!=src or rec['sourceSha256']!=sh:
                file_errors.append({'path':item['path'],'window':item['window'],'error':f'conflicting source identity for {sid}'})
            rec['windows'].append(item['window']); rec['inputPaths'].append(item['path'])
        passed=(digest==item['pinnedSha256']==item['currentSha256'] and len(rows)==item['pinnedRows'] and len(ids)==item['pinnedUniqueSourceIds'])
        if not passed: file_errors.append({'path':item['path'],'window':item['window'],'error':'pinned/current hash or row/ID count mismatch'})
        prior_file_rows.append({'window':item['window'],'path':item['path'],'pinnedSha256':item['pinnedSha256'],
          'currentSha256':digest,'rows':len(rows),'pinnedRows':item['pinnedRows'],'uniqueSourceIds':len(ids),
          'pinnedUniqueSourceIds':item['pinnedUniqueSourceIds'],'matchesW43Reattestation':passed})
    if file_errors: raise SystemExit(f'W1-W41 pin reattestation errors: {file_errors[:8]}')
    if len(prior_file_rows)!=41 or len(w1_w41_id_rows)!=1022:
        raise SystemExit(f'Unexpected W1-W41 count: files={len(prior_file_rows)} IDs={len(w1_w41_id_rows)}')

    # Load and verify W42/W43 reviewed source IDs, preserving their recorded source ordinals only as provenance.
    w42_sources=read_jsonl(W42_SOURCE_SLICE)
    if len(w42_sources)!=25: raise SystemExit(f'W42 source-slice row count is {len(w42_sources)}')
    w42_ids={}
    for r in w42_sources:
        src=r['source']; sh=sha_text(src); sid='src_'+sh[:16]
        if sid!=r['sourceId'] or sh!=r['sourceSha256'] or not 51<=r['sourceOrdinal']<=75:
            raise SystemExit(f'W42 source-slice identity mismatch for {r.get("sourceId")}')
        w42_ids[sid]={'sourceId':sid,'source':src,'sourceSha256':sh,'window':42,'sourceOrdinal':r['sourceOrdinal'],
          'evidencePath':str(W42_SOURCE_SLICE.relative_to(REPO))}
    w43_ids={}
    for r in w43_order['sourceIdsByOrdinal']:
        src=r['source']; sh=sha_text(src); sid='src_'+sh[:16]
        if sid!=r['sourceId'] or sh!=r['sourceSha256'] or not 76<=r['sourceOrdinal']<=100:
            raise SystemExit(f'W43 retained source identity mismatch for {sid}')
        w43_ids[sid]={'sourceId':sid,'source':src,'sourceSha256':sh,'window':43,'sourceOrdinal':r['sourceOrdinal'],
          'evidencePath':str(W43_ORDER.relative_to(REPO))}
    w1_ids=set(w1_w41_id_rows); w42_id_set=set(w42_ids); w43_id_set=set(w43_ids)
    if w1_ids & w42_id_set or w1_ids & w43_id_set or w42_id_set & w43_id_set:
        raise SystemExit('Committed W1-W43 source-ID windows overlap.')
    prior_ids=w1_ids|w42_id_set|w43_id_set
    if len(prior_ids)!=1072: raise SystemExit(f'Expected 1,072 unique W1-W43 IDs; got {len(prior_ids)}')

    # Current 12 JSON catalogs each contain the same ordered 6,170 English source keys.
    catalogs={}; catalog_meta={}; ordered_keys=None
    for loc in LOCALES:
        rel=catalog_path(loc); p=REPO/rel; raw=p.read_bytes(); data=json.loads(raw.decode('utf-8')); keys=list(data)
        if len(keys)!=6170: raise SystemExit(f'{loc} catalog has {len(keys)} keys, expected 6,170.')
        if ordered_keys is None: ordered_keys=keys
        elif keys!=ordered_keys: raise SystemExit(f'{loc} catalog has a different ordered source-key inventory.')
        catalogs[loc]=data
        catalog_meta[loc]={'locale':loc,'path':rel,'blobOid':run('git','rev-parse',f'HEAD:{rel}'),
          'fileSha256':sha_bytes(raw),'bytes':len(raw),'entryCount':len(keys)}
    if len(set(ordered_keys))!=6170: raise SystemExit('Duplicate source keys in current locale catalogs.')
    source_by_id={}
    for source in ordered_keys:
        sh=sha_text(source); sid='src_'+sh[:16]
        if sid in source_by_id and source_by_id[sid]['source']!=source: raise SystemExit(f'16-hex source ID collision at {sid}')
        source_by_id[sid]={'sourceId':sid,'source':source,'sourceSha256':sh}
    if len(source_by_id)!=6170: raise SystemExit('Source ID inventory is not a one-to-one mapping.')

    # All historical W1-W43 sources must still exist under the exact same English catalog key.
    current_sources=set(ordered_keys)
    prior_not_current=[]
    for sid,rec in {**w1_w41_id_rows,**w42_ids,**w43_ids}.items():
        if rec['source'] not in current_sources: prior_not_current.append(sid)
    if prior_not_current: raise SystemExit(f'Previously reviewed source IDs absent from current catalog: {prior_not_current[:10]}')
    pending=sorted((rec['sourceId'],rec['source'],rec['sourceSha256']) for rec in source_by_id.values() if rec['sourceId'] not in prior_ids)
    if len(pending)!=5098: raise SystemExit(f'Expected 5,098 pending source IDs after W1-W43; got {len(pending)}')
    selected=pending[:25]
    if [r[0] for r in selected]!=EXPECTED_RECONSTRUCTED_IDS:
        raise SystemExit('Deterministic reconstructed slice differs from the previously derived expected ID list.')
    selections=[]
    selected_by_id={}
    for rank,(sid,source,sh) in enumerate(selected,1):
        if sid in prior_ids: raise SystemExit(f'Selected source {sid} was already reviewed.')
        selected_by_id[sid]={'selectionRank':rank,'sourceId':sid,'source':source,'sourceSha256':sh}
        selections.append({'selectionRank':rank,'sourceId':sid,'source':source,'sourceSha256':sh,
          'sourceOrdinal':None,'selectionBasis':'rank in lexicographically sorted current pending source IDs; no historical ordinal claimed'})

    # Load all tracked source code and pin direct localization calls to exact current lines/files.
    src_paths=run('git','ls-files','src/web/src').splitlines()
    lines_by_path={}; file_pin_cache={}
    for rel in src_paths:
        if '.test.' in rel or '.stories.' in rel or '.spec.' in rel: continue
        p=REPO/rel
        if not p.is_file(): continue
        try: lines_by_path[rel]=p.read_text(encoding='utf-8').splitlines()
        except UnicodeDecodeError: continue
    def file_pin(rel):
        if rel not in file_pin_cache:
            p=REPO/rel; file_pin_cache[rel]={'path':rel,'blobOid':run('git','rev-parse',f'HEAD:{rel}'),'fileSha256':sha_bytes(p.read_bytes())}
        return file_pin_cache[rel]
    def make_ref(sid,source,rel,line_no,role,exact=True):
        lines=lines_by_path[rel]; line=lines[line_no-1]
        return {'sourceId':sid,'source':source,'sourceSha256':sha_text(source),'path':rel,'line':line_no,
          'lineText':line,'lineSha256':sha_text(line),'fileSha256':file_pin(rel)['fileSha256'],
          'blobOid':file_pin(rel)['blobOid'],'contextBefore':lines[max(0,line_no-4):line_no-1],
          'contextAfter':lines[line_no:min(len(lines),line_no+3)],'referenceRole':role,
          'exactSourceLiteralMatch':exact,'verifiedAtCurrentHead':True}
    def direct_patterns(source):
        q=re.escape(source); quote=r'(["\'])'
        return [
          re.compile(r'interface(?:Attribute|Toast)?Text(?:Props|Output)?\s*\(\s*'+quote+q+r'\1'),
          re.compile(r'(?:LocalizedText|LocalizedOutputText|LocalizedRichText)\s+source\s*=\s*\{\s*'+quote+q+r'\1'),
          re.compile(r'(?:LocalizedText|LocalizedOutputText|LocalizedRichText)\s+source\s*=\s*'+quote+q+r'\1'),
          re.compile(r'getApiErrorMessageOutput\s*\(\s*'+quote+q+r'\1'),
          re.compile(r'\bt\s*\(\s*'+quote+q+r'\1'),
        ]
    caller_records=[]; caller_by_id={}
    for sid,source,sh in selected:
        refs=[]
        pats=direct_patterns(source)
        for rel,lines in lines_by_path.items():
            for n,line in enumerate(lines,1):
                if any(p.search(line) for p in pats):
                    refs.append(make_ref(sid,source,rel,n,'direct-localized-caller'))
        # Preserve the data branch that selects the limited-download reason before its localizer.
        if source=='limited download history':
            rel='src/web/src/lib/searchCandidateRanking.js'
            for n,line in enumerate(lines_by_path[rel],1):
                if re.search(r'(["\'])limited download history\1',line):
                    refs.append(make_ref(sid,source,rel,n,'reason-selection-branch'))
        # The untrusted-tier source is catalog data passed through a dynamic localizer.
        if source=='untrusted provenance tier: {tier}':
            rel='src/web/src/lib/meshEvidenceReasonSources.json'
            for n,line in enumerate(lines_by_path[rel],1):
                if source in line:
                    refs.append(make_ref(sid,source,rel,n,'localized-source-data'))
            rel='src/web/src/lib/meshEvidencePolicy.js'
            for n,line in enumerate(lines_by_path[rel],1):
                if 'interfaceText(source,' in line:
                    refs.append(make_ref(sid,source,rel,n,'dynamic-localization-helper',False))
            rel='src/web/src/components/System/Mesh/MeshEvidencePolicy.jsx'
            for n,line in enumerate(lines_by_path[rel],1):
                if 'LocalizedText source={source}' in line:
                    refs.append(make_ref(sid,source,rel,n,'dynamic-localized-renderer',False))
        # Pin a non-localizing feature-gate use to explain the pods caller gap.
        if source=='pods':
            rel='src/web/src/components/System/MediaCore/index.jsx'
            for n,line in enumerate(lines_by_path[rel],1):
                if "isFeatureEnabled(featureGates, 'pods')" in line:
                    refs.append(make_ref(sid,source,rel,n,'feature-gate-only-reference',False))
        # The private-message phrase is present only in a test ledger; keep that evidence separate.
        if source=='Private Message from {username}':
            for rel in src_paths:
                if '.test.' not in rel: continue
                p=REPO/rel
                if not p.is_file(): continue
                try: test_lines=p.read_text(encoding='utf-8').splitlines()
                except UnicodeDecodeError: continue
                for n,line in enumerate(test_lines,1):
                    if source in line:
                        raw=p.read_bytes()
                        refs.append({'sourceId':sid,'source':source,'sourceSha256':sha_text(source),'path':rel,'line':n,
                          'lineText':line,'lineSha256':sha_text(line),'fileSha256':sha_bytes(raw),
                          'blobOid':run('git','rev-parse',f'HEAD:{rel}'),'contextBefore':test_lines[max(0,n-4):n-1],
                          'contextAfter':test_lines[n:min(len(test_lines),n+3)],'referenceRole':'test-only-source-ledger-reference',
                          'exactSourceLiteralMatch':True,'verifiedAtCurrentHead':True})
        refs.sort(key=lambda x:(x['path'],x['line'],x['referenceRole']))
        caller_by_id[sid]=refs
        prod=[x for x in refs if x['referenceRole'] in {'direct-localized-caller','dynamic-localization-helper','dynamic-localized-renderer','localized-source-data','reason-selection-branch'}]
        status='production-localization-reference-found' if prod else 'no-production-localization-caller-found'
        if sid=='src_049c287ed3e2d554': status='feature-gate-only-no-production-display-caller'
        if sid=='src_07340fd83dfc3c75': status='test-only-reference-no-production-caller'
        caller_records.append({'sourceId':sid,'source':source,'sourceSha256':sh,'callerSearchScope':'all tracked src/web/src files; exact quoted source keys matched against known localizers; tests/stories excluded except separately pinned test-only references',
          'callerUseStatus':status,'callerRefs':refs,'callerReferenceCount':len(refs),
          'productionLocalizationReferenceCount':len(prod),'contextSummary':CONTEXT_NOTES[source]})
    # Two no-caller sources are held; all other selected sources need at least one production localized path.
    for sid,source,sh in selected:
        if sid not in HOLD_SOURCE_IDS and not any(r['referenceRole'] in {'direct-localized-caller','dynamic-localization-helper','dynamic-localized-renderer','localized-source-data','reason-selection-branch'} for r in caller_by_id[sid]):
            raise SystemExit(f'Unexpected caller gap for selected source {sid}: {source}')
        if sid in HOLD_SOURCE_IDS and any(r['referenceRole']=='direct-localized-caller' for r in caller_by_id[sid]):
            raise SystemExit(f'Unexpected production localization caller for held source {sid}')

    # Spanish formal lane pin and direct-address applicability: no W44 source text addresses the user.
    formal_bytes=FORMAL_IDS.read_bytes()
    if sha_bytes(formal_bytes)!=FORMAL_IDS_SHA256: raise SystemExit('Spanish formal-lane accumulator hash changed.')
    formal_ids={r['id'] for r in read_jsonl(FORMAL_IDS)}
    if len(formal_ids)!=4800: raise SystemExit(f'Unexpected Spanish formal accumulator row count: {len(formal_ids)}')
    user_address=re.compile(r'\b(?:you|your|yours|yourself|yourselves)\b',re.I)
    spanish_address=re.compile(r'\b(?:tú|usted|ustedes|vosotros|vosotras|te|ti|contigo|tuyo|tuya|tuyos|tuyas|puedes|podrás|debes|quieres)\b',re.I)
    spanish_formal_rows=[]
    for sid,source,sh in selected:
        es=catalogs['es'][source]; formal_present=f'es:{sid}' in formal_ids
        english_forms=user_address.findall(source); spanish_forms=spanish_address.findall(es)
        spanish_formal_rows.append({'selectionRank':selected_by_id[sid]['selectionRank'],'sourceId':sid,'source':source,
          'sourceSha256':sh,'currentSpanishTarget':es,'currentSpanishTargetSha256':sha_text(es),
          'formalLaneAccumulatorCellPresent':formal_present,'englishDirectAddressForms':english_forms,
          'currentSpanishDirectAddressForms':spanish_forms,
          'formalRegisterApplicability':'not-applicable-no-direct-address-in-source',
          'reviewedRegisterDisposition':'keep-neutral-current-or-proposed-label',
          'nativeSpeakerApproval':'outstanding'})

    # Structural and protected-literal validation for all 300 exact current targets and every proposed target.
    placeholder_re=re.compile(r'\{[A-Za-z0-9_]+\}')
    markup_re=re.compile(r'</?[A-Za-z][^>]*>')
    def tokens(text):
        return sorted(placeholder_re.findall(text)), sorted(markup_re.findall(text))
    def literal_count(text,literal):
        return len(re.findall(r'(?<![A-Za-z0-9])'+re.escape(literal)+r'(?![A-Za-z0-9])',text))
    cells=[]; proposals=[]; disposition_counts=Counter(); structural_issues=[]
    for rank,(sid,source,sh) in enumerate(selected,1):
        for loc in LOCALES:
            current=catalogs[loc][source]; current_sha=sha_text(current)
            src_ph,src_markup=tokens(source); cur_ph,cur_markup=tokens(current)
            protected=PROTECTED_BY_SOURCE.get(source,[])
            missing_current=[t for t in protected if literal_count(current,t)!=literal_count(source,t)]
            if src_ph!=cur_ph or src_markup!=cur_markup:
                structural_issues.append({'sourceId':sid,'locale':loc,'currentTargetSha256':current_sha,'placeholderMismatch':src_ph!=cur_ph,'markupMismatch':src_markup!=cur_markup,'protectedLiteralMismatches':missing_current})
            cand=CANDIDATES.get((source,loc))
            if sid in HOLD_SOURCE_IDS:
                disposition='hold'; target=None; target_sha=None
                if sid=='src_049c287ed3e2d554':
                    reason='No production localized caller uses the catalog key pods. Its only exact code use is the feature-gate identifier in MediaCore/index.jsx; longer pod-related messages are separate source keys. Hold pending a concrete user-facing caller.'
                else:
                    reason='The only exact occurrence is in pendingSourceLedger.test.js; no production localized caller is present. Hold until a production UI callsite is identified.'
                confidence='high'
            elif cand:
                target,disposition,reason,confidence=cand
                target_sha=sha_text(target)
            else:
                disposition='accept-current'; target=current; target_sha=current_sha
                reason=CONTEXT_NOTES[source]+' Current wording preserves the source meaning in this pinned caller context.'
                confidence='moderate'
            target_ph,target_markup=(tokens(target) if target is not None else (None,None))
            missing_candidate=[t for t in protected if target is not None and literal_count(target,t)!=literal_count(source,t)]
            if target is not None and (src_ph!=target_ph or src_markup!=target_markup or missing_candidate):
                raise SystemExit(f'Candidate/current structural or protected-literal mismatch {loc}:{sid}: {src_ph}/{target_ph} {src_markup}/{target_markup} {missing_candidate}')
            if disposition=='hold' and current_sha is None: raise SystemExit('hold without a current exact hash')
            disposition_counts[disposition]+=1
            caller_info=caller_by_id[sid]
            caller_use=next(x['callerUseStatus'] for x in caller_records if x['sourceId']==sid)
            formal_info=next((x for x in spanish_formal_rows if x['sourceId']==sid),None) if loc=='es' else None
            row={
              'selectionRank':rank,'sourceOrdinal':None,'sourceSelectionMethod':'lexicographic rank among pending source IDs; no historical ordinal claimed',
              'sourceId':sid,'sourceText':source,'sourceSha256':sh,'locale':loc,'catalogKey':source,
              'catalogPath':catalog_path(loc),'catalogBlobOid':catalog_meta[loc]['blobOid'],'catalogFileSha256':catalog_meta[loc]['fileSha256'],
              'currentTarget':current,'currentTargetSha256':current_sha,
              'disposition':disposition,'reviewedTarget':target,'reviewedTargetSha256':target_sha,
              'rationale':reason,'confidence':confidence,
              'callerUseStatus':caller_use,'callerRefsSourceId':sid,'callerContextSummary':CONTEXT_NOTES[source],
              'priorEvidenceScan':{'w1Through41InputFilesReattested':41,'w1Through41UniqueSourceIds':1022,
                'w42SourceIds':25,'w43SourceIds':25,'w1Through43UniqueSourceIds':1072,
                'sourceIdPreviouslyReviewed':sid in prior_ids,'exactPriorDispositionRows':0},
              'sourcePlaceholders':src_ph,'currentTargetPlaceholders':cur_ph,'reviewedTargetPlaceholders':target_ph,
              'sourceMarkup':src_markup,'currentTargetMarkup':cur_markup,'reviewedTargetMarkup':target_markup,
              'currentPlaceholderParity':'exact' if src_ph==cur_ph else 'mismatch',
              'reviewedPlaceholderParity':'exact' if target is not None and src_ph==target_ph else ('held-unproposed' if target is None else 'mismatch'),
              'currentMarkupParity':'exact' if src_markup==cur_markup else 'mismatch',
              'reviewedMarkupParity':'exact' if target is not None and src_markup==target_markup else ('held-unproposed' if target is None else 'mismatch'),
              'protectedLiterals':protected,'currentProtectedLiteralMismatches':missing_current,
              'reviewedProtectedLiteralMismatches':missing_candidate,
              'protectedLiteralParity':'exact' if target is not None and not missing_candidate else ('held-unproposed' if target is None else 'mismatch'),
              'sourceContainsUserAddress':bool(user_address.search(source)),
              'spanishFormalApplicability':formal_info,
              'nativeSpeakerReview':'outstanding'}
            cells.append(row)
            if cand:
                proposals.append({'selectionRank':rank,'sourceOrdinal':None,'sourceId':sid,'source':source,'sourceSha256':sh,
                  'locale':loc,'catalogPath':catalog_path(loc),'catalogBlobOid':catalog_meta[loc]['blobOid'],
                  'catalogFileSha256':catalog_meta[loc]['fileSha256'],'currentTarget':current,'currentTargetSha256':current_sha,
                  'proposedTarget':target,'proposedTargetSha256':target_sha,'disposition':disposition,'confidence':confidence,
                  'rationale':reason,'sourcePlaceholders':src_ph,'proposedPlaceholders':target_ph,
                  'sourceMarkup':src_markup,'proposedMarkup':target_markup,'protectedLiterals':protected,
                  'proposedProtectedLiteralMismatches':missing_candidate,'callerRefsSourceId':sid,
                  'nativeSpeakerApproval':'outstanding'})
    if structural_issues: raise SystemExit(f'Current target structure needs review: {structural_issues[:8]}')
    if len(cells)!=300 or len(proposals)!=31: raise SystemExit(f'Unexpected result rows: {len(cells)} cells, {len(proposals)} candidates')
    if disposition_counts!=Counter({'accept-current':245,'propose-correction':15,'propose-refinement':16,'hold':24}):
        raise SystemExit(f'Unexpected disposition counts: {disposition_counts}')

    # Reattest the 11 prior W98 holds at the live head without folding them into the new pending slice.
    w43_decision_rows=read_jsonl(W43_DECISIONS)
    w98_old=[r for r in w43_decision_rows if r['sourceId']==W98_ID and r['disposition']=='hold']
    if len(w98_old)!=11: raise SystemExit(f'Expected 11 prior W98 non-Spanish holds, found {len(w98_old)}')
    w98_source=w98_old[0]['source']; w98_sha=sha_text(w98_source)
    if w98_source!='seen in pod' or 'src_'+w98_sha[:16]!=W98_ID: raise SystemExit('W98 source identity mismatch.')
    w98_file='src/web/src/components/System/MediaCore/MediaCorePods.jsx'
    w98_lines=lines_by_path[w98_file]
    w98_ref_no=next(i for i,line in enumerate(w98_lines,1) if 'LocalizedText source={"seen in pod"}' in line)
    w98_context=[make_ref(W98_ID,w98_source,w98_file,w98_ref_no,'fragment-in-concatenated-result')]
    for fragment in ['LocalizedText source={"Message"}','LocalizedText source={"has been"}','LocalizedText source={"has not been"}']:
        n=next(i for i,line in enumerate(w98_lines,1) if fragment in line)
        w98_context.append(make_ref(W98_ID,fragment,w98_file,n,'adjacent-localized-fragment',False))
    w98_rows=[]
    for old in w98_old:
        loc=old['locale']; current=catalogs[loc][w98_source]; cur_sha=sha_text(current)
        if current!=old['currentTarget'] or cur_sha!=old['currentTargetSha256']:
            raise SystemExit(f'Prior W98 held target changed at current head for {loc}.')
        w98_rows.append({'priorWindow':43,'priorDisposition':'hold','sourceId':W98_ID,'source':w98_source,
          'sourceSha256':w98_sha,'locale':loc,'catalogPath':catalog_path(loc),'catalogBlobOid':catalog_meta[loc]['blobOid'],
          'catalogFileSha256':catalog_meta[loc]['fileSha256'],'currentTarget':current,'currentTargetSha256':cur_sha,
          'w43TargetSha256':old['currentTargetSha256'],'matchesPriorHeldValue':True,'priorReason':old['rationale'],
          'currentCallerFile':w98_file,'currentCallerRefs':w98_context,'outstandingHold':True,
          'newW44SliceMember':False,'disposition':'preserve-existing-hold','reason':W98_REASON})
    runtime_rows=read_jsonl(W43_RUNTIME_GAPS)
    w98_runtime=next((r for r in runtime_rows if r.get('sourceId')==W98_ID),None)
    if not w98_runtime: raise SystemExit('W43 W98 source/runtime gap evidence missing.')

    # Verify live PR #409 and local tree again; also capture the other six PRs at finish.
    prs_end=[pr_snapshot(slug,num) for slug,num in REPO_NAMES]
    pr409_end=next(x for x in prs_end if x['number']==409)
    remote_end_line=run('git','ls-remote','taskgithub',f'refs/heads/{PR_BRANCH}')
    remote_end=remote_end_line.split()[0] if remote_end_line else None
    if pr409_end!=pr409_start or remote_end!=EXPECTED_HEAD or run('git','rev-parse','HEAD')!=EXPECTED_HEAD or run('git','rev-parse','HEAD^{tree}')!=EXPECTED_TREE or run('git','status','--porcelain=v1'):
        raise SystemExit('Live PR #409, remote branch, or local worktree changed during review.')

    # Exact inventory and prior-ID material retained in the packet.
    prior_records=[]
    for sid,rec in sorted({**w1_w41_id_rows,**w42_ids,**w43_ids}.items()):
        prior_records.append({**rec,'presentInCurrentInventory':rec['source'] in current_sources,
          'sourceIdRecheckedAgainstCurrentKey':sid=='src_'+sha_text(rec['source'])[:16]})
    inventory_rows=[]
    selected_rank={r['sourceId']:r['selectionRank'] for r in selections}
    for source in ordered_keys:
        sid='src_'+sha_text(source)[:16]
        inventory_rows.append({'sourceId':sid,'source':source,'sourceSha256':sha_text(source),
          'previouslyReviewed':sid in prior_ids,'selectedPendingRank':selected_rank.get(sid),
          'currentTargetCount':len(LOCALES)})
    w43_match_state={
      'retainedW43Head':w43_exact.get('head'),'retainedW43Tree':w43_exact.get('tree'),
      'retainedSourceOrdinalRange':w43_order['sourceOrdinalRange'],
      'explicitW44BoundaryFound':False,'searchedW42W43PacketMatches':[],
      'w42FutureBoundaryScope':sorted({r.get('window') for r in w42_future_rows}),
      'w44EvidenceDirectoryExists':False,'noW44OrdinalInvented':True,
      'w40BundlePaths':w40_bundle_status,
      'provenanceLimit':'W43 pins only source ordinals 76–100; W42 future-boundary evidence pins W43 only. The task-named W40 frozen bundle directories are absent, so the historical full pending queue cannot be reconstructed. W44 selection is reconstructed deterministically from the exact current 6,170-key inventory after excluding every committed W1–W43 source ID; selectionRank is used instead of a fabricated ordinal.'
    }

    # Write checksummed task-scratch packet.
    write_json(OUT/'exact-head.json',{
      'repository':'snapetech-org/slskdN','pullRequest':409,'state':'OPEN','isDraft':True,
      'head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'branch':branch,'prHeadBranch':PR_BRANCH,
      'remote':'taskgithub','remoteHeadAtStart':remote_head,'remoteHeadAtEnd':remote_end,
      'livePRAtStart':pr409_start,'livePRAtEnd':pr409_end,'allSevenLocalizationPRsAtStart':prs_start,
      'allSevenLocalizationPRsAtEnd':prs_end,'verifiedAtUtc':datetime.now(timezone.utc).isoformat(),
      'worktree':str(REPO),'worktreeCleanBeforeAndAfter':True})
    write_json(OUT/'input-integrity.json',{
      'head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'sourceSubtreeTree':source_tree,'localeCatalogSubtreeTree':locale_tree,
      'w43PacketManifest':w43_integrity,'w42RepoEvidenceManifests':w42_manifests,'retainedScratchPacketManifests':external_manifests,
      'w43ExactHeadRecord':w43_exact,'w43OrderBoundaryRecord':w43_order,'w42FutureBoundarySha256':sha_bytes(w42_future.read_bytes()),
      'w42FutureBoundaryOnlyPinsW43':True,'explicitW44BoundaryFound':False,
      'w1ThroughW41InputFilesReattested':len(prior_file_rows),'w1ThroughW41UniqueSourceIds':len(w1_w41_id_rows),
      'w42SourceIdsReattested':len(w42_ids),'w43SourceIdsReattested':len(w43_ids),
      'w1ThroughW43UniqueSourceIds':len(prior_ids),'priorWindowSetsDisjoint':True,
      'allPriorSourceKeysPresentInCurrentCatalog':True,'sourceCatalogCount':len(catalog_meta),
      'sourceInventoryCount':len(source_by_id),'pendingCountAfterExclusion':len(pending),
      'w40BundlePaths':w40_bundle_status,'readOnly':True,'repoMutated':False,'testsBuildsCiBrowserRun':False})
    write_json(OUT/'catalog-structure.json',{
      'head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'sourceSubtreeTree':source_tree,'localeCatalogSubtreeTree':locale_tree,
      'sourceKeyCountPerLocale':6170,'orderedKeyInventoryCount':len(ordered_keys),
      'orderedKeyInventorySha256':sha_text(json.dumps(ordered_keys,ensure_ascii=False,separators=(',',':'))),
      'sourceIdInventorySha256':sha_text(json.dumps(sorted(source_by_id),separators=(',',':'))),
      'sourceIsLocaleJsonObjectKey':True,'englishLocaleFilePresent':(REPO/'src/web/public/locales/en.json').exists(),
      'catalogs':[catalog_meta[x] for x in LOCALES]})
    write_json(OUT/'order-and-boundary.json',{
      'windowLabel':'W44 deterministic reconstruction; not a historically pinned ordinal window',
      'selectionMethod':'Build source IDs as src_ plus the first 16 hex characters of SHA-256 over each exact English source key. Exclude all 1,072 source IDs in committed W1-W43 inputs. Sort the remaining IDs lexicographically and select ranks 1-25.',
      'sourceOrdinalRange':None,'selectionRankRange':[1,25],'selectedSourceIds':[r['sourceId'] for r in selections],
      'pendingSourceIdsBeforeSelection':len(pending),'currentCatalogInventoryCount':len(source_by_id),
      'priorW1W41UniqueSourceIds':len(w1_w41_id_rows),'priorW42SourceIds':len(w42_ids),'priorW43SourceIds':len(w43_ids),
      'priorW1W43UniqueSourceIds':len(prior_ids),'priorWindowSetsDisjoint':True,
      'fullFrozenPendingQueueReproduced':False,'noOrdinal101To125Invented':True,
      'w43BoundaryAssessment':w43_match_state})
    write_jsonl(OUT/'prior-window-input-reattestation.jsonl',prior_file_rows)
    write_jsonl(OUT/'prior-source-ids.jsonl',prior_records)
    write_jsonl(OUT/'source-inventory.jsonl',inventory_rows)
    write_jsonl(OUT/'pending-source-selection.jsonl',selections)
    write_jsonl(OUT/'caller-context.jsonl',caller_records)
    write_jsonl(OUT/'review-decisions.jsonl',cells)
    write_jsonl(OUT/'candidate-proposals.jsonl',proposals)
    write_jsonl(OUT/'source-runtime-gaps.jsonl',[
      {'sourceId':'src_049c287ed3e2d554','source':'pods','affectedCells':12,'disposition':'hold-all-12-cells',
       'callerUseStatus':'feature-gate-only-no-production-display-caller',
       'callerRefs':caller_by_id['src_049c287ed3e2d554'],
       'gap':'No exact production localization callsite uses the catalog key. The only exact code reference is the pods feature-gate identifier; separate longer UI phrases have their own source keys.',
       'actionNeeded':'Identify a production display callsite and the exact UI role before proposing translations.'},
      {'sourceId':'src_07340fd83dfc3c75','source':'Private Message from {username}','affectedCells':12,'disposition':'hold-all-12-cells',
       'callerUseStatus':'test-only-reference-no-production-caller',
       'callerRefs':caller_by_id['src_07340fd83dfc3c75'],
       'gap':'No production localized callsite found; the exact phrase appears only in a pending-source-ledger test.',
       'actionNeeded':'Identify a production display callsite and the exact UI role before proposing translations.'},
      {'sourceId':W98_ID,'source':'seen in pod','affectedCells':11,'disposition':'prior-W43-hold-still-outstanding',
       'callerRefs':w98_context,'sourceRuntimeGapFromW43':w98_runtime,
       'gap':W98_REASON,'actionNeeded':'Replace the fragment-composition caller with complete positive and negative localized receipt results, then review all affected locales.'}
    ])
    write_jsonl(OUT/'w98-holds-reattestation.jsonl',w98_rows)
    write_jsonl(OUT/'spanish-formal-applicability.jsonl',spanish_formal_rows)
    write_jsonl(OUT/'structural-validation.jsonl',[
      {'selectionRank':r['selectionRank'],'sourceId':r['sourceId'],'locale':r['locale'],
       'currentTargetSha256':r['currentTargetSha256'],'reviewedTargetSha256':r['reviewedTargetSha256'],
       'sourcePlaceholders':r['sourcePlaceholders'],'reviewedTargetPlaceholders':r['reviewedTargetPlaceholders'],
       'currentPlaceholderParity':r['currentPlaceholderParity'],'reviewedPlaceholderParity':r['reviewedPlaceholderParity'],
       'sourceMarkup':r['sourceMarkup'],'reviewedTargetMarkup':r['reviewedTargetMarkup'],
       'currentMarkupParity':r['currentMarkupParity'],'reviewedMarkupParity':r['reviewedMarkupParity'],
       'protectedLiterals':r['protectedLiterals'],'currentProtectedLiteralMismatches':r['currentProtectedLiteralMismatches'],
       'reviewedProtectedLiteralMismatches':r['reviewedProtectedLiteralMismatches'],
       'disposition':r['disposition']} for r in cells])
    summary={
      'result':'PRIMARY_STATIC_REVIEW_COMPLETE_PENDING_INDEPENDENT_CROSS_REVIEW_AND_NATIVE_SPEAKER_REVIEW',
      'pullRequest':409,'head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'state':'OPEN','draft':True,
      'windowLabel':'W44 deterministic reconstruction','sourceOrdinalRange':None,
      'selectionRanks':[1,25],'sourceIds':25,'locales':len(LOCALES),'cells':len(cells),
      'dispositions':dict(disposition_counts),'candidateRows':len(proposals),
      'candidateByLocale':dict(Counter(p['locale'] for p in proposals)),
      'callerGaps':2,'heldCellsForCallerGaps':24,'currentStructuralMismatches':0,'candidateStructuralMismatches':0,
      'protectedLiteralMismatchesCurrent':sum(bool(r['currentProtectedLiteralMismatches']) for r in cells),
      'protectedLiteralMismatchesProposed':sum(bool(r['reviewedProtectedLiteralMismatches']) for r in cells),
      'spanishFormalApplicabilityRows':len(spanish_formal_rows),
      'spanishRowsWithDirectAddress':sum(bool(r['englishDirectAddressForms']) for r in spanish_formal_rows),
      'spanishFormalAccumulatorPresentForSelectedRows':sum(r['formalLaneAccumulatorCellPresent'] for r in spanish_formal_rows),
      'spanishFormalDisposition':'No selected English source directly addresses the user; formal/informal lane is not applicable. Existing Spanish values and neutral proposal remain unchanged.',
      'w1ThroughW43IdsReattested':len(prior_ids),'w1ThroughW41FilesReattested':len(prior_file_rows),
      'pendingSourceIdsAfterPriorExclusion':len(pending),'fullFrozenQueueReproduced':False,
      'w40BundleMissing':True,'explicitW44BoundaryFound':False,
      'w98PriorHoldCellsReattested':len(w98_rows),'w98PriorHoldCellsStillOutstanding':len(w98_rows),
      'nativeSpeakerReview':'outstanding','readOnly':True,'repoModified':False,'testsBuildsCiBrowserRun':False,
      'confidence':'moderate',
      'notes':['W44 has no exact historical boundary in retained W42/W43 evidence. No source ordinal 101-125 was invented.',
        'The slice is the first 25 lexicographically sorted pending source IDs from the exact current 6,170-key inventory after excluding all committed W1-W43 IDs.',
        'All 300 cells have exact source, current target, current catalog, and caller/source-gap pins.',
        'pods and Private Message from {username} are held in all 12 locales because no production localization caller exists.',
        'The prior W98 11-cell source/runtime hold was reattested and remains separately outstanding.',
        'Spanish formal register is not applicable for the selected strings because none contains direct user address.',
        'Static review only; no native-speaker or browser acceptance is claimed.']}
    write_json(OUT/'summary.json',summary)
    readme='''# slskdN PR #409 W44 reconstructed primary review

Scope: a deterministic pending-source reconstruction for 25 source IDs x 12 locales = 300 cells.

Live PR #409 remained OPEN/DRAFT at head f3fbd3f8db10f78768b9951a67b4b9de8581a408 and tree 9495c35a540ef2d2e845c833acb709365e0e26ac. The worktree was clean before and after. Seven localization PR heads were freshly queried at start and finish; see exact-head.json.

Selection provenance: W43 retained evidence pins only source ordinals 76-100, and W42 future-boundary evidence pins W43 only. No explicit W44 boundary was found. The task-named W40 frozen bundle paths are absent, so a historical pending-queue ordinal cannot be reconstructed. This packet derives the current 6,170-key source inventory from all 12 identical ordered locale catalogs, computes source IDs from exact English source keys, excludes all 1,072 committed W1-W43 IDs, sorts pending IDs lexicographically, then selects ranks 1-25. The packet does not call these ranks source ordinals and does not invent 101-125.

The ledger includes 300 exact-hash cell decisions with source/current target/catalog hashes, caller pins or caller-gap findings, placeholders, markup, protected literals, and Spanish formality applicability. Dispositions: 245 accept-current, 15 propose-correction, 16 propose-refinement, and 24 hold. The 24 holds are the two source keys with no production localization caller: pods and Private Message from {username}.

W98 seen in pod is not part of this reconstructed slice. Its prior 11 non-Spanish holds were reattested at the current head and remain outstanding because the caller concatenates English fragments in a fixed order.

Spanish register: none of the selected English strings directly addresses the user, so formal/informal lane applicability is not applicable. No native-speaker approval or browser review is claimed.

Static review only. No repository or PR files were changed; no tests, builds, CI, browser work, releases, or tags were run.

Files:
- review-decisions.jsonl: exact-hash decisions for all 300 cells.
- candidate-proposals.jsonl: 31 exact replacements.
- pending-source-selection.jsonl: the 25 ranked current pending source IDs.
- source-inventory.jsonl and prior-source-ids.jsonl: complete 6,170-key and W1-W43 ID exclusion evidence.
- w98-holds-reattestation.jsonl: prior W98 holds, kept separate from this slice.
- SHA256SUMS.txt: checksums for every packet file except the manifest itself.
'''
    (OUT/'README.md').write_text(readme,encoding='utf-8')
    files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt')
    (OUT/'SHA256SUMS.txt').write_text(''.join(f'{sha_bytes(p.read_bytes())}  {p.name}\n' for p in files),encoding='utf-8')
    print(json.dumps({'output':str(OUT),'head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'sources':25,'cells':len(cells),
      'dispositions':dict(disposition_counts),'proposals':len(proposals),'priorIds':len(prior_ids),
      'pendingAfterPriorExclusion':len(pending),'w98Holds':len(w98_rows),
      'callerGaps':2,'files':len(files)+1},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
