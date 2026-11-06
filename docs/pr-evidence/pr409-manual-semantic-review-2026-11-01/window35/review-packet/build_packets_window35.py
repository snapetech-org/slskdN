#!/usr/bin/env python3
"""Build a row-level W35 semantic review and root cross-review packet."""
import collections, hashlib, json, re
from pathlib import Path

ROOT = Path('/mnt/disks/scratch/task-scratch/slskdn-manual-review-window35-91727326-20261102')
LOCALES = ['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode('utf-8')).hexdigest()


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def write_jsonl(path, rows):
    path.write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n' for row in rows), encoding='utf-8')

# Each target below is grounded in the frozen caller text and exact source contexts.
# The independent root pass should confirm or refine every candidate before any catalog write.
fixes = {
    'src_04f125038ce71bc8': {
        'vi': ('Kết quả ý kiến tổng hợp', 'The current value contains two invisible U+200B characters between words. Removing them preserves the intended phrase and avoids hidden characters in a visible header.', 'high'),
    },
    'src_04f13cecbc50590b': {
        'ko': ('연속적', 'This label is the automation cadence option paired with Daily and other schedules. 마디 없는 means jointless/without joints, not continuous.', 'high'),
    },
    'src_05111e1ef45a3be6': {
        'id': ('Mundurkan pemutaran lokal 15 detik.', 'The player button calls seekBy(-15), so this action rewinds playback. Putar ulang means replay/play again, and sebanyak makes the duration phrasing unnatural.', 'high'),
    },
    'src_051b1355a50fbc4e': {
        'hi': ('प्रतिकूल परिवेश के लिए सुरक्षा सुविधाएँ उपलब्ध नहीं हैं', 'The following exact caller describes advanced security options designed for users in adversarial environments. The current प्रतिकूल सुविधाएँ means adverse/unfavorable features; the revision names the security options for that environment.', 'moderate'),
        'de': ('Sicherheitsfunktionen für feindliche Umgebungen nicht verfügbar', 'The following exact caller describes advanced security options designed for users in adversarial environments. Gegnerische Funktionen can mean functions belonging to or acting against opponents; this names the security features for hostile environments.', 'moderate'),
        'ja': ('敵対的な環境向けのセキュリティ機能は利用できません', 'The following exact caller describes advanced security options designed for users in adversarial environments. 敵対的機能 can read as features that are themselves hostile; this states that the security features for such environments are unavailable.', 'moderate'),
        'fr': ('Fonctionnalités de sécurité en environnement hostile indisponibles', 'The following exact caller describes advanced security options designed for users in adversarial environments. Contradictoires means contradictory, not adversarial; this states the supported security context.', 'high'),
        'pt-BR': ('Recursos de segurança para ambientes adversariais indisponíveis', 'The following exact caller describes advanced security options designed for users in adversarial environments. Recursos adversários can read as features belonging to adversaries; this names security features for adversarial environments.', 'moderate'),
        'ar': ('ميزات الأمان للبيئات المعادية غير متاحة', 'The following exact caller describes advanced security options designed for users in adversarial environments. ميزات الخصومة names hostility rather than the security features intended for hostile environments.', 'moderate'),
        'ko': ('적대적 환경을 위한 보안 기능을 사용할 수 없습니다', 'The following exact caller describes advanced security options designed for users in adversarial environments. 적대적인 기능 can read as hostile features; this names security features intended for adversarial environments.', 'moderate'),
        'vi': ('Các tính năng bảo mật dành cho môi trường đối kháng hiện không khả dụng', 'The following exact caller describes advanced security options designed for users in adversarial environments. Tính năng đối nghịch reads as opposing/contrary features; this names the security context.', 'moderate'),
        'id': ('Fitur keamanan untuk lingkungan adversarial tidak tersedia', 'The following exact caller describes advanced security options designed for users in adversarial environments. Fitur Permusuhan means hostility features; this names the security features for adversarial environments.', 'moderate'),
    },
    'src_05487af3f074b4f3': {
        'hi': ('नाम बदला गया', 'This string is a success toast after a request has been renamed. नाम बदलकर is a dependent/converb form (“having changed the name”) and is incomplete as a standalone confirmation.', 'high'),
    },
    'src_05903727c237b6da': {
        'zh-Hans': ('为此浏览器配置 ListenBrainz 听歌记录提交。', 'The caller is a player control for the ListenBrainz integration. The current 乱码 means garbled text; the established locale wording for scrobbling/listens is listening records, so this says to configure their submission.', 'high'),
        'de': ('Konfigurieren Sie das Scrobbeln an ListenBrainz für diesen Browser.', 'This player control opens ListenBrainz integration settings. The current word order lacks the relation to ListenBrainz; an sends scrobbles to the service and preserves the music-specific term.', 'moderate'),
        'ja': ('このブラウザーから ListenBrainz への再生履歴送信を設定します。', 'The caller is a player control for the ListenBrainz integration. This names scrobbling as sending playback history to ListenBrainz, rather than relying on an unclear phonetic rendering of the technical term.', 'moderate'),
        'fr': ('Configurez l’envoi de vos écoutes à ListenBrainz pour ce navigateur.', 'The caller is a player control for the ListenBrainz integration. The current scrobling is misspelled; this clearly describes sending listening history to the service.', 'high'),
        'ar': ('قم بتهيئة إرسال سجل الاستماع إلى ListenBrainz من هذا المتصفح.', 'The caller is a player control for the ListenBrainz integration. التمرير means scrolling, not music scrobbling; the revision identifies sending listening history to ListenBrainz.', 'high'),
        'ko': ('이 브라우저에서 ListenBrainz로 청취 기록을 제출하도록 설정합니다.', 'The caller is a player control for the ListenBrainz integration. 스크롤 means scrolling, not music scrobbling; the revision identifies submitting listening history to ListenBrainz.', 'high'),
        'zh-Hant': ('為此瀏覽器設定 ListenBrainz 聆聽紀錄提交。', 'The caller is a player control for the ListenBrainz integration. The current 亂碼 means garbled text; the established locale wording for scrobbling/listens is listening records, so this says to configure their submission.', 'high'),
        'vi': ('Cấu hình việc gửi lịch sử nghe lên ListenBrainz cho trình duyệt này.', 'The caller is a player control for the ListenBrainz integration. The current value omits scrobbling/listening-history submission; this names the action configured by the control.', 'moderate'),
    },
    'src_059c7c7ff9dafcbb': {
        'hi': ('यह उपयोगकर्ता अब इस फ़ाइल को साझा नहीं करता. किसी अन्य पीयर को ढूंढने का पुनः प्रयास करें.', 'This is a Soulseek transfer error and “peer” means another network participant, not a coworker. Hindi സഹकर्मी means colleague; पीयर is the product’s established P2P wording.', 'high'),
        'pt-BR': ('Este usuário não compartilha mais este arquivo. Tente novamente para encontrar outro peer.', 'The caller is a Soulseek transfer failure that directs the user to another network peer. This locale already uses “peer” in the sibling transfer-limit message; par can be read as a pair here.', 'moderate'),
        'vi': ('Người dùng này không còn chia sẻ tệp này nữa. Hãy thử lại để tìm một peer khác.', 'This is a Soulseek transfer error and “peer” means another network participant, not a colleague. The current đồng nghiệp means coworker; peer is used for this network entity elsewhere in the locale.', 'high'),
        'id': ('Pengguna ini tidak lagi membagikan file ini. Coba lagi untuk mencari peer lain.', 'This is a Soulseek transfer error and “peer” means another network participant, not an associate/colleague. The current rekan is broad; peer is the established P2P wording elsewhere in this locale.', 'high'),
    },
    'src_05c963d66fcc88b9': {
        'pt-BR': ('Construa um atlas a partir de uma semente acima ou restaure uma ramificação salva.', 'This is an empty state in Discovery Graph Atlas. galho usually means a tree limb/twig; ramificação expresses a saved graph branch.', 'moderate'),
        'ko': ('위의 시드에서 아틀라스를 만들거나 저장된 분기를 복원하세요.', 'This is an empty state in Discovery Graph Atlas. 가지 suggests a tree branch; 분기 is the appropriate branch/path term in a graph.', 'moderate'),
    },
    'src_05cda9f50fa087de': {
        'zh-Hans': ('还没有专辑目标。请匹配一个 MusicBrainz 发行版本或录音，以开始跟踪完成进度。', 'This is the Album Completion empty state; the adjacent MusicBrainz panel resolves a canonical database target. The current 发布/记录 reads as publish/record, while 发行版本/录音 names MusicBrainz entities; 匹配 conveys identifying the target.', 'moderate'),
        'hi': ('अभी तक कोई एल्बम लक्ष्य नहीं है। ट्रैकिंग शुरू करने के लिए MusicBrainz रिलीज़ या रिकॉर्डिंग की पहचान करें।', 'This is the Album Completion empty state; the adjacent MusicBrainz panel resolves a canonical database target. समाधान करें reads as solving a problem; पहचान करें tells the user to identify the release or recording.', 'moderate'),
        'de': ('Noch keine Albumziele. Wählen Sie eine MusicBrainz-Veröffentlichung oder -Aufnahme aus, um den Fortschritt zu verfolgen.', 'This is the Album Completion empty state; the adjacent MusicBrainz panel resolves a canonical database target. Version/Aufzeichnung and lösen are poor matches for the release/recording entities and the selection action.', 'moderate'),
        'ja': ('アルバムの目標はまだありません。完了状況の追跡を始めるには、MusicBrainzのリリースまたは録音を特定してください。', 'This is the Album Completion empty state; the adjacent MusicBrainz panel resolves a canonical database target. 記録 means a record/document rather than an audio recording, and 解決 is an awkward literal for resolving the target.', 'moderate'),
        'fr': ('Aucun album cible pour l’instant. Associez une parution ou un enregistrement MusicBrainz pour commencer à suivre l’avancement.', 'This is the Album Completion empty state; the adjacent MusicBrainz panel resolves a canonical database target. version is not the MusicBrainz release entity here, and résolvez reads like solving; associez names linking the selected target.', 'moderate'),
        'pt-BR': ('Ainda não há alvos de álbum. Selecione um lançamento ou uma gravação do MusicBrainz para começar a acompanhar o progresso da conclusão.', 'This is the Album Completion empty state; the adjacent MusicBrainz panel resolves a canonical database target. liberação means permission/release in a generic sense, while lançamento is the music release; select expresses identifying the target.', 'high'),
        'ar': ('لا توجد أهداف للألبوم بعد. حدِّد إصدارًا أو تسجيلًا في MusicBrainz لبدء تتبّع اكتمال الألبوم.', 'This is the Album Completion empty state; the adjacent MusicBrainz panel resolves a canonical database target. The current wording says to solve a release or recording; حدِّد asks the user to identify/select those entities.', 'moderate'),
        'ko': ('아직 앨범 추적 대상이 없습니다. MusicBrainz 릴리스 또는 녹음을 선택하여 완료 진행 상황 추적을 시작하세요.', 'This is the Album Completion empty state; the adjacent MusicBrainz panel resolves a canonical database target. 해결하세요 reads as solving; 선택하여 tells the user to select the release or recording.', 'moderate'),
        'zh-Hant': ('還沒有專輯目標。請配對 MusicBrainz 的發行版本或錄音，以開始追蹤完成進度。', 'This is the Album Completion empty state; the adjacent MusicBrainz panel resolves a canonical database target. 發布/記錄 reads as publish/record, while 發行版本/錄音 names MusicBrainz entities; 配對 conveys identifying the target.', 'moderate'),
        'vi': ('Chưa có mục tiêu album nào. Hãy chọn một bản phát hành hoặc bản thu âm trên MusicBrainz để bắt đầu theo dõi tiến độ hoàn tất.', 'This is the Album Completion empty state; the adjacent MusicBrainz panel resolves a canonical database target. Giải quyết means solve/resolve a problem; bản thu âm names the audio recording and chọn gives a clear target-selection action.', 'moderate'),
        'id': ('Belum ada target album. Pilih rilisan atau rekaman MusicBrainz untuk mulai melacak progres penyelesaian.', 'This is the Album Completion empty state; the adjacent MusicBrainz panel resolves a canonical database target. Selesaikan means complete/finish; pilih tells the user to identify the release or recording to track.', 'moderate'),
    },
}

uncertain = {}
inputs = read_jsonl(ROOT / 'review-input.jsonl')
manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
by_id = {row['id']: row for row in inputs}
if len(by_id) != len(inputs):
    raise SystemExit('duplicate review input IDs')
selected = {row['sourceId'] for row in inputs}
for source_id, locales in fixes.items():
    if source_id not in selected:
        raise SystemExit(f'correction source not selected: {source_id}')
    for locale in locales:
        matching = [row for row in inputs if row['sourceId'] == source_id and row['locale'] == locale]
        if len(matching) != 1:
            raise SystemExit(f'correction cell absent/duplicate: {source_id}/{locale}')

placeholder_pattern = re.compile(r'\{[^{}]+\}')
def placeholders(value):
    return sorted(placeholder_pattern.findall(value))

decisions, plan, uncertain_rows = [], [], []
for row in inputs:
    source_id, locale, ident = row['sourceId'], row['locale'], row['id']
    current, current_hash = row['target'], sha(row['target'])
    if current_hash != row['targetSha256']:
        raise SystemExit(f'input target hash mismatch: {ident}')
    if sha(row['source']) != row['sourceSha256']:
        raise SystemExit(f'input source hash mismatch: {ident}')
    if placeholders(row['source']) != sorted(row.get('placeholders', [])) or placeholders(row['source']) != placeholders(current):
        raise SystemExit(f'source/current placeholder mismatch: {ident}')
    if ident in uncertain:
        reason = uncertain[ident]
        decisions.append({'schemaVersion':1,'window':35,'id':ident,'locale':locale,'sourceId':source_id,'sourceSha256':row['sourceSha256'],'currentTargetSha256':current_hash,'verdict':'uncertain','reason':reason})
        uncertain_rows.append({'schemaVersion':1,'window':35,'id':ident,'locale':locale,'sourceId':source_id,'source':row['source'],'sourceSha256':row['sourceSha256'],'catalogKey':row['catalogKey'],'catalogPath':row['catalogPath'],'currentTarget':current,'currentTargetSha256':current_hash,'reason':reason,'sourceCallsites':row.get('sourceCallsites',[]),'sourceContexts':row.get('sourceContexts',[]),'placeholders':row.get('placeholders',[]),'protectedLiterals':row.get('protectedLiterals',[]),'currentCatalogFileSha256':manifest['currentCatalogFileSha256'][locale],'currentPrHead':manifest['headCommit'],'currentPrTree':manifest['tree'],'currentSourceSubtreeTree':manifest['sourceSubtreeTree'],'nativeSpeakerApproved':False})
    elif locale in fixes.get(source_id, {}):
        target, reason, confidence = fixes[source_id][locale]
        target_hash = sha(target)
        if placeholders(row['source']) != placeholders(target):
            raise SystemExit(f'proposed placeholder mismatch: {ident}')
        for literal in row.get('protectedLiterals', []):
            if literal not in target:
                raise SystemExit(f'protected literal missing: {ident}/{literal}')
        decisions.append({'schemaVersion':1,'window':35,'id':ident,'locale':locale,'sourceId':source_id,'sourceSha256':row['sourceSha256'],'currentTargetSha256':current_hash,'verdict':'correct','candidateTargetSha256':target_hash,'reason':reason})
        plan.append({'schemaVersion':1,'window':35,'id':ident,'locale':locale,'sourceId':source_id,'source':row['source'],'sourceSha256':row['sourceSha256'],'catalogKey':row['catalogKey'],'catalogPath':row['catalogPath'],'currentTarget':current,'currentTargetSha256':current_hash,'proposedTarget':target,'proposedTargetSha256':target_hash,'reason':reason,'confidence':confidence,'sourceCallsites':row.get('sourceCallsites',[]),'sourceContexts':row.get('sourceContexts',[]),'placeholders':row.get('placeholders',[]),'protectedLiterals':row.get('protectedLiterals',[]),'placeholderCheck':'source/current/proposed placeholder sequences match','protectedLiteralCheck':'all protected literals are present in the proposed target','currentCatalogFileSha256':manifest['currentCatalogFileSha256'][locale],'currentPrHead':manifest['headCommit'],'currentPrTree':manifest['tree'],'currentSourceSubtreeTree':manifest['sourceSubtreeTree'],'nativeSpeakerApproved':False})
    else:
        decisions.append({'schemaVersion':1,'window':35,'id':ident,'locale':locale,'sourceId':source_id,'sourceSha256':row['sourceSha256'],'currentTargetSha256':current_hash,'verdict':'keep','reason':'Meaning, locale usage, exact caller context, placeholders, and protected literals are acceptable for this review; native-speaker review remains outstanding.'})

if len(decisions) != len(inputs) or len({d['id'] for d in decisions}) != len(inputs):
    raise SystemExit('decision coverage mismatch')
write_jsonl(ROOT / 'review-decisions.jsonl', decisions)
write_jsonl(ROOT / 'crossreview-plan.jsonl', plan)
write_jsonl(ROOT / 'uncertain-ledger.jsonl', uncertain_rows)
counts = collections.Counter(d['verdict'] for d in decisions)
per_locale = {loc: dict(collections.Counter(d['verdict'] for d in decisions if d['locale'] == loc)) for loc in LOCALES if any(d['locale'] == loc for d in decisions)}
per_source = {}
for decision in decisions:
    per_source.setdefault(decision['sourceId'], collections.Counter())[decision['verdict']] += 1

for name, key in [('review-decisions.jsonl','reviewDecisionLedger'),('crossreview-plan.jsonl','candidatePlan'),('uncertain-ledger.jsonl','uncertainLedger')]:
    payload = (ROOT / name).read_bytes()
    manifest[key] = {'path':name,'rows':len(read_jsonl(ROOT / name)),'sha256':sha(payload)}
manifest.update({'manualReview':'complete pending independent root cross-review','reviewDecisionCounts':dict(sorted(counts.items())),'nativeSpeakerReview':'outstanding','rootCrossReview':'pending','targetsApplied':False,'catalogsEdited':False})
(ROOT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

summary = {
 'result':'MANUAL_REVIEW_COMPLETE_PENDING_ROOT_CROSS_REVIEW',
 'window':35,
 'reviewBaseHead':manifest['headCommit'],
 'reviewBaseTree':manifest['tree'],
 'sourceSubtreePath':manifest['sourceSubtreePath'],
 'sourceSubtreeTree':manifest['sourceSubtreeTree'],
 'sourceKeys':len(selected),
 'cells':len(inputs),
 'verdicts':dict(sorted(counts.items())),
 'correctionRows':len(plan),
 'correctionSourceKeys':len({p['sourceId'] for p in plan}),
 'uncertainRows':len(uncertain_rows),
 'perLocale':per_locale,
 'perSourceKey':{sid:dict(sorted(counter.items())) for sid,counter in sorted(per_source.items())},
 'reviewInputSha256':sha((ROOT/'review-input.jsonl').read_bytes()),
 'decisionLedgerSha256':sha((ROOT/'review-decisions.jsonl').read_bytes()),
 'candidatePlanSha256':sha((ROOT/'crossreview-plan.jsonl').read_bytes()),
 'uncertainLedgerSha256':sha((ROOT/'uncertain-ledger.jsonl').read_bytes()),
 'sourceCallerLinesPinned':manifest['sourceCallerLinesPreflighted'],
 'semanticDecisionConfidence':'high for direct mistranslations, hidden characters, and caller-bound terminology; moderate for nuanced technical terms and locale phrasing; native-speaker review outstanding',
 'reviewerMethod':'manual review of every selected locale cell against frozen English source, exact caller context, neighboring UI usage, placeholders, protected literals, and pinned product context; no translation API/model calls',
 'rootCrossReview':'pending',
 'nativeSpeakerReview':'outstanding',
 'targetsApplied':False,
 'catalogsEdited':False,
}
(ROOT / 'review-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
freeze_summary = json.loads((ROOT/'freeze-summary.json').read_text(encoding='utf-8'))
freeze_summary.update({'result':summary['result'],'manualDecisionsPending':0,'correctionRows':len(plan),'keepRows':counts.get('keep',0),'uncertainRows':len(uncertain_rows),'rootCrossReview':'pending','nativeSpeakerReview':'outstanding','catalogsEdited':False})
(ROOT/'freeze-summary.json').write_text(json.dumps(freeze_summary, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
report = {'result':'PACKET_BUILT_PENDING_READ_ONLY_VALIDATION','window':35,'inputRows':len(inputs),'sourceKeys':len(selected),'candidateRows':len(plan),'uncertainRows':len(uncertain_rows),'decisionCounts':dict(sorted(counts.items())),'perLocale':per_locale,'reviewInputSha256':sha((ROOT/'review-input.jsonl').read_bytes()),'decisionLedgerSha256':sha((ROOT/'review-decisions.jsonl').read_bytes()),'candidatePlanSha256':sha((ROOT/'crossreview-plan.jsonl').read_bytes()),'uncertainLedgerSha256':sha((ROOT/'uncertain-ledger.jsonl').read_bytes()),'currentPrHead':manifest['headCommit'],'currentPrTree':manifest['tree'],'currentSourceSubtreeTree':manifest['sourceSubtreeTree'],'callerLines':manifest['sourceCallerLinesPreflighted'],'nativeSpeakerReview':'outstanding','catalogsEdited':False}
(ROOT/'verification-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
