#!/usr/bin/env python3
import hashlib,json,re,subprocess,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

TASK=Path(__file__).resolve().parent
I=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w70-ranks628-652-candidate-free-20261103/input")
O=TASK/"primary-review"
HEAD="335a96a9ec125b30c20c31be219da4e27db1ab03"; TREE="7168de556608115be3b7e16b9ceb30b977df904b"
BRANCH="codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode("utf-8")).hexdigest()
def j(p): return json.loads(p.read_text(encoding="utf-8"))
def jl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
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
def checks(source,target):
 a,b=tok(source),tok(target)
 return {"placeholdersPreserved":a["placeholders"]==b["placeholders"],"markupPreserved":a["markup"]==b["markup"],"numericTokensPreserved":a["numeric"]==b["numeric"],"protectedLiteralsPreserved":all(target.count(x)>=source.count(x) for x in a["protectedLiterals"])}
if O.exists() and any(O.iterdir()): raise SystemExit(f"refusing to overwrite {O}")
O.mkdir(parents=True,exist_ok=True)
im=j(I/"manifest.json")
if (im["head"],im["tree"],im["continuationRankRange"],im["remainingQueueRankRange"])!=(HEAD,TREE,[628,652],[528,552]): raise SystemExit("candidate-free exact head/window mismatch")
verified=subprocess.run([sys.executable,str(I/"verify_input.py")],check=True,capture_output=True,text=True)
subprocess.run(["sha256sum","-c","PACKET-SHA256SUMS.txt"],cwd=I,check=True,capture_output=True,text=True)
cells=jl(I/"source-current-cells.jsonl"); contexts=jl(I/"caller-contexts.jsonl"); prior=jl(I/"prior-held-cell-reattestation.jsonl"); ps=j(I/"prior-held-cell-reattestation-summary.json")
if len(cells)!=300 or len(contexts)!=25 or len(prior)!=140 or not ps["allTargetHashesMatchPrior"]: raise SystemExit("candidate-free coverage or carried holds mismatch")
cx={x["continuationRank"]:x for x in contexts}

D={}
def add(rank, targets, disposition, rationale, confidence="high"):
 for loc,target in targets.items():
  if loc not in LOCALES: raise SystemExit("bad locale")
  D[(rank,loc)]={"disposition":disposition,"target":target,"rationale":rationale,"confidence":confidence}
def why(rank, rationale, confidence="high"):
 for loc in LOCALES:
  D[(rank,loc)]={"disposition":"accept-current","target":None,"rationale":rationale,"confidence":confidence}
# Caller-backed fixes and refinements.
add(628,{"es":"Se guardó en YAML la configuración de integración del flujo de origen.","vi":"Đã lưu cài đặt tích hợp nguồn cấp dữ liệu vào YAML.","zh-Hans":"源数据流集成设置已保存到 YAML。","zh-Hant":"來源資料流整合設定已儲存至 YAML。"},"correction","The success notice follows a saved source-feed integration configuration. Spanish duplicates “source,” while the Vietnamese and Chinese current forms are awkward literal calques; use clear source-data-feed wording and preserve YAML.","moderate")
add(630,{"ar":"، الدقة="},"correction","The production caller concatenates this label after F1 and its value. Arabic currently drops the separator comma, merging the two metric labels; restore an Arabic comma.","high")
add(631,{"ar":"اختر إعدادًا مسبقًا لجودة MilkDrop الأصلي. يقلّل الخيار الفعّال من حمل GPU، ويحدّ الخيار المتوازن الأداء عند 60 FPS، بينما يترك الخيار الكامل العرض بلا حد.","hi":"मूल MilkDrop गुणवत्ता प्रीसेट चुनें। कुशल विकल्प GPU पर भार कम करता है, संतुलित विकल्प 60 FPS की सीमा लगाता है, और पूर्ण विकल्प रेंडरिंग की सीमा हटाता है।"},"correction","The pinned tooltip describes three native MilkDrop quality presets and their GPU/FPS behavior. Current Arabic and Hindi distort the Efficient/Balanced/Full descriptions and omit protected literals; restore the meaning and exact MilkDrop, GPU, FPS, and 60 tokens.","high")
add(633,{"ar":"من أصل","fr":"sur","hi":"में से","ja":" / ","ko":" / ","zh-Hans":" / ","zh-Hant":" / "},"correction","Ten callers place this connector between a page range or latest-message count and its total. Use each locale’s natural “out of” construction; replace possessive or awkward fragments with standard pagination notation where needed.","moderate")
add(635,{"ar":"لم تُسجّل تعارضات في فهرس الموضوع — النطاق:","de":"Keine Konflikte im Themenindex gemeldet — Realm:","hi":"विषय-सूचकांक टकराव की कोई रिपोर्ट नहीं — Realm:","id":"Tidak ada konflik indeks subjek yang dilaporkan untuk","ja":"件名インデックスの競合は未報告 — Realm:","ko":"주제 색인 충돌 보고 없음 — Realm:","zh-Hans":"未报告主题索引冲突 — Realm：","zh-Hant":"未回報主題索引衝突 — Realm："},"correction","The caller appends report.realmId after this fragment. These targets lacked a grammatical link to the appended realm ID; use a clear realm label or trailing preposition so the complete status names the realm being reported on.","moderate")
add(637,{"hi":"प्लेयर ड्रॉअर को विस्तृत करें।"},"refinement","The exact caller is the expand-player-drawer control. “बड़ा करें” reads as make larger; “विस्तृत करें” states the expand action more directly.","moderate")
add(638,{"ar":"تمويه Soulseek من النوع 1"},"correction","This network heading names Soulseek Type-1 obfuscation. The current Arabic says “first type” and drops the source’s numeric token; preserve the exact 1 and Soulseek literal.","high")
add(640,{"de":"Attribute freigegebener Medien prüfen","hi":"साझा की गई मीडिया फ़ाइलों के गुण जाँचें","pt-BR":"Verificar atributos da mídia compartilhada","vi":"Kiểm tra thuộc tính của tệp phương tiện được chia sẻ","zh-Hans":"检测共享媒体属性","zh-Hant":"偵測共享媒體屬性"},"correction","The checkbox controls probing shared audio-file metadata during share scans. Replace wording that misreads this as a test share, uses awkward word order, or renders “probe” as a noun; name the check of shared-media attributes.","moderate")
add(640,{"ko":"공유 미디어 속성 확인"},"refinement","The checkbox controls probing metadata of shared audio during share scans. This wording keeps the meaning while using a natural Korean control label instead of a literal transliteration of “probe.”","moderate")
add(649,{"ar":"معرّف MBID للفنان مطلوب","de":"Die MBID des Künstlers ist erforderlich","es":"Se requiere el MBID del artista","fr":"L’identifiant MBID de l’artiste est requis","hi":"कलाकार का MBID आवश्यक है","id":"MBID artis wajib diisi","ja":"アーティストのMBIDが必要です","ko":"아티스트의 MBID가 필요합니다","pt-BR":"O MBID do artista é obrigatório","vi":"Cần có MBID của nghệ sĩ","zh-Hans":"艺术家的 MBID 为必填项","zh-Hant":"藝術家的 MBID 為必填項"},"refinement","Both pinned callers show a validation toast when the requested artist has no MBID. Rephrase each target as the artist’s MBID being required, keeping the exact protected MBID literal.","moderate")
add(650,{"ar":"نتائج المطابقة في الكوربوس","id":"Hasil pencocokan korpus"},"correction","This is a heading in the SongID corpus search panel. The Arabic and Indonesian current words can read as sports matches; name corpus matching results.","moderate")
add(650,{"ko":"코퍼스 일치 결과","vi":"Kết quả khớp trong kho ngữ liệu"},"refinement","This is the SongID corpus search-results heading. Make clear that these are matches found in the corpus, while preserving the existing short heading style.","moderate")
add(651,{"hi":"कतार में अगला आइटम चलाएँ।"},"correction","The pinned caller is the next-item player action. The current Hindi word order makes the queue item phrase awkward; use the natural “play the next item in the queue” construction.","high")

WHY={
628:"Success notice after source-feed integration settings are persisted to YAML; keep the format name exact.",
629:"Success notice from the hated-interest branch of the add-interest action; {interest} is the dynamic interest label.",
630:"Concatenated metric label after the algorithm's F1 score; the caller supplies the precision value immediately afterward.",
631:"Tooltip and accessible description for the native MilkDrop quality preset select; it explains Efficient, Balanced, and Full behaviors.",
632:"Player bar artist fallback shown when there is no active playback.",
633:"Ten pagination/message-history callers place this connector between a range or count and its total.",
634:"Library-health report count line for quarantine review previews; {count} is formatted from the report array length.",
635:"Conflict status followed immediately by the report's realmId.",
636:"Rich-text explanation appended to a rejected Mesh evidence-policy result; {reasons} is rendered as a localized component list.",
637:"Player-bar action expands the player drawer.",
638:"Heading for the network's Soulseek Type-1 obfuscation setting.",
639:"Playlist-intake status after preparing a tag and organization dry run; {playlistName} is the selected playlist.",
640:"Admin checkbox for probing shared audio files for bitrate, duration, and sample metadata during share scans.",
641:"Error toast when saving the current search filter to browser storage fails.",
642:"Admin-policy field label for the HTTPS port.",
643:"Statistic and library-health report label for issues that remain open.",
644:"Playlist-intake field label naming the source of the playlist.",
645:"Experience-settings help text explaining browser-local storage, no server/search/download effects, and what hiding the player does.",
646:"Share-groups form label for adding entries from the Contacts list.",
647:"Network information section heading.",
648:"Provenance annotation appended to a discovery-graph edge; {provenance} is the edge's dynamic origin.",
649:"Artist lookup validation toast when the required MusicBrainz identifier is absent.",
650:"Header for matches found in the SongID corpus.",
651:"Player-bar action tooltip for playing the next queue item.",
652:"Search-filter field label; file extensions are entered with spaces between them."
}
rows=[]
for c in cells:
 rank,loc=c["continuationRank"],c["locale"]
 d=D.get((rank,loc),{"disposition":"accept-current","target":None,"rationale":WHY[rank],"confidence":"high"})
 disp=d["disposition"]
 target=d["target"] if disp in ("correction","refinement") else c["currentTarget"]
 if disp in ("correction","refinement") and (not target or target==c["currentTarget"]): raise SystemExit(f"blank/no-op proposal {rank} {loc}")
 ck=checks(c["source"],target)
 if not all(ck.values()): raise SystemExit(f"token mismatch {(rank,loc)} {ck}")
 ctx=cx[rank]
 row={"schema":"slskdn-primary-cell-review/v1","repository":im["repository"],"pullRequest":409,"window":"W70","head":HEAD,"tree":TREE,"continuationRank":rank,"remainingQueueRank":c["remainingQueueRank"],"sourceId":c["sourceId"],"source":c["source"],"sourceSha256":c["sourceSha256"],"locale":loc,"catalogKey":c["catalogKey"],"catalogPath":c["catalogPath"],"catalogFileSha256":c["catalogFileSha256"],"catalogGitBlob":c["catalogGitBlob"],"currentTarget":c["currentTarget"],"currentTargetSha256":c["currentTargetSha256"],"callerContextSha256":c["callerContextSha256"],"callerRefs":c["callerRefs"],"callerContextSourceId":ctx["sourceId"],"callerContextSourceSha256":ctx["sourceSha256"],"callerContexts":ctx["callers"],"containsCandidate":False,"verdict":None,"disposition":disp,"rationale":d["rationale"],"confidence":d["confidence"],"selectedTarget":target,"selectedTargetSha256":sha(target),"tokenAudit":{"source":tok(c["source"]),"current":tok(c["currentTarget"]),"selected":tok(target),"checks":ck}}
 if disp in ("correction","refinement"): row["proposedTarget"]=target
 rows.append(row)
if len(rows)!=300 or len({(r["continuationRank"],r["locale"]) for r in rows})!=300: raise SystemExit("primary ledger coverage mismatch")
if set(D)!={(r["continuationRank"],r["locale"]) for r in rows if r["disposition"]!="accept-current"}: raise SystemExit("decision map coverage mismatch")
counts=Counter(r["disposition"] for r in rows)
base=Counter(); final=Counter()
for r in rows:
 s,cur,t=tok(r["source"]),tok(r["currentTarget"]),tok(r["selectedTarget"])
 base["placeholder"]+=s["placeholders"]!=cur["placeholders"]; base["markup"]+=s["markup"]!=cur["markup"]; base["numeric"]+=s["numeric"]!=cur["numeric"]; base["protectedLiteral"]+=not all(r["currentTarget"].count(x)>=r["source"].count(x) for x in s["protectedLiterals"])
 final["placeholder"]+=s["placeholders"]!=t["placeholders"]; final["markup"]+=s["markup"]!=t["markup"]; final["numeric"]+=s["numeric"]!=t["numeric"]; final["protectedLiteral"]+=not all(r["selectedTarget"].count(x)>=r["source"].count(x) for x in s["protectedLiterals"])
if dict(base)!=im["baselineTokenMismatchSummary"] or any(final.values()): raise SystemExit(f"token audit mismatch: {dict(base)} / {dict(final)}")
if not all(r["productionCallerCount"]>0 for r in contexts): raise SystemExit("callerless source unexpectedly selected; review disposition required")
dumpjl(O/"primary-ledger.jsonl",rows)
summary={"schemaVersion":1,"repository":im["repository"],"pullRequest":409,"window":"W70","head":HEAD,"tree":TREE,"sourceCount":25,"localeCount":12,"cellCount":300,"dispositionCounts":dict(counts),"proposalCount":counts["correction"]+counts["refinement"],"correctionCount":counts["correction"],"refinementCount":counts["refinement"],"holdCount":counts["hold"],"callerlessRanks":[],"callerCountByRank":{str(x["continuationRank"]):x["productionCallerCount"] for x in contexts},"baselineTokenMismatches":dict(base),"reviewedTokenMismatches":dict(final),"carriedHoldsReattested":140,"carriedHoldsUnchanged":True,"priorSelectedIdsExcluded":1732,"candidateFreeInputVerified":True,"blindPacketAccessed":False,"crossAuditPacketAccessed":False,"repositoryOrPRFilesEdited":False,"nativeSpeakerReview":"not performed","browserReview":"not performed"}
dump(O/"summary.json",summary)
(O/"input-verification.txt").write_text("Candidate-free W70 verifier passed before primary review.\n\n"+verified.stdout,encoding="utf-8")
readme=("# slskdN PR #409 W70 primary semantic review\n\n"
"This packet independently reviews 300 cells across 25 sources and 12 locales at exact PR head "+HEAD+" and tree "+TREE+", continuation ranks 628–652 (remaining-queue ranks 528–552). Decisions were made from the sealed candidate-free input and its exact caller contexts.\n\n"
"Disposition counts: "+", ".join(f"{k}: {v}" for k,v in sorted(counts.items()))+". The review proposes "+str(summary["proposalCount"])+" target changes ("+str(counts["correction"])+" corrections and "+str(counts["refinement"])+" refinements), retains all other values, and adds no holds. The callerless set is empty. The three baseline token issues are repaired: Arabic Type-1 numeric 1 at rank 638 and protected GPU/ MilkDrop literals at rank 631 (Arabic and Hindi). Placeholder, markup, numeric-token, and protected-literal checks pass at all selected targets.\n\n"
"All 140 prior held cells were reattested unchanged; the complete input also records the 1,732 prior/excluded IDs. No blind or cross-audit output was accessed. No repository or PR files were edited. Qualified native-speaker and browser reviews were not performed.\n\nRun python3 verify_primary.py in this directory to validate checksums, input pins, decisions, tokens, holds, and live refs.\n")
(O/"README.md").write_text(readme,encoding="utf-8")
manifest={"schemaVersion":1,"artifact":"slskdN PR #409 W70 primary semantic review ledger","reviewType":"primary-semantic","sealed":True,"candidateFreeInput":True,"repository":im["repository"],"pullRequest":409,"branch":BRANCH,"window":"W70","head":HEAD,"tree":TREE,"sourceCount":25,"localeCount":12,"cellCount":300,"locales":LOCALES,"inputPath":str(I),"inputManifestSha256":sha((I/"manifest.json").read_bytes()),"inputChecksumListSha256":sha((I/"PACKET-SHA256SUMS.txt").read_bytes()),"inputCellLedgerSha256":sha((I/"source-current-cells.jsonl").read_bytes()),"inputCallerContextSha256":sha((I/"caller-contexts.jsonl").read_bytes()),"carriedHoldsReattested":140,"priorSelectedIdsExcluded":1732,"dispositionCounts":dict(counts),"proposalCount":summary["proposalCount"],"blindPacketAccessed":False,"crossAuditPacketAccessed":False,"nativeSpeakerReview":"not performed","browserReview":"not performed","createdAtUtc":datetime.now(timezone.utc).isoformat()}
manifest["files"]=[{"path":p.name,"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for p in sorted(O.iterdir()) if p.is_file() and p.name not in ("manifest.json","SHA256SUMS.txt")]
dump(O/"manifest.json",manifest)
files=[p for p in sorted(O.iterdir()) if p.is_file() and p.name!="SHA256SUMS.txt"]
(O/"SHA256SUMS.txt").write_text("".join(f"{sha(p.read_bytes())}  {p.name}\n" for p in files),encoding="utf-8")
print(json.dumps({"built":True,"head":HEAD,"tree":TREE,"cells":len(rows),"dispositions":dict(counts),"proposals":summary["proposalCount"],"baselineTokenMismatches":dict(base),"reviewedTokenMismatches":dict(final),"carriedHoldsReattested":140,"priorIds":1732,"callerlessRanks":[]},ensure_ascii=False,indent=2))
