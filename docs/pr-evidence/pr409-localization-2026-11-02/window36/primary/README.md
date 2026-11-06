# slskdN PR #409 W36 primary semantic review

This packet is a read-only primary semantic review of the next 25 ordered pending source IDs at PR #409 head `370c172e91935d7753c398eaf1b1fbc2e82f65ba` (tree `61bd0c6af797b0e810fdf9fad82c7d3a95c88b9c`, `src/web/src` subtree `594e56c3f439bad476b1bd57e0de1665c62fa1bb`). The selected source IDs and their caller contexts were frozen from the exact PR head in `review-input.jsonl`; the live PR remained OPEN/DRAFT/CLEAN at the same head when rechecked.

## Scope and routing

- 25 source IDs, 275 pending catalog cells across 11 locales (25 each): ar, de, fr, hi, id, ja, ko, pt-BR, vi, zh-Hans, zh-Hant.
- The same source IDs have 25 Spanish cells already routed through the formal review lane. They are recorded in `preserved-prior-routed.jsonl`, with current Spanish target hashes and formal cell IDs. No new Spanish verdicts are emitted.
- The standard all-locale window size is 300 cells; the 275-cell W36 pending set is the expected result of preserving those 25 formal-lane cells.
- Decisions: 236 keep, 39 correction candidates, 0 uncertain.
- Placeholders and protected literals were checked for every proposed correction. Source IDs and source hashes, current catalog values and hashes, catalog file hashes, and caller source file/line hashes were recomputed against the detached exact-head worktree.
- Caller attestation covers 429 row-to-caller references over 39 unique caller lines.
- No catalogs, workflows, or PR state were changed. No tests, builds, scans, CI, or releases were run.

## Correction candidates

- `src_05da9cbb4bd46c0f` — **Filter to {format} files**: 7 locale correction candidate(s).
  - `zh-Hans`: `过滤到 {format} 文件` → `筛选 {format} 文件` (high; “过滤到” is a calque; this source is a filter action on a file format.)
  - `ja`: `{format} ファイルにフィルターします` → `{format} ファイルに絞り込む` (high; The current “filter to” wording is unnatural in Japanese; this expresses filtering down to files of the selected format.)
  - `pt-BR`: `Filtrar para arquivos {format}` → `Filtrar arquivos {format}` (high; “Filtrar para arquivos” is an awkward calque; the control filters the list to files of this format.)
  - `ar`: `قم بالتصفية إلى ملفات {format}` → `صفِّ الملفات بصيغة {format}` (high; The current construction calques “filter to”; this is an imperative to filter files by format.)
  - `zh-Hant`: `過濾到 {format} 文件` → `篩選 {format} 檔案` (high; “過濾到” is a calque; this is the natural filter action for files of the selected format.)
  - `vi`: `Lọc thành các tệp {format}` → `Lọc các tệp {format}` (high; “Lọc thành” calques “filter to” and reads as changing files into something; this says to filter the listed files by format.)
  - `id`: `Filter ke file {format}` → `Saring file berformat {format}` (high; The current phrase uses “Filter” in English and “ke” makes the format relation awkward; this is a natural Indonesian filter label.)
- `src_05e48200ad1eb8ac` — **Live logs are disconnected**: 1 locale correction candidate(s).
  - `pt-BR`: `Os registros ativos estão desconectados` → `Os logs em tempo real estão desconectados.` (high; “Registros ativos” means active records and loses the live-log meaning.)
- `src_060b076be748ec44` — **received /**: 1 locale correction candidate(s).
  - `ar`: `تلقى /` → `مستلمة /` (high; The current verb means “he received”; this fragment labels bytes received before the slash in a transfer statistic.)
- `src_0610a61ef22aea6a` — **No failed jobs visible**: 7 locale correction candidate(s).
  - `hi`: `कोई असफल नौकरियां दिखाई नहीं दे रही हैं` → `कोई विफल कार्य दिखाई नहीं दे रहा है।` (high; The current word means jobs/employment; this health check reports failed background tasks.)
  - `ja`: `失敗したジョブは表示されません` → `失敗したジョブは見当たりません。` (high; The current wording says failed jobs are not displayed; the diagnostic means none are visible.)
  - `fr`: `Aucun travail ayant échoué visible` → `Aucune tâche en échec n’est visible.` (high; The current wording is unidiomatic and uses “travail” for a background job; this names the failed tasks shown by the health check.)
  - `ko`: `실패한 작업이 표시되지 않습니다.` → `실패한 작업이 보이지 않습니다.` (high; The current wording can mean failed jobs are not being displayed; this says none are visible, as the diagnostic intends.)
  - `zh-Hant`: `沒有可見失敗的作業` → `看不到失敗的工作` (moderate; This is a natural diagnostic statement that no failed jobs are visible.)
  - `vi`: `Không có công việc thất bại nào được hiển thị` → `Không thấy công việc nào thất bại.` (high; The current wording says failed jobs are not displayed; this says no failed task is visible.)
  - `id`: `Tidak ada pekerjaan yang gagal terlihat` → `Tidak terlihat ada pekerjaan yang gagal.` (high; The current phrase is awkward; this expresses that the health check sees no failed jobs.)
- `src_061c01268f7c9950` — **Path to Soulfind binary**: 3 locale correction candidate(s).
  - `ar`: `الطريق إلى Soulfind الثنائي` → `مسار ملف Soulfind التنفيذي` (high; The current word is a physical road; this is a filesystem path to the Soulfind executable binary.)
  - `vi`: `Đường dẫn đến nhị phân Soulfind` → `Đường dẫn đến tệp nhị phân Soulfind` (high; The current wording makes “binary” sound like a mathematical number; this names the Soulfind binary file.)
  - `id`: `Jalan menuju biner Soulfind` → `Jalur ke berkas biner Soulfind` (high; The current phrase says “road to”; this is a filesystem path to the Soulfind binary.)
- `src_06650b05b4cab744` — **Room broadcast**: 3 locale correction candidate(s).
  - `ja`: `室内放送` → `ルーム配信` (high; The current term means an indoor/public-address broadcast; the fallback identifies the online listening room’s broadcast.)
  - `fr`: `Diffusion en salle` → `Diffusion du salon` (moderate; “Salle” suggests a physical hall; this is the broadcast associated with a chat/listening salon.)
  - `ko`: `방방송` → `룸 방송` (high; The current string has a duplicated “room” syllable and reads as a typo.)
- `src_069c12967ebd313f` — **Fetch the entered user's public interest and hated-item lists.**: 2 locale correction candidate(s).
  - `fr`: `Récupérez les listes publiques d'intérêts et d'éléments rejetés de l'utilisateur indiqué.` → `Récupérez les listes publiques d'intérêts et d'éléments détestés de l'utilisateur indiqué.` (high; “Éléments rejetés” means rejected items, while this Soulseek profile list is the user’s hated items.)
  - `pt-BR`: `Busque as listas públicas de interesses e itens rejeitados do usuário informado.` → `Busque as listas públicas de interesses e itens que o usuário odeia.` (high; “Itens rejeitados” means rejected items, while this Soulseek profile list contains items the user hates.)
- `src_06ab0f6d089fc024` — **Cover Traffic**: 9 locale correction candidate(s).
  - `zh-Hans`: `覆盖交通` → `掩护流量` (high; The current phrase means road/transport traffic; this privacy setting generates network cover traffic.)
  - `hi`: `ट्रैफ़िक कवर करें` → `कवर ट्रैफ़िक` (moderate; The current phrase is an imperative to cover traffic; this is the noun technical term used as a section heading.)
  - `de`: `Verkehr abdecken` → `Tarn-Datenverkehr` (high; The current phrase is an imperative to cover traffic; this privacy setting generates obfuscating network traffic.)
  - `fr`: `Couvrir le trafic` → `Trafic de couverture` (high; The current phrase is an imperative; this is the network privacy term for cover traffic.)
  - `pt-BR`: `Cobrir o tráfego` → `Tráfego de cobertura` (high; The current phrase is an imperative; this is the network privacy term for cover traffic.)
  - `ar`: `تغطية حركة المرور` → `حركة مرور تمويهية` (high; The current wording suggests covering road traffic; this names obfuscating network traffic.)
  - `zh-Hant`: `覆蓋交通` → `掩護流量` (high; The current phrase means road/transport traffic; this privacy setting generates network cover traffic.)
  - `vi`: `Che phủ giao thông` → `Lưu lượng ngụy trang` (high; The current phrase says to cover road traffic; this names camouflage/cover traffic in the privacy settings.)
  - `id`: `Tutupi Lalu Lintas` → `Lalu lintas kamuflase` (high; The current phrase is an imperative about road traffic; this names camouflage network traffic.)
- `src_06af0870f8f66ed4` — **Outbound Types**: 2 locale correction candidate(s).
  - `ar`: `أنواع الصادرة` → `الأنواع الصادرة` (high; The current adjective construction is ungrammatical; this is the plural label for outbound evidence types.)
  - `vi`: `Các loại đi` → `Các loại bằng chứng gửi đi` (high; The current phrase means only “types that go”; caller context shows this is the count of outbound evidence types.)
- `src_06dfd9bfbec866df` — **Pod ID, Content ID, and Variant Hash are required**: 1 locale correction candidate(s).
  - `vi`: `Cần có ID nhóm, ID nội dung và Hash biến thể` → `ID Pod, ID nội dung và mã băm biến thể là bắt buộc` (high; The current translation changes the product field “Pod ID” to “group ID”; keep the product entity name to match the form field.)
- `src_06e70139fcf5e5c7` — **Attempts**: 1 locale correction candidate(s).
  - `vi`: `Nỗ lực` → `Số lần thử` (moderate; This count is the number of transfer retry attempts; “nỗ lực” means effort and is less precise as a count label.)
- `src_072c79f620d6edd4` — **Manual Route Dispatch**: 2 locale correction candidate(s).
  - `ar`: `إرسال الطريق اليدوي` → `إرسال المسار يدويًا` (high; The current wording reads as sending a physical road; this section manually dispatches a network route.)
  - `vi`: `Gửi lộ trình thủ công` → `Điều phối tuyến thủ công` (high; The current word “lộ trình” suggests a travel itinerary; this section dispatches network routes.)

## Files

- `review-input.jsonl`: frozen source/current catalog rows with source contexts, caller refs, and exact input hashes.
- `review-decisions.jsonl`: compact verdicts matching the existing semantic-review decision shape, with source/current target hashes and window number.
- `review-evidence.jsonl`: per-cell decision join containing source/current target hashes, correction text/hash where proposed, caller refs, placeholders/protected literals, and frozen row hash.
- `source-attestation.jsonl`: source-ID/source-text hash re-attestation.
- `caller-attestation.jsonl`: unique source caller line and file hash re-attestation.
- `preserved-prior-routed.jsonl`: Spanish cells preserved because they are in the formal-lane ID set.
- `preflight.json`, `freeze-summary.json`, `manifest.json`, `formal-cell-ids.jsonl`, `freeze_window36.py`: exact-head freeze and lane-exclusion evidence.
- `review-summary.json`: pins and counts.
- `build_review_packet.py`: packet generation and exact-head re-attestation code.

Semantic and locale-quality confidence is moderate overall. This packet is not native-speaker review and does not settle final locale style. The parent workflow can cross-review the proposed targets before deciding whether to apply them.
