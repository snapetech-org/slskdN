#!/usr/bin/env python3
import hashlib,json,re,subprocess,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
O=Path(__file__).resolve().parent
I=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w65-ranks503-527-primary-20261103/input")
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def j(n): return json.loads((I/n).read_text(encoding="utf-8"))
def jl(n): return [json.loads(x) for x in (I/n).read_text(encoding="utf-8").splitlines() if x.strip()]
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def dump_lines(p,x): p.write_text("".join(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n" for r in x),encoding="utf-8")
def ph(s): return sorted(set(re.findall(r"\{[^{}]+\}",s)))
def tags(s): return sorted(re.findall(r"</?[A-Za-z][^>]*>",s))
def nums(s): return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)
def prot(s):
 f=set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])",s))
 for x in ("Wishlist","Soulseek","Discogs","Pod"):
  if re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",s): f.add(x)
 return sorted(f)
def tok(s): return {"placeholders":ph(s),"markup":tags(s),"numeric":nums(s),"protectedLiterals":prot(s)}
packet=subprocess.run([sys.executable,str(I/"verify_input.py")],capture_output=True,text=True)
if packet.returncode: raise SystemExit(packet.stdout+packet.stderr)
if {p.name for p in O.iterdir() if p.is_file()}!={"build_primary.py","verify_primary.py"}: raise SystemExit("Output directory is not clean")
im=j("manifest.json"); cells=jl("source-current-cells.jsonl"); contexts=jl("caller-contexts.jsonl")
cx={x["continuationRank"]:x for x in contexts}
D={}
def add(rank,locales,dis,target,why,conf="high"):
 for locale in locales: D[(rank,locale)]=(dis,target,why,conf)
add(503,["hi"],"correction","इसका ग्राफ़ प्राप्त करने के लिए ContentID दर्ज करें","Preserves exact ContentID spelling in the graph input placeholder.")
add(504,["ar","de","es","fr","hi","pt-BR"],"hold",None,"Caller taxonomy separates recording-subject from WorkRef identity and alias-subject but does not define whether recording subject means identity or subject; retain current pending glossary context.","low")
add(507,["hi"],"correction","ज़रूर बाहर रखें (स्पेस से अलग)","Current wording means something should be removed; this filter label requires explicit exclusion.")
add(509,["ar"],"refinement","تم تجاهل إشارات الجودة المحلية","Clarifies local as the application's local source context in the ranking override.","moderate")
add(509,["hi"],"refinement","स्थानीय गुणवत्ता संकेतों को अनदेखा किया गया","Clarifies local as the application's local source context in the ranking override.","moderate")
add(509,["ja"],"correction","ローカル品質シグナルは無視されます","Avoids 地元, which means geographic hometown rather than local source context.")
add(509,["ko"],"correction","로컬 품질 신호 무시","Avoids 지역, which suggests a geographic region rather than local source context.")
add(509,["vi"],"correction","Tín hiệu chất lượng cục bộ bị bỏ qua","Avoids địa phương, which suggests geographic locality rather than local source context.")
add(511,["ar"],"correction","أنشئ قناة في هذا pod بالاسم الذي أدخلته.","Repairs Arabic word order while preserving caller pod terminology and channel action.")
add(512,["hi"],"correction","VPN गेटवे:","Keeps the protected VPN acronym intact in this capability label.")
add(515,["fr"],"correction","Rapport sur la santé de la bibliothèque","Repairs the ungrammatical French noun sequence for the generated report title.")
add(515,["ja"],"correction","ライブラリ健全性レポート","Uses natural software-library terminology for the generated media-library health report.","moderate")
for loc,target in [("ar","حجم واجهة المستخدم للرسائل (UI)"),("de","Größe der Nachrichten-Benutzeroberfläche (UI)"),("es","Tamaño de la interfaz de usuario de mensajes (UI)"),("fr","Taille de l'interface utilisateur des messages (UI)"),("hi","संदेश UI का आकार"),("pt-BR","Tamanho da UI de mensagens"),("vi","Kích thước giao diện tin nhắn (UI)"),("zh-Hans","消息界面大小（UI）"),("zh-Hant","訊息介面大小（UI）")]:
 add(516,[loc],"correction",target,"Preserves protected UI in the message display-size control label.")
for loc,target,why in [
 ("ar","عنوان URL للخادم","Uses natural Arabic ordering while retaining protected URL."),
 ("es","URL del servidor","Uses natural Spanish ordering for the server URL label."),
 ("fr","URL du serveur","Uses natural French ordering for the server URL label."),
 ("pt-BR","URL do servidor","Uses natural Brazilian Portuguese ordering for the server URL label."),
 ("vi","URL máy chủ","Uses natural Vietnamese ordering for the server URL label.")]:
 add(517,[loc],"correction",target,why)
for loc,dis,target in [
 ("ar","correction","مسار التنزيلات المكتملة على slskdN"),
 ("de","refinement","Pfad für abgeschlossene Downloads auf slskdN"),
 ("es","correction","Ruta de las descargas completadas en slskdN"),
 ("fr","correction","Chemin des téléchargements terminés sur slskdN"),
 ("hi","correction","slskdN पर पूर्ण हो चुके डाउनलोड का पथ"),
 ("id","correction","Jalur untuk unduhan yang telah selesai di slskdN"),
 ("ja","refinement","slskdNで完了したダウンロードのパス"),
 ("pt-BR","refinement","Caminho dos downloads concluídos no slskdN"),
 ("vi","correction","Đường dẫn lưu các nội dung đã tải xong trên slskdN"),
 ("zh-Hans","correction","slskdN 上已完成下载的路径"),
 ("zh-Hant","correction","slskdN 上已完成下載的路徑")]:
 add(518,[loc],dis,target,"Clarifies the server-side path for completed downloads.","moderate" if dis=="refinement" else "high")
add(519,["zh-Hans"],"correction","API 密钥","Uses the standard Chinese term for an API key, not a physical key.")
add(519,["zh-Hant"],"correction","API 金鑰","Uses the standard Traditional Chinese term for an API key, not a physical key.")
add(522,["de"],"refinement","Registriert","Uses the standard provider registration status label.","moderate")
add(522,["hi"],"correction","पंजीकृत","Replaces an awkward verb phrase with a concise registered-status label.")
add(522,["ko"],"correction","등록됨","Replaces the registry or registered-mail sense with registered status.")
add(522,["vi"],"correction","Đã đăng ký","Expresses completed provider registration status.")
add(522,["zh-Hans"],"correction","已注册","Replaces the registered-mail sense with the provider's registered status.")
add(522,["zh-Hant"],"correction","已註冊","Replaces the registered-mail sense with the provider's registered status.")
for loc,target in [
 ("ar","تم تحديث عنصر Wishlist"),("de","Wishlist-Eintrag aktualisiert"),("es","Elemento de Wishlist actualizado"),
 ("fr","Élément de la Wishlist mis à jour"),("hi","Wishlist आइटम अपडेट किया गया"),("ja","Wishlist の項目を更新しました"),
 ("ko","Wishlist 항목이 업데이트되었습니다"),("pt-BR","Item de Wishlist atualizado"),("vi","Đã cập nhật mục trong Wishlist"),
 ("zh-Hans","Wishlist 项目已更新"),("zh-Hant","Wishlist 項目已更新")]:
 add(523,[loc],"correction",target,"Preserves protected Wishlist in the success toast.")
add(525,["id"],"refinement","Ketahanan terhadap penyensoran","Uses the Indonesian term for censorship rather than the homograph for sensor.","moderate")
for loc,target in [
 ("es","Tiempo promedio de firma:"),("hi","औसत हस्ताक्षर समय:"),("id","Rata-rata waktu penandatanganan:"),
 ("pt-BR","Tempo médio de assinatura:"),("vi","Thời gian ký trung bình:")]:
 add(526,[loc],"correction",target,"Uses signature/signing terminology in the cryptographic timing-statistics context.")
for loc,target,why in [
 ("de","Entdeckungsregal öffnen","Changes the adjective-like label into the requested button action."),
 ("es","Abrir estante de descubrimiento","Changes the adjective-like label into the requested button action."),
 ("fr","Ouvrir l’étagère de découverte","Changes the adjective-like label into the requested button action."),
 ("ja","ディスカバリーシェルフを開く","Uses an imperative action label instead of a transliteration of open."),
 ("ko","디스커버리 선반 열기","Uses discovery-shelf terminology instead of search-shelf terminology."),
 ("pt-BR","Abrir estante de descoberta","Changes the adjective-like label into the requested button action.")]:
 add(527,[loc],"correction",target,why)

why={
503:"Current instruction is clear for the ContentID graph input.",504:"Current rendering preserves recording-subject, but the caller taxonomy does not define identity versus subject.",505:"Current action label is clear and retains the search-name placeholder.",506:"Clear connection status in the service-state labels.",507:"Clearly names the space-separated exclusion filter.",508:"Accurately labels completed search, job, or transfer status.",509:"Conveys ignored quality signals in the local ranking override.",510:"Concise section heading for semantic zoom.",511:"Describes creating a named channel in the pod.",512:"Clearly labels the VPN gateway capability.",513:"Accurately names the MusicBrainz lookup section.",514:"Plausible discography coverage label; caller shows a mission label but not its detailed state.",515:"Accurately names the generated library-health report.",516:"Clearly labels the message display-size control.",517:"Clearly labels the server URL input.",518:"Identifies the completed-download path field used for server-side path mapping.",519:"Accurately labels an API key in integration and settings forms.",520:"Accurately labels the database-size statistic.",521:"Clearly says authentication is required and the page should be refreshed.",522:"Communicates the provider's registered state.",523:"Clearly reports that a Wishlist item was updated.",524:"Preserves the deduplication interval and count placeholder.",525:"Accurately labels the capability of resisting censorship.",526:"Conveys average cryptographic signing time in paired timing statistics.",527:"Gives a clear action for opening the player discovery shelf."}
rows=[]
for c in cells:
 rank,loc=c["continuationRank"],c["locale"]
 dis,target,rationale,conf=D.get((rank,loc),("accept-current",None,why[rank],"moderate" if rank in (504,514,518) else "high"))
 reviewed=target if dis in ("correction","refinement") else c["currentTarget"]
 st,ct,rt=tok(c["source"]),tok(c["currentTarget"]),tok(reviewed)
 checks={"placeholdersPreserved":st["placeholders"]==rt["placeholders"],"markupPreserved":st["markup"]==rt["markup"],"numericTokensPreserved":st["numeric"]==rt["numeric"],"protectedLiteralsPreserved":all(x in reviewed for x in st["protectedLiterals"])}
 if not all(checks.values()): raise SystemExit(f"token failure {(rank,loc)} {checks}")
 ctx=cx[rank]
 r={"schema":"slskdn-primary-cell-review/v1","repository":im["repository"],"pullRequest":im["pullRequest"],"window":"W65","head":im["head"],"tree":im["tree"],
 "continuationRank":rank,"remainingQueueRank":c["remainingQueueRank"],"sourceId":c["sourceId"],"source":c["source"],"sourceSha256":c["sourceSha256"],
 "locale":loc,"catalogKey":c["catalogKey"],"catalogPath":c["catalogPath"],"catalogFileSha256":c["catalogFileSha256"],"catalogGitBlob":c["catalogGitBlob"],
 "currentTarget":c["currentTarget"],"currentTargetSha256":c["currentTargetSha256"],"callerContextSha256":c["callerContextSha256"],"callerRefs":c["callerRefs"],
 "callerContextSourceId":ctx["sourceId"],"callerContextSourceSha256":ctx["sourceSha256"],"callerContexts":ctx["callers"],
 "containsCandidate":False,"verdict":None,"disposition":dis,"rationale":rationale,"confidence":conf,"reviewedTargetSha256":sha(reviewed),
 "tokenAudit":{"source":st,"current":ct,"reviewed":rt,"checks":checks}}
 if dis in ("correction","refinement"): r["proposedTarget"]=target
 rows.append(r)
assert set(D)=={(r["continuationRank"],r["locale"]) for r in rows if r["disposition"]!="accept-current"}
dump_lines(O/"primary-ledger.jsonl",rows)
counts=Counter(r["disposition"] for r in rows); base=Counter(); final=Counter()
for r in rows:
 st,ct=tok(r["source"]),tok(r["currentTarget"])
 review=r["proposedTarget"] if r["disposition"] in ("correction","refinement") else r["currentTarget"]; rt=tok(review)
 base["placeholder"]+=st["placeholders"]!=ct["placeholders"]; base["markup"]+=st["markup"]!=ct["markup"]
 base["numeric"]+=st["numeric"]!=ct["numeric"]; base["protectedLiteral"]+=not all(x in r["currentTarget"] for x in st["protectedLiterals"])
 final["placeholder"]+=st["placeholders"]!=rt["placeholders"]; final["markup"]+=st["markup"]!=rt["markup"]
 final["numeric"]+=st["numeric"]!=rt["numeric"]; final["protectedLiteral"]+=not all(x in review for x in st["protectedLiterals"])
assert counts==Counter({"accept-current":227,"correction":60,"refinement":7,"hold":6})
assert dict(base)==im["baselineTokenMismatchSummary"] and not any(final.values())
summary={"schemaVersion":1,"repository":im["repository"],"pullRequest":im["pullRequest"],"window":"W65","head":im["head"],"tree":im["tree"],
"sourceCount":25,"localeCount":12,"cellCount":300,"dispositionCounts":dict(counts),"proposalCount":67,
"holdCells":[{"continuationRank":r["continuationRank"],"locale":r["locale"],"source":r["source"],"rationale":r["rationale"]} for r in rows if r["disposition"]=="hold"],
"baselineTokenMismatches":dict(base),"reviewedTokenMismatches":dict(final),"priorHeldCellsReattested":98,"callerlessSelectedRanks":[],
"candidateFreeInputVerified":True,"blindPacketAccessed":False,"repositoryOrPRFilesEdited":False,"nativeSpeakerReview":"not performed","browserReview":"not performed"}
dump(O/"summary.json",summary)
(O/"input-verification.txt").write_text("Candidate-free input verifier ran before ledger construction.\n\n"+packet.stdout,encoding="utf-8")
(O/"README.md").write_text("# slskdN PR #409 W65 primary semantic review\n\nThis sealed ledger reviews ranks 503–527 (25 sources × 12 locales = 300 cells) against candidate-free input at head "+im["head"]+" and tree "+im["tree"]+". Each row binds the source and target to pinned catalog provenance and exact caller context. Only correction/refinement rows carry proposedTarget; accept-current and hold rows retain currentTarget.\n\nThe candidate-free input verifier ran before ledger creation and is rerun by verify_primary.py. Checksums and manifest pin all files. No blind packet was accessed; no repository or PR files were edited. Native-speaker and browser review were not performed. Six recording-subject cells remain on hold pending glossary context.\n\nRun python3 verify_primary.py here to verify input, row bindings, token preservation, manifest hashes, and checksums.\n",encoding="utf-8")
m={"schemaVersion":1,"artifact":"slskdN PR #409 W65 primary semantic review ledger","reviewType":"primary-semantic","sealed":True,"candidateFreeInput":True,
"repository":im["repository"],"pullRequest":im["pullRequest"],"branch":im["branch"],"window":"W65","head":im["head"],"tree":im["tree"],
"sourceCount":25,"localeCount":12,"cellCount":300,"locales":im["locales"],"inputPath":str(I),
"inputManifestSha256":sha((I/"manifest.json").read_bytes()),"inputChecksumListSha256":sha((I/"PACKET-SHA256SUMS.txt").read_bytes()),
"priorHeldCellsReattested":98,"dispositionCounts":dict(counts),"proposalCount":67,"blindPacketAccessed":False,
"nativeSpeakerReview":"not performed","browserReview":"not performed","createdAtUtc":datetime.now(timezone.utc).isoformat()}
m["files"]=[{"path":p.name,"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for p in sorted(O.iterdir()) if p.is_file() and p.name not in ("manifest.json","SHA256SUMS.txt")]
dump(O/"manifest.json",m)
paths=sorted(p for p in O.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt")
(O/"SHA256SUMS.txt").write_text("".join(f"{sha(p.read_bytes())}  {p.name}\n" for p in paths),encoding="utf-8")
print(json.dumps({"built":True,"output":str(O),"rows":len(rows),"counts":dict(counts),"files":[x["path"] for x in m["files"]]},ensure_ascii=False,indent=2))
