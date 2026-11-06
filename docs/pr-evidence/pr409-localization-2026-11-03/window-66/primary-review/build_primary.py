#!/usr/bin/env python3
import hashlib,json,re,subprocess,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
I=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w66-ranks528-552-primary-20261103/input")
O=Path(__file__).resolve().parent
def sha(b): return hashlib.sha256(b if isinstance(b,bytes) else b.encode()).hexdigest()
def j(p): return json.loads(p.read_text(encoding="utf-8"))
def jl(p): return [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s.strip()]
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def dumpjl(p,rs): p.write_text("".join(json.dumps(r,ensure_ascii=False,separators=(",",":"))+"\n" for r in rs),encoding="utf-8")
def ph(s): return sorted(set(re.findall(r"\{[^{}]+\}",s)))
def tags(s): return sorted(re.findall(r"</?[A-Za-z][^>]*>",s))
def nums(s): return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)
def prot(s):
    found=set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])",s))
    for x in ("Wishlist","Soulseek","Discogs","Pod"):
        if re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",s): found.add(x)
    return sorted(found)
def tok(s): return {"placeholders":ph(s),"markup":tags(s),"numeric":nums(s),"protectedLiterals":prot(s)}
def add(rank,locales,dis,target,why,conf="high"):
    for locale in locales: D[(rank,locale)]=(dis,target,why,conf)
im=j(I/"manifest.json")
if im["head"]!="c258a11d25a5cffc82b6b7cb2964d8f57b8eeac1": raise SystemExit("unexpected candidate-free input head")
subprocess.run([sys.executable,str(I/"verify_input.py")],check=True,capture_output=True,text=True)
cells=jl(I/"source-current-cells.jsonl"); contexts=jl(I/"caller-contexts.jsonl")
assert len(cells)==300 and len(contexts)==25
cx={x["continuationRank"]:x for x in contexts}
D={}
# Callerless rows remain held until an exact live production path is located.
for rank in (533,541):
    src=next(x for x in cells if x["continuationRank"]==rank)["source"]
    add(rank,im["locales"],"hold",None,
        "No exact production caller is pinned for this source at the live PR head; preserve the current value until a production use is established.","low")
# Source-bound terminology and language corrections/refinements from the pinned callers.
add(530,["id"],"correction","Hapus metadata Pod ini dari DHT agar tidak lagi muncul dalam pencarian. Gunakan ini jika Anda ingin menarik sebuah entri.",
    "The exact tooltip describes withdrawing a published Pod listing; daftar means a list, not the listing entry being withdrawn.")
add(534,["ar"],"correction","معروفة بالفعل",
    "The nested toast status refers to the message (رسالة), a feminine noun; use feminine agreement.")
add(534,["pt-BR"],"correction","Já conhecida",
    "The nested toast status refers to mensagem, a feminine noun in Brazilian Portuguese.")
add(535,["ar"],"correction","معرّف المحتوى (ID)",
    "The table header and input label refer to the content identifier; retain the protected ID acronym.")
add(535,["es"],"correction","ID de contenido",
    "The table header and input label refer to an identifier; retain the protected ID acronym.")
add(535,["hi"],"correction","सामग्री ID",
    "The table header and input label refer to an identifier; retain the protected ID acronym.")
add(536,["ar"],"correction","عدد محاولات إعادة إرسال خطاف الويب",
    "This is a numeric webhook retry-attempt setting. Match the neighboring Arabic Webhook target URL terminology and express the retry count.")
add(536,["es"],"refinement","Número de reintentos del webhook",
    "The caller is a numeric configuration field; make the retry count explicit rather than repeating intentos de reintento.")
add(536,["fr"],"refinement","Nombre de tentatives de réessai du webhook",
    "The caller is a numeric configuration field; name the retry count directly.")
add(536,["hi"],"correction","Webhook के पुनः प्रयासों की संख्या",
    "The current value repeats the attempt term. This numeric field needs the number of webhook retries.")
add(536,["id"],"correction","Jumlah percobaan ulang webhook",
    "The current value repeats the attempt term. This numeric field needs the webhook retry count.")
add(536,["ja"],"refinement","Webhook の再試行回数",
    "The caller is a numeric configuration field; specify the number of webhook retries.")
add(536,["ko"],"correction","웹훅 재시도 횟수",
    "The caller is a numeric configuration field; specify the number of webhook retries.")
add(536,["pt-BR"],"refinement","Número de tentativas de reenvio do webhook",
    "The caller is a numeric configuration field; clarify that this is the webhook retry count.")
add(536,["vi"],"refinement","Số lần thử lại webhook",
    "The caller is a numeric configuration field; state the number of webhook retries.")
add(536,["zh-Hans"],"refinement","Webhook 重试次数",
    "The caller is a numeric configuration field; state the number of webhook retries.")
add(536,["zh-Hant"],"refinement","Webhook 重試次數",
    "The caller is a numeric configuration field; state the number of webhook retries.")
add(538,["es"],"refinement","en la configuración antes de la operación a largo plazo.",
    "The exact caller appends this fragment after the DHT setting; the definite article makes the Spanish configuration reference grammatical.")
add(539,["ar"],"correction","ملخص:",
    "This is a generated report section heading; remove the space before the colon.")
add(539,["de"],"correction","Zusammenfassung:",
    "This is a generated report section heading; German punctuation has no space before the colon.")
add(539,["hi"],"correction","सारांश:",
    "This is a generated report section heading; सारांश names a summary directly instead of saying in brief.")
add(539,["id"],"correction","Ringkasan:",
    "This is a report heading; Ringkasan means summary, while Kesimpulannya reads as in conclusion.")
add(539,["ko"],"correction","요약:",
    "This is a generated report section heading; use the direct heading rather than the content of a summary.")
add(539,["vi"],"correction","Tóm tắt:",
    "This is a report section heading; Tóm tắt directly names the summary.")
add(539,["pt-BR"],"refinement","Resumo:",
    "Use the concise section-heading form in this generated report.")
add(540,["de"],"correction","Adversarial-Einstellungen wurden erfolgreich aktualisiert",
    "This is the named security settings group; retain Adversarial consistently with the component's Adversarial-Funktionen wording.")
add(540,["fr"],"correction","Paramètres adversariaux mis à jour avec succès",
    "The caller is the security settings page. Contradictoires means contradictory, not adversarial.")
add(540,["pt-BR"],"correction","Configurações adversárias atualizadas com sucesso",
    "The security settings page uses adversarial as a feature category; the current phrase says settings of an adversary.")
add(542,["de"],"refinement","Erweiterte Optionen für die ContentID-Registrierung",
    "This details summary opens registration form controls; Optionen is clearer than Kontrollen, which can mean checks.")
add(542,["hi"],"correction","उन्नत ContentID पंजीकरण विकल्प",
    "The details summary opens form controls and the protocol identifier must retain exact ContentID spelling.")
add(545,["ja"],"refinement","このコレクション項目をブラウザプレーヤーで再生します。",
    "This is a player tooltip; remove the unnatural space inside the Japanese collection-item and browser-player compounds.")
add(545,["pt-BR"],"correction","Reproduza este item da coleção no player do navegador.",
    "This is a media-player tooltip; reproduza is the natural verb for playing an audio item, while jogue suggests playing a game.")
add(545,["vi"],"refinement","Phát mục này trong bộ sưu tập bằng trình phát trên trình duyệt.",
    "This is a media-player tooltip; clarify the browser player relationship and avoid the redundant trình phát trình duyệt construction.")
add(548,["hi"],"correction","चुनें कि अंतर्निहित MilkDrop के दूसरे प्रीसेट पर जाने से पहले कितनी पहचानी गई बास बीट्स बीतनी चाहिए।",
    "This describes the built-in visualizer mode; preserve the proper name MilkDrop and translate native as built-in, not indigenous.")
add(549,["ja"],"refinement","現在のサーバー側スキャンの状態確認を再開します。これによって二回目のスキャンが開始されることはありません。",
    "The source spells out second; use the natural Japanese ordinal 二回目 and keep the promise that no additional scan starts.")
add(549,["pt-BR"],"correction","Retomar as verificações de status da varredura atual no servidor. Isso não inicia uma segunda varredura.",
    "The caller is monitoring a server-side library scan; verificação do servidor suggests a server check instead of a scan.")
add(550,["pt-BR"],"correction","Falha na marcação automática ({exceptionType})",
    "The caller parses an Auto-tagging failure; codificação means encoding, not assigning metadata tags.")
add(551,["hi"],"correction","संपर्क लोड नहीं किए जा सके",
    "Correct the spelling of किए in this contacts-load error.")
# Gold Star Club is a named, irreversible pod-membership feature; preserve its exact English feature name.
for loc,target in [
 ("ar","إلغاء Gold Star"),("es","Revocar Gold Star"),("fr","Révoquer Gold Star"),
 ("hi","Gold Star रद्द करें"),("id","Cabut Gold Star"),("ja","Gold Star を取り消す"),
 ("ko","Gold Star 취소"),("pt-BR","Revogar Gold Star"),("vi","Thu hồi Gold Star"),
 ("zh-Hans","撤销 Gold Star"),("zh-Hant","撤銷 Gold Star")]:
    add(552,[loc],"correction",target,
        "The exact caller branches on the Gold Star Club membership state; Gold Star is the named feature in the product documentation and adjacent confirmation copy.")
why={
528:"A MediaCore form label for pixel bytes; current target preserves the explanatory range and caller data format.",
529:"The Dashboard page heading for the transfer overview.",
530:"A destructive MediaCore tooltip for removing this node's metadata from the discovery DHT.",
531:"The Contacts page's fallback message when invite creation fails.",
532:"A text field label and placeholder for entering an artist's name.",
533:"No exact production caller is pinned for this source at the live PR head; keep the value on hold.",
534:"The status in a toast that reports whether a message was newly registered or already known.",
535:"A table header and form label for a content identifier.",
536:"A numeric administrator configuration field for the number of webhook retries.",
537:"A toggle for allowing directory listeners to stream from this node over the mesh.",
538:"The final sentence fragment in a Network warning that follows the dht.lan_only configuration snippet.",
539:"A section heading in the generated library health report.",
540:"A success message after saving the security page's adversarial settings.",
541:"No exact production caller is pinned for this source at the live PR head; keep the value on hold.",
542:"An expandable details summary above advanced local ContentID registry form controls.",
543:"A success heading shown after updating VPN gateway configuration.",
544:"A MediaCore tooltip describing updating a selected descriptor in the DHT.",
545:"A player tooltip explaining the action that plays a collection item in the browser player.",
546:"A footer accessibility label for combined upload and download transfer speed.",
547:"A label for the total mapping count in the ContentID registry report.",
548:"A player tooltip for the native MilkDrop beat-trigger preset setting.",
549:"A player tooltip explaining that status polling resumes for the current server-side scan without starting another scan.",
550:"A stable failure template for Auto-tagging that keeps the exception type placeholder.",
551:"A Contacts page heading for the load-error state.",
552:"A membership-state button that revokes the named Gold Star feature."
}
rows=[]
for c in cells:
    rank,loc=c["continuationRank"],c["locale"]
    dis,target,rationale,conf=D.get((rank,loc),("accept-current",None,why[rank],"high"))
    reviewed=target if dis in ("correction","refinement") else c["currentTarget"]
    st,ct,rt=tok(c["source"]),tok(c["currentTarget"]),tok(reviewed)
    checks={"placeholdersPreserved":st["placeholders"]==rt["placeholders"],
      "markupPreserved":st["markup"]==rt["markup"],"numericTokensPreserved":st["numeric"]==rt["numeric"],
      "protectedLiteralsPreserved":all(x in reviewed for x in st["protectedLiterals"])}
    if not all(checks.values()): raise SystemExit(f"token failure {(rank,loc)} {checks} source={c['source']!r} target={reviewed!r}")
    ctx=cx[rank]
    r={"schema":"slskdn-primary-cell-review/v1","repository":im["repository"],"pullRequest":im["pullRequest"],
      "window":"W66","head":im["head"],"tree":im["tree"],"continuationRank":rank,"remainingQueueRank":c["remainingQueueRank"],
      "sourceId":c["sourceId"],"source":c["source"],"sourceSha256":c["sourceSha256"],"locale":loc,
      "catalogKey":c["catalogKey"],"catalogPath":c["catalogPath"],"catalogFileSha256":c["catalogFileSha256"],
      "catalogGitBlob":c["catalogGitBlob"],"currentTarget":c["currentTarget"],"currentTargetSha256":c["currentTargetSha256"],
      "callerContextSha256":c["callerContextSha256"],"callerRefs":c["callerRefs"],
      "callerContextSourceId":ctx["sourceId"],"callerContextSourceSha256":ctx["sourceSha256"],"callerContexts":ctx["callers"],
      "containsCandidate":False,"verdict":None,"disposition":dis,"rationale":rationale,"confidence":conf,
      "reviewedTargetSha256":sha(reviewed),"tokenAudit":{"source":st,"current":ct,"reviewed":rt,"checks":checks}}
    if dis in ("correction","refinement"): r["proposedTarget"]=target
    rows.append(r)
assert set(D)=={(r["continuationRank"],r["locale"]) for r in rows if r["disposition"]!="accept-current"}
dumpjl(O/"primary-ledger.jsonl",rows)
counts=Counter(r["disposition"] for r in rows)
base=Counter(); final=Counter()
for r in rows:
    st,ct=tok(r["source"]),tok(r["currentTarget"])
    target=r.get("proposedTarget",r["currentTarget"]); rt=tok(target)
    base["placeholder"]+=st["placeholders"]!=ct["placeholders"]
    base["markup"]+=st["markup"]!=ct["markup"]
    base["numeric"]+=st["numeric"]!=ct["numeric"]
    base["protectedLiteral"]+=not all(x in r["currentTarget"] for x in st["protectedLiterals"])
    final["placeholder"]+=st["placeholders"]!=rt["placeholders"]
    final["markup"]+=st["markup"]!=rt["markup"]
    final["numeric"]+=st["numeric"]!=rt["numeric"]
    final["protectedLiteral"]+=not all(x in target for x in st["protectedLiterals"])
assert base==Counter(im["baselineTokenMismatchSummary"])
assert not any(final.values()),dict(final)
assert all((r["continuationRank"] in (533,541))==(r["disposition"]=="hold") for r in rows)
proposal_count=sum(r["disposition"] in ("correction","refinement") for r in rows)
summary={"schemaVersion":1,"repository":im["repository"],"pullRequest":im["pullRequest"],"window":"W66",
 "head":im["head"],"tree":im["tree"],"sourceCount":25,"localeCount":12,"cellCount":300,
 "dispositionCounts":dict(counts),"proposalCount":proposal_count,"holdCells":[
  {"continuationRank":r["continuationRank"],"locale":r["locale"],"source":r["source"],"rationale":r["rationale"]}
  for r in rows if r["disposition"]=="hold"],"baselineTokenMismatches":dict(base),"reviewedTokenMismatches":dict(final),
 "priorHeldCellsReattested":104,"callerlessSelectedRanks":[533,541],"candidateFreeInputVerified":True,
 "blindPacketAccessed":False,"repositoryOrPRFilesEdited":False,"nativeSpeakerReview":"not performed",
 "browserReview":"not performed"}
dump(O/"summary.json",summary)
(O/"input-verification.txt").write_text("Candidate-free W66 input verifier ran before ledger construction.\n\n"+subprocess.check_output([sys.executable,str(I/"verify_input.py")],text=True),encoding="utf-8")
(O/"README.md").write_text("# slskdN PR #409 W66 primary semantic review\n\nThis sealed primary ledger reviews continuation ranks 528–552 (remaining-queue ranks 428–452), 25 sources and 300 locale cells, at exact live PR head "+im["head"]+" / tree "+im["tree"]+". The candidate-free input binds every current target to ordered locale-catalog hashes and exact production-caller context.\n\nDisposition counts: "+", ".join(f"{k}: {v}" for k,v in sorted(counts.items()))+". Proposed target rows: "+str(proposal_count)+". The 104 earlier holds were reattested at this exact head. All selected cells pass placeholder, markup, numeric, and protected-literal checks after proposed edits. The callerless Validation failed and Release Calendar rows remain held in all locales.\n\nNo blind packet was accessed and no repository/PR files were edited. Headed-browser and qualified native-speaker review were not performed. Run python3 verify_primary.py in this folder to check the ledger and checksums.\n",encoding="utf-8")
m={"schemaVersion":1,"artifact":"slskdN PR #409 W66 primary semantic review ledger","reviewType":"primary-semantic",
 "sealed":True,"candidateFreeInput":True,"repository":im["repository"],"pullRequest":im["pullRequest"],"branch":im["branch"],
 "window":"W66","head":im["head"],"tree":im["tree"],"sourceCount":25,"localeCount":12,"cellCount":300,
 "locales":im["locales"],"inputPath":str(I),"inputManifestSha256":sha((I/"manifest.json").read_bytes()),
 "inputChecksumListSha256":sha((I/"PACKET-SHA256SUMS.txt").read_bytes()),"priorHeldCellsReattested":104,
 "dispositionCounts":dict(counts),"proposalCount":proposal_count,"blindPacketAccessed":False,
 "nativeSpeakerReview":"not performed","browserReview":"not performed","createdAtUtc":datetime.now(timezone.utc).isoformat()}
m["files"]=[{"path":p.name,"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())}
 for p in sorted(O.iterdir()) if p.is_file() and p.name not in ("manifest.json","SHA256SUMS.txt")]
dump(O/"manifest.json",m)
paths=sorted(p for p in O.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt")
(O/"SHA256SUMS.txt").write_text("".join(f"{sha(p.read_bytes())}  {p.name}\n" for p in paths),encoding="utf-8")
print(json.dumps({"built":True,"head":im["head"],"tree":im["tree"],"rows":len(rows),"dispositions":dict(counts),
 "proposalCount":proposal_count,"holdRows":len(summary["holdCells"]),"baselineTokenMismatches":dict(base),
 "reviewedTokenMismatches":dict(final),"files":len(paths)},ensure_ascii=False,indent=2))
