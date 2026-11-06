#!/usr/bin/env python3
"""Build the W80 independent primary semantic-review ledger from its sealed input."""
import collections
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent.parent / "candidate-free" / "input"
HEAD = "7a1ca27fd0519674c3b42a3e3df3638b0f671567"
TREE = "b3525218d0f9676c88c4991e78775d113f18b7d9"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]

PROPOSALS = {
    "881|ar": "Pod / قناة",
    "881|vi": "Pod / Kênh",
    "881|zh-Hans": "Pod / 频道",
    "881|zh-Hant": "Pod / 頻道",
    "879|es": "Controles avanzados para recuperar DHT sin usar la caché",
    "879|fr": "Commandes avancées pour récupérer des données DHT sans cache",
    "879|pt-BR": "Controles avançados para recuperar DHT sem usar o cache",
    "879|ar": "عناصر تحكم متقدمة لاسترجاع DHT دون استخدام ذاكرة التخزين المؤقت",
    "879|id": "Kontrol lanjutan untuk mengambil DHT tanpa menggunakan cache",
    "882|id": "Menunggu",
    "882|ja": "待機中",
    "882|ko": "대기 중",
    "882|vi": "Đang chờ",
    "882|zh-Hans": "待处理",
    "882|zh-Hant": "待處理",
    "883|ko": "원격 경로 매핑: 원본",
    "885|ar": "ابحث عن محتوى مشابه لهذا الـ ID وفق مستوى الثقة وحدّ النتائج المحددين.",
    "886|ar": "اتصالات المقابس المُنشأة",
    "886|de": "Hergestellte Socket-Verbindungen",
    "886|es": "Conexiones de socket establecidas",
    "886|fr": "Connexions de socket établies",
    "886|hi": "स्थापित सॉकेट कनेक्शन",
    "886|id": "Koneksi socket yang terjalin",
    "886|ja": "確立済みのソケット接続",
    "886|ko": "성립된 소켓 연결",
    "886|pt-BR": "Conexões de socket estabelecidas",
    "886|vi": "Kết nối socket đã thiết lập",
    "886|zh-Hans": "已建立的套接字连接",
    "886|zh-Hant": "已建立的套接字連線",
    "889|vi": "Sao chép báo cáo văn bản về bản xem trước chính sách kệ hiện tại để xem xét. Điều này không áp dụng bất kỳ hành động nào.",
    "890|de": "Wählen Sie aus, ob Hörer diese Sendung entdecken können. Änderungen werden sofort übernommen, solange Sie Gastgeber sind; andernfalls klicken Sie auf „Übertragen“, um die Änderungen anzuwenden.",
    "890|id": "Pilih apakah pendengar dapat menemukan siaran ini. Perubahan langsung berlaku saat Anda menjadi host; jika tidak, klik tombol Siarkan untuk menerapkan perubahan.",
    "890|zh-Hans": "选择听众是否可以发现此广播。您主持时更改会立即生效；否则请点击“广播”以应用更改。",
    "890|zh-Hant": "選擇聽眾是否可以發現此廣播。您主持時變更會立即生效；否則請點擊「廣播」以套用變更。",
    "895|ko": "이 사용자의 Soulseek 본래 관심사를 불러옵니다.",
    "895|zh-Hans": "加载此用户的 Soulseek 原生兴趣。",
    "895|zh-Hant": "載入此使用者的 Soulseek 原生興趣。",
    "896|ja": "最終検索日時",
    "898|ar": "حوّل الفجوات المعتمدة في تحليلات الاستماع إلى عناصر مرشّحة لقائمة انتظار الاقتناء.",
    "898|es": "Convierta las brechas aprobadas del análisis de escucha en candidatos para la cola de adquisición.",
    "898|hi": "स्वीकृत श्रवण-विश्लेषण की कमियों को अधिग्रहण कतार के उम्मीदवारों में बदलें।",
    "898|id": "Ubah kesenjangan yang disetujui dalam analitik aktivitas mendengarkan menjadi kandidat antrean akuisisi.",
    "898|ko": "승인된 청취 분석의 누락 항목을 획득 대기열 후보로 전환합니다.",
    "898|pt-BR": "Transforme as lacunas aprovadas nas análises de escuta em candidatos para a fila de aquisição.",
    "898|vi": "Chuyển các khoảng trống đã được phê duyệt trong phân tích lượt nghe thành ứng viên cho hàng đợi thu thập.",
    "898|zh-Hans": "将获批的聆听分析缺口转为获取队列候选项。",
    "898|zh-Hant": "將核准的聆聽分析缺口轉為取得佇列候選項。",
    "901|de": "Nicht verifiziert",
    "901|es": "Sin verificar",
    "901|ko": "미검증",
    "902|ar": "الإعجابات",
    "902|es": "Le gusta",
    "902|fr": "Aimés",
    "902|ko": "좋아하는 항목",
    "902|pt-BR": "Curtidos",
}

SOURCE_RATIONALES = {
    878: "The caller renders provenanceSignals from a run scorecard as a label; the current translation names those provenance or origin signals.",
    879: "The caller places this summary above cache-bypass controls for DHT descriptor retrieval; the current translations describe advanced retrieval controls.",
    880: "The caller is a tooltip for loading perceptual-hash performance and accuracy metrics; the current translations preserve that action and domain.",
    881: "The caller labels the Pod and Channel columns in route-attempt records; the current terms identify both routing fields.",
    882: "The callers use this as a job or work-chunk status before Running/Completed; the current labels communicate a pending or waiting state.",
    883: "The caller labels the source side of a remote-path mapping form; the current translations express a from/source direction.",
    884: "The callers distinguish a directory from a file and name the path being imported; the current translations preserve that item type.",
    885: "The caller is explanatory text for a similar-content search using confidence and result limits; the current translations preserve the search action and criteria.",
    886: "The caller displays the system_net_sockets_connections_established_total metric; the current translations identify established network sockets or socket connections.",
    887: "The caller displays the Quarantine Jury result when trusted jurors fall short of the required supermajority; the current translations convey that outcome.",
    888: "The caller is a setting tooltip for automated replies to private-message human-check or share-gate prompts; the current translations preserve that behavior.",
    889: "The caller is a copy-report tooltip for a non-mutating Discovery shelf policy preview; the current translations describe copying a report and applying no action.",
    890: "The caller is the visibility setting for a live broadcast, with immediate changes while hosting and a Broadcast action otherwise; current translations preserve that flow.",
    891: "The caller is a toggle tooltip for the browser player's equalizer; the current translations identify enabling the equalizer for this player.",
    892: "The caller labels a destructive bulk action after confirmation; the current translations identify deleting selected Wishlist searches.",
    893: "The caller describes an alternative or nearby track from one SongID run; the current translations preserve candidate, track, and same-run context.",
    894: "The caller explains a local registry search over ContentIDs with an optional type; the current translations preserve the identifiers, scope, and purpose.",
    895: "The caller loads an individual's interests from Soulseek's native discovery data; the current translations describe loading that user's interests.",
    896: "The caller is a table header whose cells display lastSearchedAt timestamps; the current translations indicate when the last search occurred.",
    897: "The caller interpolates an exception type into a provider-request failure message; the current translations preserve the failure and placeholder.",
    898: "The caller is a media-server integration description for converting approved listening-intelligence gaps into acquisition-queue candidates; the current translations preserve that handoff.",
    899: "The caller labels the AcoustID Client configuration field beside Configured/Missing status; the current translations identify the client setting.",
    900: "The caller is a success toast after a saved search filter is persisted; the current translations report that success.",
    901: "The caller is the false branch of a contact.verified status; the current translations indicate the contact has not been verified.",
    902: "The caller labels the loaded user's positive Soulseek interest list, paired with the Hated list; the current wording indicates liked interests.",
}

CORRECTION_RATIONALES_BY_RANK = {
    879: "The caller exposes a force-fresh retrieval option by bypassing the cache. The current Spanish/French/Portuguese phrases omit or misattach freshness; this states that the controls retrieve DHT data without cache.",
    881: "The route-attempt record carries podId and channelId. These locales currently translate Pod as a physical pouch/group/cabin; the proposal keeps Pod as the technical routing field and retains Channel.",
    882: "This status is the queue state before Running or Completed. The current locale word means postponed, on hold, unresolved, or to-do; the proposal names waiting/pending work.",
    883: "The field maps a remote source path; Korean 시작 means a start point or beginning, while 원본 names the source side.",
    885: "The protected source acronym ID was translated away in Arabic. This keeps the readable Arabic phrase and preserves the UI's ID token.",
    886: "The caller exposes a network socket-connection metric. The current wording can read as electrical plugs/outlets or configured sockets; the proposal identifies established socket connections.",
    889: "In this shelf-policy report tooltip, the Vietnamese word giá means price. Kệ means shelf and matches the Discovery shelf feature in the caller.",
    890: "The caller says click Broadcast to apply the setting. The current translation says apply for/register/request; the proposal says apply the changes.",
    895: "The caller loads a user's Soulseek-native interest data. The current wording means default/local-machine interests; the proposal expresses native/original Soulseek interests.",
    896: "This table cell is a lastSearchedAt timestamp. The current Japanese target says the place searched; the proposal names the last-search date and time.",
    898: "The caller places this in a media-server play-history and scrobble integration. Listening intelligence means analysis of listening activity here, not hearing ability; the proposal makes that feature meaning clear.",
    901: "The contact.verified branch reports verification status. The current wording means unconfirmed or an unusual non-word; the proposal says not verified.",
    902: "The label heads the loaded user's liked-interest list. The current wording implies the viewer liked something or an awkward participle; the proposal names likes/liked items as a category.",
}


def sha(data): return hashlib.sha256(data).hexdigest()
def ph(s): return collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", s))
def tags(s): return collections.Counter(re.findall(r"</?[A-Za-z][^>]*>", s))
def nums(s): return ["".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in n) for n in re.findall(r"\d+", s)]
def prot(s):
    vals=set(re.findall(r"\b[A-Z][A-Z0-9]{1,}\b",s)); vals.update(x for x in ("slskdN","Tor","Wishlist","Chromaprint") if x in s); return sorted(vals)
def not_less(a,b):
    x,y=collections.Counter(a),collections.Counter(b); return all(y[k]>=n for k,n in x.items())
def token_check(source,current,target=None):
    r={"sourcePlaceholderTokens":sorted(ph(source).elements()),"currentPlaceholderTokens":sorted(ph(current).elements()),
       "sourceMarkupTokens":sorted(tags(source).elements()),"currentMarkupTokens":sorted(tags(current).elements()),
       "sourceNumericTokens":nums(source),"currentNumericTokens":nums(current),"sourceProtectedLiterals":prot(source),
       "currentProtectedLiterals":[x for x in prot(source) if x in current],"placeholderParityCurrent":ph(source)==ph(current),
       "markupParityCurrent":tags(source)==tags(current),"numericTokensPreservedCurrent":not_less(nums(source),nums(current)),
       "protectedLiteralsPreservedCurrent":all(x in current for x in prot(source))}
    if target is not None:
        r["proposal"]={"placeholderTokens":sorted(ph(target).elements()),"markupTokens":sorted(tags(target).elements()),
                        "numericTokens":nums(target),"protectedLiterals":prot(target),"placeholderParity":ph(source)==ph(target),
                        "markupParity":tags(source)==tags(target),"numericTokensPreserved":not_less(nums(source),nums(target)),
                        "protectedLiteralsPreserved":all(x in target for x in prot(source))}
    return r

def write_rows(name, values):
    (ROOT/name).write_text("".join(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n" for v in values),encoding="utf-8")

def main():
    cells=[json.loads(x) for x in (INPUT/"source-current-cells.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    caller_rows=[json.loads(x) for x in (INPUT/"caller-contexts.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    callers={r["sourceId"]:r for r in caller_rows}
    if len(cells)!=300 or len(callers)!=25: raise SystemExit("REFUSED: candidate-free coverage")
    selected_keys={f"{r['continuationRank']}|{r['locale']}" for r in cells}
    if any(k not in selected_keys for k in PROPOSALS): raise SystemExit("REFUSED: proposal key not selected")
    ledger, corrections, holds=[] ,[],[]
    for cell in cells:
        rank,locale=cell["continuationRank"],cell["locale"]; caller=callers[cell["sourceId"]]; key=f"{rank}|{locale}"; proposal=PROPOSALS.get(key)
        base={"schemaVersion":1,"reviewPass":"independent-primary","head":HEAD,"tree":TREE,"continuationRank":rank,
              "remainingQueueRank":cell["remainingQueueRank"],"sourceId":cell["sourceId"],"sourceSha256":cell["sourceSha256"],
              "locale":locale,"catalogPath":cell["catalogPath"],"catalogFileSha256":cell["catalogFileSha256"],"catalogGitBlob":cell["catalogGitBlob"],
              "currentTargetSha256":cell["currentTargetSha256"],"callerContextSha256":cell["callerContextSha256"],"callerRefs":cell["callerRefs"],
              "productionCallerCount":caller["productionCallerCount"],"sourceRewriteRecommendation":None}
        if not caller["productionCallerCount"]:
            if proposal is not None: raise SystemExit(f"REFUSED: callerless proposal {rank}/{locale}")
            hold=dict(base); hold.update({"disposition":"hold","confidence":"high","holdReasonCode":"CALLERLESS_TEXT_FREE_HOLD",
                "holdReasonSha256":sha(b"CALLERLESS_TEXT_FREE_HOLD"),"sourceTextIncluded":False,"currentTargetTextIncluded":False,
                "tokenEvidenceSha256":cell["tokenEvidenceSha256"]}); ledger.append(hold); holds.append(hold); continue
        source,current=cell["source"],cell["currentTarget"]
        row=dict(base); row.update({"source":source,"catalogKey":cell["catalogKey"],"currentTarget":current,"sourceTextIncluded":True,
                                   "currentTargetTextIncluded":True,"disposition":"correct" if proposal is not None else "accept-current",
                                   "confidence":"moderate","rationale":CORRECTION_RATIONALES_BY_RANK[rank] if proposal is not None else SOURCE_RATIONALES[rank],
                                   "tokenCheck":token_check(source,current,proposal)})
        if proposal is not None:
            check=token_check(source,current,proposal)["proposal"]
            if not all((ph(source)==ph(proposal),tags(source)==tags(proposal),not_less(nums(source),nums(proposal)),all(t in proposal for t in prot(source)))):
                raise SystemExit(f"REFUSED: token integrity {rank}/{locale}")
            row["target"]=proposal; row["targetSha256"]=sha(proposal.encode("utf-8")); row["proposalTokenCheck"]=check; corrections.append(row)
        ledger.append(row)
    if len(ledger)!=300 or len(corrections)!=len(PROPOSALS) or len(holds)!=0: raise SystemExit("REFUSED: primary decision coverage/count")
    correction_keys={f"{r['continuationRank']}|{r['locale']}" for r in corrections}
    if correction_keys!=set(PROPOSALS): raise SystemExit("REFUSED: correction decisions do not match proposal map")
    counts=collections.Counter(r["disposition"] for r in ledger)
    write_rows("primary-review.jsonl",ledger); write_rows("corrections.jsonl",corrections); write_rows("holds-hash-only.jsonl",holds)
    (ROOT/"proposal-map.json").write_text(json.dumps(PROPOSALS,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    rationale={"accepted":{str(k):v for k,v in SOURCE_RATIONALES.items()},"corrections":{k:CORRECTION_RATIONALES_BY_RANK[int(k.split("|",1)[0])] for k in sorted(PROPOSALS)}}
    (ROOT/"rationale-map.json").write_text(json.dumps(rationale,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (ROOT/"source-rewrite-recommendations.json").write_text(json.dumps({"schemaVersion":1,"recommendations":[]},indent=2)+"\n",encoding="utf-8")
    input_manifest=(INPUT/"manifest.json").read_bytes(); input_sums=(INPUT/"PACKET-SHA256SUMS.txt").read_bytes()
    input_live=json.loads((INPUT/"live-after.json").read_text(encoding="utf-8")); input_drift=(INPUT/"main-drift.json").read_bytes()
    proposals_summary=[]
    for row in corrections: proposals_summary.append({"continuationRank":row["continuationRank"],"sourceId":row["sourceId"],"locale":row["locale"],"currentTargetSha256":row["currentTargetSha256"],"targetSha256":row["targetSha256"]})
    summary={"artifact":"slskdN PR #409 W80 independent primary-only semantic review","window":"W80","head":HEAD,"tree":TREE,
             "sourceCount":25,"localeCount":12,"cellCount":300,"dispositions":{k:counts.get(k,0) for k in ("accept-current","correct","hold")},
             "proposedTargetCount":len(corrections),"hashOnlyHoldCount":len(holds),"callerlessSources":sum(r["productionCallerCount"]==0 for r in caller_rows),
             "callerlessCells":len(holds),"candidateFreeInputManifestSha256":sha(input_manifest),"candidateFreeInputChecksumListSha256":sha(input_sums),
             "selectionBoundarySha256":sha((INPUT/"selection-boundary.jsonl").read_bytes()),"sourceInventorySelectionSha256":sha((INPUT/"source-inventory-selection.jsonl").read_bytes()),
             "callerContextSha256":sha((INPUT/"caller-contexts.jsonl").read_bytes()),"sourceCurrentCellsSha256":sha((INPUT/"source-current-cells.jsonl").read_bytes()),
             "mainDriftSha256":sha(input_drift),"liveMainSha":input_live["liveMainSha"],"baseApiSha":input_live["baseRefOid"],
             "priorSelectedIdsExcluded":1957,"priorHeldCellsCarried":382,"priorHoldResolutionHistoryRows":13,"priorAppliedTargetsReattested":109,
             "w79AppliedTargets":46,"w79HoldsCarried":39,"w79CallerlessHoldsHashOnly":24,"blindReviewUsed":False,"crossReviewUsed":False,
             "nativeSpeakerSignoff":False,"browserReview":False,"sourceRewritesRecommended":0,"proposals":proposals_summary,
             "heldCells":[]}
    (ROOT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    readme=f"""# slskdN PR #409 W80 independent primary review\n\nThis packet reviews continuation ranks 878–902 and remaining-queue ranks 778–802: 25 source strings × 12 locales = 300 cells. The exact source head/tree are `{HEAD}` / `{TREE}`.\n\nPrimary decisions: {counts.get('accept-current',0)} accept-current, {len(corrections)} correction proposals, and {len(holds)} holds. All 25 selected source strings have bounded production callers. The one baseline protected-literal mismatch is corrected while preserving `ID`; every proposed target preserves source placeholders, markup, numeric tokens, and protected literals.\n\nReview used the sealed W80 candidate-free packet and its pinned caller context. It did not use blind or cross-review output. W79 continuity carries 1,957 prior selected IDs, 382 prior held cells, 13 historical hold-resolution rows, and 109 applied-target hashes, including all 46 W79 corrections. The 24 W79 callerless holds remain hash-only. No native-speaker signoff or browser review is claimed. No source rewrites are recommended.\n\nNo catalogs or pull request were modified. Run `python3 verify_primary.py --repo /path/to/pinned-clean-worktree` from this directory to verify input linkage, exact cell bindings, target hashes, token evidence, and packet checksums.\n"""
    (ROOT/"README.md").write_text(readme,encoding="utf-8")
    print(json.dumps({"result":"BUILT-PRIMARY-UNSEALED","head":HEAD,"tree":TREE,"dispositions":summary["dispositions"],
                      "proposalCount":len(corrections),"hashOnlyHolds":len(holds),"blindReviewUsed":False,"crossReviewUsed":False},ensure_ascii=False,indent=2))


if __name__=="__main__": main()
