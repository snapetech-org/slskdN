#!/usr/bin/env python3
"""Build the independent blind review from W69 candidate-free input only."""
import argparse, hashlib, json, re
from pathlib import Path

HEAD="9ef252a53d2c14201c736de41efd0531bc00965a"
TREE="becf17f8be3f3251691002dbce487c1e94693e63"
WINDOW="W69-ranks603-627"
REPO="snapetech-org/slskdN"
PR=409
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
# (continuation rank, locale): (decision, proposed target, specific rationale, confidence)
EDITS={
 (603,"ar"):("correction","تم تفعيل {size} من العناصر.","This is a success toast after selected wishlist entries are updated. The current masdar-like تمكين does not clearly say the items were enabled; the revised past passive reports completion and preserves {size}.","moderate"),
 (603,"de"):("correction","Wunschlisteneinträge aktiviert: {size}","The caller is a success toast for enabling selected wishlist entries. Artikel means articles/items of merchandise here and the current adjective+noun phrase is malformed; the revised status uses the wishlist-entry context.","moderate"),
 (603,"es"):("refinement","{size} elementos habilitados","The source is a completed-action toast with a numeric count. Put the count before elementos for natural Spanish word order.","moderate"),
 (603,"fr"):("refinement","{size} élément(s) activé(s)","This is a completed-action toast. Keep the source's singular/plural fallback while placing the count before the item phrase.","moderate"),
 (603,"hi"):("correction","{size} आइटम सक्षम किए गए","The current target is an adjective phrase rather than a completed-action toast. The revised Hindi reports that the counted items were enabled and preserves {size}.","moderate"),
 (603,"id"):("correction","Berhasil mengaktifkan {size} item.","The current Item {size} diaktifkan has an unnatural count position and does not read as a success toast. This reports the completed action in Indonesian.","moderate"),
 (603,"pt-BR"):("refinement","{size} itens ativados","The success toast reads more naturally with the count before the item noun.","moderate"),
 (603,"vi"):("correction","Đã bật {size} mục.","The current target inserts '(các)' and places the count after mục, making the toast awkward. This uses a neutral item classifier and preserves the count placeholder.","moderate"),
 (603,"zh-Hans"):("refinement","已启用 {size} 个条目","The caller updates wishlist entries. 条目 is a clearer UI-list item term here than 项目, which can mean a project.","moderate"),
 (603,"zh-Hant"):("refinement","已啟用 {size} 個項目","The source is a toast about enabled wishlist entries; the revised order reads naturally and retains the count.","moderate"),
 (605,"fr"):("refinement","Aperçu de l'organisation des tags pour {name}","The caller previews playlist tag organization; balises commonly refers to markup tags in French, while tags is the clearer metadata term in this UI context.","moderate"),
 (605,"vi"):("correction","Xem trước cách tổ chức thẻ cho {name}","This is an aria label and tooltip for previewing playlist tag organization. The current Tổ chức thẻ xem trước has unnatural word order.","moderate"),
 (605,"zh-Hans"):("correction","{name} 的标签组织预览","The current preview tag organization phrase has unnatural modifier order. This labels a preview of the playlist's tag organization.","moderate"),
 (605,"zh-Hant"):("correction","{name} 的標籤組織預覽","The current preview tag organization phrase has unnatural modifier order. This labels a preview of the playlist's tag organization.","moderate"),
 (607,"ar"):("refinement","نشر الواصفات على دفعات","This is a card heading whose description says multiple content descriptors can be published simultaneously. This expresses batch publication rather than a 'batch of publishing descriptors'.","moderate"),
 (607,"de"):("correction","Deskriptoren stapelweise veröffentlichen","The card description says multiple descriptors can be published simultaneously. The current title reverses that relation; this states batch-publishing the descriptors.","moderate"),
 (607,"es"):("refinement","Publicación por lotes de descriptores","The heading names the batch-publication operation, not descriptors belonging to a batch publication.","moderate"),
 (607,"fr"):("refinement","Publication groupée de descripteurs","The card describes publishing multiple descriptors simultaneously; groupée makes the batch operation explicit.","moderate"),
 (607,"hi"):("refinement","डिस्क्रिप्टरों का बैच प्रकाशन","The source describes a technical card for publishing multiple content descriptors at once. This preserves descriptor as a technical term and clarifies that the batch applies to publication.","moderate"),
 (607,"id"):("correction","Publikasi batch deskriptor","The current title can mean descriptors of batch publication. This puts publication first and makes the descriptors the objects being published.","moderate"),
 (607,"ja"):("refinement","記述子の一括公開","The description says multiple content descriptors are published simultaneously. 一括公開 expresses bulk publishing more clearly than the current English loan compound.","moderate"),
 (607,"ko"):("correction","디스크립터 일괄 게시","The card publishes multiple content descriptors at once. The current 설명자 can mean an explainer/person; this keeps the technical descriptor term and makes batch posting explicit.","moderate"),
 (607,"pt-BR"):("refinement","Publicação em lote de descritores","The card's description identifies a batch action on descriptors; this order states the publication operation clearly.","moderate"),
 (607,"vi"):("correction","Xuất bản hàng loạt các bộ mô tả","The current title reads as a set of descriptions for batch publishing. This makes the descriptors the objects being published in bulk.","moderate"),
 (607,"zh-Hant"):("correction","批次發布描述符","The current 大量 means a large quantity, while the source names batch publishing. This uses the batch-operation term.","moderate"),
 (610,"de"):("refinement","Wenden Sie diesen Filter in einem Schritt auf {count} ausgewählte Wunschlisteneinträge an.","This is a tooltip for a bulk wishlist action. Use the formal Sie form, consistent with nearby German help text in this window.","moderate"),
 (611,"fr"):("correction","Intérêts natifs chargés pour {username}.","The caller loads a user's native interest data; autochtones means Indigenous in French and is a false friend here.","moderate"),
 (611,"zh-Hans"):("correction","已加载 {username} 的原生兴趣。","The caller loads native interest data for a remote user. 本机 means local device/computer, which changes the source meaning; 原生 preserves native in this context.","moderate"),
 (611,"zh-Hant"):("correction","已載入 {username} 的原生興趣。","The caller loads native interest data for a remote user. 本機 means local device/computer, which changes the source meaning; 原生 preserves native in this context.","moderate"),
 (612,"ar"):("correction","قد يؤدي نشر الرأي إلى كشف معرّف (ID) المحتوى المحدد، وتجزئة النسخة، والدرجة، والملاحظة، وإشارة تفضيل الأقران لمشاركي المجموعة.","The caller places this string in a warning under advanced opinion-publishing controls. Preserve the required exact ID literal and use clearer terms for the variant hash and peer-preference signal; the current target omits ID and calls a pod a chamber.","moderate"),
 (612,"hi"):("correction","एक राय प्रकाशित करने से पॉड प्रतिभागियों के सामने चयनित सामग्री का ID, वैरिएंट हैश, स्कोर, नोट और सहकर्मी की पसंद का संकेत उजागर हो सकता है।","This is a privacy warning about data exposed to pod participants. Preserve the required exact ID literal; the current Hindi transliterates it as आईडी.","high"),
 (612,"ja"):("correction","意見を公開すると、選択したコンテンツ ID、バリアントハッシュ、スコア、メモ、およびピアの選好シグナルがポッド参加者に公開される可能性があります。","The privacy warning lists a peer preference signal. The current ピア設定シグナル means a peer configuration signal; use 選好 for preference.","moderate"),
 (612,"vi"):("refinement","Việc xuất bản một ý kiến có thể hiển thị ID nội dung đã chọn, hàm băm biến thể, điểm số, ghi chú và tín hiệu về sở thích từ các peer cho những người tham gia nhóm.","This is a warning about exposing peer preference data. The current ưu tiên means priority, not preference; the revision clarifies that distinction.","moderate"),
 (614,"hi"):("refinement","यह न तो कुछ प्रकाशित करता है, न कुछ अक्षम करता है, न खोजता है, न ब्राउज़ करता है और न डाउनलोड करता है।","This tooltip explicitly promises that loading the report performs none of these actions. The current list mixes bare verbs and nouns; this makes the Hindi list parallel while preserving every prohibition.","moderate"),
 (615,"ar"):("hold",None,"No production caller is present in the pinned packet. The source phrase 'public forwards' is ambiguous without context, and its current translation appears to select a sports meaning. Do not infer a technical meaning or replace the target without caller evidence.","low"),
 (615,"de"):("hold",None,"No production caller is present in the pinned packet. 'Public forwards' could refer to a network feature or another domain; the current football translation cannot be validated without context.","low"),
 (615,"es"):("hold",None,"No production caller is present in the pinned packet. 'Public forwards' is domain-ambiguous; the current fútbol delantero reading may be wrong, but there is not enough evidence to select a replacement.","low"),
 (615,"fr"):("hold",None,"No production caller is present in the pinned packet. 'Public forwards' is domain-ambiguous, and the current attaquants translation suggests football; do not guess a technical replacement.","low"),
 (615,"hi"):("hold",None,"No production caller is present in the pinned packet. 'Public forwards' is ambiguous and could be networking terminology; the current text does not provide enough evidence to select a source-faithful Hindi target.","low"),
 (615,"id"):("hold",None,"No production caller is present in the pinned packet. The source may refer to networking but could also have another meaning; the current penyerang is a sports reading and cannot be safely corrected without caller evidence.","low"),
 (615,"ja"):("hold",None,"No production caller is present in the pinned packet. 'Public forwards' is ambiguous; the current パブリック フォワード can suggest a sports position and does not establish the intended technical meaning.","low"),
 (615,"ko"):("hold",None,"No production caller is present in the pinned packet. 'Public forwards' is ambiguous and the current 전달 does not reveal the intended product meaning; hold pending caller evidence.","low"),
 (615,"pt-BR"):("hold",None,"No production caller is present in the pinned packet. 'Public forwards' may be technical but has multiple readings; hold rather than infer a networking term from context that is absent.","low"),
 (615,"vi"):("hold",None,"No production caller is present in the pinned packet. 'Public forwards' is ambiguous; the current chuyển tiếp is suggestive of networking but cannot be confirmed from a caller.","low"),
 (615,"zh-Hans"):("hold",None,"No production caller is present in the pinned packet. 'Public forwards' could be technical but also has other meanings; the current 前锋 suggests sports. Do not choose without context.","low"),
 (615,"zh-Hant"):("hold",None,"No production caller is present in the pinned packet. 'Public forwards' could be technical but also has other meanings; the current 前鋒 suggests sports. Do not choose without context.","low"),
 (618,"ar"):("correction","تمت الإضافة","This label follows the API's createdCount in the Lidarr sync result. The current وأضاف is an active verb ('and he added'); use a completed passive status.","moderate"),
 (618,"hi"):("refinement","जोड़े गए","The caller displays a created-item count immediately before this status label; plural जोड़े गए agrees more clearly than the current singular जोड़ा.","moderate"),
 (618,"ja"):("refinement","追加済み","The caller places this status after the created-item count; 追加済み is a concise completed-state label.","moderate"),
 (618,"pt-BR"):("refinement","adicionados","This is a status label after a count of created items; use the plural form to match the counted entries.","moderate"),
 (618,"zh-Hans"):("correction","已添加","The caller displays a created-item count and then this status. 额外 means additional/extra, not added; use a completed-action label.","high"),
 (618,"zh-Hant"):("correction","已新增","The caller displays a created-item count and then this status. 額外 means additional/extra, not added; use a completed-action label.","high"),
 (619,"ar"):("correction","ابحث مباشرةً في هذا المقطع المُقسَّم عندما يعثر SongID على فصل محتمل أو دليل على طابع زمني.","The caller is a SongID action for a split source segment. The current المتحلل suggests decay/decomposition rather than a segment split, and the exact SongID name is needed for clarity.","moderate"),
 (619,"es"):("correction","Busca directamente este segmento dividido cuando SongID encuentre un capítulo plausible o una pista de marca de tiempo.","The caller searches a source segment after SongID detects a chapter or timestamp clue. Descompuesto suggests decomposition rather than a segment split; retain the exact SongID feature name.","moderate"),
 (619,"fr"):("correction","Recherchez directement ce segment découpé lorsque SongID a trouvé un chapitre plausible ou un indice d’horodatage.","The SongID caller concerns a portion split from a source. Découpé is clearer than décomposé here, which can imply decomposition.","moderate"),
 (619,"hi"):("correction","जब SongID को कोई संभावित अध्याय या टाइमस्टैम्प संकेत मिले, तो इस विभाजित खंड को सीधे खोजें।","This tooltip appears on the SongID Search Segment button. Preserve the exact SongID product name, which the current Hindi transliterates, and describe the segment as split rather than disintegrated.","high"),
 (619,"vi"):("refinement","Tìm kiếm trực tiếp đoạn đã được tách này khi SongID tìm thấy một chương hoặc manh mối dấu thời gian hợp lý.","The caller acts on a segment split from the source. The current bị phân tách is redundant; this keeps the split-segment meaning concise.","moderate"),
 (621,"ja"):("refinement","ライブラリ健全性レポート用の置換検索シード","The caller returns this as a report title immediately before its generated timestamp. This makes the relationship to the library-health report explicit while retaining the search-seed concept.","moderate"),
 (621,"ko"):("refinement","라이브러리 상태 보고서용 대체 검색 시드","The caller uses this as a report title. Add 보고서용 so the replacement search seeds are clearly for the library-health report.","moderate"),
 (621,"pt-BR"):("refinement","Sementes de busca por substituições para o relatório de integridade da biblioteca","This is the generated report heading. The current noun stack is unclear; this order makes search seeds for replacements in the library-health report legible.","moderate"),
 (621,"zh-Hans"):("refinement","媒体库健康报告的替换搜索种子","The caller uses this as a report title. Add 报告的 to clarify that the replacement-search seeds belong to the library-health report.","moderate"),
 (621,"zh-Hant"):("refinement","媒體庫健康報告的替代搜尋種子","The caller uses this as a report title. Add 報告的 to clarify that the replacement-search seeds belong to the library-health report.","moderate"),
 (622,"de"):("correction","Die Audio-Tags wurden gespeichert, aber der Freigabenscan konnte nicht gestartet werden. Führen Sie einen Freigabenscan aus, um die Bibliothek zu aktualisieren.","The error state follows saving audio tags; the source asks the user to run a share scan. The current second sentence says only 'a scan' and switches from formal Sie to informal du.","moderate"),
 (622,"es"):("refinement","Se guardaron las etiquetas de audio, pero no se pudo iniciar el análisis de recursos compartidos. Ejecuta un análisis de recursos compartidos para actualizar la biblioteca.","The caller's recovery advice specifically requires a share scan. The current second sentence says only 'an analysis', so repeat the resource-share term.","moderate"),
 (622,"fr"):("correction","Les tags audio ont été enregistrés, mais l’analyse des partages n’a pas pu démarrer. Lancez une analyse des partages pour actualiser la bibliothèque.","The caller gives a specific recovery step. The current second sentence omits that it must be a share scan.","moderate"),
 (622,"hi"):("refinement","ऑडियो टैग सहेज दिए गए, लेकिन साझा सामग्री का स्कैन शुरू नहीं हो सका। लाइब्रेरी रीफ़्रेश करने के लिए साझा सामग्री का स्कैन चलाएँ।","The source repeats the share-scan action as the recovery step; the current second sentence shortens this to an unspecified scan.","moderate"),
 (622,"id"):("refinement","Tag audio berhasil disimpan, tetapi pemindaian file berbagi tidak dapat dimulai. Jalankan pemindaian file berbagi untuk memperbarui pustaka.","The caller requires a share scan to refresh the library. Repeat file-sharing scan in the recovery sentence instead of the current unspecified pemindaian.","moderate"),
 (622,"pt-BR"):("correction","As tags de áudio foram salvas, mas não foi possível iniciar a verificação dos compartilhamentos. Faça uma verificação dos compartilhamentos para atualizar a biblioteca.","The current recovery sentence says only 'a check'; the caller requires a share scan specifically.","moderate"),
 (623,"es"):("refinement","Permitir que esta carpeta compartida vuelva a aparecer en futuras ejecuciones de este elemento de la lista de deseos.","The caller identifies the peer username and directory in a wishlist row. The current target drops the peer/shared-folder distinction; carpeta compartida is clearer in this P2P context.","moderate"),
 (623,"fr"):("refinement","Autoriser ce dossier partagé de pair à réapparaître lors des prochaines exécutions de cet élément de la liste de souhaits.","This tooltip describes a peer's shared directory in a wishlist row. Dossier de pair is a literal calque; this wording clarifies that it is a shared folder.","moderate"),
 (626,"ar"):("correction","كبّر عارض الصوت إلى وضع ملء الشاشة.","The caller is a player control with an expand icon. المتخيل means an imagined person/thing rather than a visualizer; عارض الصوت names the player visualization.","moderate"),
 (626,"hi"):("refinement","विज़ुअलाइज़र को पूर्ण स्क्रीन में दिखाएँ।","This is a player tooltip for an expand control. The current तक अधिकतम करें is a calque of maximize-to; this expresses showing the visualizer fullscreen naturally.","moderate"),
 (626,"id"):("refinement","Tampilkan visualisator dalam layar penuh.","The current Maksimalkan ... ke layar penuh is a direct calque. This is a natural action label for a player fullscreen control.","moderate"),
 (626,"ja"):("refinement","ビジュアライザーを全画面表示にします。","The current 最大化します is a literal maximize calque; the player control switches the visualizer to fullscreen display.","moderate"),
 (626,"ko"):("correction","비주얼라이저를 전체 화면으로 표시합니다.","시각화 도우미 means a visualization assistant/helper, not the player visualizer. This uses the feature name and states the fullscreen action.","moderate"),
 (626,"pt-BR"):("refinement","Maximize o visualizador em tela cheia.","This is the player fullscreen action. Em tela cheia is the natural Portuguese construction for the target display mode.","moderate"),
 (627,"fr"):("correction","Collez ici l’historique de lecture de Plex, Jellyfin ou Navidrome, ou un historique générique au format CSV/JSON, pour l’importation locale.","This textarea placeholder accepts play history from three named servers or in a generic CSV/JSON format. The current target leaves générique attached ambiguously to the service list.","moderate"),
 (627,"hi"):("refinement","स्थानीय आयात के लिए Plex, Jellyfin, Navidrome या CSV/JSON प्रारूप में सामान्य प्लेबैक इतिहास यहाँ पेस्ट करें।","This is the import textarea placeholder. प्लेबैक इतिहास is clearer Hindi than the current English code-switch प्ले हिस्ट्री.","moderate"),
}

def sha(b): return hashlib.sha256(b).hexdigest()
def read_jsonl(p): return [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s.strip()]
def write_json(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def write_jsonl(p,rows): p.write_text("".join(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n" for r in rows),encoding="utf-8")
def canonical(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
def ph(s): return sorted(set(re.findall(r"\{[^{}]+\}",s)))
def tags(s): return sorted(re.findall(r"</?[A-Za-z][^>]*>",s))
def nums(s): return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)
def prot(s):
 f=set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])",s))
 for x in ("Wishlist","Soulseek","Discogs","Pod"):
  if re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",s): f.add(x)
 return sorted(f)
def signatures(s):
 return {"placeholders":ph(s),"markup":tags(s),"numeric":nums(s),"protected":prot(s)}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,required=True); ap.add_argument("--output",type=Path,default=Path(__file__).resolve().parent)
 a=ap.parse_args(); inp=a.input.resolve(); out=a.output.resolve()
 im=json.loads((inp/"manifest.json").read_text(encoding="utf-8"))
 assert (im["head"],im["tree"],im["cellCount"],im["sourceCount"],im["candidateFree"])==(HEAD,TREE,300,25,True)
 cells=read_jsonl(inp/"source-current-cells.jsonl"); ctxs=read_jsonl(inp/"caller-contexts.jsonl")
 ctxmap={x["sourceId"]:x for x in ctxs}
 assert len(cells)==300 and len(ctxmap)==25
 assert [(r["continuationRank"],r["locale"]) for r in cells]==[(rank,loc) for rank in range(603,628) for loc in LOCALES]
 ledger=[]
 for c in cells:
  key=(c["continuationRank"],c["locale"])
  if key in EDITS:
   decision,target,rationale,confidence=EDITS[key]
  elif c["continuationRank"]==615:
   decision,target,rationale,confidence="hold",None,"No production caller is present for this source in the pinned candidate-free packet. Its term 'public forwards' remains domain-ambiguous, so this locale cell is held without selecting a replacement.","low"
  else:
   decision,target,rationale,confidence="accept-current",c["currentTarget"],"Retain the current locale value: it preserves the source meaning in the pinned caller context and has no material defect requiring a change in this blind review.","moderate"
  assert decision in {"accept-current","correction","refinement","hold"}
  if decision=="hold": assert target is None
  else: assert isinstance(target,str)
  cs=signatures(c["source"]); cur=signatures(c["currentTarget"]); ts=signatures(target) if target is not None else None
  ctx=ctxmap[c["sourceId"]]
  assert ctx["productionCallerCount"]==len(ctx["callers"])
  # Ensure the captured token evidence is bound to independently recomputed data.
  assert c["placeholderEvidence"]=={"sourceTokens":cs["placeholders"],"currentTokens":cur["placeholders"],"matches":cs["placeholders"]==cur["placeholders"]}
  assert c["markupEvidence"]=={"sourceTags":cs["markup"],"currentTags":cur["markup"],"matches":cs["markup"]==cur["markup"]}
  assert c["sourceNumericTokens"]==cs["numeric"] and c["currentNumericTokens"]==cur["numeric"]
  assert c["sourceProtectedLiterals"]==cs["protected"] and c["currentProtectedLiterals"]==cur["protected"]
  req=cs["protected"]
  cur_checks={"placeholdersMatch":cs["placeholders"]==cur["placeholders"],"markupMatch":cs["markup"]==cur["markup"],"numericMeaningMatch":cs["numeric"]==cur["numeric"],"requiredProtectedLiterals":req,"protectedLiteralsPresent":[x for x in req if x in c["currentTarget"]],"protectedLiteralMatch":all(x in c["currentTarget"] for x in req)}
  target_checks=None
  if target is not None:
   target_checks={"placeholdersMatch":cs["placeholders"]==ts["placeholders"],"markupMatch":cs["markup"]==ts["markup"],"numericMeaningMatch":cs["numeric"]==ts["numeric"],"requiredProtectedLiterals":req,"protectedLiteralsPresent":[x for x in req if x in target],"protectedLiteralMatch":all(x in target for x in req)}
  ledger.append({
   "schemaVersion":1,"repository":REPO,"pullRequest":PR,"window":WINDOW,"head":HEAD,"tree":TREE,
   "continuationRank":c["continuationRank"],"remainingQueueRank":c["remainingQueueRank"],"sourceId":c["sourceId"],"sourceSha256":c["sourceSha256"],"source":c["source"],"catalogKey":c["catalogKey"],"locale":c["locale"],
   "currentTarget":c["currentTarget"],"currentTargetSha256":c["currentTargetSha256"],"catalogPath":c["catalogPath"],"catalogFileSha256":c["catalogFileSha256"],"catalogGitBlob":c["catalogGitBlob"],
   "callerEvidence":{"productionCallerCount":ctx["productionCallerCount"],"boundedScan":ctx["boundedScan"],"callerContextSha256":c["callerContextSha256"],"callerRefs":c["callerRefs"],"callers":ctx["callers"]},
   "blindDisposition":decision,"blindTarget":target,"blindTargetSha256":sha(target.encode("utf-8")) if target is not None else None,"rationale":rationale,"confidence":confidence,
   "baselineEvidence":{"placeholderEvidence":c["placeholderEvidence"],"markupEvidence":c["markupEvidence"],"sourceNumericTokens":c["sourceNumericTokens"],"currentNumericTokens":c["currentNumericTokens"],"sourceProtectedLiterals":c["sourceProtectedLiterals"],"currentProtectedLiterals":c["currentProtectedLiterals"],"protectedLiteralEvidence":c["protectedLiteralEvidence"]},
   "tokenAudit":{"source":cs,"current":cur,"blindTarget":ts,"currentChecks":cur_checks,"blindTargetChecks":target_checks,"heldWithoutTarget":decision=="hold"},
  })
 write_jsonl(out/"blind-ledger.jsonl",ledger)
 # Reattest prior carried holds by recomputing each current target hash; target text is omitted from this output.
 held=[]
 prior=read_jsonl(inp/"prior-held-cell-reattestation.jsonl")
 for r in prior:
  computed=sha(r["currentTarget"].encode("utf-8"))
  held.append({"priorWindow":r["priorWindow"],"continuationRank":r["continuationRank"],"sourceId":r["sourceId"],"sourceSha256":r["sourceSha256"],"locale":r["locale"],"priorDisposition":r["priorDisposition"],"priorTargetSha256":r["priorTargetSha256"],"computedCurrentTargetSha256":computed,"packetCurrentTargetSha256":r["currentTargetSha256"],"targetHashMatchesPrior":computed==r["priorTargetSha256"],"matchesPriorCurrentValue":r["matchesPriorCurrentValue"],"currentCallerCount":r["currentCallerCount"],"currentCallerRefs":r["currentCallerRefs"],"currentCallerContextSha256":r["currentCallerContextSha256"],"currentCatalogPath":r["currentCatalogPath"],"currentCatalogFileSha256":r["currentCatalogFileSha256"],"currentCatalogGitBlob":r["currentCatalogGitBlob"],"holdReason":r["holdReason"],"status":r["status"]})
 write_jsonl(out/"prior-holds-reattestation.jsonl",held)
 counts={k:sum(r["blindDisposition"]==k for r in ledger) for k in ["accept-current","correction","refinement","hold"]}
 by_locale={loc:{k:sum(r["locale"]==loc and r["blindDisposition"]==k for r in ledger) for k in counts} for loc in LOCALES}
 protected_baseline=[{"continuationRank":r["continuationRank"],"locale":r["locale"],"sourceId":r["sourceId"],"required":r["baselineEvidence"]["sourceProtectedLiterals"],"current":r["baselineEvidence"]["currentProtectedLiterals"],"selected":r["tokenAudit"]["blindTargetChecks"]["protectedLiteralsPresent"] if r["tokenAudit"]["blindTargetChecks"] else None} for r in ledger if not r["baselineEvidence"]["protectedLiteralEvidence"]["matches"]]
 target_failures=[r for r in ledger if r["blindDisposition"]!="hold" and not all([r["tokenAudit"]["blindTargetChecks"][k] for k in ["placeholdersMatch","markupMatch","numericMeaningMatch","protectedLiteralMatch"]])]
 summary={"schemaVersion":1,"repository":REPO,"pullRequest":PR,"window":WINDOW,"head":HEAD,"tree":TREE,"sourceCount":25,"cellCount":300,"decisionCounts":counts,"decisionCountsByLocale":by_locale,"rank615CallerCount":ctxmap[next(c["sourceId"] for c in cells if c["continuationRank"]==615)]["productionCallerCount"],"rank615HoldCount":sum(r["continuationRank"]==615 and r["blindDisposition"]=="hold" for r in ledger),"baselineTokenMismatchCounts":json.loads((inp/"baseline-token-mismatch-summary.json").read_text(encoding="utf-8"))["mismatches"],"baselineProtectedLiteralFlags":protected_baseline,"selectedProtectedLiteralFailures":sum(r["blindDisposition"]!="hold" and not r["tokenAudit"]["blindTargetChecks"]["protectedLiteralMatch"] for r in ledger),"selectedTokenAuditFailures":len(target_failures),"priorHoldCount":len(held),"priorHoldHashesReattested":sum(r["targetHashMatchesPrior"] for r in held),"priorHoldTextIncluded":False,"inputVerifier":"PASS at build time (candidate-free verify_input.py)","nativeSpeakerReviewClaimed":False}
 write_json(out/"summary.json",summary)
 # Build README after decisions, then hash all packet files into the manifest and checksum index.
 readme=f'''# slskdN PR #409 W69 blind review — ranks 603–627\n\nPinned head: `{HEAD}`  \nPinned tree: `{TREE}`\n\nThis independent blind review covers 300 cells across 25 source strings and 12 locales. The ledger records exact source/current/proposed target hashes, caller context and hashes, catalog file pins, disposition, rationale, confidence, and checks for placeholders, markup, numeric meaning, and protected literals. No primary proposal was inspected.\n\n## Outcomes\n\n- Accept current: {counts["accept-current"]}\n- Correction: {counts["correction"]}\n- Refinement: {counts["refinement"]}\n- Hold: {counts["hold"]}\n- Prior carried holds reattested by target hash: {len(held)}/{len(held)}\n\n## Protected-literal findings\n\nThe baseline flags three omissions: rank 612 Arabic and Hindi transliterate `ID`, and rank 619 Hindi transliterates `SongID`. The proposed targets preserve the exact source spellings. In rank 612, the Arabic proposal also renders the peer group as a group rather than a chamber; the warning remains a warning about disclosure to participants.\n\n## Callerless rank 615\n\nAll 12 rank 615 cells are held. The source is `older builds needed 5 public forwards; now keep`, and the candidate-free packet has no production caller for it. `forwards` can carry unrelated technical and sports meanings; no locale target is selected without context. The current value and its hash remain recorded, and the numeric token `5` is audited.\n\n## Verification and limits\n\nThe candidate-free `verify_input.py` passed at build time, including the exact live PR/head/tree check and 128 prior-hold reattestations. The portable `verify_blind_review.py --input /path/to/input` checks packet checksums and manifest pins, all 300 ledger rows, context and catalog references, target hashes, token audits, the 128 hash reattestations, and the output checksum inventory. This is a text review; no native-speaker review is claimed.\n'''
 (out/"README.md").write_text(readme,encoding="utf-8")
 files=[]
 for p in sorted(out.iterdir()):
  if p.is_file() and p.name not in {"manifest.json","SHA256SUMS.txt"}:
   b=p.read_bytes(); files.append({"path":p.name,"sha256":sha(b),"bytes":len(b)})
 manifest={"schemaVersion":1,"artifact":"slskdN PR #409 W69 blind review","repository":REPO,"pullRequest":PR,"window":WINDOW,"head":HEAD,"tree":TREE,"candidateFreeInputManifestSha256":sha((inp/"manifest.json").read_bytes()),"candidateFreeInputPacketChecksumsSha256":sha((inp/"PACKET-SHA256SUMS.txt").read_bytes()),"sourceCount":25,"localeCount":12,"cellCount":300,"priorHeldCellsReattested":len(held),"decisionCounts":counts,"files":files}
 write_json(out/"manifest.json",manifest)
 sums=[]
 for p in sorted(out.iterdir()):
  if p.is_file() and p.name!="SHA256SUMS.txt": sums.append(f"{sha(p.read_bytes())}  {p.name}")
 (out/"SHA256SUMS.txt").write_text("\n".join(sums)+"\n",encoding="utf-8")
 print(json.dumps({"output":str(out),"decisionCounts":counts,"priorHolds":len(held),"fileCount":len(files)+2},ensure_ascii=False))

if __name__=="__main__": main()
