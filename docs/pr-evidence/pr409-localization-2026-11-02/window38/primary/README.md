# slskdN PR #409 W38 primary semantic review

This packet reviews the next 25 disjoint source IDs at pinned PR head `2be3fa4dd46a0f0f49adad342f289721e4777035` (tree `f838ae565086dec8639f8a54aa4c7d4572342b5f`, `src/web/src` subtree `594e56c3f439bad476b1bd57e0de1665c62fa1bb`). The review is read-only and covers the exact current locale catalogs and caller contexts.

## Scope and overlap

- 269 pending cells across 11 locales: ar 25, de 24, fr 24, hi 25, id 24, ja 24, ko 25, pt-BR 24, vi 24, zh-Hans 25, zh-Hant 25.
- Previous exact manual windows 1–37: 10874 cells / 922 source IDs; W38 cell and source-key overlap: 0.
- Selected sorted source-key positions 1–25 from the 4728 IDs remaining after W1–W37; ordered IDs are in `manifest.json` and `preflight.json`.
- Frozen formal lane: 4,800 cells. W38 preserves 25 selected Spanish cells in that lane and 0 additional Spanish exact-reuse cells; no Spanish verdicts are emitted.
- Previous applied corrections: 1455; W38 applied-correction overlap: 0.
- Preserved 50 explicit prior hold rows across seven unique held source IDs; all current targets and all caller refs available in the original records were re-attested at W38 head. Hold/source-key overlap: 0.
- Decisions: 215 keep, 54 correction candidates, 0 uncertain.
- Current source, target, catalog, caller-file and caller-line pins match the exact pushed head. 48 unique caller lines and 498 row-to-caller references were checked.
- All 54 candidate targets differ from current targets and preserve source placeholders and reviewer-protected literals; candidate no-op count: 0.
- Prior W37 candidate re-attestation: 42 proposals, 0 current-target no-ops.
- The Pod help fragment is concatenated after a separately localized Enable label and the feature.Pods code literal; sentence-level review remains necessary before applying its row-level proposals.
- No catalogs, workflows, or PR state were changed. No tests, builds, scans, CI, or releases were run.

## Correction candidates

- `src_084ee5f9dc342f13` — **Unable to save release radar subscription.**: 4 locale correction candidate(s).
  - `zh-Hans`: `无法保存发布雷达订阅。` → `无法保存发行雷达订阅。` (moderate; The caller is an artist release alert; 发行 is the music-release term here.)
  - `fr`: `Impossible d'enregistrer l'abonnement au radar de publication.` → `Impossible d’enregistrer l’abonnement au radar des sorties.` (high; Publication means publishing; the panel subscribes to alerts for music releases.)
  - `ar`: `غير قادر على حفظ اشتراك الرادار الإصدار.` → `تعذّر حفظ الاشتراك في رادار الإصدارات.` (high; The current Arabic order is unnatural; this names a subscription to new-release alerts.)
  - `zh-Hant`: `無法儲存發布雷達訂閱。` → `無法儲存發行雷達訂閱。` (moderate; The caller is an artist release alert; 發行 is the music-release term here.)
- `src_0894b7f847440bec` — **Player hidden**: 8 locale correction candidate(s).
  - `zh-Hans`: `玩家隐藏` → `播放器已隐藏` (high; 玩家 means a person or game player; this UI status is for the music player.)
  - `de`: `Spieler ausgeblendet` → `Player ausgeblendet` (moderate; Spieler suggests a person or game player; the icon and caller identify the media player.)
  - `fr`: `Joueur caché` → `Lecteur masqué` (high; Joueur means a person or game player; this caller is the media player.)
  - `pt-BR`: `Jogador oculto` → `Reprodutor oculto` (high; Jogador means a person or game player; this caller is the media player.)
  - `ar`: `اللاعب مخفي` → `تم إخفاء مشغل الوسائط` (high; اللاعب means a person or athlete; this status refers to the media player.)
  - `zh-Hant`: `玩家隱藏` → `播放器已隱藏` (high; 玩家 means a person or game player; this UI status is for the music player.)
  - `vi`: `Người chơi bị ẩn` → `Trình phát đã bị ẩn` (high; Người chơi means a person or game player; this caller is the media player.)
  - `id`: `Pemain disembunyikan` → `Pemutar media disembunyikan` (high; Pemain means a person or game player; this caller is the media player.)
- `src_08b30b1aba98a1d4` — **Native MilkDrop shape fragment**: 3 locale correction candidate(s).
  - `zh-Hans`: `原生奶滴形状片段` → `原生 MilkDrop 形状片段` (high; MilkDrop is the visualizer name; 奶滴 translates its parts literally and loses the product name.)
  - `hi`: `देशी मिल्कड्रॉप आकार का टुकड़ा` → `मूल MilkDrop आकार का अंश` (moderate; MilkDrop is the visualizer name; preserve the exact product name rather than transliterating it as milk drop.)
  - `zh-Hant`: `原生奶滴形狀片段` → `原生 MilkDrop 形狀片段` (high; MilkDrop is the visualizer name; 奶滴 translates its parts literally and loses the product name.)
- `src_08cddda722527ffd` — **Search Segment**: 3 locale correction candidate(s).
  - `zh-Hans`: `搜索部分` → `搜索片段` (high; This button searches tracks derived from a segment; 部分 means a generic part.)
  - `ar`: `قسم البحث` → `ابحث عن المقطع` (high; This is an action to search the selected audio segment; قسم means a section.)
  - `zh-Hant`: `搜尋部分` → `搜尋片段` (high; This button searches tracks derived from a segment; 部分 means a generic part.)
- `src_08f271887ce94707` — **M**: 5 locale correction candidate(s).
  - `zh-Hans`: `中号` → `M` (high; The same label is a keyboard key, memory-size unit, and QR/error-correction code; preserve the Latin symbol.)
  - `hi`: `एम` → `M` (high; The same label is a keyboard key, memory-size unit, and QR/error-correction code; preserve the Latin symbol.)
  - `ar`: `م` → `M` (high; The same label is a keyboard key, memory-size unit, and QR/error-correction code; preserve the Latin symbol.)
  - `ko`: `중` → `M` (high; The same label is a keyboard key, memory-size unit, and QR/error-correction code; preserve the Latin symbol.)
  - `zh-Hant`: `中號` → `M` (high; The same label is a keyboard key, memory-size unit, and QR/error-correction code; preserve the Latin symbol.)
- `src_090269ba94d47580` — **Target Peer IDs (comma-separated)**: 1 locale correction candidate(s).
  - `fr`: `ID d'homologue cible (séparés par des virgules)` → `IDs des pairs cibles (séparés par des virgules)` (high; The source has plural IDs; make the French noun plural to agree with séparés.)
- `src_090512d93fcc3c0d` — **Integrations**: 1 locale correction candidate(s).
  - `ar`: `التكامل` → `التكاملات` (moderate; The settings page groups several integration providers, so the plural heading is more exact.)
- `src_090940bae1e24f54` — **Query:**: 6 locale correction candidate(s).
  - `zh-Hans`: `询问：` → `查询：` (high; This labels a SongID search query value; 询问 means an inquiry or question.)
  - `hi`: `सवाल:` → `खोज क्वेरी:` (high; This labels the submitted SongID search query, not a question.)
  - `ar`: `استفسار:` → `الاستعلام:` (high; استفسار means an inquiry; this label introduces the actual search query.)
  - `ko`: `질문:` → `검색어:` (high; 질문 means a question; this label introduces the actual search term.)
  - `zh-Hant`: `詢問：` → `查詢：` (high; 詢問 means an inquiry or question; this label introduces the actual search query.)
  - `id`: `Pertanyaan:` → `Kueri:` (high; Pertanyaan means a question; this label introduces the actual search query.)
- `src_09155891b81b403c` — **Loading shares**: 7 locale correction candidate(s).
  - `zh-Hans`: `加载共享` → `正在加载共享内容` (moderate; The inbox is loading shared items; adding 内容 makes the status phrase natural and clear.)
  - `hi`: `शेयर लोड हो रहे हैं` → `साझा की गई फ़ाइलें लोड हो रही हैं` (high; शेयर is ambiguous with financial shares; the inbox is loading shared files.)
  - `de`: `Laden von Anteilen` → `Freigaben werden geladen` (high; Anteile suggests financial or fractional shares; Freigaben is the usual file-sharing term.)
  - `ar`: `جارٍ تحميل الأسهم` → `جارٍ تحميل الملفات المشتركة` (high; الأسهم means financial shares; the inbox is loading files that were shared.)
  - `zh-Hant`: `載入共享` → `正在載入共享內容` (moderate; Adding 內容 clarifies that the inbox is loading shared items.)
  - `vi`: `Đang tải lượt chia sẻ` → `Đang tải nội dung được chia sẻ` (high; Lượt chia sẻ sounds like a count of shares; this is a loading status for shared content.)
  - `id`: `Memuat bagian` → `Memuat file yang dibagikan` (high; Bagian means a part or section; the inbox is loading files shared with the user.)
- `src_091a998e1a186d71` — **Stop broadcast**: 1 locale correction candidate(s).
  - `hi`: `प्रसारण बंद करो` → `प्रसारण रोकें` (moderate; Use the standard polite imperative for a room-control button.)
- `src_09230b3dbc35635f` — **Fail**: 5 locale correction candidate(s).
  - `hi`: `असफल` → `विफलता` (moderate; The label counts failed checks; the noun विफलता fits this statistic better than an adjective.)
  - `fr`: `Échouer` → `Échec` (high; Échouer is an infinitive; the statistic label names a failure.)
  - `pt-BR`: `Falhar` → `Falha` (high; Falhar is an infinitive; the statistic label names a failure.)
  - `ar`: `يفشل` → `فشل` (high; يفشل is a verb; the statistic and status label needs a noun.)
  - `ko`: `실패하다` → `실패` (high; 실패하다 is a verb; this statistic label names the failed outcome.)
- `src_0924a671165fef5a` — **Cooldown**: 6 locale correction candidate(s).
  - `hi`: `शांत हो जाओ` → `कूलडाउन अवधि` (high; शांत हो जाओ is an instruction to calm down; this label names an automation waiting interval.)
  - `fr`: `Refroidir` → `Période d’attente` (high; Refroidir is a verb; the value beside this label is an automation waiting period.)
  - `pt-BR`: `Esfriar` → `Intervalo de espera` (high; Esfriar is a verb; the value beside this label is an automation waiting interval.)
  - `ar`: `ترطيب` → `فترة الانتظار` (high; ترطيب means moistening or cooling; this automation label names a waiting interval.)
  - `vi`: `Thời gian hồi chiêu` → `Thời gian chờ` (moderate; The caller is an automation recipe interval, not a game ability cooldown.)
  - `id`: `Pendinginan` → `Masa jeda` (high; Pendinginan means cooling; this automation label names a pause between runs.)
- `src_093fc8439d0ade12` — **in the server configuration to use pod rooms and discovery.**: 3 locale correction candidate(s).
  - `ar`: `في تكوين الخادم لاستخدام غرف الكبسولة والاكتشاف.` → `في إعدادات الخادم لاستخدام غرف Pod وميزة الاكتشاف.` (moderate; غرف الكبسولة is a literal capsule-room rendering; retain the product term Pod.)
  - `ko`: `포드 룸 및 검색을 사용하려면 서버 구성에서` → `포드 룸 및 탐색 기능을 사용하려면 서버 구성에서` (moderate; Discovery is broader than search here; 탐색 기능 better names the discovery feature.)
  - `vi`: `trong cấu hình máy chủ để sử dụng phòng nhóm và khám phá.` → `trong cấu hình máy chủ để sử dụng phòng Pod và tính năng khám phá.` (moderate; phòng nhóm means group rooms; retain the product term Pod and name discovery as a feature.)
- `src_094e2630f1d48460` — **No artist data available**: 1 locale correction candidate(s).
  - `ar`: `لا توجد بيانات الفنان المتاحة` → `لا تتوفر بيانات للفنان` (high; The current Arabic construction is awkward; this is the empty artist-data state.)

## Prior holds and review limitations

Byte-exact copies of all explicit active prior hold ledgers are in `prior-holds/`; `preserved-prior-holds.jsonl` joins each original row to its source-ledger path/hash, and `hold-revalidation.jsonl` records current-head target and available caller re-attestation. All 50 held targets remain unchanged. W38 adds no new hold; the W34 French uncertain cell was independently resolved as keep-current.
No native-speaker signoff or browser/visual review was performed in this primary packet. Translation confidence is high for direct semantic errors and exact-key fixes, moderate overall; native locale review and headed browser work remain outstanding in the parent workflow.

## Files

- `review-input.jsonl`: exact frozen pending source/current target rows with caller context.
- `review-decisions.jsonl`: one primary verdict per cell.
- `review-evidence.jsonl` and `correction-candidates.jsonl`: row-level source/current/candidate hashes, reasons, caller refs, and literal checks.
- `source-attestation.jsonl` and `caller-attestation.jsonl`: source and caller pins re-attested at the exact head.
- `preserved-prior-routed.jsonl` / `preserved-spanish-reused.jsonl`: Spanish formal-lane and exact-reuse cells left outside W38 decisions.
- `preserved-prior-holds.jsonl`, `hold-revalidation.jsonl`, and `prior-holds/`: all explicit prior hold rows and their exact source ledgers.
- `window38-review-holds.jsonl`: empty new-hold ledger; all prior holds remain separately preserved.
- `manifest.json`, `preflight.json`, `freeze-summary.json`, and `formal-cell-ids.jsonl`: window derivation and overlap evidence.
- `review-summary.json`: decision counts and remaining native/browser/JIT gaps.
- `freeze_window38.py` and `build_review_packet.py`: scratch-only packet generation scripts.

Cross-review is required before any candidate is applied.
