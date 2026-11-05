#!/usr/bin/env python3
"""Build a sealed, read-only cross-review packet from the pinned review inputs."""
from __future__ import annotations
import collections, hashlib, json, re, shutil, unicodedata
from pathlib import Path

INPUT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w1003-1027-20261105')
CAND = INPUT / 'candidate-free'
PRIMARY = INPUT / 'primary-review'
BLIND = INPUT / 'blind-review'
OUT = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-crossreview-w1003-1027-20261105')
HEAD = '8c752c49281418fdd96341ed46f5c321627b625f'
TREE = 'b930b0d82679e843849e54456f3250e422c4682c'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

def readj(path): return json.loads(path.read_text(encoding='utf-8'))
def readjl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def sha(data): return hashlib.sha256(data).hexdigest()
def text_sha(value): return sha(value.encode('utf-8'))
def file_sha(path): return sha(path.read_bytes())
def writej(path, obj): path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
def writejl(path, rows): path.write_text(''.join(json.dumps(x, ensure_ascii=False, separators=(',', ':')) + '\n' for x in rows), encoding='utf-8')

def token_data(source, target):
    placeholders = lambda s: collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}', s))
    tags = lambda s: collections.Counter(re.findall(r'</?[A-Za-z][^>]*>', s))
    nums = lambda s: [''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in t) for t in re.findall(r'\d+', s)]
    protected = lambda s: sorted(set(re.findall(r'\b[A-Z][A-Z0-9]{1,}\b', s)) | {x for x in ('slskdN','PodCore','Wishlist','soulfind','FFmpeg','Lidarr') if x in s})
    sp, tp = placeholders(source), placeholders(target)
    st, tt = tags(source), tags(target)
    sn, tn = nums(source), nums(target)
    sl = protected(source)
    missing = [x for x in sl if x not in target]
    return {
        'placeholderParity': sp == tp,
        'markupParity': st == tt,
        'numericTokensPreserved': all(tn.count(x) >= n for x, n in collections.Counter(sn).items()),
        'missingProtectedLiterals': missing,
        'protectedLiteralsPreserved': not missing,
    }

def target_ok(result):
    return all(result[k] for k in ('placeholderParity','markupParity','numericTokensPreserved','protectedLiteralsPreserved'))

# Independently selected cross-review targets for the union of the 57 primary
# corrections and 59 blind proposals (71 distinct cells). No catalog is edited.
FIXES = {
 (1004,'fr'):'Nombre maximal de clients legacy simultanés',
 (1004,'hi'):'अधिकतम समवर्ती लेगेसी क्लाइंट',
 (1004,'id'):'Jumlah maksimum klien legacy secara bersamaan',
 (1004,'vi'):'Số máy khách đời cũ tối đa hoạt động đồng thời',
 (1005,'ar'):'تحذيرات بشأن حالة الاتحاد',
 (1005,'de'):'Warnungen zum Status der Föderation',
 (1005,'es'):'Advertencias sobre el estado de la federación',
 (1005,'hi'):'फ़ेडरेशन की स्थिति संबंधी चेतावनियाँ',
 (1005,'id'):'Peringatan tentang status federasi',
 (1005,'ja'):'フェデレーションの状態に関する警告',
 (1005,'vi'):'Cảnh báo về trạng thái liên đoàn',
 (1007,'ar'):'لا يوجد تشويه',
 (1007,'de'):'Keine Verzerrung',
 (1007,'hi'):'वार्प प्रभाव नहीं',
 (1007,'id'):'Tidak ada distorsi',
 (1008,'ar'):'عدد مرات إعادة المحاولة عبر FTP',
 (1008,'es'):'Reintentos de FTP',
 (1008,'hi'):'FTP पुनः प्रयासों की संख्या',
 (1008,'id'):'Jumlah percobaan ulang FTP',
 (1008,'ja'):'FTP 再試行回数',
 (1008,'ko'):'FTP 재시도 횟수',
 (1008,'zh-Hans'):'FTP 重试次数',
 (1008,'zh-Hant'):'FTP 重試次數',
 (1011,'ar'):'أكمل جاهزية عنوان URL الأساسي والرمز المميز وخريطة المسارات قبل التنفيذ المباشر.',
 (1011,'es'):'Asegúrate de que la URL base, el token y el mapa de rutas estén listos antes de la ejecución en vivo.',
 (1012,'ar'):'نظّف سجلات العضوية المنتهية الصلاحية',
 (1012,'de'):'Abgelaufene Mitgliedschaftseinträge bereinigen',
 (1012,'es'):'Eliminar los registros de membresía vencidos',
 (1012,'fr'):'Nettoyer les enregistrements d’adhésion expirés',
 (1012,'hi'):'समाप्त हो चुके सदस्यता रिकॉर्ड हटाएँ',
 (1012,'id'):'Bersihkan catatan keanggotaan yang kedaluwarsa',
 (1012,'ja'):'期限切れの会員記録を削除',
 (1012,'ko'):'만료된 회원 기록 정리',
 (1012,'pt-BR'):'Limpar registros de associação expirados',
 (1012,'vi'):'Dọn dẹp hồ sơ thành viên đã hết hạn',
 (1012,'zh-Hans'):'清理已过期的会员记录',
 (1012,'zh-Hant'):'清理已過期的會員紀錄',
 (1013,'de'):'Auswirkung: {impact}',
 (1013,'id'):'Dampak: {impact}',
 (1014,'de'):'Titel',
 (1014,'hi'):'ट्रैक',
 (1014,'id'):'lagu',
 (1015,'de'):'Mitgliedschaftsdatensatz abrufen',
 (1016,'es'):'Clave de API de YouTube',
 (1016,'zh-Hans'):'YouTube API 密钥',
 (1016,'zh-Hant'):'YouTube API 金鑰',
 (1018,'ar'):'جسر',
 (1018,'id'):'Jembatan',
 (1021,'vi'):'Xóa tác vụ truyền',
 (1022,'ar'):'مدة الاحتفاظ بالملفات المكتملة (بالدقائق)',
 (1022,'de'):'Aufbewahrungsdauer abgeschlossener Dateien (Minuten)',
 (1022,'es'):'Tiempo de retención de archivos completados (min)',
 (1022,'fr'):'Durée de conservation des fichiers terminés (min)',
 (1022,'hi'):'पूरी हो चुकी फ़ाइलों को रखने की अवधि (मिनट)',
 (1022,'id'):'Masa simpan file yang selesai (menit)',
 (1022,'ja'):'完了ファイルの保持期間（分）',
 (1022,'ko'):'완료 파일 보관 기간(분)',
 (1022,'pt-BR'):'Tempo de retenção de arquivos concluídos (min)',
 (1022,'vi'):'Thời gian lưu giữ tệp đã hoàn tất (phút)',
 (1022,'zh-Hans'):'已完成文件的保留时间（分钟）',
 (1022,'zh-Hant'):'已完成檔案的保留時間（分鐘）',
 (1023,'ar'):'اسم مفتاح API',
 (1026,'ar'):'منفذ TCP لشبكة التراكب الخاصة بـ DHT',
 (1026,'es'):'Puerto TCP de la red superpuesta de DHT',
 (1026,'fr'):'Port TCP du réseau superposé DHT',
 (1026,'hi'):'DHT ओवरले नेटवर्क का TCP पोर्ट',
 (1026,'id'):'Port TCP jaringan overlay DHT',
 (1026,'pt-BR'):'Porta TCP da rede de sobreposição DHT',
 (1026,'vi'):'Cổng TCP của mạng overlay DHT',
 (1026,'zh-Hans'):'DHT 覆盖网络 TCP 端口',
 (1026,'zh-Hant'):'DHT 覆蓋網路 TCP 連接埠',
}
CORRECTION_REASONS = {
 1004:'This limit concerns older software clients; the target must distinguish legacy clients from existing or inherited customers.',
 1005:'The diagnostics heading labels warnings about federation state; literal stance or physical-posture wording is unclear in this section.',
 1007:'The visualizer shader status says the warp section is absent; the target should describe no warp or distortion effect, not a command or textile term.',
 1008:'The caller is a numeric FTP retry-count field; the target removes redundant attempts wording and preserves the exact protected literal FTP.',
 1011:'The readiness helper requires a base URL, token, and path-map before live execution; the target explicitly includes the base URL.',
 1012:'The button removes expired membership records from local state; the target names expired membership records as the cleanup objects.',
 1013:'The caller formats playlist-network impact; the target uses the resulting effect or impact sense rather than influence.',
 1014:'All three callers count music tracks; the target uses music-track terminology rather than railway tracks or traces.',
 1015:'The MediaCore panel retrieves a membership record; the German target must not identify a membership card.',
 1016:'The label names a YouTube API credential; the target uses the API-key term rather than a physical key.',
 1018:'This is the noun label for a Bridge settings pane; Arabic uses a standard noun and Indonesian uses a noun rather than a verb.',
 1021:'The transfer-list action removes a file transfer without changing its source file; the Vietnamese current phrase commonly means a bank transfer.',
 1022:'The numeric setting is the retention duration for completed files, in minutes; the target includes both retention and duration.',
 1023:'The policy field is the name of an API key; Arabic word order must preserve that noun phrase.',
 1026:'The Admin Policies field is a TCP port for the DHT overlay network; the target must describe a network port rather than a visual layer or harbor.',
}
RETAIN_REASONS = {
 1003:'The target describes cleanup of old messages and preserves the 30-day period in the button label.',
 1004:'The target preserves the maximum-concurrency limit and the legacy-client sense in this Bridge setting.',
 1005:'The target conveys federation warnings in the diagnostics section; its local technical term is intelligible in this context.',
 1006:'The target instructs the user to stop the currently running search, matching the conditional stop action in the caller.',
 1007:'The target describes the absence of the warp effect in the visualizer shader status.',
 1008:'The target identifies FTP retry attempts or retries in the numeric input context and preserves the protected FTP literal.',
 1009:'The target states that no logs match the selected filter, as shown in the connected log table.',
 1010:'ID is an identifier label and is correctly preserved as the same technical abbreviation.',
 1011:'The target includes the base URL, token, path-map, and live-execution timing required by the readiness helper.',
 1012:'The target describes cleanup of expired membership records in the action context.',
 1013:'The target labels the network effect and preserves the {impact} placeholder.',
 1014:'The target denotes music tracks in directory, release-coverage, and album contexts.',
 1015:'The target describes retrieving a membership record in the MediaCore panel.',
 1016:'The target identifies a YouTube API credential in the configured/missing status label.',
 1017:'The target describes skipped texture assets and preserves both {count} and {fileNames}.',
 1018:'The target names the Bridge settings pane as a noun.',
 1019:'The target preserves the publish action, ContentID, DHT destination, discovery purpose, and metadata-review instruction.',
 1020:'The target asks the user to close the log preview and return to retained files.',
 1021:'The target describes removing a file transfer from the list; the tooltip clarifies that the source file is unchanged.',
 1022:'The target describes the completed-file retention setting and its minute unit.',
 1023:'The target identifies the name field for an API key.',
 1025:'The target labels the numeric artifact score in the AI audio heuristics panel.',
 1026:'The target identifies a TCP port for the overlay-network field in the Admin Policies form.',
 1027:'The target states that federation diagnostics failed to load.',
}

cells = readjl(CAND/'source-current-cells.jsonl')
primary_rows = readjl(PRIMARY/'primary-review.jsonl')
blind_rows = readjl(BLIND/'review-cells.jsonl')
callers = {r['sourceId']: r for r in readjl(CAND/'caller-contexts.jsonl')}
prior_holds = readjl(CAND/'prior-held-cell-reattestation-hash-only.jsonl')
prior_window_holds = [r for r in readjl(CAND/'window-holds-hash-only.jsonl') if r.get('window')=='W953-W977']
active_prior_holds = prior_holds + prior_window_holds
primary = {(r['continuationRank'],r['locale']): r for r in primary_rows}
blind = {(r['continuationRank'],r['locale']): r for r in blind_rows}
if set(FIXES) != ({k for k,v in primary.items() if v['disposition']=='correction'} | {k for k,v in blind.items() if v['decision']=='proposal'}):
    raise SystemExit('cross target keys do not equal proposal union')

rows = []
for c in sorted(cells, key=lambda x:(x['continuationRank'],LOCALES.index(x['locale']))):
    key = (c['continuationRank'],c['locale'])
    p = primary.get(key)
    b = blind[key]
    common = {
      'schemaVersion': 1, 'reviewPass':'cross', 'head':HEAD, 'tree':TREE,
      'continuationRank':c['continuationRank'], 'remainingQueueRank':c['remainingQueueRank'],
      'locale':c['locale'], 'sourceId':c['sourceId'], 'sourceIdSha256':c['sourceIdSha256'],
      'sourceSha256':c['sourceSha256'], 'catalogPath':c['catalogPath'],
      'catalogFileSha256':c['catalogFileSha256'], 'catalogGitBlob':c['catalogGitBlob'],
      'callerCount':c['callerCount'], 'callerContextSha256':c['callerContextSha256'],
      'candidateFreeHold':c['candidateFreeHold'], 'crossReviewUsed':True,
      'blindReviewUsed':True, 'rootAdjudicationPerformed':False,
    }
    if c['callerCount'] == 0:
        if p is not None or key in FIXES or b['decision'] != 'hold':
            raise SystemExit(f'unexpected callerless cell state {key}')
        row = common | {
          'sourceTextIncluded':False, 'currentTargetTextIncluded':False,
          'primaryCandidateTargetTextIncluded':False, 'blindProposalTargetTextIncluded':False,
          'crossTargetTextIncluded':False, 'sourceTextOmittedForNoCallerHold':True,
          'currentTargetTextOmittedForNoCallerHold':True,
          'sourceSha256':c['sourceSha256'], 'currentTargetSha256':c['currentTargetSha256'],
          'holdReasonClass':'no-pinned-production-localization-caller',
          'primaryDisposition':'hash-only-hold', 'blindDecision':'hold',
          'crossDisposition':'hash-only-hold', 'confidence':'moderate',
        }
        rows.append(row)
        continue
    if p is None or b['decision'] not in ('retain','proposal'):
        raise SystemExit(f'missing review row {key}')
    source, current = c['source'], c['currentTarget']
    fix = FIXES.get(key)
    disposition = 'correction' if fix is not None else 'accept-current'
    effective = fix if fix is not None else current
    cross_tokens = token_data(source, effective)
    if not target_ok(cross_tokens):
        raise SystemExit(f'cross target token failure {key}: {cross_tokens}')
    additional_literals = [x for x in ('ContentID','YouTube') if x in source]
    additional_literal_checks = [{'literal':x,'preserved':x in effective} for x in additional_literals]
    if not all(x['preserved'] for x in additional_literal_checks):
        raise SystemExit(f'case-sensitive product literal failure {key}: {additional_literal_checks}')
    p_target = p.get('candidateTarget') if p['disposition']=='correction' else None
    b_target = b.get('proposedTarget') if b['decision']=='proposal' else None
    p_match = p_target is not None and p_target == fix
    b_match = b_target is not None and b_target == fix
    if p_match and b_match: selected_from='primary-and-blind'
    elif p_match: selected_from='primary'
    elif b_match: selected_from='blind'
    elif fix is not None: selected_from='cross-review-edited'
    else: selected_from='current'
    caller = callers.get(c['sourceId'], {'callers':[]})
    caller_pins = [{k:r[k] for k in ('path','line','fileSha256','gitBlob','lineSha256','contextSha256')} for r in caller.get('callers',[])]
    p_assessment = 'not-applicable' if p_target is None else ('selected-exact' if p_match else 'accepted-alternative')
    b_assessment = 'not-applicable' if b_target is None else ('selected-exact' if b_match else 'accepted-alternative')
    row = common | {
      'source':source, 'sourceTextIncluded':True,
      'currentTarget':current, 'currentTargetSha256':c['currentTargetSha256'], 'currentTargetTextIncluded':True,
      'baselineTokenChecksPass':c['tokenChecksPass'],
      'baselineTokenEvidenceSha256':c['tokenEvidenceSha256'],
      'baselineTokenEvidence':c['tokenEvidence'],
      'callerRefPins':caller_pins,
      'primaryDisposition':p['disposition'],
      'primaryRationale':p['rationale'],
      'primaryCandidateTarget':p_target,
      'primaryCandidateTargetSha256':p.get('candidateTargetSha256') if p_target is not None else None,
      'primaryCandidateTargetTextIncluded':p_target is not None,
      'primaryCandidateAssessment':p_assessment,
      'blindDecision':b['decision'],
      'blindRationale':b.get('rationale') if b['decision']=='proposal' else None,
      'blindProposalTarget':b_target,
      'blindProposalTargetSha256':text_sha(b_target) if b_target is not None else None,
      'blindProposalTargetTextIncluded':b_target is not None,
      'blindProposalAssessment':b_assessment,
      'crossDisposition':disposition,
      'crossTarget':fix,
      'crossTargetSha256':text_sha(fix) if fix is not None else None,
      'crossTargetTextIncluded':fix is not None,
      'effectiveTargetSha256':text_sha(effective),
      'effectiveTargetTokenCheck':cross_tokens,
      'additionalLiteralChecks':additional_literal_checks,
      'crossRationale':CORRECTION_REASONS[c['continuationRank']] if fix is not None else RETAIN_REASONS[c['continuationRank']],
      'targetSelectedFrom':selected_from,
      'confidence':'moderate',
    }
    rows.append(row)

# Maintain a separate hash-only copy of all previous active holds. The
# candidate-free input splits these across the older-hold and prior-window files.
prior_path = OUT/'prior-active-holds-hash-only.jsonl'
if len(active_prior_holds) != 409 or len({(r['sourceIdSha256'],r['locale']) for r in active_prior_holds}) != 409:
    raise SystemExit('previous active hold lineage/count')
writejl(prior_path, active_prior_holds)
writejl(OUT/'cross-review.jsonl', rows)

counter = collections.Counter(r['crossDisposition'] for r in rows)
by_locale = collections.Counter(r['locale'] for r in rows if r['crossDisposition']=='correction')
by_rank = collections.Counter(str(r['continuationRank']) for r in rows if r['crossDisposition']=='correction')
primary_corrections = {k for k,v in primary.items() if v['disposition']=='correction'}
blind_proposals = {k for k,v in blind.items() if v['decision']=='proposal'}
proposal_target_results = {
  'primaryCandidates':sum(1 for r in primary_rows if r['disposition']=='correction'),
  'primaryCandidatesPassing':sum(1 for r in primary_rows if r['disposition']=='correction' and target_ok(r['tokenCheck']['candidate'])),
  'blindProposals':sum(1 for r in blind_rows if r['decision']=='proposal'),
  'blindProposalsPassing':sum(1 for r in blind_rows if r['decision']=='proposal' and r['proposedTokenChecksPass']),
}
baseline_mismatches = collections.Counter()
for c in cells:
    if c['callerCount'] and not c['tokenChecksPass']:
        evidence=c['tokenEvidence']
        for part,ok in [('placeholder',evidence['placeholders']['matches']),('markup',evidence['markup']['matches']),('numeric',evidence['numbers']['sourcePreserved']),('protectedLiteral',not evidence['protectedLiterals']['missing'])]:
            if not ok: baseline_mismatches[part]+=1
selected_targets_pass = sum(1 for r in rows if r['callerCount'] and target_ok(r['effectiveTargetTokenCheck']))

input_pins = {
  'candidateFreeManifestSha256':file_sha(CAND/'manifest.json'),
  'candidateFreeChecksumsSha256':file_sha(CAND/'SHA256SUMS.txt'),
  'candidateFreeCellsSha256':file_sha(CAND/'source-current-cells.jsonl'),
  'candidateFreeCallerContextsSha256':file_sha(CAND/'caller-contexts.jsonl'),
  'primaryManifestSha256':file_sha(PRIMARY/'manifest.json'),
  'primaryChecksumsSha256':file_sha(PRIMARY/'SHA256SUMS.txt'),
  'primaryReviewRowsSha256':file_sha(PRIMARY/'primary-review.jsonl'),
  'blindChecksumsSha256':file_sha(BLIND/'SHA256SUMS.txt'),
  'blindReviewRowsSha256':file_sha(BLIND/'review-cells.jsonl'),
  'previousActiveHoldsInputSha256':file_sha(CAND/'prior-held-cell-reattestation-hash-only.jsonl'),
  'priorWindowHoldsInputSha256':file_sha(CAND/'window-holds-hash-only.jsonl'),
}
summary = {
  'artifact':'slskdN PR #409 W1003-W1027 independent cross-review',
  'schemaVersion':1, 'repository':'snapetech-org/slskdN', 'pullRequest':409,
  'head':HEAD, 'tree':TREE, 'window':'W85',
  'continuationRankRange':[1003,1027], 'remainingQueueRankRange':[903,927],
  'localeCount':12, 'sourceCount':25, 'cellCount':len(rows),
  'callerBackedCellCount':sum(1 for r in rows if r['callerCount']>0),
  'callerlessHashOnlyHoldCellCount':counter['hash-only-hold'],
  'primaryCorrectionCandidatesReviewed':proposal_target_results['primaryCandidates'],
  'blindProposalTargetsReviewed':proposal_target_results['blindProposals'],
  'proposalTargetStringsReviewed':proposal_target_results['primaryCandidates']+proposal_target_results['blindProposals'],
  'primaryCandidateTokenResults':proposal_target_results,
  'baselineCurrentTokenResults':{
    'callerBackedCellsChecked':sum(1 for c in cells if c['callerCount']>0),
    'passingCells':sum(1 for c in cells if c['callerCount']>0 and c['tokenChecksPass']),
    'mismatchingCells':sum(1 for c in cells if c['callerCount']>0 and not c['tokenChecksPass']),
    'mismatchCounts':dict(baseline_mismatches),
    'mismatchCell':{'continuationRank':1008,'locale':'hi','sourceId':'src_381531deeb3ce150','issue':'protected literal FTP is transliterated as Devanagari'},
  },
  'crossSelectedTargetTokenResults':{
    'callerBackedTargetsChecked':sum(1 for r in rows if r['callerCount']>0),
    'passingTargets':selected_targets_pass,
    'failingTargets':sum(1 for r in rows if r['callerCount']>0)-selected_targets_pass,
    'mismatchCounts':{},
  },
  'primaryCorrectionCount':len(primary_corrections),
  'blindProposalCount':len(blind_proposals),
  'proposalOverlapCellCount':len(primary_corrections & blind_proposals),
  'primaryOnlyCorrectionCellCount':len(primary_corrections-blind_proposals),
  'blindOnlyProposalCellCount':len(blind_proposals-primary_corrections),
  'proposalUnionCellCount':len(primary_corrections | blind_proposals),
  'crossDispositionCounts':dict(counter),
  'crossCorrectionsByLocale':dict(by_locale),
  'crossCorrectionsByRank':dict(by_rank),
  'previousActiveHashOnlyHoldsReattested':len(active_prior_holds),
  'newRank1024HashOnlyHolds':counter['hash-only-hold'],
  'resultingActiveHashOnlyHolds':len(active_prior_holds)+counter['hash-only-hold'],
  'inputPins':input_pins,
  'rootFlags':{
    'candidateFreeInput':True, 'blindReviewUsed':True, 'crossReviewUsed':True,
    'rootAdjudicationPerformed':False, 'catalogsEdited':False, 'translationsApplied':False,
    'testsBuildsScansCiRun':False,
  },
  'confidence':'moderate',
  'languageNote':'Cross-review independently compared source strings, exact-head targets, caller context, and both proposal sets. No native-speaker signoff is claimed.',
}
writej(OUT/'summary.json', summary)

# Packet documentation is data-bearing and therefore written before sealing.
readme = f'''# slskdN PR #409 W1003–W1027 cross-review\n\nIndependent cross-review of all {len(rows)} selected cells at head `{HEAD}` / tree `{TREE}`. The review used the candidate-free packet, the primary review, the blind review, and pinned production caller references. No catalog files were edited and no translation was applied.\n\nThe packet records {proposal_target_results['primaryCandidates']} primary candidate translations and {proposal_target_results['blindProposals']} blind proposal translations ({proposal_target_results['primaryCandidates']+proposal_target_results['blindProposals']} proposal strings total). These cover {len(primary_corrections | blind_proposals)} distinct cells: {len(primary_corrections & blind_proposals)} overlap, {len(primary_corrections-blind_proposals)} primary-only, and {len(blind_proposals-primary_corrections)} blind-only. The cross-review selects or adjusts all proposal issues and recommends {counter['correction']} corrections, retains {counter['accept-current']} current targets, and preserves {counter['hash-only-hold']} rank-1024 cells as text-free hash-only holds.\n\nThe exact-head current targets have one protected-literal mismatch: Hindi `FTP retry attempts` transliterates `FTP` instead of preserving the literal. The selected cross-review target preserves `FTP`; all {selected_targets_pass} selected caller-backed targets pass placeholder, markup, numeric-token, and protected-literal checks. All {len(active_prior_holds)} previous active holds are copied hash-only in `prior-active-holds-hash-only.jsonl`, yielding {len(active_prior_holds)+counter['hash-only-hold']} active holds when the 12 new rank-1024 holds are included.\n\nRoot adjudication remains pending. Confidence is moderate; translations were not native-speaker validated. Run `python verify_cross_review.py` from this directory to verify the seal, exact-head inputs, per-cell coverage, proposals, tokens, and hold redactions.\n'''
(OUT/'README.md').write_text(readme, encoding='utf-8')

# Build inventory and packet seal. SHA256SUMS covers every file except itself.
file_names = sorted(p.name for p in OUT.iterdir() if p.is_file() and p.name not in ('manifest.json','SHA256SUMS.txt'))
files = [{'path':n,'bytes':(OUT/n).stat().st_size,'sha256':file_sha(OUT/n)} for n in file_names]
manifest = {
  'schemaVersion':1, 'repository':'snapetech-org/slskdN', 'pullRequest':409,
  'head':HEAD, 'tree':TREE, 'window':'W85',
  'continuationRankRange':[1003,1027], 'remainingQueueRankRange':[903,927],
  'cellCount':len(rows), 'crossCorrectionCount':counter['correction'],
  'crossRetainCount':counter['accept-current'], 'hashOnlyHoldCellCount':counter['hash-only-hold'],
  'blindReviewUsed':True, 'crossReviewUsed':True, 'rootAdjudicationPerformed':False,
  'catalogsEdited':False, 'translationsApplied':False,
  'candidateFreeInputManifestSha256':input_pins['candidateFreeManifestSha256'],
  'primaryInputManifestSha256':input_pins['primaryManifestSha256'],
  'blindInputChecksumsSha256':input_pins['blindChecksumsSha256'],
  'inputPins':input_pins, 'files':files,
}
writej(OUT/'manifest.json', manifest)
seal_files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt')
(OUT/'SHA256SUMS.txt').write_text(''.join(f'{file_sha(p)}  {p.name}\n' for p in seal_files),encoding='utf-8')
print(json.dumps({'result':'BUILT','output':str(OUT),'cells':len(rows),'corrections':counter['correction'],'retains':counter['accept-current'],'holds':counter['hash-only-hold'],'primaryCandidates':proposal_target_results['primaryCandidates'],'blindProposals':proposal_target_results['blindProposals'],'candidateFiles':len(seal_files)},indent=2))
