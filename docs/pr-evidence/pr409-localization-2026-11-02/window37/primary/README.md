# slskdN PR #409 W37 primary semantic review

This packet reviews the next 25 disjoint source IDs at pinned PR head `2be3fa4dd46a0f0f49adad342f289721e4777035` (tree `f838ae565086dec8639f8a54aa4c7d4572342b5f`, `src/web/src` subtree `594e56c3f439bad476b1bd57e0de1665c62fa1bb`). The review is read-only and covers the exact current locale catalogs and caller contexts.

## Scope and overlap

- 273 pending cells across 11 locales: ar 25, de 24, fr 25, hi 25, id 24, ja 25, ko 25, pt-BR 25, vi 25, zh-Hans 25, zh-Hant 25.
- Previous exact manual windows 1–36: 10601 cells / 897 source IDs; W37 cell and source-key overlap: 0.
- Frozen formal lane: 4,800 cells. W37 preserves 24 selected Spanish cells in that lane and one additional Spanish cell marked exact prior reuse; no Spanish verdicts are emitted.
- Previous applied corrections: 1455; W37 applied-correction overlap: 0.
- Preserved 50 explicit prior hold rows across seven unique held source IDs; all current targets and all caller refs available in the original records were re-attested at W37 head. Hold/source-key overlap: 0.
- Decisions: 231 keep, 42 correction candidates, 0 uncertain.
- Current source, target, catalog, caller-file and caller-line pins match the exact pushed head. 35 unique caller lines and 383 row-to-caller references were checked.
- The 42 candidate targets preserve source placeholders and protected literals, including exact configuration key `transfers.download.auto_retry.enabled`, `URL`, `Discogs`, `Obfs4`, `AcoustID`, and `MusicBrainz` where applicable.
- No catalogs, workflows, or PR state were changed. No tests, builds, scans, CI, or releases were run.

## Correction candidates

- `src_0738bb3259fd619e` — **Auto-replace disabled. Automatic retry is separate; disable transfers.download.auto_retry.enabled to stop retries of failed downloads.**: 7 locale correction candidate(s).
  - `zh-Hans`: `自动替换已禁用。自动重试是分开的；禁用 Transfers.download.auto_retry.enabled 以停止重试失败的下载。` → `自动替换已禁用。自动重试是单独功能；要停止重试失败的下载，请禁用 transfers.download.auto_retry.enabled。` (high; The setting path is a case-sensitive configuration key; preserve its exact lowercase spelling.)
  - `hi`: `स्वतः-प्रतिस्थापन अक्षम. स्वचालित पुनः प्रयास अलग है; विफल डाउनलोड के पुनः प्रयास को रोकने के लिएTransfer.download.auto_retry.enabled को अक्षम करें।` → `स्वतः प्रतिस्थापन बंद है। स्वचालित पुनः प्रयास एक अलग सुविधा है; विफल डाउनलोड के पुनः प्रयास रोकने के लिए transfers.download.auto_retry.enabled को बंद करें।` (high; The current setting path changes the property name from transfers to Transfer; preserve the exact configuration key.)
  - `de`: `Automatisches Ersetzen deaktiviert. Der automatische Wiederholungsversuch ist separat; Deaktivieren Sie Transfers.download.auto_retry.enabled, um Wiederholungsversuche fehlgeschlagener Downloads zu stoppen.` → `Automatisches Ersetzen ist deaktiviert. Automatische Wiederholungen sind eine separate Funktion. Deaktivieren Sie transfers.download.auto_retry.enabled, um fehlgeschlagene Downloads nicht erneut zu starten.` (high; Preserve the exact configuration key and use a separate sentence for the disable instruction.)
  - `fr`: `Remplacement automatique désactivé. La nouvelle tentative automatique est distincte ; désactivez transfer.download.auto_retry.enabled pour arrêter les tentatives de téléchargement ayant échoué.` → `Le remplacement automatique est désactivé. La nouvelle tentative automatique est une fonction distincte ; désactivez transfers.download.auto_retry.enabled pour arrêter les nouvelles tentatives des téléchargements échoués.` (high; The current setting path is singularized as transfer; preserve the exact configuration key.)
  - `ar`: `تم تعطيل الاستبدال التلقائي. إعادة المحاولة التلقائية منفصلة؛ قم بتعطيل عمليات النقل.download.auto_retry.enabled لإيقاف إعادة محاولة التنزيلات الفاشلة.` → `تم تعطيل الاستبدال التلقائي. إعادة المحاولة التلقائية ميزة منفصلة؛ عطّل transfers.download.auto_retry.enabled لإيقاف إعادة محاولة التنزيلات الفاشلة.` (high; The current target translates part of the configuration key; preserve the exact lowercase key.)
  - `zh-Hant`: `自動替換已停用。自動重試是分開的；停用 Transfers.download.auto_retry.enabled 以停止重試失敗的下載。` → `自動替換已停用。自動重試是另一項功能；若要停止重試失敗的下載，請停用 transfers.download.auto_retry.enabled。` (high; The setting path must keep its exact lowercase spelling.)
  - `vi`: `Tự động thay thế bị vô hiệu hóa. Việc thử lại tự động là riêng biệt; vô hiệu hóa transfer.download.auto_retry.enabled để ngừng thử lại các lần tải xuống không thành công.` → `Tự động thay thế đã tắt. Tính năng thử lại tự động là riêng biệt; để ngừng thử lại các lượt tải xuống thất bại, hãy tắt transfers.download.auto_retry.enabled.` (high; The current setting path is singularized as transfer; preserve the exact configuration key.)
- `src_076f9c8cff1db724` — **Record the local acceptance decision for this release-candidate recommendation.**: 2 locale correction candidate(s).
  - `fr`: `Enregistrez la décision d’acceptation locale pour cette recommandation de candidat à la libération.` → `Enregistrez la décision d’acceptation locale pour cette recommandation concernant la version candidate.` (high; “Libération” reads as liberation; this caller concerns a software release-candidate recommendation.)
  - `id`: `Catat keputusan penerimaan lokal untuk rekomendasi kandidat pelepasliaran ini.` → `Catat keputusan penerimaan lokal untuk rekomendasi kandidat rilis ini.` (high; “Pelepasliaran” refers to releasing something into the wild; this caller concerns a software release candidate.)
- `src_077506f3bbc87b87` — **Chromaprint sample rate**: 1 locale correction candidate(s).
  - `id`: `Kecepatan sampel Chromaprint` → `Laju sampel Chromaprint` (moderate; For an audio setting, “laju sampel” names sample rate; “kecepatan sampel” reads as sample speed.)
- `src_07ac461a993457c4` — **Remote Path**: 1 locale correction candidate(s).
  - `hi`: `सुदूर पथ` → `दूरस्थ पथ` (moderate; This label names an FTP remote filesystem path; “दूरस्थ” is the usual technical rendering of remote.)
- `src_07c0b991c768e218` — **Incoming search concurrency**: 6 locale correction candidate(s).
  - `hi`: `आने वाली खोज समवर्तीता` → `एक साथ आने वाली खोजों की संख्या` (moderate; The current construction is an awkward calque; this numeric field controls how many incoming searches can run at once.)
  - `fr`: `Concurrence de recherche entrante` → `Nombre de recherches entrantes simultanées` (high; “Concurrence” suggests competition; the setting controls concurrent incoming searches.)
  - `pt-BR`: `Simultaneidade de pesquisa de entrada` → `Número de pesquisas recebidas simultaneamente` (moderate; This numeric field controls how many incoming searches can be processed at once.)
  - `ar`: `تزامن البحث الوارد` → `عدد عمليات البحث الواردة المتزامنة` (moderate; Name the number of incoming search requests that may run concurrently.)
  - `vi`: `Đồng thời tìm kiếm đến` → `Số lượt tìm kiếm đến đồng thời` (moderate; The current phrase is ungrammatical; this names the count of incoming searches at the same time.)
  - `id`: `Konkurensi pencarian masuk` → `Jumlah pencarian masuk bersamaan` (moderate; This numeric field controls the number of searches that can arrive concurrently.)
- `src_07ce8b8a99bc57e9` — **Topic URL**: 6 locale correction candidate(s).
  - `de`: `Thema URL` → `Themen-URL` (moderate; Use the German compound for the URL of an ntfy topic.)
  - `fr`: `Sujet URL` → `URL du sujet` (moderate; Put URL before the topic noun in this French field label.)
  - `pt-BR`: `Tópico URL` → `URL do tópico` (moderate; Use the natural Portuguese order for a topic URL.)
  - `ar`: `موضوع URL` → `عنوان URL للموضوع` (moderate; This is the URL address for an ntfy topic; retain the protected acronym URL.)
  - `vi`: `Chủ đề URL` → `URL của chủ đề` (moderate; Use the natural Vietnamese possessive order for the topic URL.)
  - `id`: `Topik URL` → `URL topik` (moderate; Use the natural Indonesian order for a topic URL.)
- `src_07ceeb4bc33842b0` — **Discogs Release/Master ID**: 5 locale correction candidate(s).
  - `zh-Hans`: `Discogs 发布/主 ID` → `Discogs 发行版/母版 ID` (moderate; “发布/主” reads as publish/main; distinguish the Discogs Release and Master record types.)
  - `fr`: `Discogs Version/ID principal` → `ID de sortie/master Discogs` (moderate; “Version/ID principal” loses the Discogs Master entity; preserve the Release/Master distinction.)
  - `pt-BR`: `Discogs Liberação/ID mestre` → `ID de lançamento/master do Discogs` (high; “Liberação” reads as liberation; this field accepts Discogs release or master identifiers.)
  - `zh-Hant`: `Discogs 發佈/主 ID` → `Discogs 發行版／母版 ID` (moderate; “發佈/主” reads as publish/main; distinguish the Discogs Release and Master record types.)
  - `vi`: `Discogs Phát hành/ID chính` → `ID bản phát hành/bản master của Discogs` (moderate; The current wording turns release/master into a verb and a generic main ID; name the two Discogs record types.)
- `src_07d70633fc2bb901` — **Video:**: 1 locale correction candidate(s).
  - `vi`: `Băng hình:` → `Video:` (high; “Băng hình” means videotape; the source is a media-property label for video content.)
- `src_07daadb6ed60272f` — **Already joined. Press Enter to open.**: 2 locale correction candidate(s).
  - `ja`: `すでに参加しています。 Enterを押して開きます。` → `すでに参加しています。Enterキーを押して開きます。` (moderate; Use the standard Japanese label Enterキー; the current text omits キー and inserts an unnatural space.)
  - `fr`: `Déjà rejoint. Appuyez sur Entrée pour ouvrir.` → `Vous avez déjà rejoint le salon. Appuyez sur Entrée pour l’ouvrir.` (moderate; The caller is a room-search hint; name the joined room and give a complete French instruction.)
- `src_07e56bf8696ead49` — **Estimated Size:**: 2 locale correction candidate(s).
  - `zh-Hans`: `预计尺寸：` → `预计大小：` (high; The caller reports totalSizeBytes; “尺寸” suggests physical dimensions instead of data size.)
  - `zh-Hant`: `預計尺寸：` → `預計大小：` (high; The caller reports totalSizeBytes; “尺寸” suggests physical dimensions instead of data size.)
- `src_07f4c78b5e0b3026` — **Opinion Statistics**: 1 locale correction candidate(s).
  - `ja`: `世論統計` → `評価統計` (high; The caller displays rating counts and score distribution; 世論統計 suggests public-opinion polling.)
- `src_07f68caa669e1912` — **Timing Obfuscation**: 1 locale correction candidate(s).
  - `id`: `Kebingungan Waktu` → `Pengaburan Waktu` (high; “Kebingungan Waktu” means time confusion; this privacy control obscures timing patterns.)
- `src_0831a9db649eaabc` — **Path:**: 6 locale correction candidate(s).
  - `zh-Hans`: `小路：` → `路径：` (high; The caller displays a filesystem/source path; 小路 means a footpath.)
  - `de`: `Weg:` → `Pfad:` (high; The caller displays a filesystem/source path; Pfad is the technical file-path term.)
  - `ar`: `طريق:` → `المسار:` (high; The caller displays a filesystem/source path; طريق means a road.)
  - `ko`: `길:` → `경로:` (high; The caller displays a filesystem/source path; 길 means a road or way.)
  - `zh-Hant`: `小路：` → `路徑：` (high; The caller displays a filesystem/source path; 小路 means a footpath.)
  - `vi`: `Con đường:` → `Đường dẫn:` (high; The caller displays a filesystem/source path; con đường means a road.)
- `src_0845f26528463f04` — **Opt-in public rendezvous is disabled**: 1 locale correction candidate(s).
  - `de`: `Öffentliches Rendezvous ist deaktiviert` → `Freiwilliges öffentliches Rendezvous ist deaktiviert.` (moderate; The source explicitly says opt-in; retain that consent-based participation in the status heading.)

## Prior holds and review limitations

Byte-exact copies of all explicit active prior hold ledgers are in `prior-holds/`; `preserved-prior-holds.jsonl` joins each original row to its source-ledger path/hash, and `hold-revalidation.jsonl` records current-head target and available caller re-attestation. The held targets remain unchanged. The older W34 French uncertain cell was independently resolved as keep-current, and W35 recorded no hold candidates.
No native-speaker signoff or browser/visual review was performed in this primary packet. Translation confidence is high for direct semantic errors and exact-key fixes, moderate overall; native locale review and headed browser work remain outstanding in the parent workflow.

## Files

- `review-input.jsonl`: exact frozen pending source/current target rows with caller context.
- `review-decisions.jsonl`: one primary verdict per cell.
- `review-evidence.jsonl` and `correction-candidates.jsonl`: row-level source/current/candidate hashes, reasons, caller refs, and literal checks.
- `source-attestation.jsonl` and `caller-attestation.jsonl`: source and caller pins re-attested at the exact head.
- `preserved-prior-routed.jsonl` / `preserved-spanish-reused.jsonl`: Spanish formal-lane and exact-reuse cells left outside W37 decisions.
- `preserved-prior-holds.jsonl`, `hold-revalidation.jsonl`, and `prior-holds/`: all explicit prior hold rows and their exact source ledgers.
- `manifest.json`, `preflight.json`, `freeze-summary.json`, and `formal-cell-ids.jsonl`: window derivation and overlap evidence.
- `review-summary.json`: decision counts and remaining native/browser/JIT gaps.
- `freeze_window37.py` and `build_review_packet.py`: scratch-only packet generation scripts.

Cross-review is required before any candidate is applied.
