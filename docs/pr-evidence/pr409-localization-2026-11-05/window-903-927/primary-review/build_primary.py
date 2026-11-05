#!/usr/bin/env python3
"""Build W81 primary semantic decisions from the sealed candidate-free input."""
import collections, hashlib, json, re, unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parent
INPUT=ROOT.parent.parent/"candidate-free"/"input"
HEAD="91da6fff5d5b628ade7ee556386e3db1db6878fa"
TREE="56930b73d10a4c419edf68f0d951ceedaa63c990"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
PROPOSALS={
"903|vi":"Số khe tải lên toàn cục",
"907|ar":"تطابقات SongRec المتميزة",
"907|fr":"Correspondances distinctes de SongRec",
"907|id":"Kecocokan unik SongRec",
"907|ja":"SongRec のユニークな一致数",
"907|pt-BR":"Correspondências distintas do SongRec",
"907|vi":"Số kết quả khớp riêng biệt của SongRec",
"912|fr":"Chemin mappé :",
"918|ar":"قيمة التجزئة B (ست عشري)",
"921|ar":"معرّف المحتوى ID (مثلًا: content:audio:album:mb-release-id)",
"921|es":"ID de contenido (por ejemplo: content:audio:album:mb-release-id)",
"921|hi":"कंटेंट ID (उदाहरण: content:audio:album:mb-release-id)",
"921|id":"ID konten (misalnya: content:audio:album:mb-release-id)",
"921|zh-Hans":"内容 ID（例如：content:audio:album:mb-release-id）",
"921|zh-Hant":"內容 ID（例如：content:audio:album:mb-release-id）",
"922|ar":"حالة النقل عبر الشبكة",
"922|hi":"नेटवर्क ट्रांसपोर्ट स्थिति",
"922|id":"Status transport jaringan",
"922|ja":"通信状態",
"922|ko":"전송 상태",
"922|pt-BR":"Status do transporte de rede",
"922|vi":"Trạng thái truyền tải mạng",
"922|zh-Hans":"传输状态",
"922|zh-Hant":"傳輸狀態",
"923|ar":"يؤدي تحديث آراء Pod وعرضها وتجميعها إلى قراءة حالة آراء Pod. وتُجمع عمليتا نشر الآراء وإعادة حساب بيانات التقارب أدناه ضمن العمليات المتقدمة.",
"923|es":"Actualizar, enumerar y agregar opiniones lee el estado de las opiniones del Pod. La publicación de opiniones y el recálculo de los datos de afinidad se agrupan a continuación como operaciones avanzadas.",
"923|fr":"L’actualisation, l’énumération et l’agrégation des avis consultent l’état des avis du Pod. La publication des avis et le recalcul des données d’affinité sont regroupés ci-dessous parmi les opérations avancées.",
"923|hi":"राय को रीफ़्रेश करने, सूचीबद्ध करने और एकत्र करने से Pod में राय की स्थिति पढ़ी जाती है। राय प्रकाशित करना और एफ़िनिटी डेटा की पुनर्गणना नीचे उन्नत कार्रवाइयों के रूप में रखी गई है।",
"923|ja":"意見の更新・一覧表示・集約では、Pod の意見状態を読み取ります。意見の公開と親和性データの再計算は、以下に高度な操作としてまとめられています。",
"923|vi":"Việc làm mới, liệt kê và tổng hợp ý kiến sẽ đọc trạng thái ý kiến của Pod. Việc công bố ý kiến và tính toán lại dữ liệu về mức độ tương hợp được nhóm bên dưới thành các thao tác nâng cao.",
"925|de":"Das Element „{itemType}“ lässt sich nicht löschen.",
"925|hi":"इस {itemType} को हटाना संभव नहीं है।",
"925|id":"Tidak dapat menghapus {itemType} ini.",
"926|ar":"افتح أداة العرض المرئي بملء الشاشة",
"926|de":"Visualizer im Vollbild öffnen",
"926|es":"Abrir el visualizador en pantalla completa",
"926|fr":"Ouvrir le visualiseur en plein écran",
"926|hi":"विज़ुअलाइज़र को फ़ुलस्क्रीन में खोलें",
"926|id":"Buka visualizer dalam layar penuh",
"926|ja":"ビジュアライザーを全画面表示にする",
"926|pt-BR":"Abrir o visualizador em tela cheia",
"926|vi":"Mở trình trực quan hóa ở chế độ toàn màn hình",
"927|hi":"इस SongID रन को खोलें और कतार में इसकी स्थिति, साक्ष्य और डाउनलोड विकल्पों पर नज़र रखें।",
}
HOLD_RANKS={910}
SOURCE_RATIONALES={
903:"The caller labels the global concurrency limit for uploads in Admin Policies.",
904:"The caller is a success message after a Library Health remediation job is queued; {count} is the reported count.",
905:"The caller is a Mesh statistics heading beside the active DHT connection count.",
906:"The caller identifies a Metadata Processing outcome when no audio fingerprint was produced.",
907:"The caller labels the scorecard count of distinct SongRec matches.",
908:"The caller is an error toast when MediaCore fails to get content metadata; {message} is the API error.",
909:"The caller is a Discovery shelf policy choice, meaning the item remains under review.",
910:"The caller splits the Enforce-mode signature instruction around an inline ed25519 code value and a second translation key.",
911:"The caller displays missing/total track counts in a Library Health album completeness reason.",
912:"The caller labels a mapped media-server path diagnostic followed by the path in code styling.",
913:"The caller is the tooltip for refreshing locally stored release-radar subscriptions and notifications.",
914:"The caller is an error toast when the pod opinion list request fails; {message} is the API error.",
915:"The caller labels the last error reported in the Tor status panel.",
916:"The caller labels pagination choices and the current page-size control; {count} is formatted for the active locale.",
917:"The caller explains a manual DHT lookup for a published ContentID descriptor and when to bypass cache for freshness.",
918:"The caller labels the second hexadecimal hash input beside the first hash value field.",
919:"The caller is the fallback error when saving a VPN policy fails.",
920:"The caller labels the signed metadata-correction evidence category in Mesh evidence policy.",
921:"The caller is a content identifier input placeholder with a concrete example identifier syntax.",
922:"The caller heads a network transport panel whose values include anonymity layer, Tor/I2P/direct mode, and failover.",
923:"The caller is an informational explanation that reading pod opinions is separate from publishing or recalculating affinity data.",
924:"The caller is the fallback API error for loading swarm visualization data.",
925:"The caller is a deletion error for either a file or directory; {itemType} is localized dynamically.",
926:"The caller is the accessible name of the visualizer action that enters browser fullscreen mode.",
927:"The caller is a tooltip for opening a SongID result run and tracking its queue position, evidence, and download options.",
}
CORRECTION_RATIONALES={
"903|vi":"The current Vietnamese word denotes an upload position, not a concurrency slot. This names the count of global upload slots.",
"907|ar":"This scorecard value counts distinct SongRec matches. The current label names distinctive SongRec without saying matches.",
"907|fr":"This scorecard value counts distinct SongRec matches. The current English adjective does not name the counted matches.",
"907|id":"Perbedaan means difference. This scorecard field counts unique SongRec matches.",
"907|ja":"The current label only says individual SongRec. This names the unique-match count shown by the caller.",
"907|pt-BR":"The current adjective can read as a distinct SongRec item. This names the distinct matches counted by the caller.",
"907|vi":"The current text says separate SongRec results but omits that these are matches and a count. This names the distinct match count.",
"912|fr":"In this media-server diagnostic, mapped is the path-mapping term. Mappé is the conventional technical rendering; cartographié suggests cartography.",
"918|ar":"This is the second hash-value input, not the act of hashing. The proposal names the value and preserves the B field label.",
"921|ar":"The input expects a Content ID. The proposal restores the protected literal ID and retains the exact example identifier syntax.",
"921|es":"The example is a literal Content ID syntax, not translatable prose. The proposal restores the protected ID and preserves every segment exactly.",
"921|hi":"The input label must retain the protected literal ID and the exact machine-readable example. The proposal does both.",
"921|id":"The example is a literal Content ID syntax, not translatable prose. The proposal preserves its segments and uses the protected ID label.",
"921|zh-Hans":"The example is a literal Content ID syntax. The proposal preserves its exact segments and the ID acronym.",
"921|zh-Hant":"The example is a literal Content ID syntax. The proposal preserves its exact segments and the ID acronym.",
"922|ar":"This panel describes network anonymity and transport modes, not physical transport. The proposal explicitly names network transport.",
"922|hi":"परिवहन स्थिति suggests physical transportation. This panel reports network transport, anonymity modes, and failover.",
"922|id":"Transportasi suggests physical transportation. This panel reports network transport, anonymity modes, and failover.",
"922|ja":"輸送状況 suggests physical shipping. This panel reports a network communication mode and failover.",
"922|ko":"운송현황 suggests physical shipping. This panel reports a data-transmission mode and failover.",
"922|pt-BR":"The current wording can suggest physical transport. The caller is a network transport status panel.",
"922|vi":"The current wording suggests physical shipment. The caller is a network transport status panel.",
"922|zh-Hans":"运输状况 suggests physical shipping. The caller reports data transport mode and failover.",
"922|zh-Hant":"運輸狀況 suggests physical shipping. The caller reports data transport mode and failover.",
"923|ar":"The current wording omits the Pod entity. The proposal restores it and keeps reading opinion state separate from publishing and affinity recalculation.",
"923|es":"The caller uses Pod as a product entity; grupo changes it to a generic group. The proposal restores Pod and keeps the read-only/advanced-operation distinction.",
"923|fr":"The current phrase la liste reads as a noun rather than the listing action. The proposal uses parallel action nouns and preserves Pod as the entity.",
"923|hi":"The current compound पॉड राय स्थिति is unclear. The proposal gives the read-only operations a natural sentence and preserves Pod as a product term.",
"923|ja":"The current リスト is an awkward noun in this action list. The proposal uses natural action nouns and preserves Pod as the product entity.",
"923|vi":"The current text changes Pod to a generic group and affinity to relationships. The proposal restores Pod and expresses affinity as compatibility.",
"925|de":"The dynamic type can be Datei (feminine) or Verzeichnis (neuter), so diese does not agree with both. The proposal uses a gender-neutral item construction.",
"925|hi":"The current sentence is subjectless. This neutral construction clearly says the dynamic file or directory cannot be deleted and keeps {itemType} intact.",
"925|id":"The current word order is unnatural. This places the dynamic item before ini while preserving the delete failure.",
"926|ar":"The current noun متخيل is not a natural label for the visualizer. The proposal names the visual display tool and its fullscreen mode.",
"926|de":"Geben Sie ... ein reads as data entry. This names opening the visualizer in fullscreen.",
"926|es":"This action opens the visualizer in fullscreen mode; the current wording can read as entering a full-screen tool.",
"926|fr":"This action switches the visualizer to fullscreen; the current wording only says to access a fullscreen viewer.",
"926|hi":"दर्ज करें means enter/input in this context. The proposal says to open the visualizer in fullscreen.",
"926|id":"The proposal makes clear that the visualizer opens in fullscreen mode.",
"926|ja":"入力してください means input/type. The proposal says to display the visualizer fullscreen.",
"926|pt-BR":"The proposal states the action as opening the visualizer in fullscreen mode.",
"926|vi":"Nhập means input/type. The proposal says to open the visualizer in fullscreen mode.",
"927|hi":"The current transliteration loses the exact SongID feature name and पालन करना is stiff for tracking status. The proposal preserves SongID and describes tracking the run details.",
}
HOLD_RATIONALE="The caller splits one complete Enforce-mode sentence into independently localized fragments around inline ed25519 code. The following fragment is separately translated after the code, so several locales cannot make natural word order by changing this fragment alone. Hold all 12 cells pending a single rich-text sentence or an interpolation that allows each locale to reorder the signature-format phrase."
SOURCE_REWRITE_RECOMMENDATIONS=[{
"recommendationId":"SR-910-01","continuationRank":910,"sourceId":"src_34419b72f6ec2d1e",
"sourceSha256":"34419b72f6ec2d1e09ce068a803ad0bac785f963bd4464efdbf948fe936af4a8",
"source":"In Enforce mode, signatures must use the",
"issue":"The sentence is split into three translation fragments around an inline code value. The second localized fragment begins with the word 'format'; locales that need the noun before the code cannot translate the fragments naturally.",
"recommendation":"Keep the instruction in one translatable rich-text sentence with the signature format supplied as a markup-safe interpolation. Render the interpolation in <code> while allowing each locale to position it grammatically.",
"relatedFragment":"format over the canonical join/leave payload and the supplied public key.",
"relatedFragmentSourceId":"src_16d9b529ed6a96b4","relatedFragmentSourceSha256":"16d9b529ed6a96b46e8c6ba91abc9a8013b7856793eb8fafbb700e6f2882a052",
"implemented":False
}]

def sha(b): return hashlib.sha256(b).hexdigest()
def ph(s): return collections.Counter(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}",s))
def tags(s): return collections.Counter(re.findall(r"</?[A-Za-z][^>]*>",s))
def nums(s): return ["".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in n) for n in re.findall(r"\d+",s)]
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
def rows(name): return [json.loads(x) for x in (INPUT/name).read_text(encoding="utf-8").splitlines() if x.strip()]
def write_rows(name, values):
    (ROOT/name).write_text("".join(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n" for v in values),encoding="utf-8")
def main():
    cells=rows("source-current-cells.jsonl"); caller_rows=rows("caller-contexts.jsonl"); callers={r["sourceId"]:r for r in caller_rows}
    if len(cells)!=300 or len(callers)!=25: raise SystemExit("REFUSED: candidate-free coverage")
    keys={f"{r['continuationRank']}|{r['locale']}" for r in cells}
    if set(PROPOSALS)-keys or {f"{r}|{l}" for r in HOLD_RANKS for l in LOCALES}-keys: raise SystemExit("REFUSED: decisions outside selected cells")
    ledger=[]; corrections=[]; review_holds=[]
    for cell in cells:
        rank,locale=cell["continuationRank"],cell["locale"]; caller=callers[cell["sourceId"]]; key=f"{rank}|{locale}"
        source,current=cell["source"],cell["currentTarget"]
        row={"schemaVersion":1,"reviewPass":"independent-primary","head":HEAD,"tree":TREE,"continuationRank":rank,
             "remainingQueueRank":cell["remainingQueueRank"],"sourceId":cell["sourceId"],"sourceSha256":cell["sourceSha256"],
             "locale":locale,"catalogPath":cell["catalogPath"],"catalogFileSha256":cell["catalogFileSha256"],"catalogGitBlob":cell["catalogGitBlob"],
             "currentTargetSha256":cell["currentTargetSha256"],"callerContextSha256":cell["callerContextSha256"],"callerRefs":cell["callerRefs"],
             "productionCallerCount":caller["productionCallerCount"],"source":source,"catalogKey":cell["catalogKey"],"currentTarget":current,
             "sourceTextIncluded":True,"currentTargetTextIncluded":True,"sourceRewriteRecommendation":None,
             "tokenCheck":token_check(source,current)}
        if rank in HOLD_RANKS:
            row.update({"disposition":"hold","confidence":"moderate","holdReasonCode":"SOURCE_FRAGMENT_ORDER_DEPENDENCY",
                "holdReasonSha256":sha(b"SOURCE_FRAGMENT_ORDER_DEPENDENCY"),"rationale":HOLD_RATIONALE,"sourceRewriteRecommendation":"SR-910-01"})
            review_holds.append(row)
        elif key in PROPOSALS:
            target=PROPOSALS[key]
            check=token_check(source,current,target)["proposal"]
            if not all((ph(source)==ph(target),tags(source)==tags(target),not_less(nums(source),nums(target)),all(t in target for t in prot(source)))):
                raise SystemExit(f"REFUSED: proposal token integrity {key}")
            row.update({"disposition":"correct","confidence":"moderate","rationale":CORRECTION_RATIONALES[key],"target":target,
                "targetSha256":sha(target.encode()),"proposalTokenCheck":check,"tokenCheck":token_check(source,current,target)})
            corrections.append(row)
        else:
            row.update({"disposition":"accept-current","confidence":"moderate","rationale":SOURCE_RATIONALES[rank]})
        ledger.append(row)
    if (len(ledger),len(corrections),len(review_holds))!=(300,43,12): raise SystemExit("REFUSED: primary decision coverage/count")
    if set(PROPOSALS)!= {f"{r['continuationRank']}|{r['locale']}" for r in corrections}: raise SystemExit("REFUSED: proposal decision mismatch")
    counts=collections.Counter(r["disposition"] for r in ledger)
    write_rows("primary-review.jsonl",ledger); write_rows("corrections.jsonl",corrections)
    write_rows("review-holds.jsonl",review_holds); write_rows("holds-hash-only.jsonl",[])
    (ROOT/"proposal-map.json").write_text(json.dumps(PROPOSALS,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (ROOT/"rationale-map.json").write_text(json.dumps({"accepted":{str(k):v for k,v in SOURCE_RATIONALES.items()},"corrections":CORRECTION_RATIONALES,"hold":HOLD_RATIONALE},ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (ROOT/"source-rewrite-recommendations.json").write_text(json.dumps({"schemaVersion":1,"recommendations":SOURCE_REWRITE_RECOMMENDATIONS},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    inp_manifest=(INPUT/"manifest.json").read_bytes(); inp_sums=(INPUT/"PACKET-SHA256SUMS.txt").read_bytes(); live=json.loads((INPUT/"live-after.json").read_text())
    selected=rows("source-inventory-selection.jsonl"); summaries=[]
    for r in corrections: summaries.append({"continuationRank":r["continuationRank"],"sourceId":r["sourceId"],"locale":r["locale"],"currentTargetSha256":r["currentTargetSha256"],"targetSha256":r["targetSha256"]})
    summary={"artifact":"slskdN PR #409 W81 independent primary semantic review","window":"W81","head":HEAD,"tree":TREE,
        "sourceCount":25,"localeCount":12,"cellCount":300,"dispositions":{k:counts.get(k,0) for k in ("accept-current","correct","hold")},
        "proposedTargetCount":len(corrections),"callerlessSources":sum(not x["productionCallerCount"] for x in caller_rows),
        "reviewHoldCount":len(review_holds),"hashOnlyHoldCount":0,"sourceRewriteRecommendationCount":len(SOURCE_REWRITE_RECOMMENDATIONS),
        "candidateFreeInputManifestSha256":sha(inp_manifest),"candidateFreeInputChecksumListSha256":sha(inp_sums),
        "selectionBoundarySha256":sha((INPUT/"selection-boundary.jsonl").read_bytes()),"sourceInventorySelectionSha256":sha((INPUT/"source-inventory-selection.jsonl").read_bytes()),
        "callerContextSha256":sha((INPUT/"caller-contexts.jsonl").read_bytes()),"sourceCurrentCellsSha256":sha((INPUT/"source-current-cells.jsonl").read_bytes()),
        "liveMainSha":live["liveMainSha"],"baseApiSha":live["baseRefOid"],"priorSelectedIdsExcluded":1982,"priorHeldCellsCarried":382,
        "priorHoldResolutionHistoryRows":13,"priorAppliedTargetsReattested":190,"w80AppliedTargets":81,"w80HoldsCarried":0,
        "priorHeldTargetsAllMatch":True,"priorHeldCallerEvidenceUnchanged":382,"blindReviewUsed":False,"crossReviewUsed":False,
        "nativeSpeakerSignoff":False,"browserReview":False,"prBodyQueried":False,"proposals":summaries,
        "heldCells":[{"continuationRank":r["continuationRank"],"sourceId":r["sourceId"],"locale":r["locale"],"holdReasonCode":r["holdReasonCode"]} for r in review_holds]}
    (ROOT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    readme=f"""# slskdN PR #409 W81 independent primary review

This packet reviews continuation ranks 903–927 and remaining-queue ranks 803–827: 25 source strings × 12 locales = 300 cells. The exact source head/tree are `{HEAD}` / `{TREE}`.

Primary decisions: {counts.get('accept-current',0)} accept-current, {len(corrections)} correction proposals, and {len(review_holds)} holds. All 25 selected strings have pinned production callers. The 43 proposals address terminology, protected `ID` and literal example preservation, network-context wording, and clear grammar errors. The 12 rank-910 cells are held because one instruction is split around an inline code value; a one-fragment translation cannot repair locale word order. One source rewrite recommendation records a rich-text/interpolation approach.

The review used only the sealed candidate-free input and pinned caller context; it did not use blind or cross-review output. Continuity reattests 1,982 earlier selected IDs, 382 active holds, 13 resolved-hold history rows, and 190 applied targets (including W80’s 81). No native-speaker signoff or browser review is claimed.

No catalogs, PR body, or remote state were changed. Run `python3 verify_primary.py --repo /path/to/pinned-clean-worktree` to verify the exact head, input linkage, decisions, targets, token evidence, live refs, and checksums.
"""
    (ROOT/"README.md").write_text(readme,encoding="utf-8")
    print(json.dumps({"result":"BUILT-PRIMARY-UNSEALED","head":HEAD,"tree":TREE,"decisions":summary["dispositions"],
        "proposals":len(corrections),"holds":len(review_holds),"sourceRewriteRecommendations":len(SOURCE_REWRITE_RECOMMENDATIONS),"blindReviewUsed":False,"crossReviewUsed":False},indent=2))
if __name__=="__main__": main()
