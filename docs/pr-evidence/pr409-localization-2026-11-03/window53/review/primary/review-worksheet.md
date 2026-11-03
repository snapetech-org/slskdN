# W53 primary review worksheet

Exact PR head/tree: `6d5723e244338a550e3dfa5182a45857156467a7` / `8435576260e9aa760609be6a28001b2bb38b8c11`.
Input packet SHA-256: `e6aa0e93e693a317a02d33a853aeade7a70445ace9c69bf106a1b1ab76fbeab8`.
25 stable-ID source rows × 12 locales = 300 cells. Historical extraction ordinals are unavailable and are not claimed.

## Rank 226 — `src_181cc0be6408b7a3`

**Source:** The item could not be deleted.

**Caller references:** 0
- None found in bounded production literal scan; all locale cells are held for context.

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | تعذّر حذف هذا العنصر. | تعذّر حذف هذا العنصر. | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. The current generic deletion-failure translation is plausible, but hold the cell until its source context is pinned. | confidence: low |
| de | Das Element konnte nicht gelöscht werden. | Das Element konnte nicht gelöscht werden. | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. The current generic deletion-failure translation is plausible, but hold the cell until its source context is pinned. | confidence: low |
| es | No se pudo eliminar el elemento. | No se pudo eliminar el elemento. | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. The current generic deletion-failure translation is plausible, but hold the cell until its source context is pinned. | confidence: low |
| fr | Impossible de supprimer cet élément. | Impossible de supprimer cet élément. | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. The current generic deletion-failure translation is plausible, but hold the cell until its source context is pinned. | confidence: low |
| hi | यह आइटम हटाया नहीं जा सका। | यह आइटम हटाया नहीं जा सका। | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. The current generic deletion-failure translation is plausible, but hold the cell until its source context is pinned. | confidence: low |
| id | Item ini tidak dapat dihapus. | Item ini tidak dapat dihapus. | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. The current generic deletion-failure translation is plausible, but hold the cell until its source context is pinned. | confidence: low |
| ja | この項目を削除できませんでした。 | この項目を削除できませんでした。 | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. The current generic deletion-failure translation is plausible, but hold the cell until its source context is pinned. | confidence: low |
| ko | 항목을 삭제하지 못했습니다. | 항목을 삭제하지 못했습니다. | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. The current generic deletion-failure translation is plausible, but hold the cell until its source context is pinned. | confidence: low |
| pt-BR | Não foi possível excluir este item. | Não foi possível excluir este item. | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. The current generic deletion-failure translation is plausible, but hold the cell until its source context is pinned. | confidence: low |
| vi | Không thể xóa mục này. | Không thể xóa mục này. | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. The current generic deletion-failure translation is plausible, but hold the cell until its source context is pinned. | confidence: low |
| zh-Hans | 无法删除此项。 | 无法删除此项。 | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. The current generic deletion-failure translation is plausible, but hold the cell until its source context is pinned. | confidence: low |
| zh-Hant | 無法刪除此項目。 | 無法刪除此項目。 | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. The current generic deletion-failure translation is plausible, but hold the cell until its source context is pinned. | confidence: low |

## Rank 227 — `src_181cda8ec31125a8`

**Source:** Server Address

**Caller references:** 1
- `src/web/src/components/System/Integrations/FtpIntegrationPanel.jsx:298` (line SHA `9e2d4f499983`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | عنوان الخادم | عنوان الخادم | accept-current |
| de | Serveradresse | Serveradresse | accept-current |
| es | Dirección del servidor | Dirección del servidor | accept-current |
| fr | Adresse du serveur | Adresse du serveur | accept-current |
| hi | सर्वर पता | सर्वर का पता | refinement |
|  | **Rationale** | This is the FTP integration form label. Adding का makes the Hindi genitive relation natural. | confidence: moderate |
| id | Alamat Server | Alamat server | refinement |
|  | **Rationale** | This is the FTP integration form label. Lowercase server follows ordinary Indonesian noun capitalization. | confidence: moderate |
| ja | サーバーアドレス | サーバーアドレス | accept-current |
| ko | 서버 주소 | 서버 주소 | accept-current |
| pt-BR | Endereço do servidor | Endereço do servidor | accept-current |
| vi | Địa chỉ máy chủ | Địa chỉ máy chủ | accept-current |
| zh-Hans | 服务器地址 | 服务器地址 | accept-current |
| zh-Hant | 伺服器位址 | 伺服器位址 | accept-current |

## Rank 228 — `src_18206e1879e621e5`

**Source:** Show the previous page of contacts.

**Caller references:** 1
- `src/web/src/components/Contacts/Contacts.jsx:440` (line SHA `045b19b8afb4`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | أظهر صفحة جهات الاتصال السابقة. | أظهر صفحة جهات الاتصال السابقة. | accept-current |
| de | Vorherige Kontaktseite anzeigen. | Vorherige Kontaktseite anzeigen. | accept-current |
| es | Mostrar la página anterior de contactos. | Mostrar la página anterior de contactos. | accept-current |
| fr | Afficher la page précédente des contacts. | Afficher la page précédente des contacts. | accept-current |
| hi | संपर्कों का पिछला पृष्ठ दिखाएँ। | संपर्कों का पिछला पृष्ठ दिखाएँ। | accept-current |
| id | Tampilkan halaman kontak sebelumnya. | Tampilkan halaman kontak sebelumnya. | accept-current |
| ja | 連絡先の前のページを表示します。 | 連絡先の前のページを表示します。 | accept-current |
| ko | 이전 연락처 페이지를 표시합니다. | 이전 연락처 페이지를 표시합니다. | accept-current |
| pt-BR | Mostrar a página anterior de contatos. | Mostrar a página anterior de contatos. | accept-current |
| vi | Hiển thị trang danh bạ trước. | Hiển thị trang danh bạ trước. | accept-current |
| zh-Hans | 显示上一页联系人。 | 显示上一页联系人。 | accept-current |
| zh-Hant | 顯示上一頁聯絡人。 | 顯示上一頁聯絡人。 | accept-current |

## Rank 229 — `src_18249e74cf9aa0ea`

**Source:** MilkDrop3-style q-register coverage across equations, primitives, and shaders.

**Caller references:** 1
- `src/web/src/components/Player/visualizers/milkdrop/presetFixtures.js:124` (line SHA `730480f956eb`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | تغطية تسجيل q على غرار MilkDrop3 عبر المعادلات والأوليات والتظليل. | تغطية سجلات q على غرار MilkDrop3 عبر المعادلات والعناصر الأولية والمظللات. | correction |
|  | **Rationale** | The caller is a MilkDrop preset fixture. تسجيل q reads as recording q; this uses the q-register concept and preserves the exact MilkDrop3 product name. | confidence: moderate |
| de | Q-Register-Abdeckung im MilkDrop3-Stil über Gleichungen, Grundelemente und Shader hinweg. | Q-Register-Abdeckung im MilkDrop3-Stil über Gleichungen, Grundelemente und Shader hinweg. | accept-current |
| es | Cobertura de registro q estilo MilkDrop3 en ecuaciones, primitivas y sombreadores. | Cobertura de registros q al estilo de MilkDrop3 en ecuaciones, primitivas y shaders. | refinement |
|  | **Rationale** | The caller is a MilkDrop preset fixture. Add the missing de in al estilo de while retaining the technical q-register and MilkDrop3 terms. | confidence: moderate |
| fr | Couverture du registre q de style MilkDrop3 sur les équations, les primitives et les shaders. | Couverture du registre q de style MilkDrop3 sur les équations, les primitives et les shaders. | accept-current |
| hi | समीकरणों, प्रिमिटिव और शेडर्स में मिल्कड्रॉप3-शैली क्यू-रजिस्टर कवरेज। | समीकरणों, प्रिमिटिव और शेडर्स में MilkDrop3-शैली के q-रजिस्टर का कवरेज। | correction |
|  | **Rationale** | The caller is a MilkDrop preset fixture. Preserve the exact MilkDrop3 product spelling; the current transliteration loses the protected product name. | confidence: moderate |
| id | Cakupan q-register gaya MilkDrop3 di seluruh persamaan, primitif, dan shader. | Cakupan q-register gaya MilkDrop3 di seluruh persamaan, primitif, dan shader. | accept-current |
| ja | MilkDrop3 スタイルの q レジスタは方程式、プリミティブ、シェーダーをカバーします。 | MilkDrop3 スタイルの q レジスタは方程式、プリミティブ、シェーダーをカバーします。 | accept-current |
| ko | 방정식, 프리미티브 및 셰이더 전반에 걸쳐 MilkDrop3 스타일의 q-레지스터 적용 범위. | 방정식, 프리미티브 및 셰이더 전반에 걸쳐 MilkDrop3 스타일의 q-레지스터 적용 범위. | accept-current |
| pt-BR | Cobertura de registro q estilo MilkDrop3 em equações, primitivas e shaders. | Cobertura de registros q no estilo do MilkDrop3 em equações, primitivas e shaders. | refinement |
|  | **Rationale** | The caller is a MilkDrop preset fixture. This makes the Portuguese phrase grammatical and keeps the q-register/MilkDrop3 concepts. | confidence: moderate |
| vi | Phạm vi bao phủ đăng ký q theo phong cách MilkDrop3 trên các phương trình, nguyên thủy và trình đổ bóng. | Phạm vi bao phủ các thanh ghi q theo phong cách MilkDrop3 trong phương trình, hình cơ bản và shader. | correction |
|  | **Rationale** | The caller is a MilkDrop preset fixture. Đăng ký means sign up/register, not a technical register; this uses thanh ghi and keeps MilkDrop3 exact. | confidence: moderate |
| zh-Hans | MilkDrop3 风格的 q 寄存器覆盖方程、基元和着色器。 | MilkDrop3 风格的 q 寄存器在方程、图元和着色器中的覆盖范围。 | refinement |
|  | **Rationale** | The caller is a MilkDrop preset fixture. The current grammar makes the register itself cover the subjects; this expresses the coverage range. | confidence: moderate |
| zh-Hant | MilkDrop3 風格的 q 暫存器覆蓋方程式、基元和著色器。 | MilkDrop3 風格的 q 暫存器在方程式、圖元和著色器中的涵蓋範圍。 | refinement |
|  | **Rationale** | The caller is a MilkDrop preset fixture. The current grammar makes the register itself cover the subjects; this expresses the coverage range. | confidence: moderate |

## Rank 230 — `src_182d84066ed1de74`

**Source:** Pushover

**Caller references:** 3
- `src/web/src/components/System/Integrations/NotificationIntegrationsPanel.jsx:45` (line SHA `18d9be094e4b`)
- `src/web/src/components/System/Integrations/NotificationIntegrationsPanel.jsx:601` (line SHA `6e7d785a4e08`)
- `src/web/src/components/System/Integrations/index.jsx:77` (line SHA `18d9be094e4b`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | مهمة سهلة | Pushover | correction |
|  | **Rationale** | The caller uses Pushover as the notification-service product name. The current Arabic text translates the ordinary “easy task” sense. | confidence: moderate |
| de | Schwächling | Pushover | correction |
|  | **Rationale** | The caller uses Pushover as the notification-service product name. The current German text describes a pushover person. | confidence: moderate |
| es | Persona fácil de convencer | Pushover | correction |
|  | **Rationale** | The caller uses Pushover as the notification-service product name. The current Spanish text describes a person who is easy to persuade. | confidence: moderate |
| fr | Jeu d'enfant | Pushover | correction |
|  | **Rationale** | The caller uses Pushover as the notification-service product name. The current French text means “child’s play.” | confidence: moderate |
| hi | छोटी बात | Pushover | correction |
|  | **Rationale** | The caller uses Pushover as the notification-service product name. The current Hindi text means a small matter. | confidence: moderate |
| id | penurut | Pushover | correction |
|  | **Rationale** | The caller uses Pushover as the notification-service product name. The current Indonesian text means a compliant person. | confidence: moderate |
| ja | プッシュオーバー | Pushover | correction |
|  | **Rationale** | The caller uses Pushover as the notification-service product name. Preserve the exact service name instead of phonetic transliteration. | confidence: moderate |
| ko | 쉬운 일 | Pushover | correction |
|  | **Rationale** | The caller uses Pushover as the notification-service product name. The current Korean text means an easy task. | confidence: moderate |
| pt-BR | Flexão | Pushover | correction |
|  | **Rationale** | The caller uses Pushover as the notification-service product name. The current Portuguese text means a push-up. | confidence: moderate |
| vi | đẩy | Pushover | correction |
|  | **Rationale** | The caller uses Pushover as the notification-service product name. The current Vietnamese text means “push.” | confidence: moderate |
| zh-Hans | 推倒 | Pushover | correction |
|  | **Rationale** | The caller uses Pushover as the notification-service product name. The current Chinese text translates the ordinary “push over” sense. | confidence: moderate |
| zh-Hant | 推倒 | Pushover | correction |
|  | **Rationale** | The caller uses Pushover as the notification-service product name. The current Chinese text translates the ordinary “push over” sense. | confidence: moderate |

## Rank 231 — `src_1830a6a76eda8b82`

**Source:** Upload errored retention minutes

**Caller references:** 2
- `src/web/src/components/System/AdminPolicies/index.jsx:1584` (line SHA `d78daa74cbba`)
- `src/web/src/components/System/AdminPolicies/index.jsx:1590` (line SHA `e82c008eef34`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | تحميل دقائق الاحتفاظ التي بها أخطاء | دقائق الاحتفاظ بالتحميلات الفاشلة | correction |
|  | **Rationale** | The caller is the Errored column of the Uploads retention table. This names the duration to retain failed uploads, rather than uploading retention minutes. | confidence: moderate |
| de | Laden Sie fehlerhafte Aufbewahrungsminuten hoch | Aufbewahrungsdauer für fehlgeschlagene Uploads (Minuten) | correction |
|  | **Rationale** | The caller is the Errored column of the Uploads retention table. The current imperative says to upload retention minutes. | confidence: moderate |
| es | Cargar minutos de retención con errores | Minutos de retención de las subidas fallidas | correction |
|  | **Rationale** | The caller is the Errored column of the Uploads retention table. This is a duration label for failed uploads, not an upload action. | confidence: moderate |
| fr | Minutes de conservation des envois en erreur | Durée de conservation des envois échoués (minutes) | correction |
|  | **Rationale** | The caller is the Errored column of the Uploads retention table. This names how long failed uploads are retained. | confidence: moderate |
| hi | त्रुटिपूर्ण अवधारण मिनट अपलोड करें | विफल अपलोड को कितने मिनट तक रखना है | correction |
|  | **Rationale** | The caller is the Errored column of the Uploads retention table. The current text reverses the action and duration. | confidence: moderate |
| id | Unggah menit retensi yang error | Lama penyimpanan unggahan yang gagal (menit) | correction |
|  | **Rationale** | The caller is the Errored column of the Uploads retention table. This names the retention duration, not an upload command. | confidence: moderate |
| ja | アップロードエラーの保存時間 | 失敗したアップロードの保持期間（分） | correction |
|  | **Rationale** | The caller is the Errored column of the Uploads retention table. Add the missing unit and identify the retained failed uploads. | confidence: moderate |
| ko | 오류가 발생한 보존 시간(분) 업로드 | 실패한 업로드 보존 기간(분) | correction |
|  | **Rationale** | The caller is the Errored column of the Uploads retention table. The current word order describes an upload action. | confidence: moderate |
| pt-BR | Carregar minutos de retenção com erro | Tempo de retenção de uploads com falha (minutos) | correction |
|  | **Rationale** | The caller is the Errored column of the Uploads retention table. This names the time to retain failed uploads. | confidence: moderate |
| vi | Tải lên số phút lưu giữ bị lỗi | Thời gian lưu giữ các lượt tải lên thất bại (phút) | correction |
|  | **Rationale** | The caller is the Errored column of the Uploads retention table. This names the duration for failed uploads. | confidence: moderate |
| zh-Hans | 上传错误的保留分钟数 | 失败的上传保留时间（分钟） | correction |
|  | **Rationale** | The caller is the Errored column of the Uploads retention table. This names the retention period for failed uploads. | confidence: moderate |
| zh-Hant | 上傳錯誤的保留分鐘數 | 失敗的上傳保留時間（分鐘） | correction |
|  | **Rationale** | The caller is the Errored column of the Uploads retention table. This names the retention period for failed uploads. | confidence: moderate |

## Rank 232 — `src_183aa9ee109b285d`

**Source:** Left {podName}

**Caller references:** 1
- `src/web/src/components/Pods/Pods.jsx:600` (line SHA `daed66cb7d0b`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | اليسار {podName} | تمت مغادرة {podName} | correction |
|  | **Rationale** | The caller emits a success toast after pods.leave completes. اليسار means “left” as a direction, not leaving a Pod. | confidence: moderate |
| de | Links {podName} | Du hast {podName} verlassen. | correction |
|  | **Rationale** | The caller emits a success toast after pods.leave completes. Links means “left” as a direction. | confidence: moderate |
| es | Izquierda {podName} | Has salido de {podName}. | correction |
|  | **Rationale** | The caller emits a success toast after pods.leave completes. Izquierda means “left” as a direction. | confidence: moderate |
| fr | Gauche {podName} | Vous avez quitté {podName}. | correction |
|  | **Rationale** | The caller emits a success toast after pods.leave completes. Gauche means “left” as a direction. | confidence: moderate |
| hi | बायां {podName} | आपने {podName} छोड़ दिया। | correction |
|  | **Rationale** | The caller emits a success toast after pods.leave completes. बायां means “left” as a direction. | confidence: moderate |
| id | Kiri {podName} | Anda telah keluar dari {podName}. | correction |
|  | **Rationale** | The caller emits a success toast after pods.leave completes. Kiri means “left” as a direction. | confidence: moderate |
| ja | 左 {podName} | {podName} から退出しました。 | correction |
|  | **Rationale** | The caller emits a success toast after pods.leave completes. 左 means “left” as a direction. | confidence: moderate |
| ko | 왼쪽 {podName} | {podName}에서 나왔습니다. | correction |
|  | **Rationale** | The caller emits a success toast after pods.leave completes. 왼쪽 means “left” as a direction. | confidence: moderate |
| pt-BR | Esquerda {podName} | Você saiu de {podName}. | correction |
|  | **Rationale** | The caller emits a success toast after pods.leave completes. Esquerda means “left” as a direction. | confidence: moderate |
| vi | Còn lại {podName} | Đã rời khỏi {podName}. | correction |
|  | **Rationale** | The caller emits a success toast after pods.leave completes. Còn lại means “remaining,” not leaving. | confidence: moderate |
| zh-Hans | 左 {podName} | 已离开 {podName}。 | correction |
|  | **Rationale** | The caller emits a success toast after pods.leave completes. 左 means “left” as a direction. | confidence: moderate |
| zh-Hant | 左 {podName} | 已離開 {podName}。 | correction |
|  | **Rationale** | The caller emits a success toast after pods.leave completes. 左 means “left” as a direction. | confidence: moderate |

## Rank 233 — `src_183d5aa09b97882e`

**Source:** Failed to update: {message}

**Caller references:** 1
- `src/web/src/components/Wishlist/Wishlist.jsx:1644` (line SHA `58b5feca8be9`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | فشل التحديث: {message} | فشل التحديث: {message} | accept-current |
| de | Aktualisierung fehlgeschlagen: {message} | Aktualisierung fehlgeschlagen: {message} | accept-current |
| es | No se pudo actualizar: {message} | No se pudo actualizar: {message} | accept-current |
| fr | Échec de la mise à jour : {message} | Échec de la mise à jour : {message} | accept-current |
| hi | अद्यतन करने में विफल: {message} | अद्यतन करने में विफल: {message} | accept-current |
| id | Gagal memperbarui: {message} | Gagal memperbarui: {message} | accept-current |
| ja | 更新に失敗しました: {message} | 更新に失敗しました: {message} | accept-current |
| ko | 업데이트 실패: {message} | 업데이트 실패: {message} | accept-current |
| pt-BR | Falha ao atualizar: {message} | Falha ao atualizar: {message} | accept-current |
| vi | Không cập nhật được: {message} | Không cập nhật được: {message} | accept-current |
| zh-Hans | 更新失败：{message} | 更新失败：{message} | accept-current |
| zh-Hant | 更新失敗：{message} | 更新失敗：{message} | accept-current |

## Rank 234 — `src_1845898e47a5aa33`

**Source:** Message {label} — type / for commands, /help for the full list

**Caller references:** 1
- `src/web/src/components/Messaging/MessagingV2.jsx:1751` (line SHA `a3b6cc15b429`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | رسالة إلى {label} — اكتب / للأوامر و/help للقائمة الكاملة | رسالة إلى {label} — اكتب / للأوامر و/help للقائمة الكاملة | accept-current |
| de | Nachricht an {label} — / für Befehle, /help für die vollständige Liste eingeben | Nachricht an {label} — / für Befehle, /help für die vollständige Liste eingeben | accept-current |
| es | Mensaje para {label} — escribe / para ver comandos y /help para la lista completa | Mensaje para {label} — escribe / para ver comandos y /help para la lista completa | accept-current |
| fr | Message à {label} — saisissez / pour les commandes, /help pour la liste complète | Message à {label} — saisissez / pour les commandes, /help pour la liste complète | accept-current |
| hi | {label} को संदेश — कमांड देखने के लिए / और पूरी सूची के लिए /help लिखें | {label} को संदेश — कमांड देखने के लिए / और पूरी सूची के लिए /help लिखें | accept-current |
| id | Pesan untuk {label} — ketik / untuk perintah, /help untuk daftar lengkap | Pesan untuk {label} — ketik / untuk perintah, /help untuk daftar lengkap | accept-current |
| ja | {label} にメッセージ — / でコマンド、/help で一覧を表示 | {label} にメッセージ — / でコマンド、/help で一覧を表示 | accept-current |
| ko | {label}에게 메시지 — 명령은 /, 전체 목록은 /help 입력 | {label}에게 메시지 — 명령은 /, 전체 목록은 /help 입력 | accept-current |
| pt-BR | Mensagem para {label} — digite / para ver comandos ou /help para a lista completa | Mensagem para {label} — digite / para ver comandos ou /help para a lista completa | accept-current |
| vi | Tin nhắn gửi {label} — nhập / để xem lệnh, /help để xem toàn bộ danh sách | Tin nhắn gửi {label} — nhập / để xem lệnh, /help để xem toàn bộ danh sách | accept-current |
| zh-Hans | 给 {label} 发消息 — 输入 / 查看命令，输入 /help 查看完整列表 | 给 {label} 发消息 — 输入 / 查看命令，输入 /help 查看完整列表 | accept-current |
| zh-Hant | 傳送訊息給 {label} — 輸入 / 查看指令，輸入 /help 查看完整清單 | 傳送訊息給 {label} — 輸入 / 查看指令，輸入 /help 查看完整清單 | accept-current |

## Rank 235 — `src_184a20b7a1c37507`

**Source:** Reconnect to this room and refresh the host's current state after a connection or refresh failure.

**Caller references:** 2
- `src/web/src/components/Player/PodListenAlongPanel.jsx:237` (line SHA `62215a734490`)
- `src/web/src/components/Player/PodListenAlongPanel.jsx:248` (line SHA `a6e6a4ca0c62`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | أعد الاتصال بهذه الغرفة وقم بتحديث الحالة الحالية للمضيف بعد فشل الاتصال أو التحديث. | أعد الاتصال بهذه الغرفة وقم بتحديث الحالة الحالية للمضيف بعد فشل الاتصال أو التحديث. | accept-current |
| de | Stellen Sie nach einem Verbindungs- oder Aktualisierungsfehler erneut eine Verbindung zu diesem Raum her und aktualisieren Sie den aktuellen Status des Hosts. | Stellen Sie nach einem Verbindungs- oder Aktualisierungsfehler erneut eine Verbindung zu diesem Raum her und aktualisieren Sie den aktuellen Status des Hosts. | accept-current |
| es | Vuelva a conectarse a esta sala y actualice el estado actual del host después de una falla de conexión o actualización. | Vuelva a conectarse a esta sala y actualice el estado actual del anfitrión después de un fallo de conexión o de actualización. | correction |
|  | **Rationale** | The caller is the listen-along room retry action. Host is the person hosting playback, so anfitrión is clearer than the English loanword. | confidence: moderate |
| fr | Reconnectez-vous à cette salle et actualisez l'état actuel de l'hôte après un échec de connexion ou d'actualisation. | Reconnectez-vous à cette salle et actualisez l'état actuel de l'hôte après un échec de connexion ou d'actualisation. | accept-current |
| hi | इस कमरे से पुनः कनेक्ट करें और कनेक्शन या रिफ्रेश विफलता के बाद होस्ट की वर्तमान स्थिति को रिफ्रेश करें। | इस कमरे से पुनः कनेक्ट करें और कनेक्शन या रिफ्रेश विफलता के बाद होस्ट की वर्तमान स्थिति को रिफ्रेश करें। | accept-current |
| id | Sambungkan kembali ke ruangan ini dan segarkan status tuan rumah saat ini setelah sambungan atau penyegaran gagal. | Sambungkan kembali ke ruangan ini dan segarkan status tuan rumah saat ini setelah sambungan atau penyegaran gagal. | accept-current |
| ja | 接続または更新の失敗後に、このルームに再接続し、ホストの現在の状態を更新します。 | 接続または更新の失敗後に、このルームに再接続し、ホストの現在の状態を更新します。 | accept-current |
| ko | 연결 또는 새로 고침 실패 후 이 룸에 다시 연결하고 호스트의 현재 상태를 새로 고칩니다. | 연결 또는 새로 고침 실패 후 이 룸에 다시 연결하고 호스트의 현재 상태를 새로 고칩니다. | accept-current |
| pt-BR | Reconecte-se a esta sala e atualize o estado atual do host após uma falha de conexão ou atualização. | Reconecte-se a esta sala e atualize o estado atual do host após uma falha de conexão ou atualização. | accept-current |
| vi | Kết nối lại với phòng này và làm mới trạng thái hiện tại của máy chủ sau khi kết nối hoặc làm mới không thành công. | Kết nối lại với phòng này và làm mới trạng thái hiện tại của chủ phòng sau khi kết nối hoặc làm mới thất bại. | correction |
|  | **Rationale** | The caller is the listen-along room retry action. Máy chủ means a computer server; the host is the room’s person, chủ phòng. | confidence: moderate |
| zh-Hans | 连接或刷新失败后重新连接到该房间并刷新主机当前状态。 | 连接或刷新失败后，重新连接到该房间并刷新房主的当前状态。 | correction |
|  | **Rationale** | The caller is the listen-along room retry action. 主机 reads as a computer host; 房主 identifies the room’s playback host. | confidence: moderate |
| zh-Hant | 連線或刷新失敗後重新連線到該房間並刷新主機目前狀態。 | 連線或重新整理失敗後，重新連線到該房間並更新房主目前的狀態。 | correction |
|  | **Rationale** | The caller is the listen-along room retry action. 主機 reads as a computer host; 房主 identifies the room’s playback host. | confidence: moderate |

## Rank 236 — `src_184e54f32803f7d1`

**Source:** Collection Contents

**Caller references:** 1
- `src/web/src/components/Shares/SharedWithMe.jsx:469` (line SHA `6e1389e7d7fe`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | محتويات المجموعة | محتويات المجموعة | accept-current |
| de | Sammlungsinhalte | Sammlungsinhalte | accept-current |
| es | Contenido de la colección | Contenido de la colección | accept-current |
| fr | Contenu de la collection | Contenu de la collection | accept-current |
| hi | संग्रह की सामग्री | संग्रह की सामग्री | accept-current |
| id | Isi koleksi | Isi koleksi | accept-current |
| ja | コレクションの内容 | コレクションの内容 | accept-current |
| ko | 컬렉션 콘텐츠 | 컬렉션 콘텐츠 | accept-current |
| pt-BR | Conteúdo da coleção | Conteúdo da coleção | accept-current |
| vi | Nội dung bộ sưu tập | Nội dung bộ sưu tập | accept-current |
| zh-Hans | 合集内容 | 合集内容 | accept-current |
| zh-Hant | 收藏集內容 | 收藏集內容 | accept-current |

## Rank 237 — `src_18588677aab8f996`

**Source:** Enable Pushbullet notifications

**Caller references:** 2
- `src/web/src/components/System/Integrations/NotificationIntegrationsPanel.jsx:431` (line SHA `77f8b3e6b3e4`)
- `src/web/src/components/System/Integrations/NotificationIntegrationsPanel.jsx:439` (line SHA `7d92b2b4706a`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | تمكين الإخطارات Pushbullet | تمكين الإخطارات Pushbullet | accept-current |
| de | Aktivieren Sie Pushbullet-Benachrichtigungen | Aktivieren Sie Pushbullet-Benachrichtigungen | accept-current |
| es | Habilitar notificaciones Pushbullet | Habilitar notificaciones Pushbullet | accept-current |
| fr | Activer les notifications Pushbullet | Activer les notifications Pushbullet | accept-current |
| hi | Pushbullet सूचनाएँ सक्षम करें | Pushbullet सूचनाएँ सक्षम करें | accept-current |
| id | Aktifkan notifikasi Pushbullet | Aktifkan notifikasi Pushbullet | accept-current |
| ja | Pushbullet 通知を有効にする | Pushbullet 通知を有効にする | accept-current |
| ko | Pushbullet 알림 활성화 | Pushbullet 알림 활성화 | accept-current |
| pt-BR | Habilitar notificações Pushbullet | Habilitar notificações Pushbullet | accept-current |
| vi | Bật thông báo Pushbullet | Bật thông báo Pushbullet | accept-current |
| zh-Hans | 启用 Pushbullet 通知 | 启用 Pushbullet 通知 | accept-current |
| zh-Hant | 啟用 Pushbullet 通知 | 啟用 Pushbullet 通知 | accept-current |

## Rank 238 — `src_1859a4b709a7f566`

**Source:** Auto-tagging

**Caller references:** 1
- `src/web/src/components/System/Integrations/MetadataProcessingPanel.jsx:19` (line SHA `f67b20a0b8f9`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | وضع العلامات التلقائي | وضع العلامات التلقائي | accept-current |
| de | Automatisches Tagging | Automatisches Tagging | accept-current |
| es | Etiquetado automático | Etiquetado automático | accept-current |
| fr | Marquage automatique | Marquage automatique | accept-current |
| hi | ऑटो-टैगिंग | ऑटो-टैगिंग | accept-current |
| id | Pemberian tag otomatis | Pemberian tag otomatis | accept-current |
| ja | 自動タグ付け | 自動タグ付け | accept-current |
| ko | 자동 태그 추가 | 자동 태그 추가 | accept-current |
| pt-BR | Etiquetagem automática | Etiquetagem automática | accept-current |
| vi | Tự động gắn thẻ | Tự động gắn thẻ | accept-current |
| zh-Hans | 自动标记 | 自动标记 | accept-current |
| zh-Hant | 自動標記 | 自動標記 | accept-current |

## Rank 239 — `src_185c64e10bf3c515`

**Source:** changed fields

**Caller references:** 0
- None found in bounded production literal scan; all locale cells are held for context.

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | الحقول المتغيرة | الحقول المتغيرة | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. Hold the generic changed-fields label until its entity, register, and display context are pinned. | confidence: low |
| de | geänderte Felder | geänderte Felder | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. Hold the generic changed-fields label until its entity, register, and display context are pinned. | confidence: low |
| es | campos cambiados | campos cambiados | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. Hold the generic changed-fields label until its entity, register, and display context are pinned. | confidence: low |
| fr | champs modifiés | champs modifiés | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. Hold the generic changed-fields label until its entity, register, and display context are pinned. | confidence: low |
| hi | फ़ील्ड बदल गए | फ़ील्ड बदल गए | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. Hold the generic changed-fields label until its entity, register, and display context are pinned. | confidence: low |
| id | mengubah bidang | mengubah bidang | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. Hold the generic changed-fields label until its entity, register, and display context are pinned. | confidence: low |
| ja | 変更されたフィールド | 変更されたフィールド | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. Hold the generic changed-fields label until its entity, register, and display context are pinned. | confidence: low |
| ko | 변경된 필드 | 변경된 필드 | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. Hold the generic changed-fields label until its entity, register, and display context are pinned. | confidence: low |
| pt-BR | campos alterados | campos alterados | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. Hold the generic changed-fields label until its entity, register, and display context are pinned. | confidence: low |
| vi | trường đã thay đổi | trường đã thay đổi | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. Hold the generic changed-fields label until its entity, register, and display context are pinned. | confidence: low |
| zh-Hans | 改变的字段 | 改变的字段 | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. Hold the generic changed-fields label until its entity, register, and display context are pinned. | confidence: low |
| zh-Hant | 改變的字段 | 改變的字段 | hold-context |
|  | **Rationale** | No exact production caller was found in the bounded source scan. Hold the generic changed-fields label until its entity, register, and display context are pinned. | confidence: low |

## Rank 240 — `src_1873f429221dcdba`

**Source:** Obfs4 Proxy Path

**Caller references:** 1
- `src/web/src/components/System/Security/AdversarialSettings.jsx:1036` (line SHA `67e93915c927`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | مسار الوكيل Obfs4 | مسار الوكيل Obfs4 | accept-current |
| de | Obfs4-Proxy-Pfad | Obfs4-Proxy-Pfad | accept-current |
| es | Ruta de proxy Obfs4 | Ruta de proxy Obfs4 | accept-current |
| fr | Chemin du proxy Obfs4 | Chemin du proxy Obfs4 | accept-current |
| hi | Obfs4 प्रॉक्सी पथ | Obfs4 प्रॉक्सी पथ | accept-current |
| id | Jalur Proksi Obfs4 | Jalur Proksi Obfs4 | accept-current |
| ja | Obfs4 プロキシ パス | Obfs4 プロキシ パス | accept-current |
| ko | Obfs4 프록시 경로 | Obfs4 프록시 경로 | accept-current |
| pt-BR | Caminho do proxy Obfs4 | Caminho do proxy Obfs4 | accept-current |
| vi | Đường dẫn proxy Obfs4 | Đường dẫn proxy Obfs4 | accept-current |
| zh-Hans | Obfs4 代理路径 | Obfs4 代理路径 | accept-current |
| zh-Hant | Obfs4 代理路徑 | Obfs4 代理路徑 | accept-current |

## Rank 241 — `src_187897ce0afcf20b`

**Source:** more

**Caller references:** 1
- `src/web/src/components/System/Network/index.jsx:1090` (line SHA `581038e88550`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | أكثر | أكثر | accept-current |
| de | mehr | mehr | accept-current |
| es | más | más | accept-current |
| fr | plus | plus | accept-current |
| hi | अधिक | अधिक | accept-current |
| id | lagi | lagi | accept-current |
| ja | もっと | 人 | refinement |
|  | **Rationale** | The only caller appends this label after a number of worker usernames. 人 gives a natural count of the additional people. | confidence: moderate |
| ko | 더 | 명 | refinement |
|  | **Rationale** | The only caller appends this label after a number of worker usernames. 명 supplies the natural Korean counter for additional people. | confidence: moderate |
| pt-BR | mais | mais | accept-current |
| vi | hơn | nữa | correction |
|  | **Rationale** | The only caller appends this label after a number of worker usernames. hơn requires a comparison; nữa expresses additional workers. | confidence: moderate |
| zh-Hans | 更多的 | 人 | correction |
|  | **Rationale** | The only caller appends this label after the count of extra worker usernames. 人 gives a natural count of additional people; 的 makes the current suffix ungrammatical. | confidence: moderate |
| zh-Hant | 更多的 | 人 | correction |
|  | **Rationale** | The only caller appends this label after the count of extra worker usernames. 人 gives a natural count of additional people; 的 makes the current suffix ungrammatical. | confidence: moderate |

## Rank 242 — `src_18833da39fb9b7f8`

**Source:** Delta

**Caller references:** 1
- `src/web/src/components/Search/SongIDPanel.jsx:1217` (line SHA `f65b5781526f`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | الفرق | الفرق | accept-current |
| de | Differenz | Differenz | accept-current |
| es | Diferencia | Diferencia | accept-current |
| fr | Écart | Écart | accept-current |
| hi | अंतर | अंतर | accept-current |
| id | Selisih | Selisih | accept-current |
| ja | 差分 | 差分 | accept-current |
| ko | 차이 | 차이 | accept-current |
| pt-BR | Diferença | Diferença | accept-current |
| vi | Độ chênh lệch | Độ chênh lệch | accept-current |
| zh-Hans | 差值 | 差值 | accept-current |
| zh-Hant | 差值 | 差值 | accept-current |

## Rank 243 — `src_1888c1912646b77a`

**Source:** Failed to cleanup: {message}

**Caller references:** 2
- `src/web/src/components/System/MediaCore/MediaCorePods.jsx:449` (line SHA `e6fb3a97569a`)
- `src/web/src/components/System/MediaCore/MediaCorePods.jsx:905` (line SHA `e6fb3a97569a`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | فشل التنظيف: {message} | فشل التنظيف: {message} | accept-current |
| de | Bereinigung fehlgeschlagen: {message} | Bereinigung fehlgeschlagen: {message} | accept-current |
| es | Error al limpiar: {message} | Error al limpiar: {message} | accept-current |
| fr | Échec du nettoyage : {message} | Échec du nettoyage : {message} | accept-current |
| hi | सफ़ाई करने में विफल: {message} | सफ़ाई करने में विफल: {message} | accept-current |
| id | Gagal membersihkan: {message} | Gagal membersihkan: {message} | accept-current |
| ja | クリーンアップに失敗しました: {message} | クリーンアップに失敗しました: {message} | accept-current |
| ko | 정리 실패: {message} | 정리 실패: {message} | accept-current |
| pt-BR | Falha na limpeza: {message} | Falha na limpeza: {message} | accept-current |
| vi | Không dọn dẹp được: {message} | Không dọn dẹp được: {message} | accept-current |
| zh-Hans | 清理失败：{message} | 清理失败：{message} | accept-current |
| zh-Hant | 清理失敗：{message} | 清理失敗：{message} | accept-current |

## Rank 244 — `src_188b150a7d7b1b78`

**Source:** Clear imported native presets

**Caller references:** 2
- `src/web/src/components/Player/Visualizer.jsx:2049` (line SHA `58010d7ae2c5`)
- `src/web/src/components/Player/Visualizer.jsx:2054` (line SHA `56045e44ee8b`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | مسح الإعدادات المسبقة الأصلية المستوردة | مسح الإعدادات المسبقة المستوردة إلى العارض الأصلي | refinement |
|  | **Rationale** | The Visualizer caller clarifies these are imported presets for the native MilkDrop renderer. الأصلية reads as “original”; this states the renderer relationship. | confidence: moderate |
| de | Importierte native Voreinstellungen löschen | Importierte native Voreinstellungen löschen | accept-current |
| es | Borrar ajustes preestablecidos nativos importados | Borrar ajustes preestablecidos nativos importados | accept-current |
| fr | Effacer les préréglages natifs importés | Effacer les préréglages natifs importés | accept-current |
| hi | आयातित देशी प्रीसेट साफ़ करें | आयातित नेटिव प्रीसेट हटाएँ | correction |
|  | **Rationale** | The Visualizer caller clarifies these are presets for the native MilkDrop renderer. देशी suggests indigenous/local origin rather than the software renderer. | confidence: moderate |
| id | Hapus preset asli yang diimpor | Hapus preset native yang diimpor | refinement |
|  | **Rationale** | The Visualizer caller clarifies native means the app’s renderer. Asli reads as original; native is the relevant software term. | confidence: moderate |
| ja | インポートされたネイティブ プリセットをクリアする | インポートされたネイティブ プリセットをクリアする | accept-current |
| ko | 가져온 기본 사전 설정 지우기 | 가져온 네이티브 프리셋 지우기 | correction |
|  | **Rationale** | The Visualizer caller clarifies these are presets for the native MilkDrop renderer. 기본 means default, which is not the source meaning. | confidence: moderate |
| pt-BR | Limpar predefinições nativas importadas | Limpar predefinições nativas importadas | accept-current |
| vi | Xóa cài đặt trước gốc đã nhập | Xóa các preset native đã nhập | correction |
|  | **Rationale** | The Visualizer caller clarifies native means the app’s renderer. Gốc means original/root, not a native renderer. | confidence: moderate |
| zh-Hans | 清除导入的本机预设 | 清除已导入的原生预设 | refinement |
|  | **Rationale** | The Visualizer caller clarifies these are presets for the native MilkDrop renderer. 本机 means local-machine presets; 原生 preserves the renderer meaning. | confidence: moderate |
| zh-Hant | 清除導入的本機預設 | 清除已匯入的原生預設 | refinement |
|  | **Rationale** | The Visualizer caller clarifies these are presets for the native MilkDrop renderer. 本機 means local-machine presets; 原生 preserves the renderer meaning. | confidence: moderate |

## Rank 245 — `src_188ed889bef38cbf`

**Source:** Kestrel Connections

**Caller references:** 1
- `src/web/src/components/System/Metrics/index.jsx:83` (line SHA `3accc84f61ea`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | اتصالات كيستريل | اتصالات Kestrel | correction |
|  | **Rationale** | The caller is the ASP.NET Core Kestrel current-connections metric. Preserve Kestrel as the exact technology name rather than transliterating it. | confidence: moderate |
| de | Kestrel-Verbindungen | Kestrel-Verbindungen | accept-current |
| es | Conexiones de cernícalo | Conexiones de Kestrel | correction |
|  | **Rationale** | The caller is the ASP.NET Core Kestrel current-connections metric. Cernícalo means the bird kestrel; preserve the exact technology name. | confidence: moderate |
| fr | Connexions crécerelle | Connexions Kestrel | correction |
|  | **Rationale** | The caller is the ASP.NET Core Kestrel current-connections metric. Crécerelle means the bird kestrel; preserve the exact technology name. | confidence: moderate |
| hi | केस्टरेल कनेक्शन | Kestrel कनेक्शन | correction |
|  | **Rationale** | The caller is the ASP.NET Core Kestrel current-connections metric. Preserve the exact technology spelling instead of transliteration. | confidence: moderate |
| id | Koneksi Kestrel | Koneksi Kestrel | accept-current |
| ja | ケストレル接続 | Kestrel 接続数 | correction |
|  | **Rationale** | The caller is the ASP.NET Core Kestrel current-connections metric. Preserve the exact technology spelling and label the connection count. | confidence: moderate |
| ko | 케스트렐 연결 | Kestrel 연결 수 | correction |
|  | **Rationale** | The caller is the ASP.NET Core Kestrel current-connections metric. Preserve the exact technology spelling and label the connection count. | confidence: moderate |
| pt-BR | Conexões Kestrel | Conexões Kestrel | accept-current |
| vi | Kết nối Kestrel | Kết nối Kestrel | accept-current |
| zh-Hans | 红隼连接 | Kestrel 连接数 | correction |
|  | **Rationale** | The caller is the ASP.NET Core Kestrel current-connections metric. 红隼 means the bird; preserve the exact technology name. | confidence: moderate |
| zh-Hant | 紅隼連接 | Kestrel 連線數 | correction |
|  | **Rationale** | The caller is the ASP.NET Core Kestrel current-connections metric. 紅隼 means the bird; preserve the exact technology name. | confidence: moderate |

## Rank 246 — `src_18ae308732d9a519`

**Source:** Security Module Unavailable

**Caller references:** 1
- `src/web/src/components/System/Security/index.jsx:125` (line SHA `44724be0bed7`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | وحدة الأمان غير متوفرة | وحدة الأمان غير متوفرة | accept-current |
| de | Sicherheitsmodul nicht verfügbar | Sicherheitsmodul nicht verfügbar | accept-current |
| es | Módulo de seguridad no disponible | Módulo de seguridad no disponible | accept-current |
| fr | Module de sécurité indisponible | Module de sécurité indisponible | accept-current |
| hi | सुरक्षा मॉड्यूल अनुपलब्ध | सुरक्षा मॉड्यूल अनुपलब्ध | accept-current |
| id | Modul Keamanan Tidak Tersedia | Modul Keamanan Tidak Tersedia | accept-current |
| ja | セキュリティモジュールが使用できません | セキュリティモジュールが使用できません | accept-current |
| ko | 보안 모듈을 사용할 수 없음 | 보안 모듈을 사용할 수 없음 | accept-current |
| pt-BR | Módulo de segurança indisponível | Módulo de segurança indisponível | accept-current |
| vi | Mô-đun bảo mật không khả dụng | Mô-đun bảo mật không khả dụng | accept-current |
| zh-Hans | 安全模块不可用 | 安全模块不可用 | accept-current |
| zh-Hant | 安全模組不可用 | 安全模組不可用 | accept-current |

## Rank 247 — `src_18b38ae8ef3cd8fc`

**Source:** Top 10

**Caller references:** 1
- `src/web/src/components/System/SwarmAnalytics/index.jsx:240` (line SHA `eed36b8f0666`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | أعلى 10 | أفضل 10 | refinement |
|  | **Rationale** | The caller is a ranking-limit option alongside 20 and 50. أفضل is the natural label for the top-ranked entries. | confidence: moderate |
| de | Top 10 | Top 10 | accept-current |
| es | 10 mejores | 10 mejores | accept-current |
| fr | Top 10 | Top 10 | accept-current |
| hi | सर्वोत्तम 10 | सर्वोत्तम 10 | accept-current |
| id | 10 teratas | 10 teratas | accept-current |
| ja | トップ10 | トップ10 | accept-current |
| ko | 상위 10위 | 상위 10위 | accept-current |
| pt-BR | 10 principais | 10 principais | accept-current |
| vi | Top 10 | Top 10 | accept-current |
| zh-Hans | 前10名 | 前10名 | accept-current |
| zh-Hant | 前10名 | 前10名 | accept-current |

## Rank 248 — `src_18d40fddbec02bd8`

**Source:** Estimated Impact:

**Caller references:** 1
- `src/web/src/components/System/SwarmAnalytics/index.jsx:503` (line SHA `15c6d8fec6c6`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | التأثير المقدر: | التأثير المقدر: | accept-current |
| de | Geschätzte Auswirkung: | Geschätzte Auswirkung: | accept-current |
| es | Impacto estimado: | Impacto estimado: | accept-current |
| fr | Impact estimé : | Impact estimé : | accept-current |
| hi | अनुमानित प्रभाव: | अनुमानित प्रभाव: | accept-current |
| id | Perkiraan Dampak: | Perkiraan Dampak: | accept-current |
| ja | 推定される影響: | 推定される影響: | accept-current |
| ko | 예상 영향: | 예상 영향: | accept-current |
| pt-BR | Impacto estimado: | Impacto estimado: | accept-current |
| vi | Tác động ước tính: | Tác động ước tính: | accept-current |
| zh-Hans | 预计影响： | 预计影响： | accept-current |
| zh-Hant | 預計影響： | 預計影響： | accept-current |

## Rank 249 — `src_18d7b3545b378f2b`

**Source:** Wanted and cutoff-unmet items can be pulled into slskdN Wishlist review.

**Caller references:** 3
- `src/web/src/lib/servarrReadiness.js:29` (line SHA `0069e8cb5b2f`)
- `src/web/src/lib/servarrReadiness.js:78` (line SHA `e6e563654775`)
- `src/web/src/lib/servarrReadiness.js:79` (line SHA `39b712aba4e8`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | يمكن سحب العناصر المطلوبة والعناصر التي لم يتم تلبيتها إلى مراجعة قائمة أمنيات slskdN. | يمكن إضافة العناصر المطلوبة والعناصر التي لم تبلغ الحد المطلوب إلى مراجعة قائمة أمنيات slskdN. | correction |
|  | **Rationale** | The caller is a Servarr readiness description for pulling wanted and cutoff-unmet items into Wishlist review. This explains the unmet cutoff as a required threshold and uses إضافة for adding items. | confidence: moderate |
| de | Gesuchte und nicht erfüllte Artikel können in die Wunschliste-Überprüfung slskdN aufgenommen werden. | Gesuchte Einträge und solche, die den Grenzwert nicht erreichen, können zur Prüfung in die slskdN-Wunschliste übernommen werden. | correction |
|  | **Rationale** | The caller is a Servarr readiness description. The current “nicht erfüllte” omits the cutoff condition; this makes the unmet threshold explicit. | confidence: moderate |
| es | Los artículos deseados y no satisfechos se pueden incluir en la revisión de la lista de deseos slskdN. | Los elementos deseados y los que no alcanzan el umbral pueden añadirse a la revisión de la lista de deseos de slskdN. | correction |
|  | **Rationale** | The caller is a Servarr readiness description. The current “no satisfechos” omits the cutoff condition; this names the unmet threshold. | confidence: moderate |
| fr | Les éléments recherchés et non satisfaits peuvent être extraits de la liste de souhaits slskdN. | Les éléments souhaités et ceux qui n’atteignent pas le seuil peuvent être ajoutés à la liste de souhaits de slskdN pour examen. | correction |
|  | **Rationale** | The caller is a Servarr readiness description. Recherchés can mean searched and extraits de reverses the direction; this says wanted items below the cutoff are added for review. | confidence: moderate |
| hi | वांछित और कटऑफ-अनमेट आइटम को slskdN विशलिस्ट समीक्षा में खींचा जा सकता है। | चाहे गए आइटम और सीमा तक न पहुँचे आइटम समीक्षा के लिए slskdN की इच्छा-सूची में जोड़े जा सकते हैं। | correction |
|  | **Rationale** | The caller is a Servarr readiness description. Replace the unexplained cutoff-unmet hybrid with items that have not reached the threshold. | confidence: moderate |
| id | Item yang diinginkan dan item yang belum terpenuhi dapat ditarik ke ulasan Daftar Keinginan slskdN. | Item yang diinginkan dan item yang belum mencapai ambang batas dapat ditambahkan ke Daftar Keinginan slskdN untuk ditinjau. | correction |
|  | **Rationale** | The caller is a Servarr readiness description. The current wording omits the cutoff; this names the unmet threshold and review action. | confidence: moderate |
| ja | 欲しいアイテムや条件が満たされていないアイテムは、slskdN ウィッシュリストのレビューに取り込むことができます。 | 希望するアイテムや基準に達していないアイテムを、slskdN のウィッシュリストに追加して確認できます。 | refinement |
|  | **Rationale** | The caller is a Servarr readiness description. Make the cutoff threshold explicit and express the Wishlist review action naturally. | confidence: moderate |
| ko | 구함 및 충족되지 않은 컷오프 항목은 slskdN 위시리스트 검토로 가져올 수 있습니다. | 원하는 항목과 기준에 미달한 항목을 slskdN 위시리스트 검토에 추가할 수 있습니다. | correction |
|  | **Rationale** | The caller is a Servarr readiness description. The current phrasing is awkward and does not clearly identify items below the cutoff. | confidence: moderate |
| pt-BR | Itens desejados e não atendidos podem ser incluídos na revisão da lista de desejos do slskdN. | Itens desejados e os que não atingiram o limite podem ser adicionados à revisão da lista de desejos do slskdN. | correction |
|  | **Rationale** | The caller is a Servarr readiness description. The current “não atendidos” omits the cutoff condition; this names the unmet threshold. | confidence: moderate |
| vi | Các mặt hàng mong muốn và chưa đáp ứng được có thể được đưa vào phần đánh giá Danh sách yêu thích của slskdN. | Các mục được yêu cầu và các mục chưa đạt ngưỡng có thể được thêm vào phần rà soát Danh sách yêu thích của slskdN. | correction |
|  | **Rationale** | The caller is a Servarr readiness description. The current text omits the cutoff; this names the unmet threshold and review section. | confidence: moderate |
| zh-Hans | 想要的和截止未满足的项目可以拉到 slskdN 愿望清单评论中。 | 想要的项目和未达到门槛的项目可以加入 slskdN 愿望清单审核。 | correction |
|  | **Rationale** | The caller is a Servarr readiness description. The current cutoff phrase is unnatural and 评论 means comments; this names the threshold and review. | confidence: moderate |
| zh-Hant | 想要的和截止未滿足的項目可以拉到 slskdN 願望清單評論中。 | 想要的項目和未達到門檻的項目可以加入 slskdN 願望清單審查。 | correction |
|  | **Rationale** | The caller is a Servarr readiness description. The current cutoff phrase is unnatural and 評論 means comments; this names the threshold and review. | confidence: moderate |

## Rank 250 — `src_18e805b373a547da`

**Source:** Review this item’s linked search history and past results.

**Caller references:** 1
- `src/web/src/components/Wishlist/Wishlist.jsx:308` (line SHA `b45f1f8103c0`)

| Locale | Current | Primary proposal | Disposition |
|---|---|---|---|
| ar | راجع سجل البحث المرتبط بهذا العنصر والنتائج السابقة. | راجع سجل البحث المرتبط بهذا العنصر والنتائج السابقة. | accept-current |
| de | Verknüpften Suchverlauf und frühere Ergebnisse für diesen Eintrag überprüfen. | Verknüpften Suchverlauf und frühere Ergebnisse für diesen Eintrag überprüfen. | accept-current |
| es | Revisa el historial de búsqueda vinculado y los resultados anteriores de este elemento. | Revisa el historial de búsqueda vinculado y los resultados anteriores de este elemento. | accept-current |
| fr | Consulter l’historique de recherche lié à cet élément et ses résultats précédents. | Consulter l’historique de recherche lié à cet élément et ses résultats précédents. | accept-current |
| hi | इस आइटम के लिंक किए गए खोज इतिहास और पुराने परिणामों की समीक्षा करें। | इस आइटम के लिंक किए गए खोज इतिहास और पुराने परिणामों की समीक्षा करें। | accept-current |
| id | Tinjau riwayat pencarian tertaut dan hasil sebelumnya untuk item ini. | Tinjau riwayat pencarian tertaut dan hasil sebelumnya untuk item ini. | accept-current |
| ja | この項目にリンクされた検索履歴と過去の結果を確認します。 | この項目にリンクされた検索履歴と過去の結果を確認します。 | accept-current |
| ko | 이 항목에 연결된 검색 기록과 이전 결과를 검토합니다. | 이 항목에 연결된 검색 기록과 이전 결과를 검토합니다. | accept-current |
| pt-BR | Revise o histórico de pesquisas vinculado a este item e os resultados anteriores. | Revise o histórico de pesquisas vinculado a este item e os resultados anteriores. | accept-current |
| vi | Xem lại lịch sử tìm kiếm được liên kết và kết quả trước đây của mục này. | Xem lại lịch sử tìm kiếm được liên kết và kết quả trước đây của mục này. | accept-current |
| zh-Hans | 查看此项目关联的搜索历史和以往结果。 | 查看此项目关联的搜索历史和以往结果。 | accept-current |
| zh-Hant | 檢視此項目連結的搜尋記錄和先前結果。 | 檢視此項目連結的搜尋記錄和先前結果。 | accept-current |
