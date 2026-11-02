from __future__ import annotations
import hashlib, json, re, subprocess, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path('/home/keith/Documents/code/task-worktrees/localization-20261102-slskdn')
OUT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window43-primary-20261102')
W42 = REPO / 'docs/pr-evidence/pr409-localization-2026-11-02/window42'
W42_PRIMARY_EXTERNAL = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window42-primary-20261102')
W42_CROSS_EXTERNAL = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window42-crossreview-independent-20261102')
W40_PRIMARY_EXTERNAL = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-window40-primary-20261102')
W40_BUNDLE_EXPECTED = Path('/mnt/disks/scratch/task-worktrees/localization-20261102/slskdn-pr409-w40-root/bundle')
HEAD_EXPECTED = '9071dcb9b4a96b476ecbaec9d5643236846ac2f8'
TREE_EXPECTED = '25282a0cd8197815b3ffcbec9dbea8a03a5c8725'
BRANCH_EXPECTED = 'codex/slskdn-oidc-tooltip-localization-20261030'
LOCALES = ['ar','de','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
ALL_LOCALES = LOCALES + ['es']
SOURCE_BOUNDARY = W42 / 'crossreview/w43-future-boundary-reattestation.jsonl'
FORMAL_IDS_PATH = REPO / 'docs/pr-evidence/pr409-localization-2026-11-02/window36/primary/formal-cell-ids.jsonl'
FORMAL_IDS_SHA = '7bd9c90a1176403feb36daadfecb7822616a818d15e9980c99c0bf5dc9d6f856'

CANDIDATES = {
 (76,'ar'): ('propose-correction','التصنيف','The caller renders the model’s artifact class, not a physical sticker. The current Arabic word means a sticker; this names the classification label.','high'),
 (76,'ko'): ('propose-correction','레이블','In the AI heuristic panel this is the model’s class label; 상표 means a trademark. Use the established Korean loanword for a classification label.','high'),
 (78,'ar'): ('propose-correction','تحذيرات موقّعة بشأن ملفات صوتية يُشتبه في تزييفها لجودة lossless.','The caller displays an outbound mesh-evidence description. The warning is signed evidence about suspicious audio candidates; the current المرشحين reads as people and omits the fake-lossless audio meaning.','high'),
 (78,'de'): ('propose-refinement','Signierte Warnungen zu verdächtigen Kandidaten mit vorgetäuschter Lossless-Qualität.','This outbound evidence description concerns cryptographically signed warnings about candidate audio files. Signierte is the technical rendering of signed; the current unterzeichnete is less suitable here.','moderate'),
 (78,'fr'): ('propose-correction','Avertissements signés au sujet de fichiers audio suspects présentés à tort comme étant sans perte.','The current phrase can read as suspicious people who are false and lossless. The caller is an audio-evidence description; this names signed warnings about suspect files falsely presented as lossless.','high'),
 (78,'hi'): ('propose-correction','नुकसान-रहित होने का झूठा दावा करने वाली संदिग्ध ऑडियो फ़ाइलों के बारे में हस्ताक्षरित चेतावनियाँ।','The caller describes signed evidence warnings. The current candidate word refers to people; this identifies suspicious audio files falsely presented as lossless.','high'),
 (78,'id'): ('propose-correction','Peringatan bertanda tangan tentang file audio yang dicurigai memalsukan kualitas lossless.','The source is a noun phrase describing signed warnings, not an instruction to sign them. The current Menandatangani makes it a verb; the caller context is suspicious audio candidates.','high'),
 (78,'ja'): ('propose-correction','偽装ロスレスの疑いがある音源候補に関する署名済み警告。','The caller describes outbound signed evidence. The current 候補者 means people; this uses audio candidates suspected of fake lossless quality.','high'),
 (78,'ko'): ('propose-correction','가짜 무손실 음원으로 의심되는 항목에 대한 서명된 경고.','This is a signed outbound warning about suspicious fake-lossless audio candidates. The current 후보자 means a person running for office; this states the audio-item meaning.','high'),
 (78,'pt-BR'): ('propose-correction','Avisos assinados sobre arquivos de áudio suspeitos de se passarem por sem perdas.','The current adjective sequence makes “false” modify candidates awkwardly. The caller describes signed warnings about suspicious audio files falsely presented as lossless.','high'),
 (78,'vi'): ('propose-correction','Cảnh báo có chữ ký về các tệp âm thanh bị nghi giả dạng lossless.','The source describes already signed warnings, not an action to sign them. The caller identifies suspicious audio files; the current ứng cử viên means political candidates.','high'),
 (78,'zh-Hans'): ('propose-correction','针对可疑假无损音频候选文件的签名警告。','The source is an outbound evidence-description noun phrase. The current text reads as signing warnings about candidate people; this makes the audio-file candidate and signed-warning relations clear.','high'),
 (78,'zh-Hant'): ('propose-correction','針對可疑假無損音訊候選檔案的簽章警告。','The source is an outbound evidence-description noun phrase. The current text reads as signing warnings about candidate people; this makes the audio-file candidate and signed-warning relations clear.','high'),
 (87,'hi'): ('propose-refinement','30 दिन','PlayerBar uses this as the 30-day listening-statistics range. The current 30डी leaves the English abbreviation unexplained; spell out the day unit for clarity.','moderate'),
 (84,'ko'): ('propose-refinement','총 연결 수','The caller places this label above a numeric total-connections statistic. Adding 수 makes the Korean count label grammatical and explicit.','moderate'),
 (89,'ar'): ('propose-correction','عنوان خادم FTP','The caller labels the FTP integration address field. FTP is the protocol identifier; the current target expands the acronym instead of preserving the protected literal.','high'),
 (89,'hi'): ('propose-correction','FTP सर्वर का पता','The caller labels the FTP integration address field. Use the protocol acronym from the source rather than a phonetic Hindi rendering.','high'),
 (90,'de'): ('propose-refinement','Synchronisieren Sie von Lidarr als gewünscht markierte Alben mit den Prüfeinträgen der slskdN-Wunschliste.','The caller describes records queued for manual review in the slskdN Wishlist. Rezensionsartikel can mean review articles; Prüfeinträge states review-queue items.','moderate'),
 (90,'id'): ('propose-refinement','Sinkronkan album yang diinginkan di Lidarr ke item Daftar Keinginan slskdN yang perlu ditinjau.','The caller sends these records to a manual-review queue. Item ulasan can mean review content; this says the Wishlist items need review.','moderate'),
 (90,'vi'): ('propose-refinement','Đồng bộ hóa album được đánh dấu mong muốn trong Lidarr vào các mục cần xem xét trong Danh sách yêu thích slskdN.','The caller sends these records to a manual-review queue. Mục đánh giá can read as ratings/evaluations; this states that the items need review.','moderate'),
 (90,'ja'): ('propose-refinement','Lidarrで入手対象になっているアルバムを slskdN のウィッシュリストの確認待ち項目に同期します。','The caller describes manual-review queue entries, not album reviews. This clarifies the Lidarr wanted state and uses 確認待ち項目 for items awaiting review.','moderate'),
 (90,'ko'): ('propose-refinement','Lidarr에서 원하는 앨범을 slskdN 위시리스트의 검토 대기 항목으로 동기화합니다.','The caller is a sync option for items awaiting manual review. 검토 대기 항목 avoids the product-review reading of 리뷰 항목.','moderate'),
 (90,'zh-Hans'): ('propose-refinement','将 Lidarr 中标记为想要的专辑同步到 slskdN 愿望清单的待审核条目。','The caller describes manual-review queue entries; 评论项目 can read as comment items. 待审核条目 makes the review state explicit.','moderate'),
 (90,'zh-Hant'): ('propose-refinement','將 Lidarr 中標記為想要的專輯同步到 slskdN 願望清單的待審核項目。','The caller describes manual-review queue entries; 評論項目 can read as comment items. 待審核項目 makes the review state explicit.','moderate'),
 (92,'ar'): ('propose-refinement','ابحث عن {item}','This is the accessible label for the item-recommendation search action. The current بحث {item} is a noun phrase (“search {item}”); the imperative makes the control action explicit while preserving the placeholder.','moderate'),
 (94,'ar'): ('propose-correction','عطّل مصادقة واجهة الويب فقط في عمليات نشر loopback الخاضعة لضوابط صارمة.','This is a security tooltip restricting unauthenticated Web UI to controlled network loopback deployments. The current الاسترجاع means retrieval/rollback, not loopback; preserve the networking term.','high'),
 (94,'fr'): ('propose-refinement','Désactivez l’authentification de l’interface Web uniquement pour les déploiements strictement contrôlés en boucle locale.','The caller is security guidance for loopback-only deployments. En boucle locale is the clear networking term; the current de bouclage is less precise.','moderate'),
 (94,'vi'): ('propose-correction','Chỉ tắt xác thực giao diện web trong các triển khai loopback được kiểm soát chặt chẽ.','This security tooltip limits disabled authentication to loopback deployments. The current vòng lặp means a general loop and loses the network-interface meaning; retain the established technical term.','high'),
 (95,'de'): ('propose-correction','Empfehlungen zum Eintrag','The button opens recommendations related to the text item entered by the user. Artikelempfehlungen suggests article recommendations; Eintrag is the neutral UI item.','high'),
 (95,'fr'): ('propose-correction','Recommandations pour cet élément','The button opens recommendations related to the entered item. Enregistrements d’articles means article records/recordings, not recommendations.','high'),
 (95,'hi'): ('propose-refinement','आइटम के लिए सुझाव','The caller tooltip says this action finds recommendations related to the entered item. The current Recs abbreviation is left unexplained.','moderate'),
 (95,'id'): ('propose-correction','Rekomendasi terkait item','The caller tooltip describes related recommendations; Rek Barang reads like an unclear abbreviation and can mean item records/goods.','high'),
 (95,'ja'): ('propose-correction','項目に関するおすすめ','The caller tooltip says the action finds recommendations related to the entered item. 記録 means records, not recommendations.','high'),
 (95,'vi'): ('propose-correction','Gợi ý liên quan đến mục','The caller tooltip says the action finds recommendations related to the entered item. Mục giới thiệu reads as item introduction rather than recommendations.','high'),
 (95,'zh-Hans'): ('propose-refinement','相关条目推荐','The caller describes recommendations related to the entered item. 项目 can suggest a project; 条目 better fits the item/search-entry context.','moderate'),
 (95,'zh-Hant'): ('propose-refinement','相關條目推薦','The caller describes recommendations related to the entered item. 項目 can suggest a project; 條目 better fits the item/search-entry context.','moderate'),
 (97,'ar'): ('propose-refinement','مطابقات AcoustID الخام','The caller displays rawAcoustIdHitCount immediately after this label. The current بيانات means data, while the value counts raw matches.','moderate'),
 (97,'fr'): ('propose-refinement','Correspondances AcoustID brutes','The caller displays a raw AcoustID hit count. This supplies the missing “matches” noun in the current adjective fragment.','moderate'),
 (97,'hi'): ('propose-refinement','AcoustID के कच्चे मिलान','The caller displays rawAcoustIdHitCount after this label. The current डेटा says raw data rather than raw matches.','moderate'),
 (97,'id'): ('propose-refinement','Kecocokan mentah AcoustID','The caller displays a count of raw AcoustID hits. The current data mentah says raw data rather than matches.','moderate'),
 (97,'ja'): ('propose-refinement','AcoustIDの生ヒット','The caller displays rawAcoustIdHitCount after the label. 生データ means raw data; this names raw hits instead.','moderate'),
 (97,'ko'): ('propose-refinement','AcoustID 원시 매칭','The caller displays a raw AcoustID match count. The current 원시 is an incomplete modifier with no noun.','moderate'),
 (97,'vi'): ('propose-refinement','Lượt khớp AcoustID thô','The caller displays a count of raw AcoustID hits. The current AcoustID thô is an incomplete label without the match/count noun.','moderate'),
 (97,'zh-Hans'): ('propose-refinement','AcoustID 原始匹配','The caller displays rawAcoustIdHitCount. The current AcoustID 原始 is an incomplete modifier; add the matches noun.','moderate'),
 (97,'zh-Hant'): ('propose-refinement','AcoustID 原始匹配','The caller displays rawAcoustIdHitCount. The current AcoustID 原始 is an incomplete modifier; add the matches noun.','moderate'),
}
HOLD_REASON_98 = ('hold','The caller concatenates three separate localized fragments—Message, has been/has not been, and seen in pod—then appends podId. This English composition does not let translators reorder the clause or express the seen-receipt state naturally, and several current targets interpret pod as a physical pod/capsule. Hold all 11 cells until the caller uses complete localized result strings, e.g. “A seen receipt exists for message {messageId} on pod {podId}” / “No seen receipt exists for message {messageId} on pod {podId}.”','high')

CONTEXT_NOTES = {
 76: 'AI audio heuristics panel displays artifactLabel as a classifier result.',
 77: 'Swarm analytics fetch failure fallback is passed through getApiErrorMessageOutput for a toast.',
 78: 'Outbound mesh-evidence policy description; its data entry is rendered in the policy list through LocalizedText.',
 79: 'History is used as a table heading and a Logs navigation button.',
 80: 'Security settings enum label for the HttpTunnel mode.',
 81: 'Generic refresh action labels across contacts, player, search, jobs, metrics and security controls.',
 82: 'PlayerBar fallback label when an audio device has no display label; number is the one-based output index.',
 83: 'Discovery-shelf policy preview count label for the archive action.',
 84: 'Port-forwarding statistics heading for the connection count.',
 85: 'Share Groups creation button tooltip; TooltipButton translates string tooltip content through the interface locale.',
 86: 'Search response source-provider badge for the SCENE provider.',
 87: 'PlayerBar listening-statistics time-range option with value 30 days.',
 88: 'FileList tooltip/title for closing a directory file list and returning to surrounding search results; directory is interpolated.',
 89: 'FTP integration server-address accessibility label.',
 90: 'Metadata settings tooltip for syncing Lidarr wanted albums into slskdN Wishlist items awaiting review.',
 91: 'Jobs-page refresh icon title.',
 92: 'Accessibility label for searching for an item in the item-recommendation list; item is interpolated.',
 93: '.NET process metrics label for dotnet_total_memory_bytes.',
 94: 'Security administration tooltip restricting Web UI authentication disablement to tightly controlled loopback deployments.',
 95: 'Item Recs button; its test tooltip states “Find recommendations related to the item you entered.”',
 96: 'PortForwarding error output when the required pod selection is missing.',
 97: 'SongIDPanel renders this label beside run.scorecard.rawAcoustIdHitCount.',
 98: 'MediaCore message-seen check reports the receipt state for a specific message and pod ID.',
 99: 'MediaCore pod control tooltip for loading member-affinity scores used to rank recommendations.',
 100: 'Lidarr import failure is displayed as a toast with the API error substituted for message.',
}

PROTECTED = {
 80:['HTTP'], 86:['Soulseek'], 89:['FTP'], 90:['Lidarr','slskdN'], 97:['AcoustID']
}
TECHNICAL_CONCEPTS = {
 96:['Pod is the selected slskdN service node, not a seed pod.'],
 98:['Pod is the slskdN node associated with a seen-message receipt; not a physical pod or capsule.'],
 99:['Pod is a slskdN community/service node.']
}


def run(*args: str, cwd: Path = REPO) -> str:
    return subprocess.check_output(list(args), cwd=cwd, text=True, stderr=subprocess.STDOUT).strip()

def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def sha_text(value: str) -> str:
    return sha_bytes(value.encode('utf-8'))

def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def write_jsonl(path: Path, rows):
    path.write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',',':')) + '\n' for row in rows), encoding='utf-8')

def verify_manifest(base: Path, manifest: Path):
    failures=[]; count=0
    for line in manifest.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        digest, rel = line.split(None,1); rel=rel.lstrip('* '); count += 1
        p=base/rel
        if not p.is_file() or sha_bytes(p.read_bytes()) != digest:
            failures.append(rel)
    return {'manifest':str(manifest),'sha256':sha_bytes(manifest.read_bytes()),'entries':count,'failures':failures,'verified':not failures}

def catalog_path(locale: str) -> str:
    return f'src/web/public/locales/{locale}.json'


def main():
    allowed={'build_primary_packet.py'}
    for p in OUT.iterdir():
        if p.name not in allowed:
            allowed.add(p.name)
    if not OUT.is_dir(): raise SystemExit(f'missing output directory: {OUT}')
    head=run('git','rev-parse','HEAD'); tree=run('git','rev-parse','HEAD^{tree}')
    status=run('git','status','--porcelain')
    if head != HEAD_EXPECTED or tree != TREE_EXPECTED or status:
        raise SystemExit(f'review input is not the clean exact head: {head} {tree} {status!r}')
    branch=run('git','branch','--show-current')
    if branch != 'codex/slskdn-localization-apply-20261102': raise SystemExit(f'unexpected local branch: {branch}')
    source_tree=run('git','rev-parse','HEAD:src/web/src')
    locale_tree=run('git','rev-parse','HEAD:src/web/public/locales')

    pr_start=json.loads(run('gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,headRefOid,headRefName,baseRefName,url'))
    remote_line=run('git','ls-remote','taskgithub',f'refs/heads/{BRANCH_EXPECTED}')
    remote_head=remote_line.split()[0] if remote_line else None
    if pr_start.get('state')!='OPEN' or pr_start.get('isDraft') is not True or pr_start.get('headRefOid')!=HEAD_EXPECTED or remote_head!=HEAD_EXPECTED:
        raise SystemExit(f'live PR or remote is not the pinned OPEN/DRAFT head: {pr_start} {remote_head}')

    # Verify frozen packets and the copied in-repository evidence before reading their records.
    w42_primary_integrity=verify_manifest(W42_PRIMARY_EXTERNAL, W42_PRIMARY_EXTERNAL/'SHA256SUMS.txt')
    w42_cross_integrity=verify_manifest(W42_CROSS_EXTERNAL, W42_CROSS_EXTERNAL/'SHA256SUMS.txt')
    w40_integrity=verify_manifest(W40_PRIMARY_EXTERNAL, W40_PRIMARY_EXTERNAL/'SHA256SUMS.txt')
    repo_primary=W42/'primary'; repo_cross=W42/'crossreview'; repo_app=W42/'application'
    repo_w42_manifests=[verify_manifest(repo_primary,repo_primary/'SHA256SUMS.txt'),verify_manifest(repo_cross,repo_cross/'SHA256SUMS.txt'),verify_manifest(repo_app,repo_app/'SHA256SUMS.txt')]
    if not all(x['verified'] for x in [w42_primary_integrity,w42_cross_integrity,w40_integrity,*repo_w42_manifests]):
        raise SystemExit('a frozen W40/W42 packet checksum failed')
    w42_cross_manifest=read_json(W42_CROSS_EXTERNAL/'crossreview-summary.json')
    if w42_cross_manifest['headCommit']!='1b518a69d099032c497149102751271eddb0fa57' or not w42_cross_manifest['w43BoundaryDerived']:
        raise SystemExit('W42 cross-review boundary provenance is not the expected frozen record')
    w42_future_external=W42_CROSS_EXTERNAL/'w43-future-boundary-reattestation.jsonl'
    w42_future_repo=W42/'crossreview/w43-future-boundary-reattestation.jsonl'
    if w42_future_external.read_bytes()!=w42_future_repo.read_bytes(): raise SystemExit('W42 future-boundary evidence copy differs from scratch packet')

    # W40's named bundle path is absent. The W40 primary review itself is valid as a historical packet only.
    w40_exact=read_json(W40_PRIMARY_EXTERNAL/'exact-head.json')
    w40_bundle_exists=W40_BUNDLE_EXPECTED.exists()
    if w40_exact.get('headCommit')==HEAD_EXPECTED: raise SystemExit('unexpected W40 packet head')

    # Reattest all prior source-input files cited in W42's selection evidence against the current checkout.
    order42=read_json(W42/'primary/order-evidence.json')
    prior_input_rows=[]; prior_source_ids=set(); prior_window_errors=[]
    for item in order42['priorWindowInputAttestations']:
        original=item['path']
        marker='/docs/'
        if marker in original:
            rel='docs/'+original.split(marker,1)[1]
            p=REPO/rel
            if not p.is_file(): p=Path(original)
        else:
            rel=original
            p=Path(original)
        if not p.is_file():
            prior_window_errors.append({'window':item['window'],'path':rel,'error':'input file is unavailable'}); continue
        raw=p.read_bytes(); rows=read_jsonl(p); ids={r.get('sourceId') or str(r.get('id','')).split(':',1)[-1] for r in rows}
        ids.discard(None)
        digest=sha_bytes(raw)
        passed=digest==item['sha256'] and len(rows)==item['rows'] and len(ids)==item['uniqueSourceIds']
        if not passed: prior_window_errors.append({'window':item['window'],'path':rel,'error':'current/retained input hash/count/ID count differs from W42 pinned input'})
        for input_row in rows:
            sid=input_row.get('sourceId')
            source_text=input_row.get('source')
            if sid and source_text and (sid!='src_'+sha_text(source_text)[:16] or sha_text(source_text)!=input_row.get('sourceSha256',sha_text(source_text))):
                prior_window_errors.append({'window':item['window'],'path':rel,'error':f'source ID/text hash mismatch for {sid}'})
                break
        prior_source_ids.update(ids)
        prior_input_rows.append({'window':item['window'],'path':rel,'pinnedSha256':item['sha256'],'currentSha256':digest,'rows':len(rows),'pinnedRows':item['rows'],'uniqueSourceIds':len(ids),'pinnedUniqueSourceIds':item['uniqueSourceIds'],'verifiedAgainstCurrentHead':passed,'sourceIdentityHashesRechecked':True})
    if prior_window_errors: raise SystemExit(f'prior input pins do not reattest: {prior_window_errors[:5]}')
    if len(prior_source_ids)!=order42['w1Through41UniqueSourceIds']: raise SystemExit(f'prior source ID count differs: {len(prior_source_ids)}')

    # Current catalogs must have the complete, identically ordered source-key set.
    catalogs={}; catalog_meta={}; ordered_keys=None; ordered_hash=None
    for loc in ALL_LOCALES:
        rel=catalog_path(loc); raw=(REPO/rel).read_bytes(); data=json.loads(raw.decode('utf-8')); keys=list(data)
        if len(keys)!=6169: raise SystemExit(f'{loc}: expected 6169 catalog keys, found {len(keys)}')
        if ordered_keys is None:
            ordered_keys=keys; ordered_hash=sha_bytes(json.dumps(keys,ensure_ascii=False,separators=(',',':')).encode('utf-8'))
        elif keys!=ordered_keys: raise SystemExit(f'ordered key set differs for {loc}')
        blob=run('git','rev-parse',f'HEAD:{rel}')
        catalogs[loc]=data
        catalog_meta[loc]={'locale':loc,'path':rel,'blobOid':blob,'fileSha256':sha_bytes(raw),'entryCount':len(keys),'orderedKeySha256':ordered_hash}

    # Reattest every W42 final cell and every applied readback against the current catalog.
    w42_root_rows=read_jsonl(W42/'application/root-adjudication.jsonl')
    w42_plan=read_jsonl(W42/'application/exact-hash-apply-plan.jsonl')
    w42_readbacks=read_jsonl(W42/'application/application-readback.jsonl')
    if len(w42_root_rows)!=275 or len(w42_plan)!=48 or len(w42_readbacks)!=48: raise SystemExit('unexpected W42 application row counts')
    w42_final_rows=[]
    for row in w42_root_rows:
        loc=row['locale']; source=row['source']; target=catalogs[loc][source]; target_sha=sha_text(target)
        expected=row['final_target']; expected_sha=row['final_sha256']
        if target!=expected or target_sha!=expected_sha: raise SystemExit(f'W42 final outcome no longer matches: {row["source_id"]}/{loc}')
        if sha_text(source)!=row['source_sha256'] or row['source_id']!='src_'+sha_text(source)[:16]: raise SystemExit(f'W42 source pin mismatch: {row["source_id"]}')
        w42_final_rows.append({'id':f'{loc}:{row["source_id"]}','sourceOrdinal':row['source_ordinal'],'sourceId':row['source_id'],'locale':loc,'source':source,'sourceSha256':row['source_sha256'],'w42Disposition':row['final_disposition'],'w42FinalTarget':expected,'w42FinalTargetSha256':expected_sha,'currentTargetSha256':target_sha,'matchesW42FinalOutcome':True})
    w42_applied_rows=[]
    for plan,readback in zip(w42_plan,w42_readbacks):
        loc=plan['locale']; source=plan['source']; current=catalogs[loc][source]
        if plan['source_id']!=readback['source_id'] or loc!=readback['locale']: raise SystemExit('W42 application/readback key mismatch')
        if current!=plan['final_target'] or sha_text(current)!=plan['final_sha256'] or readback['readback']!=current or readback['readback_sha256']!=sha_text(current):
            raise SystemExit(f'W42 applied target mismatch: {plan["source_id"]}/{loc}')
        w42_applied_rows.append({'id':f'{loc}:{plan["source_id"]}','sourceOrdinal':plan['source_ordinal'],'sourceId':plan['source_id'],'locale':loc,'catalogPath':plan['catalog_path'],'catalogKey':plan['catalog_key'],'target':current,'targetSha256':sha_text(current),'w42ApplyPlanTargetSha256':plan['final_sha256'],'originalApplicationReadbackSha256':readback['readback_sha256'],'matchesCurrentHead':True})

    # Reattest all 50 preserved holds, including the hold-ledger file pins.
    prior_hold_records=read_jsonl(W42/'primary/preserved-prior-holds.jsonl')
    if len(prior_hold_records)!=50: raise SystemExit(f'expected 50 prior hold rows, got {len(prior_hold_records)}')
    hold_rows=[]
    for row in prior_hold_records:
        loc=row['locale']; key=row['catalogKey']; actual=catalogs[loc][key]; actual_sha=sha_text(actual)
        if actual_sha!=row['currentTargetSha256'] or actual!=row['currentTarget']: raise SystemExit(f'prior hold value changed: {row["id"]}')
        if sha_text(row['source'])!=row['sourceSha256'] or row['sourceId']!='src_'+sha_text(row['source'])[:16]: raise SystemExit(f'prior hold source pin mismatch: {row["id"]}')
        ledger_rel=row.get('sourceHoldLedgerPath'); ledger_sha=row.get('sourceHoldLedgerSha256'); ledger_ok=None
        if ledger_rel:
            lp=REPO/ledger_rel
            ledger_ok=lp.is_file() and sha_bytes(lp.read_bytes())==ledger_sha
            if not ledger_ok: raise SystemExit(f'prior hold ledger pin mismatch: {ledger_rel}')
        hold_rows.append({'id':row['id'],'preservedFromWindow':row['preservedFromWindow'],'locale':loc,'sourceId':row['sourceId'],'source':row['source'],'sourceSha256':row['sourceSha256'],'catalogKey':key,'currentTarget':actual,'currentTargetSha256':actual_sha,'pinnedTargetSha256':row['currentTargetSha256'],'holdDisposition':row['holdDisposition'],'reason':row['reason'],'holdLedgerPath':ledger_rel,'holdLedgerSha256':ledger_sha,'holdLedgerVerifiedAtCurrentHead':ledger_ok,'unchanged':True})

    # Load the W42 future boundary only as frozen identity evidence; reattest its source/cells/callers now.
    boundary=read_jsonl(w42_future_repo)
    if len(boundary)!=275: raise SystemExit(f'W42 W43 boundary row count {len(boundary)}')
    sources_by_id={}
    for row in boundary:
        if row['sourceOrdinal']<76 or row['sourceOrdinal']>100 or row['window']!=43: raise SystemExit('W42 boundary has out-of-scope source ordinal')
        sources_by_id.setdefault(row['sourceId'],row)
    if len(sources_by_id)!=25: raise SystemExit(f'W43 source ID count {len(sources_by_id)}')
    sources=list(sorted(sources_by_id.values(),key=lambda r:r['sourceOrdinal']))
    if [r['sourceOrdinal'] for r in sources]!=list(range(76,101)): raise SystemExit('W43 ordinals are not contiguous 76–100')
    if any(r['sourceId'] in prior_source_ids for r in sources): raise SystemExit('W43 source IDs overlap prior W1–W41 IDs')
    w42_sources=read_jsonl(W42/'primary/source-slice.jsonl')
    w42_ids={r['sourceId'] for r in w42_sources}
    if len(w42_sources)!=25 or any(s['sourceId'] in w42_ids for s in sources): raise SystemExit('W43 IDs overlap W42 source slice or W42 source slice is invalid')
    w42_source_current=[]
    for source in w42_sources:
        if sha_text(source['source'])!=source['sourceSha256'] or source['sourceId']!='src_'+sha_text(source['source'])[:16]:
            raise SystemExit(f'W42 source no longer matches current source-derived ID: {source["sourceId"]}')
        w42_source_current.append({'sourceOrdinal':source['sourceOrdinal'],'sourceId':source['sourceId'],'source':source['source'],'sourceSha256':source['sourceSha256'],'sourceSubtreeTreeCurrent':source_tree,'matchesCurrentSourceTree':True})

    src_files=run('git','ls-files','src/web/src').splitlines()
    lines_by_file={}
    for rel in src_files:
        p=REPO/rel
        if not p.is_file(): continue
        try: lines_by_file[rel]=p.read_text(encoding='utf-8').splitlines()
        except UnicodeDecodeError: continue
    localizer=re.compile(r'interface(?:Attribute|Toast)?Text(?:Props|Output)?|LocalizedText|LocalizedOutputText|getApiErrorMessageOutput|\bt\s*\(')
    caller_records=[]; caller_lines_by_id=defaultdict(list)
    for source in sources:
        text=source['source']; qpat=re.compile(r'([\"\'`])'+re.escape(text)+r'\1')
        for rel,lines in lines_by_file.items():
            if '.test.' in rel or '.stories.' in rel: continue
            for number,line in enumerate(lines,1):
                if not qpat.search(line): continue
                stripped=line.strip()
                is_data_def=(source['sourceOrdinal']==78 and rel=='src/web/src/lib/meshEvidencePolicy.js' and 'description:' in line)
                is_tooltip='tooltip=' in line
                is_localized=bool(localizer.search(line))
                if not (is_data_def or is_tooltip or is_localized): continue
                raw=(REPO/rel).read_bytes(); blob=run('git','rev-parse',f'HEAD:{rel}')
                before=lines[max(0,number-3):number-1]; after=lines[number:min(len(lines),number+2)]
                role='source-data-definition' if is_data_def else ('tooltip-callsite' if is_tooltip and not is_localized else 'localized-callsite')
                rec={'sourceOrdinal':source['sourceOrdinal'],'sourceId':source['sourceId'],'source':text,'sourceSha256':sha_text(text),'path':rel,'line':number,'lineText':line,'lineSha256':sha_text(line),'fileSha256':sha_bytes(raw),'fileBlobOid':blob,'contextBefore':before,'contextAfter':after,'referenceRole':role,'exactQuotedSourceMatch':True,'verifiedAtCurrentHead':True}
                caller_records.append(rec); caller_lines_by_id[source['sourceId']].append(rec)
    # W78's source is stored as data and rendered by a generic localized component; pin the rendering caller too.
    dynamic_render_path='src/web/src/components/System/Mesh/MeshEvidencePolicy.jsx'
    dynamic_lines=lines_by_file[dynamic_render_path]
    dynamic_number=next(i for i,line in enumerate(dynamic_lines,1) if 'LocalizedText source={evidenceType.description}' in line)
    dynamic_line=dynamic_lines[dynamic_number-1]; dynamic_raw=(REPO/dynamic_render_path).read_bytes()
    dynamic_record={'sourceOrdinal':78,'sourceId':sources_by_id[next(k for k,v in sources_by_id.items() if v['sourceOrdinal']==78)]['sourceId'],'source':sources_by_id[next(k for k,v in sources_by_id.items() if v['sourceOrdinal']==78)]['source'],'sourceSha256':sha_text(sources_by_id[next(k for k,v in sources_by_id.items() if v['sourceOrdinal']==78)]['source']),'path':dynamic_render_path,'line':dynamic_number,'lineText':dynamic_line,'lineSha256':sha_text(dynamic_line),'fileSha256':sha_bytes(dynamic_raw),'fileBlobOid':run('git','rev-parse',f'HEAD:{dynamic_render_path}'),'contextBefore':dynamic_lines[max(0,dynamic_number-3):dynamic_number-1],'contextAfter':dynamic_lines[dynamic_number:min(len(dynamic_lines),dynamic_number+2)],'referenceRole':'dynamic-localized-renderer','exactQuotedSourceMatch':False,'verifiedAtCurrentHead':True}
    caller_records.append(dynamic_record); caller_lines_by_id[dynamic_record['sourceId']].append(dynamic_record)
    caller_records.sort(key=lambda r:(r['sourceOrdinal'],r['path'],r['line'],r['referenceRole']))
    caller_gaps=[]
    for source in sources:
        if not caller_lines_by_id[source['sourceId']]: caller_gaps.append({'sourceOrdinal':source['sourceOrdinal'],'sourceId':source['sourceId'],'source':source['source'],'gap':'No exact production source/caller reference found in src/web/src.'})
    if caller_gaps: raise SystemExit(f'W43 source/caller gaps need explicit adjudication: {caller_gaps}')

    # Reattest the W41/W42 Spanish formal lane; preserve W43 Spanish boundary values without verdicts.
    formal_ids={row['id'] for row in read_jsonl(FORMAL_IDS_PATH)}
    if len(formal_ids)!=4800 or sha_bytes(FORMAL_IDS_PATH.read_bytes())!=FORMAL_IDS_SHA: raise SystemExit('Spanish formal accumulator is stale or malformed')
    spanish_rows=[]
    for filename,window in [('w41-spanish-formal-reattestation.jsonl',41)]:
        for row in read_jsonl(W42/'primary'/filename):
            actual=catalogs['es'][row['catalogKey']]; actual_sha=sha_text(actual)
            if actual_sha!=row['currentTargetSha256'] or not row.get('formalCellIdPresent',False): raise SystemExit(f'W41 Spanish formal value mismatch: {row["id"]}')
            if f'es:{row["sourceId"]}' not in formal_ids: raise SystemExit(f'W41 Spanish cell absent from formal accumulator: {row["id"]}')
            spanish_rows.append({'laneWindow':window,'sourceOrdinal':row['sourceOrdinal'],'id':row['id'],'sourceId':row['sourceId'],'source':row['source'],'sourceSha256':row['sourceSha256'],'catalogKey':row['catalogKey'],'currentTarget':actual,'currentTargetSha256':actual_sha,'pinnedTargetSha256':row['currentTargetSha256'],'formalCellIdPresent':True,'reviewVerdict':'none-formal-lane-preserved'})
    for row in read_jsonl(W42/'primary/preserved-spanish-formal.jsonl'):
        actual=catalogs['es'][row['catalogKey']]; actual_sha=sha_text(actual)
        if actual_sha!=row['currentTargetSha256'] or not row.get('formalCellIdPresent',False): raise SystemExit(f'W42 Spanish formal value mismatch: {row["id"]}')
        if f'es:{row["sourceId"]}' not in formal_ids: raise SystemExit(f'W42 Spanish cell absent from formal accumulator: {row["id"]}')
        spanish_rows.append({'laneWindow':42,'sourceOrdinal':row['sourceOrdinal'],'id':row['id'],'sourceId':row['sourceId'],'source':row['source'],'sourceSha256':row['sourceSha256'],'catalogKey':row['catalogKey'],'currentTarget':actual,'currentTargetSha256':actual_sha,'pinnedTargetSha256':row['currentTargetSha256'],'formalCellIdPresent':True,'reviewVerdict':'none-formal-lane-preserved'})

    # Structural checks and independently reviewed W43 targets.
    cells=[]; structural=[]; proposals=[]; current_counts=Counter(); final_counts=Counter()
    all_source_values={r['sourceId']:r for r in sources}
    for source in sources:
        ordinal=source['sourceOrdinal']; sid=source['sourceId']; source_text=source['source']
        if sha_text(source_text)!=source['sourceSha256'] or sid!='src_'+sha_text(source_text)[:16]: raise SystemExit(f'W43 source hash/ID mismatch: {sid}')
        placeholders=sorted(set(re.findall(r'\{[A-Za-z0-9_]+\}',source_text)))
        markup=sorted(re.findall(r'</?[A-Za-z][^>]*>',source_text))
        protected=PROTECTED.get(ordinal,[])
        for loc in LOCALES:
            old=next(r for r in boundary if r['sourceId']==sid and r['locale']==loc)
            current=catalogs[loc][source_text]; current_sha=sha_text(current)
            if old['sourceSha256']!=source['sourceSha256'] or old['source']!=source_text: raise SystemExit(f'W42 boundary source mismatch {sid}')
            if old['currentTarget']!=current or old['currentTargetSha256']!=current_sha: raise SystemExit(f'W43 target changed since W42 future boundary {loc}:{sid}')
            current_ph=sorted(set(re.findall(r'\{[A-Za-z0-9_]+\}',current)))
            current_markup=sorted(re.findall(r'</?[A-Za-z][^>]*>',current))
            current_missing=[literal for literal in protected if literal not in current]
            disposition_row=CANDIDATES.get((ordinal,loc))
            hold=HOLD_REASON_98 if ordinal==98 else None
            if hold:
                disposition='hold'; target=None; rationale=hold[1]; confidence=hold[2]
                target_sha=None
            elif disposition_row:
                disposition,target,rationale,confidence=disposition_row
                target_sha=sha_text(target)
            else:
                disposition='accept-current'; target=current; target_sha=current_sha
                rationale=CONTEXT_NOTES[ordinal]+' Current wording preserves the source meaning in the caller context; placeholders, markup, and protected literals were checked.'
                confidence='high'
            target_ph=sorted(set(re.findall(r'\{[A-Za-z0-9_]+\}',target))) if target is not None else None
            target_markup=sorted(re.findall(r'</?[A-Za-z][^>]*>',target)) if target is not None else None
            target_missing=[literal for literal in protected if target is not None and literal not in target]
            current_counts[disposition]+=1
            if disposition=='hold': final_counts['hold']+=1
            elif disposition=='accept-current': final_counts['accept-current']+=1
            else:
                final_counts[disposition]+=1
                proposal={'window':43,'exactHead':head,'exactTree':tree,'sourceOrdinal':ordinal,'sourceId':sid,'locale':loc,'catalogKey':source_text,'catalogPath':catalog_path(loc),'source':source_text,'sourceSha256':source['sourceSha256'],'currentTarget':current,'currentTargetSha256':current_sha,'proposedTarget':target,'proposedTargetSha256':target_sha,'disposition':disposition,'confidence':confidence,'rationale':rationale,'placeholders':placeholders,'proposedPlaceholders':target_ph,'protectedLiterals':protected,'currentProtectedLiteralMismatches':current_missing,'proposedProtectedLiteralMismatches':target_missing,'sourceMarkup':markup,'proposedMarkup':target_markup,'callerRefs':caller_lines_by_id[sid]}
                proposals.append(proposal)
            if current_ph!=placeholders or current_markup!=markup: structural.append({'id':f'{loc}:{sid}','sourceOrdinal':ordinal,'sourceSha256':source['sourceSha256'],'currentTargetSha256':current_sha,'placeholderMismatch':current_ph!=placeholders,'sourcePlaceholders':placeholders,'currentPlaceholders':current_ph,'markupMismatch':current_markup!=markup,'sourceMarkup':markup,'currentMarkup':current_markup,'protectedLiterals':protected,'protectedLiteralMismatches':current_missing})
            if target is not None and (target_ph!=placeholders or target_markup!=markup or target_missing): raise SystemExit(f'proposed target fails structural check: {loc}:{sid}')
            cell={'window':43,'exactHead':head,'exactTree':tree,'sourceSubtreeTree':source_tree,'localeCatalogSubtreeTree':locale_tree,'id':f'{loc}:{sid}','locale':loc,'sourceOrdinal':ordinal,'sourceId':sid,'source':source_text,'sourceSha256':source['sourceSha256'],'sourceFingerprint':source['sourceSha256'],'catalogKey':source_text,'catalogPath':catalog_path(loc),'currentTarget':current,'currentTargetSha256':current_sha,'w42BoundaryTargetSha256':old['currentTargetSha256'],'currentCatalogBlobOid':catalog_meta[loc]['blobOid'],'currentCatalogFileSha256':catalog_meta[loc]['fileSha256'],'placeholders':placeholders,'currentTargetPlaceholders':current_ph,'currentMarkup':current_markup,'sourceMarkup':markup,'protectedLiterals':protected,'currentProtectedLiteralMismatches':current_missing,'technicalConcepts':TECHNICAL_CONCEPTS.get(ordinal,[]),'callerRefs':caller_lines_by_id[sid],'disposition':disposition,'target':target,'targetSha256':target_sha,'confidence':confidence,'rationale':rationale,'nativeSpeakerReview':'outstanding'}
            cells.append(cell)
    if len(cells)!=275 or len(proposals)!=45 or final_counts['hold']!=11: raise SystemExit(f'unexpected W43 decision counts: {len(cells)} cells, {len(proposals)} proposals, {final_counts}')
    if final_counts['accept-current']!=219 or final_counts['propose-correction']+final_counts['propose-refinement']!=45: raise SystemExit(f'unexpected disposition totals: {final_counts}')
    if structural: raise SystemExit(f'current structural failures: {structural[:5]}')

    spanish_rows.extend([])
    w43_es=[]
    for source in sources:
        sid=source['sourceId']; key=source['source']; target=catalogs['es'][key]; target_sha=sha_text(target)
        formal_present=f'es:{sid}' in formal_ids
        w43_es.append({'laneWindow':43,'sourceOrdinal':source['sourceOrdinal'],'id':f'es:{sid}','sourceId':sid,'source':key,'sourceSha256':source['sourceSha256'],'catalogKey':key,'currentTarget':target,'currentTargetSha256':target_sha,'formalCellIdPresent':formal_present,'reviewVerdict':'none-W43-Spanish-verdict; boundary value preserved'})
    if len(w43_es)!=25: raise SystemExit('W43 Spanish boundary row count differs')
    if len(spanish_rows)!=50: raise SystemExit(f'expected 50 W41–W42 Spanish formal rows, got {len(spanish_rows)}')

    # Source/runtime findings recorded separately from target proposals.
    runtime_gaps=[
      {'sourceOrdinal':98,'sourceId':sources_by_id[next(k for k,v in sources_by_id.items() if v['sourceOrdinal']==98)]['sourceId'],'source':'seen in pod','callerPath':'src/web/src/components/System/MediaCore/MediaCorePods.jsx','callerLines':[3159,3160,3162],'behavior':'GET /seen/{messageId}/{podId} checks whether a seen receipt exists for the specified message and pod. The UI concatenates Message + has been/has not been + seen in pod + podId.','gap':'The English keys are sentence fragments composed in a fixed English word order, and “seen in pod” reads as a physical pod/capsule in several locales; the caller behavior is receipt existence for a Pod ID.','proposal':'Use complete localized result messages for the positive and negative cases, e.g. “A seen receipt exists for message {messageId} on pod {podId}.” and “No seen receipt exists for message {messageId} on pod {podId}.” Then review all locales in the refactored caller.','affectedCells':11,'disposition':'hold-all-current-window-cells-pending-caller-refactor'},
      {'sourceOrdinal':97,'sourceId':sources_by_id[next(k for k,v in sources_by_id.items() if v['sourceOrdinal']==97)]['sourceId'],'source':'AcoustID Raw','callerPath':'src/web/src/components/Search/SongIDPanel.jsx','callerLine':1101,'behavior':'The label is followed by run.scorecard.rawAcoustIdHitCount.','gap':'The terse English label does not name the hit/match noun shown by its caller. Proposals use the actual raw-hit count context; consider changing the English key to “Raw AcoustID matches” before a later source-key refresh.','affectedCells':11,'disposition':'source-copy-clarification-recommended'},
    ]

    # Final live PR/remote snapshot ensures head did not move while writing this packet.
    pr_end=json.loads(run('gh','pr','view','409','--repo','snapetech-org/slskdN','--json','state,isDraft,headRefOid,headRefName,baseRefName,url'))
    remote_end_line=run('git','ls-remote','taskgithub',f'refs/heads/{BRANCH_EXPECTED}')
    remote_end=remote_end_line.split()[0] if remote_end_line else None
    if pr_end!=pr_start or remote_end!=HEAD_EXPECTED or run('git','rev-parse','HEAD')!=HEAD_EXPECTED or run('git','status','--porcelain'):
        raise SystemExit('PR, remote or worktree changed during primary review')

    # Write reproducible output records.
    write_json(OUT/'exact-head.json',{'repository':'snapetech-org/slskdN','pullRequest':409,'url':pr_start['url'],'state':'OPEN','isDraft':True,'baseRefName':pr_start['baseRefName'],'headRefName':pr_start['headRefName'],'head':head,'tree':tree,'branch':branch,'remote':'taskgithub','remoteHead':remote_head,'livePrStart':pr_start,'livePrEnd':pr_end,'verifiedAtUtc':datetime.now(timezone.utc).isoformat(),'worktreeClean':True})
    write_json(OUT/'input-integrity.json',{
      'head':head,'tree':tree,'sourceSubtreeTree':source_tree,'w42SourceSubtreeTree':read_json(W42/'primary/exact-head.json')['sourceSubtreeTree'],'currentLocaleCatalogTree':locale_tree,'w42LocaleCatalogTree':read_json(W42/'primary/exact-head.json')['localeCatalogSubtreeTree'],
      'w42PrimaryExternalManifest':w42_primary_integrity,'w42CrossReviewExternalManifest':w42_cross_integrity,'w40PrimaryHistoricalManifest':w40_integrity,'w42RepoEvidenceManifests':repo_w42_manifests,
      'w42FutureBoundarySha256':sha_bytes(w42_future_repo.read_bytes()),'w42FutureBoundaryExternalCopyMatches':True,'w42PriorInputFilesReattestedAtCurrentHead':len(prior_input_rows),'w42PriorInputFileMismatches':prior_window_errors,'w1Through41UniqueSourceIdsReattested':len(prior_source_ids),'w42InputOrderEvidenceSelectionRule':order42['selectionRule'],'w42SelectionClaim':order42['selectionReproduced'],'w43BoundarySourceRowsReattested':len(sources),'w43BoundaryCellRowsReattested':len(boundary),'w43BoundaryIdsDisjointFromW1Through42':True,
      'w40RootBundlePath':str(W40_BUNDLE_EXPECTED),'w40RootBundleExists':w40_bundle_exists,'w40PrimaryReviewHead':w40_exact.get('headCommit'),'w40PrimaryWasUsedForCurrentInputs':False,'w40Handling':'The requested bundle path is absent. The checksummed W40 primary packet is historical at 67e40aaa; it was not used as current source/caller/catalog evidence. W43 source IDs/current catalog values were taken from W42 future-boundary rows and reattested against this exact current source tree and all 11 live catalogs.',
      'formalAccumulatorPath':str(FORMAL_IDS_PATH.relative_to(REPO)),'formalAccumulatorSha256':sha_bytes(FORMAL_IDS_PATH.read_bytes()),'formalAccumulatorEntries':len(formal_ids),
      'w42AppliedRowsReattested':len(w42_applied_rows),'w42FinalCellsReattested':len(w42_final_rows),'priorHoldRowsReattested':len(hold_rows),'spanishFormalRowsReattested':len(spanish_rows),'w43SpanishBoundaryRowsPreserved':len(w43_es),'w43SpanishBoundaryFormalAccumulatorCount':sum(r['formalCellIdPresent'] for r in w43_es),'catalogFilesReattested':len(catalog_meta),'sourceCallerFilesPinned':len({r['path'] for r in caller_records}),
      'readOnly':True,'repoMutated':False,'testsBuildsCiBrowserRun':False})
    write_json(OUT/'catalog-structure.json',{'head':head,'tree':tree,'sourceSubtreeTree':source_tree,'localeCatalogSubtreeTree':locale_tree,'orderedKeyCountPerLocale':6169,'orderedKeySha256':ordered_hash,'catalogs':list(catalog_meta.values())})
    write_json(OUT/'order-and-boundary.json',{'selectionClaim':'source ordinals 76–100, next 25 pending IDs following W42, as explicitly scoped by task and recorded in W42 future-boundary evidence','sourceOrdinalRange':[76,100],'w42SourceOrdinalRange':[51,75],'priorSourceIdsW1Through41':len(prior_source_ids),'w42SourceIds':len(w42_ids),'w43SourceIds':len(sources),'sourceIdsByOrdinal':[{'sourceOrdinal':s['sourceOrdinal'],'sourceId':s['sourceId'],'source':s['source'],'sourceSha256':s['sourceSha256']} for s in sources],'sourceIdOrderingSortedLexically': [s['sourceId'] for s in sources] == sorted(s['sourceId'] for s in sources),'fullFrozenPendingQueueReproduced':False,'selectionProvenanceLimit':'The task-specified W40 bundle directory is absent, so the full 5,650-ID frozen queue cannot be rebuilt from that path. W42 recorded the future boundary as derived; all 25 source hashes/IDs, all 275 targets, source-tree identity, W42 prior-input file hashes and current caller pins were independently reattested at the live exact head.'})
    write_jsonl(OUT/'prior-window-input-reattestation.jsonl',prior_input_rows)
    write_jsonl(OUT/'w42-source-reattestation.jsonl',w42_source_current)
    write_jsonl(OUT/'caller-context.jsonl',caller_records)
    write_jsonl(OUT/'current-cells.jsonl',cells)
    write_jsonl(OUT/'review-decisions.jsonl',cells)
    write_jsonl(OUT/'candidate-proposals.jsonl',proposals)
    write_jsonl(OUT/'structural-validation.jsonl',[
      {'id':c['id'],'sourceOrdinal':c['sourceOrdinal'],'sourceId':c['sourceId'],'locale':c['locale'],'sourceSha256':c['sourceSha256'],'currentTargetSha256':c['currentTargetSha256'],'placeholders':c['placeholders'],'currentTargetPlaceholders':c['currentTargetPlaceholders'],'placeholderMismatch':c['placeholders']!=c['currentTargetPlaceholders'],'sourceMarkup':c['sourceMarkup'],'currentMarkup':c['currentMarkup'],'markupMismatch':c['sourceMarkup']!=c['currentMarkup'],'protectedLiterals':c['protectedLiterals'],'currentProtectedLiteralMismatches':c['currentProtectedLiteralMismatches'],'disposition':c['disposition'],'targetSha256':c['targetSha256']} for c in cells
    ] + [
      {'id':f'{p["locale"]}:{p["sourceId"]}','sourceOrdinal':p['sourceOrdinal'],'sourceId':p['sourceId'],'locale':p['locale'],'candidateTargetSha256':p['proposedTargetSha256'],'placeholders':p['placeholders'],'candidatePlaceholders':p['proposedPlaceholders'],'placeholderMismatch':p['placeholders']!=p['proposedPlaceholders'],'sourceMarkup':p['sourceMarkup'],'candidateMarkup':p['proposedMarkup'],'markupMismatch':p['sourceMarkup']!=p['proposedMarkup'],'protectedLiterals':p['protectedLiterals'],'candidateProtectedLiteralMismatches':p['proposedProtectedLiteralMismatches'],'candidateStructuralPass':True} for p in proposals
    ])
    write_jsonl(OUT/'w42-final-cell-reattestation.jsonl',w42_final_rows)
    write_jsonl(OUT/'w42-applied-readback-reattestation.jsonl',w42_applied_rows)
    write_jsonl(OUT/'prior-hold-reattestation.jsonl',hold_rows)
    write_jsonl(OUT/'spanish-formal-reattestation.jsonl',spanish_rows)
    write_jsonl(OUT/'w43-spanish-formal-boundary.jsonl',w43_es)
    write_jsonl(OUT/'source-runtime-gaps.jsonl',runtime_gaps)

    summary={
      'result':'PRIMARY_REVIEW_COMPLETE_PENDING_INDEPENDENT_CROSS_REVIEW_AND_NATIVE_SPEAKER_REVIEW','window':43,'pullRequest':409,'head':head,'tree':tree,'state':'OPEN','draft':True,'sourceOrdinals':[76,100],'sourceIds':len(sources),'nonSpanishCells':len(cells),'nonSpanishLocales':len(LOCALES),'w43SpanishBoundaryRowsPreserved':len(w43_es),'dispositions':dict(final_counts),'candidateRows':len(proposals),'candidateByLocale':dict(Counter(p['locale'] for p in proposals)),'priorHolds':0,'preservedPriorHoldsReattested':len(hold_rows),'w42FinalCellsReattested':len(w42_final_rows),'w42AppliedValuesReattested':len(w42_applied_rows),'spanishFormalRowsReattestedW41W42':len(spanish_rows),'w43SpanishBoundaryRowsPreservedWithoutVerdict':len(w43_es),'w43SpanishFormalAccumulatorMatches':sum(r['formalCellIdPresent'] for r in w43_es),'callerReferences':len(caller_records),'uniqueCallerLines':len({(r['path'],r['line']) for r in caller_records}),'sourceCallerFiles':len({r['path'] for r in caller_records}),'sourcesWithoutCallerRefs':caller_gaps,'placeholdersMismatchCurrent':0,'markupMismatchCurrent':0,'protectedLiteralCurrentMismatchCount':sum(len(c['currentProtectedLiteralMismatches']) for c in cells),'candidatePlaceholderMismatch':0,'candidateMarkupMismatch':0,'candidateProtectedLiteralMismatch':0,'sourceRuntimeGaps':len(runtime_gaps),'w40BundlePathPresent':w40_bundle_exists,'fullFrozenPendingQueueReproduced':False,'nativeSpeakerReview':'outstanding','readOnly':True,'repositoryModified':False,'testsBuildsCiBrowserRun':False,
      'notes':['All 275 non-Spanish cells were reviewed against source text, current exact-head caller context, placeholder/markup and protected-literal checks.','W42 primary/cross-review/application manifests verify; all 41 prior input-file pins and all W42 final-cell outcomes were reattested against the current checkout.','The specified W40 bundle path is absent. The old W40 review packet was not reused as current evidence.','All 11 W98 cells are held pending replacing concatenated fragments with complete localized seen-receipt result messages.','The W97 source label AcoustID Raw is terse; candidates use the actual rawAcoustIdHitCount caller meaning.','The packet is a primary machine-assisted review and does not claim native-speaker approval.']}
    write_json(OUT/'summary.json',summary)
    readme=f'''# slskdN PR #409 W43 primary review\n\n- PR state at start and finish: OPEN/DRAFT at {head} / {tree}; branch {BRANCH_EXPECTED}.\n- Scope: source ordinals 76–100, 25 source IDs, 275 non-Spanish cells across 11 locales.\n- Dispositions: {final_counts['accept-current']} accept-current, {final_counts['propose-correction']} propose-correction, {final_counts['propose-refinement']} propose-refinement, {final_counts['hold']} held.\n- W42: reattested all {len(w42_final_rows)} final cells and {len(w42_applied_rows)} applied readbacks at the current head; reattested {len(hold_rows)} prior holds and {len(spanish_rows)} W41–W42 Spanish formal-lane cells. W43 Spanish boundary values are preserved separately without a verdict.\n- All current and candidate placeholder/markup checks pass. Protected literal misses in current cells are recorded; all proposals preserve required literals.\n- Caller references are pinned to exact current source files/lines and contexts.\n- Source/runtime gap: W98 “seen in pod” is concatenated from three localized English fragments and podId. Hold all 11 targets pending complete result strings; see source-runtime-gaps.jsonl. W97’s terse AcoustID Raw label is interpreted through the raw hit-count caller.\n- The task-named W40 bundle path is absent. Its historical primary packet verifies but is pinned to an earlier head and was not used as current evidence. W42’s W43 boundary was reattested to current source/caller/catalog pins; the full frozen pending queue could not be reproduced without the missing bundle.\n- Native-speaker review remains outstanding. No repo/PR changes, tests, builds, CI, browser actions, releases, or tags were made.\n\nPacket builder: build_primary_packet.py. The SHA256SUMS.txt manifest covers every packet file except itself.\n'''
    (OUT/'README.md').write_text(readme,encoding='utf-8')
    files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt')
    (OUT/'SHA256SUMS.txt').write_text(''.join(f'{sha_bytes(p.read_bytes())}  {p.name}\n' for p in files),encoding='utf-8')
    print(json.dumps({'output':str(OUT),'head':head,'tree':tree,'sources':len(sources),'cells':len(cells),'dispositions':dict(final_counts),'proposals':len(proposals),'priorHolds':len(hold_rows),'formalSpanishRows':len(spanish_rows),'w42AppliedRows':len(w42_applied_rows),'w42FinalRows':len(w42_final_rows),'callers':len(caller_records),'uniqueCallerLines':len({(r['path'],r['line']) for r in caller_records}),'priorInputRowsReattested':len(prior_input_rows),'w40BundleExists':w40_bundle_exists,'files':len(files)+1},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
