# W52 source/current worksheet

Pinned PR head/tree: `f63c8c04f3b1c3fb5e1bc8971a0d83bbf8ca4e77` / `ca9f1bf1d9f4373556476a51b863601668878eb3`.
Stable-ID ranks follow the re-attested W49 source inventory, ranks 201-225. Historical source ordinals are unavailable.

## Rank 201 — `src_1744b96470b51bf3`

**English:** Network

**Pinned production callers:**
- `src/web/src/components/PrimaryNavigation.jsx:22`:     label: "Network",
- `src/web/src/components/Shared/Footer.jsx:481`:               <span className="slskdn-footer-group-label"><LocalizedText source={"Network"} /></span>
- `src/web/src/components/System/Metrics/index.jsx:80`:     get title() { return interfaceText("Network"); },
- `src/web/src/components/System/System.jsx:112`:           <LocalizedText source={"Network"} /></Menu.Item>
- `src/web/src/lib/setupHealthCheck.js:12`:     case 'Network':
- `src/web/src/lib/setupHealthCheck.js:13`:       return interfaceText('Network');
- `src/web/src/lib/setupHealthCheck.js:352`:       group: 'Network',

| Locale | Current target |
|---|---|
| ar | الشبكة |
| de | Netzwerk |
| es | Red |
| fr | Réseau |
| hi | नेटवर्क |
| id | Jaringan |
| ja | ネットワーク |
| ko | 네트워크 |
| pt-BR | Rede |
| vi | Mạng |
| zh-Hans | 网络 |
| zh-Hant | 網路 |

## Rank 202 — `src_17504d2865b8014e`

**English:** {title} started scan {scanId} for {libraryPath}.

**Pinned production callers:**
- `src/web/src/components/System/AutomationCenter/index.jsx:130`:     const status = interfaceTextOutput("{title} started scan {scanId} for {libraryPath}.", { title: interfaceTextOutput(recipe.title), scanId, libraryPath });

| Locale | Current target |
|---|---|
| ar | بدأ {title} في فحص {scanId} بحثًا عن {libraryPath}. |
| de | {title} hat den Scan {scanId} nach {libraryPath} gestartet. |
| es | {title} inició el escaneo {scanId} en busca de {libraryPath}. |
| fr | {title} a lancé l'analyse de {scanId} pour {libraryPath}. |
| hi | {title} ने {libraryPath} के लिए {scanId} स्कैन शुरू किया। |
| id | {title} mulai memindai {scanId} untuk {libraryPath}. |
| ja | {title} が {libraryPath} の {scanId} のスキャンを開始しました。 |
| ko | {title}가 {libraryPath}에 대한 {scanId} 스캔을 시작했습니다. |
| pt-BR | {title} iniciou a varredura de {scanId} para {libraryPath}. |
| vi | {title} đã bắt đầu quét {scanId} để tìm {libraryPath}. |
| zh-Hans | {title} 开始扫描 {scanId} 以查找 {libraryPath}。 |
| zh-Hant | {title} 開始掃描 {scanId} 以尋找 {libraryPath}。 |

## Rank 203 — `src_175b89c20904bb87`

**English:** Download filters saved

**Pinned production callers:**
- `src/web/src/components/Transfers/DownloadExclusionsModal.jsx:79`:       toast.success(interfaceToastText("Download filters saved"));

| Locale | Current target |
|---|---|
| ar | تم حفظ مرشحات التنزيل |
| de | Download-Filter gespeichert |
| es | Descargar filtros guardados |
| fr | Télécharger les filtres enregistrés |
| hi | डाउनलोड फ़िल्टर सहेजे गए |
| id | Unduh filter disimpan |
| ja | ダウンロードフィルターが保存されました |
| ko | 다운로드 필터가 저장되었습니다. |
| pt-BR | Filtros de download salvos |
| vi | Đã lưu bộ lọc tải xuống |
| zh-Hans | 下载过滤器已保存 |
| zh-Hant | 下載過濾器已儲存 |

## Rank 204 — `src_176032e2bc83a536`

**English:** Synchronize missed messages when peers rejoin pods

**Pinned production callers:**
- `src/web/src/components/System/MediaCore/MediaCorePods.jsx:3540`:                 <LocalizedText source={"Synchronize missed messages when peers rejoin pods"} /></Card.Description>

| Locale | Current target |
|---|---|
| ar | مزامنة الرسائل الفائتة عندما ينضم الزملاء مرة أخرى إلى البودات |
| de | Synchronisieren Sie verpasste Nachrichten, wenn Peers wieder Pods beitreten |
| es | Sincronizar mensajes perdidos cuando los compañeros se vuelven a unir a los pods |
| fr | Synchronisez les messages manqués lorsque les pairs rejoignent les pods |
| hi | जब सहकर्मी पॉड्स में दोबारा शामिल हों तो छूटे हुए संदेशों को सिंक्रोनाइज़ करें |
| id | Sinkronkan pesan yang tidak terjawab ketika rekan-rekan bergabung kembali dengan pod |
| ja | ピアがポッドに再参加するときに欠落したメッセージを同期する |
| ko | 피어가 Pod에 다시 참여할 때 누락된 메시지 동기화 |
| pt-BR | Sincronize mensagens perdidas quando os pares reingressarem nos pods |
| vi | Đồng bộ hóa các tin nhắn bị bỏ lỡ khi các đồng nghiệp tham gia lại nhóm |
| zh-Hans | 当对等点重新加入 Pod 时同步丢失的消息 |
| zh-Hant | 當對等點重新加入 Pod 時同步遺失的訊息 |

## Rank 205 — `src_17643f922e8ca8d3`

**English:** Downloads: {downloadError}

**Pinned production callers:**
- `src/web/src/components/System/Data/index.jsx:93`:               content={<LocalizedOutputText output={interfaceTextOutput("Downloads: {downloadError}", { "downloadError": (downloadError) })} />}
- `src/web/src/components/System/Data/index.jsx:96`:              {...interfaceTextProps("Downloads: {downloadError}")}/>

| Locale | Current target |
|---|---|
| ar | التنزيلات: {downloadError} |
| de | Downloads: {downloadError} |
| es | Descargas: {downloadError} |
| fr | Téléchargements : {downloadError} |
| hi | डाउनलोड: {downloadError} |
| id | Unduhan: {downloadError} |
| ja | ダウンロード: {downloadError} |
| ko | 다운로드: {downloadError} |
| pt-BR | Transferências: {downloadError} |
| vi | Tải xuống: {downloadError} |
| zh-Hans | 下载次数：{downloadError} |
| zh-Hant | 下載次數：{downloadError} |

## Rank 206 — `src_176ed98fb50d653c`

**English:** Publish Descriptor

**Pinned production callers:**
- `src/web/src/components/System/MediaCore/index.jsx:2298`:                     <LocalizedText source={"Publish Descriptor"} /></Button>

| Locale | Current target |
|---|---|
| ar | نشر الواصف |
| de | Deskriptor veröffentlichen |
| es | Publicar descriptor |
| fr | Publier le descripteur |
| hi | डिस्क्रिप्टर प्रकाशित करें |
| id | Publikasikan Deskriptor |
| ja | パブリッシュ記述子 |
| ko | 게시 설명자 |
| pt-BR | Publicar descritor |
| vi | Xuất bản mô tả |
| zh-Hans | 发布描述符 |
| zh-Hant | 發布描述符 |

## Rank 207 — `src_17732c9394bef423`

**English:** I2P Configuration

**Pinned production callers:**
- `src/web/src/components/System/Security/AdversarialSettings.jsx:575`:                     <Message.Header><LocalizedText source={"I2P Configuration"} /></Message.Header>
- `src/web/src/components/System/Security/AdversarialSettings.jsx:859`:                     <Header as="h5"><LocalizedText source={"I2P Configuration"} /></Header>

| Locale | Current target |
|---|---|
| ar | تكوين I2P |
| de | I2P-Konfiguration |
| es | Configuración I2P |
| fr | Configuration I2P |
| hi | I2P कॉन्फ़िगरेशन |
| id | Konfigurasi I2P |
| ja | I2P構成 |
| ko | I2P 구성 |
| pt-BR | Configuração I2P |
| vi | Cấu hình I2P |
| zh-Hans | I2P配置 |
| zh-Hant | I2P配置 |

## Rank 208 — `src_177742afd8facf9a`

**English:** Show listening statistics from the last {days} days.

**Pinned production callers:**
- `src/web/src/components/Player/PlayerBar.jsx:1343`:                 ? interfaceText('Show listening statistics from the last {days} days.', { days: range.value })

| Locale | Current target |
|---|---|
| ar | اعرض إحصاءات الاستماع لآخر {days} يومًا. |
| de | Hörstatistiken der letzten {days} Tage anzeigen. |
| es | Muestra las estadísticas de escucha de los últimos {days} días. |
| fr | Afficher les statistiques d’écoute des {days} derniers jours. |
| hi | पिछले {days} दिनों के सुनने के आँकड़े दिखाएँ। |
| id | Tampilkan statistik mendengarkan selama {days} hari terakhir. |
| ja | 過去{days}日間の再生統計を表示します。 |
| ko | 지난 {days}일간의 청취 통계를 표시합니다. |
| pt-BR | Mostrar estatísticas de audição dos últimos {days} dias. |
| vi | Hiển thị thống kê nghe trong {days} ngày qua. |
| zh-Hans | 显示最近 {days} 天的收听统计。 |
| zh-Hant | 顯示最近 {days} 天的聆聽統計。 |

## Rank 209 — `src_178a6b95aac60414`

**English:** Unsupported fragment syntax may be present.

**Pinned production callers:**
- `src/web/src/components/Player/Visualizer.jsx:1392`:           message: presetError?.message || interfaceText('Unsupported fragment syntax may be present.'),

| Locale | Current target |
|---|---|
| ar | قد توجد صياغة جزء غير مدعومة. |
| de | Möglicherweise ist nicht unterstützte Fragment-Syntax enthalten. |
| es | Puede que haya sintaxis de fragmento no compatible. |
| fr | Une syntaxe de fragment non prise en charge est peut-être présente. |
| hi | असमर्थित फ़्रैगमेंट सिंटैक्स मौजूद हो सकता है। |
| id | Sintaks fragmen yang tidak didukung mungkin ada. |
| ja | 未対応のフラグメント構文が含まれている可能性があります。 |
| ko | 지원되지 않는 프래그먼트 문법이 있을 수 있습니다. |
| pt-BR | Pode haver sintaxe de fragmento incompatível. |
| vi | Có thể có cú pháp fragment không được hỗ trợ. |
| zh-Hans | 可能包含不支持的片段语法。 |
| zh-Hant | 可能含有不支援的片段語法。 |

## Rank 210 — `src_1795a5c7cc3fb82c`

**English:** Retry Contents

**Pinned production callers:**
- `src/web/src/components/Shares/SharedWithMe.jsx:492`:                   <LocalizedText source={"Retry Contents"} /></Button>

| Locale | Current target |
|---|---|
| ar | إعادة محاولة المحتويات |
| de | Inhalt erneut versuchen |
| es | Reintentar contenido |
| fr | Réessayer le contenu |
| hi | सामग्री पुनः प्रयास करें |
| id | Coba Lagi Isinya |
| ja | リトライ内容 |
| ko | 재시도 내용 |
| pt-BR | Tentar novamente o conteúdo |
| vi | Thử lại nội dung |
| zh-Hans | 重试内容 |
| zh-Hant | 重試內容 |

## Rank 211 — `src_17a8eb4b9f71c1e2`

**English:** Rebuild the local message search index from stored messages if search results are stale or incomplete.

**Pinned production callers:**
- `src/web/src/components/System/MediaCore/MediaCorePods.jsx:3422`:                   tooltip={interfaceText("Rebuild the local message search index from stored messages if search results are stale or incomplete.")}

| Locale | Current target |
|---|---|
| ar | أعد بناء فهرس البحث المحلي للرسائل من الرسائل المخزنة إذا كانت النتائج قديمة أو غير مكتملة. |
| de | Den lokalen Nachrichtensuchindex aus gespeicherten Nachrichten neu erstellen, wenn Ergebnisse veraltet oder unvollständig sind. |
| es | Reconstruye el índice local de búsqueda de mensajes si los resultados están desactualizados o incompletos. |
| fr | Reconstruisez l’index de recherche local à partir des messages stockés si les résultats sont anciens ou incomplets. |
| hi | यदि खोज परिणाम पुराने या अधूरे हों, तो संग्रहीत संदेशों से स्थानीय संदेश खोज इंडेक्स फिर बनाएँ। |
| id | Bangun ulang indeks pencarian pesan lokal dari pesan tersimpan jika hasilnya usang atau tidak lengkap. |
| ja | 検索結果が古い、または不完全な場合、保存済みメッセージからローカル検索インデックスを再構築します。 |
| ko | 검색 결과가 오래되었거나 불완전하면 저장된 메시지에서 로컬 검색 색인을 다시 만듭니다. |
| pt-BR | Reconstrua o índice local de mensagens a partir do conteúdo armazenado se os resultados estiverem desatualizados ou incompletos. |
| vi | Tạo lại chỉ mục tìm kiếm tin nhắn cục bộ từ tin nhắn đã lưu nếu kết quả cũ hoặc không đầy đủ. |
| zh-Hans | 如果搜索结果过时或不完整，请根据已存消息重建本地搜索索引。 |
| zh-Hant | 若搜尋結果過時或不完整，請從已儲存的訊息重建本機搜尋索引。 |

## Rank 212 — `src_17a9c02c8cb8179f`

**English:** Start up to three searches from similar recent session tracks. This starts search jobs only.

**Pinned production callers:**
- `src/web/src/components/Player/PlayerBar.jsx:769`:                   content={interfaceText("Start up to three searches from similar recent session tracks. This starts search jobs only.")}
- `src/web/src/components/Player/PlayerBar.jsx:782`:                  {...interfaceTextProps("Start up to three searches from similar recent session tracks. This starts search jobs only.")}/>

| Locale | Current target |
|---|---|
| ar | ابدأ ما يصل إلى ثلاث عمليات بحث من مسارات الجلسة الأخيرة المماثلة. يؤدي هذا إلى بدء البحث عن الوظائف فقط. |
| de | Starten Sie bis zu drei Suchvorgänge anhand ähnlicher aktueller Sitzungstitel. Dadurch werden nur Suchjobs gestartet. |
| es | Inicie hasta tres búsquedas a partir de pistas de sesiones recientes similares. Esto inicia la búsqueda de trabajos únicamente. |
| fr | Lancez jusqu'à trois recherches à partir de pistes de session récentes similaires. Cela démarre uniquement la recherche d'emplois. |
| hi | समान हालिया सत्र ट्रैक से तीन खोजें शुरू करें। इससे केवल नौकरी की खोज शुरू होती है। |
| id | Mulai hingga tiga penelusuran dari trek sesi terkini yang serupa. Ini hanya memulai pekerjaan pencarian. |
| ja | 同様の最近のセッション トラックから最大 3 つの検索を開始します。これにより、検索ジョブのみが開始されます。 |
| ko | 유사한 최근 세션 트랙에서 최대 3개의 검색을 시작합니다. 검색 작업만 시작됩니다. |
| pt-BR | Inicie até três pesquisas a partir de faixas de sessões recentes semelhantes. Isso inicia apenas trabalhos de pesquisa. |
| vi | Bắt đầu tối đa ba tìm kiếm từ các phiên theo dõi gần đây tương tự. Điều này chỉ bắt đầu công việc tìm kiếm. |
| zh-Hans | 从类似的近期会话轨迹中启动最多三个搜索。这仅启动搜索作业。 |
| zh-Hant | 從類似的近期會話軌跡中啟動最多三個搜尋。這僅啟動搜尋作業。 |

## Rank 213 — `src_17b6ae8b8c1c9ada`

**English:** High Quality (320kbps+)

**Pinned production callers:**
- `src/web/src/components/Search/Detail/SearchFilterModal.jsx:144`:                     {localized('High Quality (320kbps+)')}

| Locale | Current target |
|---|---|
| ar | جودة عالية (320 kbps فأكثر) |
| de | Hohe Qualität (ab 320 kbps) |
| es | Alta calidad (320 kbps o más) |
| fr | Haute qualité (320 kbps et plus) |
| hi | उच्च गुणवत्ता (320 kbps+) |
| id | Kualitas tinggi (320 kbps ke atas) |
| ja | 高音質（320 kbps以上） |
| ko | 고음질 (320 kbps 이상) |
| pt-BR | Alta qualidade (320 kbps ou mais) |
| vi | Chất lượng cao (từ 320 kbps) |
| zh-Hans | 高音质（320 kbps 及以上） |
| zh-Hant | 高音質（320 kbps 以上） |

## Rank 214 — `src_17c679a8798d336d`

**English:** Run Ready

**Pinned production callers:**
- `src/web/src/components/System/Integrations/ServarrReadinessPanel.jsx:181`:                 <LocalizedText source={"Run Ready"} /></Button>

| Locale | Current target |
|---|---|
| ar | تشغيل جاهز |
| de | Laufbereit |
| es | Ejecutar listo |
| fr | Prêt à courir |
| hi | तैयार भागो |
| id | Jalankan Siap |
| ja | 実行準備完了 |
| ko | 실행 준비 |
| pt-BR | Execute pronto |
| vi | Sẵn sàng chạy |
| zh-Hans | 运行准备 |
| zh-Hant | 運行準備 |

## Rank 215 — `src_17c77098764de0b5`

**English:** Create a pod

**Pinned production callers:**
- `src/web/src/components/Pods/Pods.jsx:649`:                   aria-label={interfaceText("Create a pod")}
- `src/web/src/components/Pods/Pods.jsx:653`:                  {...interfaceTextProps("Create a pod")}/>

| Locale | Current target |
|---|---|
| ar | إنشاء جراب |
| de | Erstellen Sie einen Pod |
| es | Crear un grupo |
| fr | Créer un module |
| hi | एक पॉड बनाएं |
| id | Buat pod |
| ja | ポッドを作成する |
| ko | 포드 만들기 |
| pt-BR | Crie um pod |
| vi | Tạo một nhóm |
| zh-Hans | 创建一个 Pod |
| zh-Hant | 創建一個 Pod |

## Rank 216 — `src_17d2b3a918ca33fa`

**English:** CPU Seconds

**Pinned production callers:**
- `src/web/src/components/System/Metrics/index.jsx:75`:       { key: 'process_cpu_seconds_total', get label() { return interfaceText("CPU Seconds"); }, format: formatNumber },

| Locale | Current target |
|---|---|
| ar | ثانية وحدة المعالجة المركزية |
| de | CPU-Sekunden |
| es | Segundos de CPU |
| fr | Secondes du processeur |
| hi | सीपीयू सेकंड |
| id | Detik CPU |
| ja | CPU秒数 |
| ko | CPU 초 |
| pt-BR | Segundos de CPU |
| vi | giây CPU |
| zh-Hans | CPU 秒数 |
| zh-Hant | CPU 秒數 |

## Rank 217 — `src_17d642d672c6d6ea`

**English:** Saved playlist

**Pinned production callers:**
- `src/web/src/components/Player/PlayerBar.jsx:728`:             <select aria-label={interfaceText("Saved playlist")} disabled={Boolean(playlistBusy)} onChange={(event) => setSelectedPlaylist(event.target.value)} value={selectedPlaylist} {...interfaceTextProps("Saved playlist")}>

| Locale | Current target |
|---|---|
| ar | قائمة التشغيل المحفوظة |
| de | Gespeicherte Playlist |
| es | Lista de reproducción guardada |
| fr | Liste de lecture enregistrée |
| hi | सहेजी गई प्लेलिस्ट |
| id | Daftar putar yang disimpan |
| ja | 保存されたプレイリスト |
| ko | 저장된 재생목록 |
| pt-BR | Lista de reprodução salva |
| vi | Danh sách phát đã lưu |
| zh-Hans | 已保存的播放列表 |
| zh-Hant | 已儲存的播放列表 |

## Rank 218 — `src_17db0725a7844322`

**English:** Load Recommendations

**Pinned production callers:**
- `src/web/src/components/Search/FederatedTasteRecommendationsPanel.jsx:212`:               <LocalizedText source={"Load Recommendations"} /></Button>

| Locale | Current target |
|---|---|
| ar | تحميل التوصيات |
| de | Empfehlungen laden |
| es | Recomendaciones de carga |
| fr | Recommandations de charge |
| hi | सिफ़ारिशें लोड करें |
| id | Memuat Rekomendasi |
| ja | 推奨事項をロードする |
| ko | 권장사항 로드 |
| pt-BR | Recomendações de carga |
| vi | Tải đề xuất |
| zh-Hans | 负载建议 |
| zh-Hant | 負載建議 |

## Rank 219 — `src_17dfe37e4170dae9`

**English:** Started 1 bounded listening seed search.

**Pinned production callers:**
- `src/web/src/components/Player/PlayerBar.jsx:1216`:         count === 1 ? 'Started 1 bounded listening seed search.' : 'Started {count} bounded listening seed searches.',

| Locale | Current target |
|---|---|
| ar | بدأ بحث محدود واحد باستخدام عبارة استماع. |
| de | Eine begrenzte Hörsuche wurde gestartet. |
| es | Se inició una búsqueda acotada con una semilla de escucha. |
| fr | Une recherche limitée à partir d’une requête d’écoute a démarré. |
| hi | सुनने की खोज के एक बीज से सीमित खोज शुरू हुई। |
| id | Pencarian terbatas dengan satu kueri dengar dimulai. |
| ja | リスニング検索シード 1 件の範囲限定検索を開始しました。 |
| ko | 청취 검색 시드 1개로 제한 검색을 시작했습니다. |
| pt-BR | Uma busca limitada com uma semente de audição foi iniciada. |
| vi | Đã bắt đầu một lượt tìm kiếm giới hạn bằng từ khóa nghe. |
| zh-Hans | 已开始 1 次有界聆听种子搜索。 |
| zh-Hant | 已開始 1 次有限聆聽種子搜尋。 |

## Rank 220 — `src_17e27b68aaeb07f1`

**English:** Copy the current mesh evidence review report.

**Pinned production callers:**
- `src/web/src/components/System/Mesh/MeshEvidencePolicy.jsx:287`:             content={interfaceText("Copy the current mesh evidence review report.")}
- `src/web/src/components/System/Mesh/MeshEvidencePolicy.jsx:298`:            {...interfaceTextProps("Copy the current mesh evidence review report.")}/>

| Locale | Current target |
|---|---|
| ar | انسخ تقرير مراجعة أدلة الشبكة الحالي. |
| de | Kopieren Sie den aktuellen Mesh-Evidence-Review-Bericht. |
| es | Copie el informe de revisión de evidencia de malla actual. |
| fr | Copiez le rapport actuel d'examen des preuves de maillage. |
| hi | वर्तमान जाल साक्ष्य समीक्षा रिपोर्ट की प्रतिलिपि बनाएँ। |
| id | Salin laporan tinjauan bukti mesh saat ini. |
| ja | 現在のメッシュ証拠レビュー レポートをコピーします。 |
| ko | 현재 메시 증거 검토 보고서를 복사합니다. |
| pt-BR | Copie o relatório atual de revisão de evidências de malha. |
| vi | Sao chép báo cáo đánh giá bằng chứng lưới hiện tại. |
| zh-Hans | 复制当前的网格证据审查报告。 |
| zh-Hant | 複製目前的網格證據審查報告。 |

## Rank 221 — `src_17eb3c0168d0d7b2`

**English:** disabled

**Pinned production callers:**
- `src/web/src/components/System/AdminPolicies/index.jsx:249`:     httpsDisabled: getOption(https, 'disabled', 'Disabled') ?? true,
- `src/web/src/components/System/AdminPolicies/index.jsx:255`:     noAuth: Boolean(getOption(auth, 'disabled', 'Disabled')),
- `src/web/src/components/System/AdminPolicies/index.jsx:476`:       document.setIn(['web', 'authentication', 'disabled'], form.noAuth);
- `src/web/src/components/System/AdminPolicies/index.jsx:497`:       document.setIn(['web', 'https', 'disabled'], form.httpsDisabled);
- `src/web/src/components/System/Network/index.jsx:621`:                 {obfuscation.enabled ? <LocalizedText source={"enabled"} /> : <LocalizedText source={"disabled"} />}
- `src/web/src/components/System/Security/AdversarialSettings.jsx:303`:     { key: 'disabled', text: interfaceText("Disabled"), value: 'Disabled' },
- `src/web/src/lib/meshEvidencePolicy.js:35`:     id: 'disabled',
- `src/web/src/lib/meshEvidencePolicy.js:83`:   inboundTrustTier: 'disabled',
- `src/web/src/lib/meshEvidencePolicy.js:176`:     inboundEnabled: policy.inboundTrustTier !== 'disabled',
- `src/web/src/lib/meshEvidencePolicy.js:180`:       policy.inboundTrustTier === 'disabled' && enabledOutbound.length === 0,
- `src/web/src/lib/meshEvidencePolicy.js:225`:     if (sanitizedPolicy.inboundTrustTier === 'disabled') {
- `src/web/src/lib/setupHealthCheck.js:324`:       ['web', 'authentication', 'disabled'],

| Locale | Current target |
|---|---|
| ar | عاجز |
| de | deaktiviert |
| es | desactivado |
| fr | désactivé |
| hi | अक्षम |
| id | dengan disabilitas |
| ja | 無効 |
| ko | 장애가 있는 |
| pt-BR | desabilitado |
| vi | tàn tật |
| zh-Hans | 残疾人 |
| zh-Hant | 殘障人士 |

## Rank 222 — `src_17f88e9346c23878`

**English:** SourceText is required

**Pinned production callers:**
- `src/web/src/lib/apiErrorMessages.js:8`:   'source-feed-import.source-text-required': 'SourceText is required',

| Locale | Current target |
|---|---|
| ar | حقل SourceText مطلوب. |
| de | SourceText ist erforderlich. |
| es | Se requiere SourceText. |
| fr | SourceText est requis. |
| hi | SourceText देना आवश्यक है। |
| id | SourceText wajib diisi. |
| ja | SourceText が必要です。 |
| ko | SourceText가 필요합니다. |
| pt-BR | É necessário informar SourceText. |
| vi | Cần có SourceText. |
| zh-Hans | 必须提供 SourceText。 |
| zh-Hant | 必須提供 SourceText。 |

## Rank 223 — `src_17fc7771738fbe2c`

**English:** HTTP Tunnel Configuration

**Pinned production callers:**
- `src/web/src/components/System/Security/AdversarialSettings.jsx:976`:                     <Header as="h5"><LocalizedText source={"HTTP Tunnel Configuration"} /></Header>

| Locale | Current target |
|---|---|
| ar | تكوين النفق HTTP |
| de | HTTP Tunnelkonfiguration |
| es | Configuración del túnel HTTP |
| fr | Configuration des tunnels HTTP |
| hi | HTTP सुरंग विन्यास |
| id | Konfigurasi Terowongan HTTP |
| ja | HTTP トンネル構成 |
| ko | HTTP 터널 구성 |
| pt-BR | Configuração do túnel HTTP |
| vi | Cấu hình đường hầm HTTP |
| zh-Hans | HTTP隧道配置 |
| zh-Hant | HTTP隧道配置 |

## Rank 224 — `src_1802ec2fff1a30e6`

**English:** Starting a recursive, read-only scan of the entered server-side path.

**Pinned production callers:**
- `src/web/src/components/System/LibraryHealth/index.jsx:307`:       setScanMessage(interfaceTextOutput('Starting a recursive, read-only scan of the entered server-side path.'));

| Locale | Current target |
|---|---|
| ar | بدء فحص متكرر للقراءة فقط للمسار الذي تم إدخاله من جانب الخادم. |
| de | Starten eines rekursiven, schreibgeschützten Scans des eingegebenen serverseitigen Pfads. |
| es | Iniciar un escaneo recursivo de solo lectura de la ruta ingresada del lado del servidor. |
| fr | Démarrage d'une analyse récursive en lecture seule du chemin saisi côté serveur. |
| hi | दर्ज किए गए सर्वर-साइड पथ का पुनरावर्ती, केवल पढ़ने योग्य स्कैन प्रारंभ करना। |
| id | Memulai pemindaian rekursif dan hanya-baca dari jalur sisi server yang dimasukkan. |
| ja | 入力されたサーバー側パスの再帰的読み取り専用スキャンを開始します。 |
| ko | 입력된 서버측 경로에 대한 반복적인 읽기 전용 스캔을 시작합니다. |
| pt-BR | Iniciando uma verificação recursiva somente leitura do caminho do lado do servidor inserido. |
| vi | Bắt đầu quét đệ quy, chỉ đọc đường dẫn phía máy chủ đã nhập. |
| zh-Hans | 开始对输入的服务器端路径进行递归、只读扫描。 |
| zh-Hant | 開始對輸入的伺服器端路徑進行遞歸、唯讀掃描。 |

## Rank 225 — `src_180964508f4f412a`

**English:** Chunk Success Rate

**Pinned production callers:**
- `src/web/src/components/System/SwarmAnalytics/index.jsx:344`:                       <Statistic.Label><LocalizedText source={"Chunk Success Rate"} /></Statistic.Label>

| Locale | Current target |
|---|---|
| ar | معدل نجاح القطعة |
| de | Chunk-Erfolgsrate |
| es | Tasa de éxito de fragmentos |
| fr | Taux de réussite des fragments |
| hi | खंड सफलता दर |
| id | Tingkat Keberhasilan Potongan |
| ja | チャンクの成功率 |
| ko | 청크 성공률 |
| pt-BR | Taxa de sucesso de pedaços |
| vi | Tỷ lệ thành công của khối |
| zh-Hans | 块成功率 |
| zh-Hant | 區塊成功率 |
