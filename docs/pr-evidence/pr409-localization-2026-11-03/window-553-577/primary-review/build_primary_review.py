#!/usr/bin/env python3
import hashlib,json,re,subprocess,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
I=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w67-ranks553-577-candidate-free-20261103/input")
O=Path(__file__).resolve().parent
HEAD="2dc64b9d00f6611aeb72713af81db53ccc5a4084"
TREE="f13462300926ac897235cd92ae68c87695c38c31"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
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
im=j(I/"manifest.json")
if (im["head"],im["tree"],im["continuationRankRange"],im["remainingQueueRankRange"])!=(HEAD,TREE,[553,577],[453,477]): raise SystemExit("candidate-free packet pin mismatch")
subprocess.run([sys.executable,str(I/"verify_input.py")],check=True,capture_output=True,text=True)
subprocess.run(["sha256sum","-c","PACKET-SHA256SUMS.txt"],cwd=I,check=True,capture_output=True,text=True)
cells=jl(I/"source-current-cells.jsonl"); contexts=jl(I/"caller-contexts.jsonl"); prior=jl(I/"prior-held-cell-reattestation.jsonl")
assert len(cells)==300 and len(contexts)==25 and len(prior)==128
cx={x["continuationRank"]:x for x in contexts}
D={}
def add(rank,targets,disposition,rationale,confidence="moderate"):
 for locale,target in targets.items(): D[(rank,locale)]=(disposition,target,rationale,confidence)
add(553,{"ar":"هذه مجرد نقطة بداية لمراجعة قائمة المراقبة؛ لم يبدأ أي استعلام إلى مزود، أو بحث على Soulseek، أو تصفح للأقران، أو تنزيل.","de":"Nur ein Ausgangspunkt für die Prüfung der Watchlist; es wurde noch keine Anbietersuche, Soulseek-Suche, Peer-Suche oder ein Download gestartet.","es":"Solo es un punto de partida para revisar la lista de seguimiento; no se ha iniciado ninguna búsqueda de proveedores, búsqueda en Soulseek, exploración de pares ni descarga.","fr":"Il s’agit seulement d’un point de départ pour examiner la liste de surveillance ; aucune recherche de fournisseur, recherche Soulseek, exploration de pairs ni aucun téléchargement n’a commencé.","hi":"यह केवल वॉचलिस्ट की समीक्षा के लिए एक शुरुआती प्रविष्टि है; प्रदाता खोज, Soulseek खोज, पीयर ब्राउज़िंग या डाउनलोड शुरू नहीं हुआ है।","id":"Ini hanya titik awal untuk meninjau daftar pantauan; pencarian penyedia, pencarian Soulseek, penelusuran peer, maupun pengunduhan belum dimulai.","ja":"ウォッチリスト確認の起点にすぎません。プロバイダー検索、Soulseek 検索、ピアの閲覧、ダウンロードはいずれも始まっていません。","ko":"관심 목록 검토를 위한 시작 항목일 뿐입니다. 공급자 조회, Soulseek 검색, 피어 탐색 또는 다운로드는 아직 시작되지 않았습니다.","pt-BR":"É apenas um ponto de partida para revisar a lista de observação; nenhuma consulta a provedores, busca no Soulseek, navegação entre peers ou download foi iniciada.","vi":"Đây chỉ là điểm khởi đầu để xem xét danh sách theo dõi; chưa bắt đầu tra cứu nhà cung cấp, tìm kiếm Soulseek, duyệt các peer hay tải xuống.","zh-Hans":"这只是审核观察列表的起点；尚未开始查询服务提供方、搜索 Soulseek、浏览对等节点或下载。","zh-Hant":"這只是審核觀察清單的起點；尚未開始查詢服務提供者、搜尋 Soulseek、瀏覽對等節點或下載。"},"refinement","The exact networkImpact caller describes a watchlist item as a review starting point and says no network activity has begun. Avoid the unnatural literal seed wording; the Hindi and Korean current rows also reverse the negative status.")
for loc in ("hi","ko"):
 D[(553,loc)]=("correction",D[(553,loc)][1],D[(553,loc)][2],"moderate")
add(555,{"es":"Exactitud general:","fr":"Exactitude globale :","pt-BR":"Acurácia geral:"},"correction","The exact metric is perceptualHashingStats.overallAccuracy. Use the locale term for accuracy rather than a term that can be read specifically as precision.")
add(561,{"ar":"تنطبق الثقة على قراءة الاحتمالية الاصطناعية فقط. ولا تتحكم في قرارات التنزيل عندما تكون الهوية قوية.","de":"Die Konfidenz gilt nur für die Anzeige der synthetischen Likelihood. Sie steuert keine Download-Entscheidungen, wenn die Identität eindeutig ist.","fr":"Le niveau de confiance s’applique uniquement à l’indicateur de vraisemblance synthétique. Il ne détermine pas les décisions de téléchargement lorsque l’identité est forte.","pt-BR":"A confiança se aplica somente à leitura da probabilidade sintética. Ela não controla as decisões de download quando a identidade é forte.","ja":"この信頼度は合成尤度の表示にのみ適用されます。識別結果の確度が高い場合、ダウンロードの判断はこの値に左右されません。","ko":"신뢰도는 합성 우도 표시값에만 적용됩니다. 곡 식별 결과가 확실하면 다운로드 결정에는 영향을 주지 않습니다."},"correction","The SongID tooltip distinguishes a confidence readout from the strength of a track identity match. Correct agreement in German, French, Portuguese, and Arabic, and do not render identity as a user ID in Japanese or Korean.")
add(563,{"ar":"فشل استكمال البيانات من سجل البحث: {error}","es":"Falló la carga de datos históricos: {error}","fr":"Échec du chargement rétrospectif de l’historique : {error}","id":"Gagal mengisi data dari riwayat: {error}","pt-BR":"Falha ao carregar dados históricos: {error}","vi":"Bổ sung dữ liệu từ lịch sử thất bại: {error}"},"correction","The exact Network caller invokes backfillFromSearchHistory. Describe loading or backfilling historical data rather than restocking or a generic refill.")
add(564,{"ar":"أزل الموجة المخصصة المحددة من الإعداد المسبق الأصلي النشط واحفظ النسخة المعدلة محليًا.","de":"Entfernen Sie die ausgewählte benutzerdefinierte Wave aus dem aktiven nativen Preset und speichern Sie die bearbeitete Kopie lokal.","es":"Elimine la onda personalizada seleccionada del ajuste preestablecido nativo activo y guarde localmente la copia editada.","fr":"Supprimez l’onde personnalisée sélectionnée du préréglage natif actif et enregistrez localement la copie modifiée.","hi":"सक्रिय अंतर्निहित प्रीसेट से चयनित कस्टम वेव हटाएँ और संपादित प्रति को स्थानीय रूप से सहेजें।","id":"Hapus gelombang kustom yang dipilih dari preset asli aktif dan simpan salinan yang diedit secara lokal.","ko":"활성 내장 프리셋에서 선택한 사용자 정의 웨이브를 제거하고 편집한 사본을 로컬에 저장합니다.","pt-BR":"Remova a onda personalizada selecionada da predefinição nativa ativa e salve a cópia editada localmente.","vi":"Xóa sóng tùy chỉnh đã chọn khỏi preset gốc đang hoạt động và lưu bản sao đã chỉnh sửa cục bộ.","zh-Hans":"从当前启用的原生预设中删除选定的自定义波形，并将编辑后的副本保存到本地。","zh-Hant":"從目前啟用的原生預設中刪除選取的自訂波形，並將編輯後的副本儲存在本機。"},"refinement","The player caller describes removing a custom waveform from the active preset and saving the edited copy locally. Make persistence explicit as saving, while preserving established locale terminology for the native preset.")
D[(564,"hi")]=("correction",D[(564,"hi")][1],D[(564,"hi")][2],"moderate")
add(565,{"hi":"अंतर्निहित MilkDrop तरंग खंड","ja":"内蔵 MilkDrop ウェーブフラグメント","ko":"내장 MilkDrop 파동 조각","vi":"Đoạn sóng MilkDrop tích hợp sẵn","zh-Hans":"内置 MilkDrop 波形片段","zh-Hant":"內建 MilkDrop 波形片段"},"refinement","The Visualizer caller labels a built-in preset-library wave fragment. Use the established built-in sense for native and preserve the exact MilkDrop product name.")
for loc in ("hi","ko"):
 D[(565,loc)]=("correction",D[(565,loc)][1],D[(565,loc)][2],"high")
add(566,{"ja":"メッシュの検出を信頼できるローカルピアのみに限定したい場合は","ko":"메시 검색을 신뢰할 수 있는 로컬 피어로만 제한하려면","vi":"Nếu bạn muốn chỉ cho phép các peer cục bộ đáng tin cậy khám phá mesh"},"correction","This text is one fragment in a paragraph split around the literal dht.lan_only=true. The following localized fragment already supplies the configuration instruction, so avoid a second imperative; the Vietnamese current target also misreads network peers as coworkers.")
add(572,{"ar":"إظهار الجهات المساهمة في التوصيات","de":"Empfehlungsgeber anzeigen","es":"Mostrar quiénes aportan las recomendaciones","fr":"Afficher les contributeurs des recommandations","hi":"सुझावों के स्रोतों में योगदान देने वालों को दिखाएँ","id":"Tampilkan kontributor rekomendasi","ja":"推薦元のユーザーを表示","ko":"추천 출처 제공자 표시","pt-BR":"Mostrar quem fornece as recomendações","vi":"Hiển thị những người đóng góp nguồn đề xuất","zh-Hans":"显示推荐来源参与者","zh-Hant":"顯示推薦來源參與者"},"refinement","The federated recommendations control and adjacent popup describe actors who provide recommendations. Use locale wording for those source participants instead of a literal performer sense of actors.")
add(573,{"es":"(umbral:","ko":"(임계값:","zh-Hans":"（阈值：","zh-Hant":"（閾值："},"refinement","The caller inserts this fragment before a numeric similarity threshold. Use the standard threshold term for the Spanish, Korean, and Chinese labels.")
add(575,{"ar":"إشارات إلى AI","de":"AI-Erwähnungen","es":"Menciones de AI","fr":"Mentions liées à AI","hi":"AI का उल्लेख","pt-BR":"Menções a AI","zh-Hans":"AI 提及","zh-Hant":"AI 提及"},"correction","The caller labels aiCommentMentionCount. Preserve the protected AI acronym while translating mentions rather than expanding or localizing the acronym.","high")
add(576,{"hi":"सक्रिय अंतर्निहित प्रीसेट को पसंदीदा से हटाएँ।","ja":"アクティブな内蔵プリセットをお気に入りから削除します。","ko":"활성 내장 프리셋을 즐겨찾기에서 제거합니다."},"refinement","The exact Player caller toggles the active native preset favorite state. Match the established built-in terminology used for the same native preset library.")
D[(576,"hi")]=("correction",D[(576,"hi")][1],D[(576,"hi")][2],"moderate")
D[(576,"ko")]=("correction",D[(576,"ko")][1],D[(576,"ko")][2],"moderate")
why={553:"A watchlist network-impact note explicitly distinguishes a review seed from provider lookup, Soulseek search, peer browsing, or download activity.",554:"A verification report heading counting failed membership checks.",555:"A perceptual-hashing metric label for overall accuracy.",556:"The Navidrome integration display name; retain the product name.",557:"Accessible label and title for selecting all wishlist items on the current page.",558:"Playlist-import summary with exact matched, skipped, and changed placeholders.",559:"Mesh settings health label for the Routing Table.",560:"Network-health summary with a localized numeric count.",561:"Song identification tooltip distinguishing synthetic-likelihood confidence from a strong identity match.",562:"Fixed WebGPU adapter availability status in visualizer fallback handling.",563:"Error toast from backfillFromSearchHistory.",564:"Player tooltip for removing a custom waveform from an active native preset and saving its local copy.",565:"Accessible select label for built-in MilkDrop wave fragments.",566:"Network settings help fragment composed around the literal dht.lan_only=true.",567:"Success heading after a message is signed.",568:"Password field label for an HTTPS certificate.",569:"Audio output-device selector label.",570:"Clipboard-copy failure status for the automation history report.",571:"Footer accessibility title showing the DHT node count.",572:"Federated taste-recommendation control for revealing source participants.",573:"Fragment labeling the similarity threshold before its numeric value.",574:"Tooltip for looking up a selected peer membership record in a Pod.",575:"Song identification scorecard count for AI mentions; preserve AI exactly.",576:"Favorite-state toggle for the active native preset.",577:"Failure toast for refreshing Pod opinions while preserving the dynamic message placeholder."}
if any(k[0] not in range(553,578) or k[1] not in LOCALES for k in D): raise SystemExit("proposal outside W67 scope")
subprocess.run(["gh","api","repos/snapetech-org/slskdN/pulls/409"],check=True,capture_output=True,text=True)
if O.exists() and any(p.name not in {"build_primary_review.py"} for p in O.iterdir()): raise SystemExit("primary output directory is not empty")
cells=jl(I/"source-current-cells.jsonl"); contexts=jl(I/"caller-contexts.jsonl")
assert len(cells)==300 and len(contexts)==25
cx={x["continuationRank"]:x for x in contexts}
rows=[]
for c in cells:
 rank,loc=c["continuationRank"],c["locale"]
 dis,target,reason,conf=D.get((rank,loc),("accept-current",None,why[rank],"high"))
 reviewed=target if dis in ("correction","refinement") else c["currentTarget"]
 if dis in ("correction","refinement") and reviewed==c["currentTarget"]: raise SystemExit("proposal is a no-op")
 st,ct,rt=tok(c["source"]),tok(c["currentTarget"]),tok(reviewed)
 checks={"placeholdersPreserved":st["placeholders"]==rt["placeholders"],"markupPreserved":st["markup"]==rt["markup"],"numericTokensPreserved":st["numeric"]==rt["numeric"],"protectedLiteralsPreserved":all(reviewed.count(z)>=c["source"].count(z) for z in st["protectedLiterals"])}
 if not all(checks.values()): raise SystemExit(f"token check failed {(rank,loc)}: {checks}; target={reviewed}")
 ctx=cx[rank]
 row={"schema":"slskdn-primary-cell-review/v1","repository":im["repository"],"pullRequest":im["pullRequest"],"window":"W67","head":HEAD,"tree":TREE,
  "continuationRank":rank,"remainingQueueRank":c["remainingQueueRank"],"sourceId":c["sourceId"],"source":c["source"],"sourceSha256":c["sourceSha256"],"locale":loc,
  "catalogKey":c["catalogKey"],"catalogPath":c["catalogPath"],"catalogFileSha256":c["catalogFileSha256"],"catalogGitBlob":c["catalogGitBlob"],
  "currentTarget":c["currentTarget"],"currentTargetSha256":c["currentTargetSha256"],"callerContextSha256":c["callerContextSha256"],"callerRefs":c["callerRefs"],
  "callerContextSourceId":ctx["sourceId"],"callerContextSourceSha256":ctx["sourceSha256"],"callerContexts":ctx["callers"],
  "containsCandidate":False,"verdict":None,"disposition":dis,"rationale":reason,"confidence":conf,"reviewedTargetSha256":sha(reviewed),
  "tokenAudit":{"source":st,"current":ct,"reviewed":rt,"checks":checks}}
 if dis in ("correction","refinement"): row["proposedTarget"]=target
 rows.append(row)
if len(rows)!=300 or len({(x["continuationRank"],x["locale"]) for x in rows})!=300: raise SystemExit("primary ledger coverage mismatch")
if set(D)!={(x["continuationRank"],x["locale"]) for x in rows if x["disposition"]!="accept-current"}: raise SystemExit("proposal disposition coverage mismatch")
dumpjl(O/"primary-ledger.jsonl",rows)
counts=Counter(r["disposition"] for r in rows); base=Counter(); final=Counter()
for r in rows:
 st,ct=tok(r["source"]),tok(r["currentTarget"]); target=r.get("proposedTarget",r["currentTarget"]); rt=tok(target)
 base["placeholder"]+=st["placeholders"]!=ct["placeholders"]; base["markup"]+=st["markup"]!=ct["markup"]
 base["numeric"]+=st["numeric"]!=ct["numeric"]; base["protectedLiteral"]+=not all(r["currentTarget"].count(z)>=r["source"].count(z) for z in st["protectedLiterals"])
 final["placeholder"]+=st["placeholders"]!=rt["placeholders"]; final["markup"]+=st["markup"]!=rt["markup"]
 final["numeric"]+=st["numeric"]!=rt["numeric"]; final["protectedLiteral"]+=not all(target.count(z)>=r["source"].count(z) for z in st["protectedLiterals"])
if dict(base)!=im["baselineTokenMismatchSummary"]: raise SystemExit("baseline token mismatch summary differs from candidate-free input")
if any(final.values()): raise SystemExit("reviewed proposals retain token mismatches: "+str(dict(final)))
assert not any(r["productionCallerCount"]==0 for r in contexts)
summary={"schemaVersion":1,"repository":im["repository"],"pullRequest":409,"window":"W67","head":HEAD,"tree":TREE,"sourceCount":25,"localeCount":12,"cellCount":300,
 "dispositionCounts":dict(counts),"proposalCount":sum(v in ("correction","refinement") for v in (r["disposition"] for r in rows)),
 "holdCount":counts.get("hold",0),"baselineTokenMismatches":dict(base),"reviewedTokenMismatches":dict(final),
 "priorHeldCellsReattested":128,"priorHeldCellsUnchanged":True,"callerlessSelectedRanks":[],"callerCountByRank":{str(x["continuationRank"]):x["productionCallerCount"] for x in contexts},
 "candidateFreeInputVerified":True,"blindPacketAccessed":False,"repositoryOrPRFilesEdited":False,"nativeSpeakerReview":"not performed","browserReview":"not performed"}
dump(O/"summary.json",summary)
(O/"input-verification.txt").write_text("Candidate-free W67 input verifier ran before primary review.\n\n"+subprocess.check_output([sys.executable,str(I/"verify_input.py")],text=True),encoding="utf-8")
(O/"README.md").write_text("# slskdN PR #409 W67 primary semantic review\n\nThis packet records the primary review of 300 catalog cells across 25 sources, ranks 553–577 (remaining-queue ranks 453–477), at PR head "+HEAD+" and tree "+TREE+". It uses the separately sealed candidate-free packet and preserves all 128 prior holds. All 25 selected sources have exact production callers; no new callerless mappings were held.\n\nDisposition counts: "+", ".join(f"{k}: {v}" for k,v in sorted(counts.items()))+". Proposed target rows: "+str(summary["proposalCount"])+". The candidate-free baseline has ten protected-literal gaps; the reviewed targets pass placeholder, markup, numeric, and protected-literal checks.\n\nNo blind packet was accessed and no repository or catalog files were edited. Native-speaker and headed-browser review were not performed. Run python3 verify_primary.py here to verify the ledger and checksums.\n",encoding="utf-8")
manifest={"schemaVersion":1,"artifact":"slskdN PR #409 W67 primary semantic review ledger","reviewType":"primary-semantic","sealed":True,"candidateFreeInput":True,
 "repository":im["repository"],"pullRequest":409,"branch":im["branch"],"window":"W67","head":HEAD,"tree":TREE,"sourceCount":25,"localeCount":12,"cellCount":300,"locales":LOCALES,
 "inputPath":str(I),"inputManifestSha256":sha((I/"manifest.json").read_bytes()),"inputChecksumListSha256":sha((I/"PACKET-SHA256SUMS.txt").read_bytes()),
 "inputLedgerSha256":sha((I/"source-current-cells.jsonl").read_bytes()),"priorHeldCellsReattested":128,"dispositionCounts":dict(counts),"proposalCount":summary["proposalCount"],
 "blindPacketAccessed":False,"nativeSpeakerReview":"not performed","browserReview":"not performed","createdAtUtc":datetime.now(timezone.utc).isoformat()}
manifest["files"]=[{"path":p.name,"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for p in sorted(O.iterdir()) if p.is_file() and p.name not in ("manifest.json","SHA256SUMS.txt")]
dump(O/"manifest.json",manifest)
paths=sorted(p for p in O.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt")
(O/"SHA256SUMS.txt").write_text("".join(f"{sha(p.read_bytes())}  {p.name}\n" for p in paths),encoding="utf-8")
print(json.dumps({"built":True,"head":HEAD,"tree":TREE,"rows":len(rows),"dispositions":dict(counts),"proposals":summary["proposalCount"],"baselineTokenMismatches":dict(base),"reviewedTokenMismatches":dict(final)},ensure_ascii=False,indent=2))
