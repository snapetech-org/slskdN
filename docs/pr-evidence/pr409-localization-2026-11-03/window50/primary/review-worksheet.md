# W50 primary review worksheet

Exact PR head `7a415b975bf0c783e3a91a9e3bab63bb7fd9e443` / tree `12b1a85af7c036dc3716d2730dfef0fa18a220a8`. Source ranks 126–150; no historical source ordinals claimed.

Review source meaning, exact caller context, locale register, placeholders/markup, and target-language fluency. Completed primary dispositions are in `review-decisions.jsonl`; native-speaker approval cannot be inferred.

## Rank 126 — `src_151f7660e593b38d`

**English:** is playing

**Callers:**

- `src/web/src/components/Messaging/MessageStream.jsx:197`:         {action === 'stop' ? <LocalizedText source={"stopped listenalong"} /> : <LocalizedText source={"is playing"} />}

| Locale | Current target |
|---|---|
| ar | يلعب |
| de | spielt |
| es | esta jugando |
| fr | joue |
| hi | खेल रहे है |
| id | sedang bermain |
| ja | 遊んでいます |
| ko | 놀고있다 |
| pt-BR | está jogando |
| vi | đang chơi |
| zh-Hans | 正在播放 |
| zh-Hant | 正在播放 |

## Rank 127 — `src_1535a621dfe1e20f`

**English:** Search retention max count

**Callers:**

- `src/web/src/components/System/AdminPolicies/index.jsx:106`:   ['searchRetentionMaxCount', 'Search retention max count'],
- `src/web/src/components/System/AdminPolicies/index.jsx:1533`:                   aria-label={interfaceText("Search retention max count")}
- `src/web/src/components/System/AdminPolicies/index.jsx:1539`:                  {...interfaceTextProps("Search retention max count")}/>

| Locale | Current target |
|---|---|
| ar | الحد الأقصى للاحتفاظ بالبحث |
| de | Maximale Anzahl der Suchaufbewahrung |
| es | Recuento máximo de retención de búsqueda |
| fr | Nombre maximum de rétention sur les recherches |
| hi | खोज प्रतिधारण अधिकतम संख्या |
| id | Jumlah maksimal retensi penelusuran |
| ja | 検索保持の最大数 |
| ko | 검색 보존 최대 개수 |
| pt-BR | Contagem máxima de retenção de pesquisa |
| vi | Số lượng giữ chân tối đa trong tìm kiếm |
| zh-Hans | 搜索保留最大计数 |
| zh-Hant | 搜尋保留最大計數 |

## Rank 128 — `src_153fcc25a70d7259`

**English:** Search filters saved as default.

**Callers:**

- `src/web/src/components/Search/Detail/SearchDetail.jsx:708`:     toast.success(localized('Search filters saved as default.'));

| Locale | Current target |
|---|---|
| ar | تم حفظ عوامل تصفية البحث كافتراضية. |
| de | Suchfilter als Standard gespeichert. |
| es | Se guardaron los filtros de búsqueda como predeterminados. |
| fr | Filtres de recherche enregistrés par défaut. |
| hi | खोज फ़िल्टर डिफ़ॉल्ट के रूप में सहेजे गए। |
| id | Filter pencarian disimpan sebagai default. |
| ja | 検索フィルターを既定として保存しました。 |
| ko | 검색 필터를 기본값으로 저장했습니다. |
| pt-BR | Filtros de busca salvos como padrão. |
| vi | Đã lưu bộ lọc tìm kiếm làm mặc định. |
| zh-Hans | 已将搜索筛选条件保存为默认值。 |
| zh-Hant | 已將搜尋篩選條件儲存為預設值。 |

## Rank 129 — `src_154af95978c7a025`

**English:** : F1=

**Callers:**

- `src/web/src/components/System/MediaCore/MediaCoreStats.jsx:555`:                               {algorithm}<LocalizedText source={": F1="} />{stats.f1Score.toFixed(2)}<LocalizedText source={", Precision="} />{stats.precision.toFixed(2)}

| Locale | Current target |
|---|---|
| ar | : ف1= |
| de | : F1= |
| es | : F1= |
| fr | :F1= |
| hi | : F1= |
| id | : F1= |
| ja | :F1= |
| ko | : F1= |
| pt-BR | : F1= |
| vi | : F1= |
| zh-Hans | ：F1= |
| zh-Hant | ：F1= |

## Rank 130 — `src_15648409cc8c4aa7`

**English:** Still Valid:

**Callers:**

- `src/web/src/components/System/MediaCore/index.jsx:2537`:                         <strong><LocalizedText source={"Still Valid:"} /></strong>{' '}

| Locale | Current target |
|---|---|
| ar | لا تزال صالحة: |
| de | Weiterhin gültig: |
| es | Aún válido: |
| fr | Toujours valable : |
| hi | अभी भी मान्य: |
| id | Masih berlaku: |
| ja | まだ有効です: |
| ko | 여전히 유효함: |
| pt-BR | Ainda válido: |
| vi | Vẫn hợp lệ: |
| zh-Hans | 仍然有效： |
| zh-Hant | 仍然有效： |

## Rank 131 — `src_156c48da9cb71329`

**English:** Nearby artist candidate surfaced in the same SongID context.

**Callers:**

- `src/web/src/lib/discoveryGraphLocale.js:81`:     case 'Nearby artist candidate surfaced in the same SongID context.':
- `src/web/src/lib/discoveryGraphLocale.js:82`:       return interfaceText('Nearby artist candidate surfaced in the same SongID context.');

| Locale | Current target |
|---|---|
| ar | مرشح فنان قريب ظهر في سياق SongID نفسه. |
| de | Benachbarter Artistkandidat, der im selben SongID-Kontext auftrat. |
| es | Candidato de artista cercano que apareció en el mismo contexto de SongID. |
| fr | Candidat artiste proche apparu dans le même contexte SongID. |
| hi | एक ही SongID संदर्भ में दिखाई देने वाला निकटवर्ती कलाकार उम्मीदवार। |
| id | Kandidat artis terdekat yang muncul dalam konteks SongID yang sama. |
| ja | 同じSongIDコンテキストに現れた近隣のアーティスト候補。 |
| ko | 같은 SongID 맥락에 나타난 인접 아티스트 후보. |
| pt-BR | Candidato a artista próximo que apareceu no mesmo contexto de SongID. |
| vi | Ứng viên nghệ sĩ ở gần xuất hiện trong cùng ngữ cảnh SongID. |
| zh-Hans | 在同一 SongID 上下文中出现的邻近艺人候选项。 |
| zh-Hant | 在同一 SongID 脈絡中出現的鄰近藝人候選項。 |

## Rank 132 — `src_157794b52ccf922f`

**English:** Show equalizer

**Callers:**

- `src/web/src/components/Player/PlayerBar.jsx:4250`:               aria-label={eqPanelOpen ? interfaceText('Hide equalizer') : interfaceText('Show equalizer')}

| Locale | Current target |
|---|---|
| ar | إظهار معادل الصوت |
| de | Equalizer anzeigen |
| es | Mostrar ecualizador |
| fr | Afficher l’égaliseur |
| hi | इक्वलाइज़र दिखाएँ |
| id | Tampilkan equalizer |
| ja | イコライザーを表示 |
| ko | 이퀄라이저 표시 |
| pt-BR | Mostrar equalizador |
| vi | Hiện bộ cân bằng |
| zh-Hans | 显示均衡器 |
| zh-Hant | 顯示等化器 |

## Rank 133 — `src_159728ef5a615920`

**English:** Playlist name

**Callers:**

- `src/web/src/components/PlaylistIntake/PlaylistIntake.jsx:202`:             aria-label={interfaceText("Playlist name")}
- `src/web/src/components/PlaylistIntake/PlaylistIntake.jsx:207`:            {...interfaceTextProps("Playlist name")}/>

| Locale | Current target |
|---|---|
| ar | اسم قائمة التشغيل |
| de | Name der Wiedergabeliste |
| es | Nombre de la lista de reproducción |
| fr | Nom de la liste de lecture |
| hi | प्लेलिस्ट का नाम |
| id | Nama daftar putar |
| ja | プレイリスト名 |
| ko | 재생목록 이름 |
| pt-BR | Nome da lista de reprodução |
| vi | Tên danh sách phát |
| zh-Hans | 播放列表名称 |
| zh-Hant | 播放清單名稱 |

## Rank 134 — `src_15a4cdfe34d36dde`

**English:** Close these request details and return to transfers.

**Callers:**

- `src/web/src/components/Transfers/RequestDetailModal.jsx:165`:           tooltip="Close these request details and return to transfers."

| Locale | Current target |
|---|---|
| ar | أغلق تفاصيل هذا الطلب وعد إلى عمليات النقل. |
| de | Schließe diese Anfragedetails und kehre zu den Übertragungen zurück. |
| es | Cierra los detalles de esta solicitud y vuelve a las transferencias. |
| fr | Fermez les détails de cette demande et revenez aux transferts. |
| hi | अनुरोध का विवरण बंद करें और ट्रांसफ़र पर लौटें। |
| id | Tutup detail permintaan ini dan kembali ke transfer. |
| ja | リクエストの詳細を閉じて転送画面に戻ります。 |
| ko | 이 요청 세부 정보를 닫고 전송 화면으로 돌아갑니다. |
| pt-BR | Feche os detalhes desta solicitação e volte às transferências. |
| vi | Đóng chi tiết yêu cầu này và quay lại mục truyền tải. |
| zh-Hans | 关闭此请求详情并返回传输列表。 |
| zh-Hant | 關閉此要求詳細資料並返回傳輸頁面。 |

## Rank 135 — `src_15ab574345cf98ee`

**English:** Download in progress

**Callers:** none found by exact-string production scan; dynamic/component/indirect usage needs manual resolution.

| Locale | Current target |
|---|---|
| ar | جارٍ التنزيل |
| de | Download läuft |
| es | Descarga en curso |
| fr | Téléchargement en cours |
| hi | डाउनलोड जारी है |
| id | Unduhan berlangsung |
| ja | ダウンロード中 |
| ko | 다운로드 진행 중 |
| pt-BR | Download em andamento |
| vi | Đang tải xuống |
| zh-Hans | 正在下载 |
| zh-Hant | 正在下載 |

## Rank 136 — `src_15aefa85207c6c5e`

**English:** Wave red

**Callers:**

- `src/web/src/components/Player/Visualizer.jsx:59`:     get label() { return interfaceText("Wave red"); },

| Locale | Current target |
|---|---|
| ar | موجة حمراء |
| de | Welle rot |
| es | Ola roja |
| fr | Vague rouge |
| hi | लहर लाल |
| id | Gelombang merah |
| ja | ウェーブレッド |
| ko | 웨이브 레드 |
| pt-BR | Onda vermelha |
| vi | Sóng đỏ |
| zh-Hans | 波红 |
| zh-Hant | 波紅 |

## Rank 137 — `src_15b61974b2707a7b`

**English:** Location

**Callers:**

- `src/web/src/components/Player/PlayerBar.jsx:2037`:                         <Table.HeaderCell><LocalizedText source={"Location"} /></Table.HeaderCell>
- `src/web/src/components/System/Integrations/VpnPanel.jsx:134`:               <Table.Cell><LocalizedText source={"Location"} /></Table.Cell>
- `src/web/src/components/System/Integrations/VpnPanel.jsx:135`:               <Table.Cell>{valueOrDash(getOption(vpnState, 'location', 'Location'))}</Table.Cell>

| Locale | Current target |
|---|---|
| ar | موقع |
| de | Standort |
| es | Ubicación |
| fr | Emplacement |
| hi | जगह |
| id | Lokasi |
| ja | 位置 |
| ko | 위치 |
| pt-BR | Localização |
| vi | Vị trí |
| zh-Hans | 地点 |
| zh-Hant | 地點 |

## Rank 138 — `src_15ca9ba30ff29cd0`

**English:** No rooms reported by the Soulseek server.

**Callers:**

- `src/web/src/components/Messaging/MessagingV2.jsx:1458`:                 : <EmptyHint><LocalizedText source={"No rooms reported by the Soulseek server."} /></EmptyHint>

| Locale | Current target |
|---|---|
| ar | لم يتم الإبلاغ عن أي غرف بواسطة خادم Soulseek. |
| de | Vom Soulseek-Server wurden keine Räume gemeldet. |
| es | No hay salas reportadas por el servidor Soulseek. |
| fr | Aucune salle signalée par le serveur Soulseek. |
| hi | Soulseek सर्वर द्वारा कोई कमरा रिपोर्ट नहीं किया गया। |
| id | Tidak ada ruangan yang dilaporkan oleh server Soulseek. |
| ja | Soulseek サーバーから報告された部屋はありません。 |
| ko | Soulseek 서버에서 보고된 회의실이 없습니다. |
| pt-BR | Nenhuma sala relatada pelo servidor Soulseek. |
| vi | Không có phòng nào được máy chủ Soulseek báo cáo. |
| zh-Hans | Soulseek 服务器没有报告房间。 |
| zh-Hant | Soulseek 伺服器沒有報告房間。 |

## Rank 139 — `src_15cbbd226c8c5871`

**English:** Title + artist + duration match

**Callers:**

- `src/web/src/lib/appGeneratedReasonText.js:217`:     'Title + artist + duration match': 'Title + artist + duration match',
- `src/web/src/lib/appGeneratedReasonText.js:242`:     case 'Title + artist + duration match':
- `src/web/src/lib/appGeneratedReasonText.js:243`:       return interfaceText('Title + artist + duration match');

| Locale | Current target |
|---|---|
| ar | تطابق العنوان والفنان والمدة |
| de | Übereinstimmung von Titel, Künstler und Laufzeit |
| es | Coincidencia por título, artista y duración |
| fr | Correspondance du titre, de l’artiste et de la durée |
| hi | शीर्षक, कलाकार और अवधि का मिलान |
| id | Kecocokan judul, artis, dan durasi |
| ja | タイトル・アーティスト・再生時間の一致 |
| ko | 제목, 아티스트, 재생 시간 일치 |
| pt-BR | Correspondência de título, artista e duração |
| vi | Khớp tiêu đề, nghệ sĩ và thời lượng |
| zh-Hans | 标题、艺人和时长匹配 |
| zh-Hant | 標題、藝人與時長相符 |

## Rank 140 — `src_15f081277a03f695`

**English:** Remove this wishlist item and its saved search settings.

**Callers:**

- `src/web/src/components/Wishlist/Wishlist.jsx:345`:                 tooltip="Remove this wishlist item and its saved search settings."
- `src/web/src/components/Wishlist/Wishlist.jsx:923`:             tooltip="Remove this wishlist item and its saved search settings."

| Locale | Current target |
|---|---|
| ar | أزِل هذا العنصر من قائمة الأمنيات وإعدادات البحث المحفوظة الخاصة به. |
| de | Entferne diesen Wunschlisteneintrag und seine gespeicherten Sucheinstellungen. |
| es | Elimina este elemento de la lista de deseos y su configuración de búsqueda guardada. |
| fr | Supprimer cet élément de la liste de souhaits et ses paramètres de recherche enregistrés. |
| hi | इस विशलिस्ट आइटम और उसकी सहेजी गई खोज सेटिंग हटाएँ। |
| id | Hapus item daftar keinginan ini beserta setelan pencarian tersimpannya. |
| ja | このウィッシュリスト項目と保存済み検索設定を削除します。 |
| ko | 이 위시리스트 항목과 저장된 검색 설정을 제거합니다. |
| pt-BR | Remova este item da lista de desejos e suas configurações de busca salvas. |
| vi | Xóa mục trong danh sách mong muốn này cùng cài đặt tìm kiếm đã lưu. |
| zh-Hans | 移除此愿望清单项目及其已保存的搜索设置。 |
| zh-Hant | 移除此願望清單項目及其已儲存的搜尋設定。 |

## Rank 141 — `src_15f8dce8554b29f6`

**English:** Metadata Portability

**Callers:**

- `src/web/src/components/System/MediaCore/MediaCoreStats.jsx:713`:               <LocalizedText source={"Metadata Portability"} /></Card.Header>

| Locale | Current target |
|---|---|
| ar | إمكانية نقل البيانات الوصفية |
| de | Metadaten-Portabilität |
| es | Portabilidad de metadatos |
| fr | Portabilité des métadonnées |
| hi | मेटाडेटा पोर्टेबिलिटी |
| id | Portabilitas Metadata |
| ja | メタデータの移植性 |
| ko | 메타데이터 이식성 |
| pt-BR | Portabilidade de Metadados |
| vi | Khả năng di chuyển siêu dữ liệu |
| zh-Hans | 元数据可移植性 |
| zh-Hant | 元資料可攜​​性 |

## Rank 142 — `src_15fb7be775ac985d`

**English:** slskdN mesh evidence review

**Callers:**

- `src/web/src/lib/meshEvidencePolicy.js:287`:     interfaceText("slskdN mesh evidence review"),

| Locale | Current target |
|---|---|
| ar | مراجعة أدلة الشبكة المتداخلة في slskdN |
| de | Prüfung von Mesh-Evidenz in slskdN |
| es | Revisión de evidencias de malla de slskdN |
| fr | revue des preuves de maillage de slskdN |
| hi | slskdN मेश साक्ष्य समीक्षा |
| id | tinjauan bukti mesh slskdN |
| ja | slskdN メッシュ証拠のレビュー |
| ko | slskdN 메시 증거 검토 |
| pt-BR | Revisão de evidências mesh do slskdN |
| vi | đánh giá bằng chứng mesh của slskdN |
| zh-Hans | slskdN 网格证据审核 |
| zh-Hant | slskdN 網狀網路證據審查 |

## Rank 143 — `src_16119d47df2376a5`

**English:** Release-candidate recommendation can be accepted manually.

**Callers:**

- `src/web/src/components/System/QuarantineJury/index.jsx:64`:   'Release-candidate recommendation can be accepted manually.',
- `src/web/src/components/System/QuarantineJury/index.jsx:117`:   if (message === 'Release-candidate recommendation can be accepted manually.') {
- `src/web/src/components/System/QuarantineJury/index.jsx:118`:     return <LocalizedText source="Release-candidate recommendation can be accepted manually." />;

| Locale | Current target |
|---|---|
| ar | يمكن قبول التوصية بالإفراج من العزل يدويًا. |
| de | Die Empfehlung zur Freigabe aus der Quarantäne kann manuell angenommen werden. |
| es | La recomendación de liberar de cuarentena puede aceptarse manualmente. |
| fr | La recommandation de sortie de quarantaine peut être acceptée manuellement. |
| hi | क्वारंटीन से मुक्त करने की सिफ़ारिश को मैन्युअल रूप से स्वीकार किया जा सकता है। |
| id | Rekomendasi pelepasan dari karantina dapat diterima secara manual. |
| ja | 隔離からの解放を勧める判断は手動で承認できます。 |
| ko | 격리 해제 권고를 수동으로 수락할 수 있습니다. |
| pt-BR | A recomendação de liberação da quarentena pode ser aceita manualmente. |
| vi | Có thể chấp nhận thủ công đề xuất giải phóng khỏi cách ly. |
| zh-Hans | 可以手动接受放行出隔离区的建议。 |
| zh-Hant | 可以手動接受解除隔離的建議。 |

## Rank 144 — `src_1629ef0d25ba6a46`

**English:** Get Graph

**Callers:**

- `src/web/src/components/System/MediaCore/index.jsx:1326`:                         <LocalizedText source={"Get Graph"} /></Button>

| Locale | Current target |
|---|---|
| ar | احصل على الرسم البياني |
| de | Holen Sie sich ein Diagramm |
| es | Obtener gráfico |
| fr | Obtenir le graphique |
| hi | ग्राफ़ प्राप्त करें |
| id | Dapatkan Grafik |
| ja | グラフの取得 |
| ko | 그래프 가져오기 |
| pt-BR | Obter gráfico |
| vi | Nhận biểu đồ |
| zh-Hans | 获取图表 |
| zh-Hant | 取得圖表 |

## Rank 145 — `src_162a4508d46ede92`

**English:** Message Search

**Callers:**

- `src/web/src/components/System/MediaCore/MediaCorePods.jsx:3473`:               <Header size="small"><LocalizedText source={"Message Search"} /></Header>

| Locale | Current target |
|---|---|
| ar | بحث الرسائل |
| de | Nachrichtensuche |
| es | Búsqueda de mensajes |
| fr | Recherche de messages |
| hi | संदेश खोज |
| id | Pencarian Pesan |
| ja | メッセージ検索 |
| ko | 메시지 검색 |
| pt-BR | Pesquisa de mensagens |
| vi | Tìm kiếm tin nhắn |
| zh-Hans | 留言搜索 |
| zh-Hant | 留言搜尋 |

## Rank 146 — `src_16300f3a8b8797a2`

**English:** Unable to delete the selected items.

**Callers:**

- `src/web/src/components/System/Files/Explorer.jsx:262`:       setError(getErrorMessage(error_, 'Unable to delete the selected items.'));

| Locale | Current target |
|---|---|
| ar | تعذّر حذف العناصر المحددة. |
| de | Die ausgewählten Elemente konnten nicht gelöscht werden. |
| es | No se pudieron eliminar los elementos seleccionados. |
| fr | Impossible de supprimer les éléments sélectionnés. |
| hi | चुने गए आइटम हटाए नहीं जा सके। |
| id | Item yang dipilih tidak dapat dihapus. |
| ja | 選択した項目を削除できませんでした。 |
| ko | 선택한 항목을 삭제하지 못했습니다. |
| pt-BR | Não foi possível excluir os itens selecionados. |
| vi | Không thể xóa các mục đã chọn. |
| zh-Hans | 无法删除所选项目。 |
| zh-Hant | 無法刪除所選項目。 |

## Rank 147 — `src_163185e9c3db522f`

**English:** Loading Security Status...

**Callers:**

- `src/web/src/components/System/Security/index.jsx:116`:           <Loader><LocalizedText source={"Loading Security Status..."} /></Loader>

| Locale | Current target |
|---|---|
| ar | جارٍ تحميل حالة الأمان... |
| de | Sicherheitsstatus wird geladen... |
| es | Cargando estado de seguridad... |
| fr | Chargement de l'état de sécurité... |
| hi | सुरक्षा स्थिति लोड हो रही है... |
| id | Memuat Status Keamanan... |
| ja | セキュリティ ステータスを読み込んでいます... |
| ko | 보안 상태 로드 중... |
| pt-BR | Carregando status de segurança... |
| vi | Đang tải trạng thái bảo mật... |
| zh-Hans | 正在加载安全状态... |
| zh-Hant | 正在載入安全狀態... |

## Rank 148 — `src_163451e420aa9745`

**English:** Apply these source-feed integration settings through the runtime configuration overlay.

**Callers:**

- `src/web/src/components/System/Integrations/SourceFeedIntegrationsPanel.jsx:475`:             content={interfaceText("Apply these source-feed integration settings through the runtime configuration overlay.")}
- `src/web/src/components/System/Integrations/SourceFeedIntegrationsPanel.jsx:488`:            {...interfaceTextProps("Apply these source-feed integration settings through the runtime configuration overlay.")}/>

| Locale | Current target |
|---|---|
| ar | قم بتطبيق إعدادات تكامل موجز المصدر هذه من خلال تراكب تكوين وقت التشغيل. |
| de | Wenden Sie diese Quell-Feed-Integrationseinstellungen über das Laufzeitkonfigurations-Overlay an. |
| es | Aplique estas configuraciones de integración de fuente-fuente a través de la superposición de configuración del tiempo de ejecución. |
| fr | Appliquez ces paramètres d’intégration de flux source via la superposition de configuration d’exécution. |
| hi | रनटाइम कॉन्फ़िगरेशन ओवरले के माध्यम से इन स्रोत-फ़ीड एकीकरण सेटिंग्स को लागू करें। |
| id | Terapkan pengaturan integrasi feed sumber ini melalui overlay konfigurasi runtime. |
| ja | これらのソース フィード統合設定は、ランタイム構成オーバーレイを通じて適用します。 |
| ko | 런타임 구성 오버레이를 통해 이러한 소스-피드 통합 설정을 적용합니다. |
| pt-BR | Aplique essas configurações de integração de feed de origem por meio da sobreposição de configuração de tempo de execução. |
| vi | Áp dụng các cài đặt tích hợp nguồn cấp dữ liệu nguồn này thông qua lớp phủ cấu hình thời gian chạy. |
| zh-Hans | 通过运行时配置覆盖应用这些源源集成设置。 |
| zh-Hant | 透過運行時配置覆蓋應用這些源源整合設定。 |

## Rank 149 — `src_16426573690bb63d`

**English:** Enable Ntfy

**Callers:**

- `src/web/src/components/System/Integrations/NotificationIntegrationsPanel.jsx:532`:                   label={interfaceText("Enable Ntfy")}

| Locale | Current target |
|---|---|
| ar | تمكين نتفي |
| de | Aktivieren Sie Ntfy |
| es | Habilitar Ntfy |
| fr | Activer Ntfy |
| hi | Ntfy सक्षम करें |
| id | Aktifkan Ntfy |
| ja | Ntfyを有効にする |
| ko | Ntfy 활성화 |
| pt-BR | Habilitar Ntfy |
| vi | Kích hoạt Ntfy |
| zh-Hans | 启用NTFY |
| zh-Hant | 啟用NTFY |

## Rank 150 — `src_1653318a216ff433`

**English:** Music acquisition via Lidarr

**Callers:**

- `src/web/src/components/Lidarr/Lidarr.jsx:750`:           <LocalizedText source={"Lidarr"} /><Header.Subheader><LocalizedText source={"Music acquisition via Lidarr"} /></Header.Subheader>

| Locale | Current target |
|---|---|
| ar | الحصول على الموسيقى عبر Lidarr |
| de | Musikerwerb über Lidarr |
| es | Adquisición de música a través de Lidarr |
| fr | Acquisition de musique via Lidarr |
| hi | Lidarr के माध्यम से संगीत अधिग्रहण |
| id | Akuisisi musik melalui Lidarr |
| ja | Lidarrによる音楽の取得 |
| ko | Lidarr를 통한 음악 획득 |
| pt-BR | Aquisição de música via Lidarr |
| vi | Thu âm nhạc qua Lidarr |
| zh-Hans | 通过 Lidarr 获取音乐 |
| zh-Hant | 透過 Lidarr 取得音樂 |
