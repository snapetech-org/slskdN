from pathlib import Path
import collections, datetime, hashlib, json, re, sys
inp = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w59-ranks353-377-primary-20261103/input')
out = Path('/mnt/disks/scratch/task-scratch/slskdn-pr409-w59-independent-blind-20261103')
sha = lambda s: hashlib.sha256(s.encode('utf-8')).hexdigest()
shab = lambda b: hashlib.sha256(b).hexdigest()
canon = lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
manifest = json.loads((inp/'manifest.json').read_text(encoding='utf-8'))
att = json.loads((inp/'head-tree-attestation.json').read_text(encoding='utf-8'))
sel = json.loads((inp/'selection-and-boundary.json').read_text(encoding='utf-8'))
assert manifest['head'] == 'fd6bf5c72a668eecac8cc57e4587bced7e4d9aad'
assert manifest['tree'] == '01c4bb4ea231e6ba72c3087d133b6e3e669853d9'
assert att['head'] == manifest['head'] and att['tree'] == manifest['tree']
assert sel['firstSelected']['continuationRank'] == 353 and sel['lastSelected']['continuationRank'] == 377
cells = [json.loads(x) for x in (inp/'source-current-cells.jsonl').read_text(encoding='utf-8').splitlines()]
contexts = {x['continuationRank']: x for x in map(json.loads, (inp/'caller-contexts.jsonl').read_text(encoding='utf-8').splitlines())}
assert len(cells) == 300 and len(contexts) == 25
fixes = {
(353,'hi'):('correction','सामग्री पर राय','This is a section heading about opinions on content; पर makes the relation clear in Hindi.'),
(353,'vi'):('correction','Ý kiến về nội dung','The current word order reads like “content opinions”; this naturally means opinions about content.'),
(357,'ko'):('refinement','출처','In this metadata context, provenance means the source/origin of the content; 출처 is clearer than 기원.'),
(360,'vi'):('correction','  Tóm tắt lần chạy: {summary}','The current wording is unnatural for a run summary; this preserves the two leading spaces and exact placeholder.'),
(362,'vi'):('correction','Chưa phát hiện nút ngang hàng slskdN nào','The caller is about peer discovery; đồng nghiệp means a colleague, while nút ngang hàng is the network peer sense.'),
(365,'zh-Hant'):('correction','未讀篩選器','The current target uses a Simplified character in Traditional Chinese; this uses the locale script for the unread filter.'),
(367,'ar'):('correction','خيارات {label}','This is a dropdown aria-label; Arabic reads naturally as “options for {label},” with the placeholder retained.'),
(368,'hi'):('correction','आसानी से पढ़ने के लिए संदेश UI को पूरी तरह बड़ा करें।','The tooltip describes the Messages interface, not a product name; localize Messages and retain the common UI abbreviation.'),
(368,'vi'):('correction','Phóng to toàn bộ giao diện Tin nhắn để dễ đọc hơn.','The tooltip describes the Messages interface; Tin nhắn is a natural localized feature name.'),
(370,'id'):('correction','Diimpor:','The label precedes a count of imported entries; Diimpor expresses the passive completed state.'),
(370,'ja'):('correction','インポート済み：','The label precedes a count of imported entries; this is software import completion, while 輸入品 means imported goods.'),
(370,'ko'):('correction','가져온 항목:','The label precedes a count of imported entries; 가져온 항목 names them, while 수입 reads as import of goods.'),
(370,'zh-Hans'):('correction','已导入：','The label precedes a count of imported entries; 已导入 expresses completed software import.'),
(370,'zh-Hant'):('correction','已匯入：','The label precedes a count of imported entries; 已匯入 is the software-import status in Traditional Chinese.'),
(372,'ar'):('correction','بيانات اعتماد المزوّد مكتملة','This is a passing setup-health status when no optional provider credential gaps remain; مكتملة says the credentials are complete.'),
(372,'de'):('correction','Anbieter-Zugangsdaten vollständig','This is a passing setup-health status when no optional credential gaps remain; vollständig says the credentials are complete.'),
(372,'es'):('correction','Credenciales del proveedor completas','The caller uses this as a passing setup-health status when no optional credential gaps remain; completas says they are present.'),
(372,'fr'):('correction','Identifiants du fournisseur complets','The caller uses this as a passing status; complets says the credentials are present, while effacés means erased.'),
(372,'hi'):('correction','प्रदाता क्रेडेंशियल पूरे हैं','This passing status means no optional credential gaps remain; पूरे हैं says credentials are complete.'),
(372,'id'):('correction','Kredensial penyedia lengkap','This passing status means no optional credential gaps remain; lengkap says credentials are complete.'),
(372,'ja'):('correction','プロバイダーの認証情報がそろっています','This passing status means no optional credential gaps remain; the current クリアされます sounds like credentials will be cleared.'),
(372,'ko'):('correction','공급자 자격 증명이 모두 입력되었습니다','This passing status means no optional credential gaps remain; the current 지우기 is a clear/delete action.'),
(372,'pt-BR'):('correction','Credenciais do provedor completas','This passing status means no optional credential gaps remain; completas says the credentials are present.'),
(372,'vi'):('correction','Thông tin xác thực của nhà cung cấp đã đầy đủ','This passing status means no optional credential gaps remain; đã đầy đủ says the credentials are complete.'),
(372,'zh-Hans'):('correction','提供商凭据齐全','This passing status means no optional credential gaps remain; 齐全 says all credentials are present.'),
(372,'zh-Hant'):('correction','提供者憑證齊全','This passing status means no optional credential gaps remain; 齊全 says all credentials are present.'),
(377,'hi'):('correction','बातचीत','This is the chat-conversations navigation label; बातचीत is the standard Hindi spelling.'),
}
contexts_summary = {
353:'MediaCore section heading above the content-opinion ID input.',354:'Policy action to discard unsaved edits and restore daemon-reported values.',355:'Phrase describing the current swarm download.',357:'MediaCore provenance metadata label.',358:'Source label followed by the visible bullet glyph.',359:'System Events category label.',360:'Automation run-summary log line with {summary}; source has two leading spaces.',361:'Action to choose audio files.',362:'Network empty state; adjacent text explains peers are discovered through searches and downloads.',363:'Servarr setup label; product name retained.',364:'Candidate-neighbor label in the discovery workflow.',365:'Checkbox label for filtering unread release-radar notifications.',367:'Accessible dropdown name with child label interpolated through {label}.',368:'Tooltip for enlarging the Messages interface.',369:'Progress toast with search counts and FLAC count.',370:'Import-result label immediately followed by the imported-entry count.',371:'Failure message when removing a member.',372:'Passing setup-health status emitted when no optional provider credential gaps remain.',373:'Action to leave a named room with {roomName}.',374:'Instruction to ignore the Wishlist product folder.',375:'Confirmation that an item was added to the wishlist.',376:'Artist field/category label.',377:'Accessible navigation name for the chat conversations tree.'}
protected = ['FLAC','slskdN','Servarr','Wishlist']
rows=[]; counts=collections.Counter()
for c in cells:
    rank,locale=c['continuationRank'],c['locale']; source,current=c['source'],c['currentTarget']; ctx=contexts[rank]
    if rank in {356,366}:
        disp='hold'; selected=current; rationale='The candidate-free input contains no exact production caller for this source ID. Preserve the current value in every locale pending caller resolution; no replacement is selected.'; confidence='high'; hold='No pinned production caller; caller-resolution hold applies to all 12 locale cells.'
    elif (rank,locale) in fixes:
        disp,selected,rationale=fixes[(rank,locale)]; confidence='moderate' if disp=='refinement' else 'high'; hold=None
    else:
        disp='accept-current'; selected=current; rationale='The current target preserves the source meaning in the pinned production caller context.'; confidence='moderate'; hold=None
    counts[disp]+=1
    s_ph=re.findall(r'\{[A-Za-z][A-Za-z0-9_]*\}',source); t_ph=re.findall(r'\{[A-Za-z][A-Za-z0-9_]*\}',selected)
    s_tags=re.findall(r'</?[A-Za-z][^>]*>',source); t_tags=re.findall(r'</?[A-Za-z][^>]*>',selected)
    s_num=re.findall(r'(?<!\w)\d+(?:[.,]\d+)?',source); t_num=re.findall(r'(?<!\w)\d+(?:[.,]\d+)?',selected)
    required=[lit for lit in protected if lit in source]; literal={lit:(lit in selected) for lit in required}
    domain={'swarm':('swarm' in selected.casefold())} if 'swarm' in source.casefold() else {}
    edge=lambda v:(len(v)-len(v.lstrip()),len(v)-len(v.rstrip()))
    checks={'sourceHashVerified':sha(source)==c['sourceSha256'],'currentTargetHashVerified':sha(current)==c['currentTargetSha256'],'selectedTargetHashComputed':True,'placeholderMultisetParity':collections.Counter(s_ph)==collections.Counter(t_ph),'markupSequenceParity':s_tags==t_tags,'numericValueParity':s_num==t_num,'protectedLiteralsPresent':all(literal.values()),'domainTermPreserved':all(domain.values()),'edgeWhitespaceParity':edge(source)==edge(selected)}
    assert all(checks.values()), (rank,locale,checks,required,literal,domain)
    row={'schemaVersion':1,'reviewType':'independent-blind-semantic','repository':'snapetech-org/slskdN','pullRequest':409,'head':manifest['head'],'tree':manifest['tree'],'window':'W59-ranks-353-377','continuationRank':rank,'historicalSourceOrdinal':c['historicalSourceOrdinal'],'sourceId':c['sourceId'],'source':source,'sourceSha256':c['sourceSha256'],'locale':locale,'catalogPath':c['catalogPath'],'catalogFileSha256':c['catalogFileSha256'],'catalogGitBlob':c['catalogGitBlob'],'currentTarget':current,'currentTargetSha256':c['currentTargetSha256'],'selectedTarget':selected,'selectedTargetSha256':sha(selected),'disposition':disp,'rationale':rationale,'confidence':confidence,'callerContext':{'callerCount':ctx['productionCallerCount'],'boundedScan':ctx['boundedScan'],'callers':ctx['callers'],'summary':contexts_summary.get(rank,'No direct caller; hold current value pending resolution.')},'sourcePlaceholders':s_ph,'selectedTargetPlaceholders':t_ph,'sourceMarkupTags':s_tags,'selectedTargetMarkupTags':t_tags,'sourceNumericValues':s_num,'selectedTargetNumericValues':t_num,'protectedLiteralsRequired':required,'protectedLiteralChecks':literal,'domainTermChecks':domain,'integrityChecks':checks,'holdReason':hold,'nativeSpeakerApproved':False}
    rows.append(row)
assert len(rows)==300 and len({(x['continuationRank'],x['locale']) for x in rows})==300
assert counts=={'accept-current':249,'correction':26,'refinement':1,'hold':24},counts
assert all(x['disposition']=='hold' for x in rows if x['continuationRank'] in {356,366})
(out/'blind-decisions.jsonl').write_text(''.join(canon(x)+'\n' for x in rows),encoding='utf-8')
summary={'schemaVersion':1,'repository':'snapetech-org/slskdN','pullRequest':409,'head':manifest['head'],'tree':manifest['tree'],'window':'W59-ranks-353-377','cellCount':300,'sourceCount':25,'localeCount':12,'localeOrder':manifest['locales'],'dispositions':dict(sorted(counts.items())),'reviewedCallerlessRanks':[356,366],'integrityFailures':0,'candidateFreeInputChecksumManifestSha256':shab((inp/'PACKET-SHA256SUMS.txt').read_bytes()),'nativeSpeakerApproved':False,'reviewType':'independent blind semantic review; no primary proposal ledger consulted'}
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
provenance={'repository':'snapetech-org/slskdN','pullRequest':409,'head':manifest['head'],'tree':manifest['tree'],'branch':att['branch'],'remoteBranchHead':att['remoteBranchHead'],'livePullRefHead':manifest['head'],'livePRState':'OPEN','isDraft':True,'inputDirectory':str(inp),'inputChecksumManifest':'PACKET-SHA256SUMS.txt','inputChecksumManifestSha256':shab((inp/'PACKET-SHA256SUMS.txt').read_bytes()),'verifiedInputFiles':len(manifest['files']),'reviewedAtUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewerType':'independent blind semantic review; current targets only','candidateExposure':'none'}
(out/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(out/'README.md').write_text('''# slskdN PR #409 W59 independent blind review\n\nThis packet independently reviews all 300 pinned current target cells (25 continuation ranks × 12 locales) from the candidate-free input. No primary proposal ledger was consulted.\n\nDisposition counts: 249 accept-current, 26 corrections, 1 refinement, and 24 holds. Holds remain on ranks 356 (“Add Torrent”) and 366 (“Searches”) for every locale because the packet has no pinned production callers.\n\nFindings include the Vietnamese “peer” mistranslation at rank 362, the Simplified character in the Traditional Chinese unread-filter label at rank 365, pass-status wording for “Provider credentials clear” at rank 372, and the Hindi spelling of “Conversations” at rank 377. The rank 370 label precedes a count of imported entries; software-import wording was corrected in five locales.\n\nAll cells pass exact source/current/selected hash, placeholder, markup, numeric, protected-literal, domain-term, and edge-whitespace checks. This machine-assisted review is not qualified native-speaker approval.\n''',encoding='utf-8')
files=sorted(p for p in out.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt')
(out/'SHA256SUMS.txt').write_text(''.join(f'{shab(p.read_bytes())}  {p.name}\n' for p in files),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
