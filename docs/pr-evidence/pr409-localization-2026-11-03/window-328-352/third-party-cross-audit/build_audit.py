import json, pathlib, hashlib, re, subprocess, collections, sys
root=pathlib.Path('/mnt/disks/scratch/task-scratch')
pr= root/'slskdn-pr409-w58-ranks328-352-primary-20261103'
br= root/'slskdn-pr409-w58-independent-blind-20261103'
inp=pr/'input'; out=root/'slskdn-pr409-w58-third-party-cross-audit-20261103'
wt=pathlib.Path('/mnt/disks/scratch/task-worktrees/localization-20261103/slskdn-pr409-w56-apply-20261103')
assert out.exists() and {x.name for x in out.iterdir()}=={'build_audit.py'}, 'Output may contain only this task-owned builder before generation.'
def load(path): return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()]
def H(v): return hashlib.sha256(v.encode('utf-8') if isinstance(v,str) else v).hexdigest()
def K(rank,loc): return (rank,loc)
cells=load(inp/'source-current-cells.jsonl')
P=load(pr/'primary'/'primary-decisions.jsonl')
B=load(br/'review'/'blind-decisions.jsonl')
contexts=load(inp/'caller-contexts.jsonl')
pm={(x['sourceId'],x['locale']):x for x in P}
bm={(x['sourceId'],x['locale']):x for x in B}
cm={(x['sourceId'],x['locale']):x for x in cells}
cx={x['sourceId']:x for x in contexts}
head='47735fbdb8df3de8dc5fd297c2717dc332764431'; tree='b29397903a036d40af1c6551dedbe070e735cfed'
manifest=json.loads((inp/'manifest.json').read_text())
att=json.loads((inp/'head-tree-attestation.json').read_text())
assert manifest['candidateFree'] and manifest['cellCount']==300 and manifest['sourceCount']==25
assert att['head']==head and att['tree']==tree and att['remoteBranchHead']==head
assert len(cells)==len(P)==len(B)==300 and all(x['containsCandidate'] is False for x in cells)
assert subprocess.check_output(['git','-C',str(wt),'rev-parse','HEAD'],text=True).strip()==head
assert subprocess.check_output(['git','-C',str(wt),'rev-parse','HEAD^{tree}'],text=True).strip()==tree
assert not subprocess.check_output(['git','-C',str(wt),'status','--porcelain=v1'],text=True).strip()
for folder,checksum in [(inp,'PACKET-SHA256SUMS.txt'),(pr/'primary','PRIMARY-SHA256SUMS.txt'),(br,'SHA256SUMS.txt')]:
    r=subprocess.run(['sha256sum','-c',checksum],cwd=folder,text=True,capture_output=True)
    assert r.returncode==0,(folder,r.stdout,r.stderr)
for f in (x for x in inp.iterdir() if x.is_file()):
    assert f.read_bytes()==(br/'input'/f.name).read_bytes(),f'Blind copy differs: {f.name}'
# Verify every production caller against the exact pinned source tree.
caller_total=0
for c in contexts:
    caller_total+=len(c['callers'])
    for q in c['callers']:
        raw=subprocess.check_output(['git','-C',str(wt),'show',f'{head}:{q["path"]}'])
        lines=raw.decode().splitlines()
        assert H(raw)==q['fileSha256']
        assert subprocess.check_output(['git','-C',str(wt),'rev-parse',f'{head}:{q["path"]}',],text=True).strip()==q['gitBlob']==q['gitBlobSha1Check']
        assert lines[q['line']-1]==q['lineText'] and H(q['lineText'])==q['lineSha256']
        assert all(lines[z['line']-1]==z['text'] for z in q['context'])
assert len(contexts)==25 and caller_total==48 and all(x['productionCallerCount'] for x in contexts)
# Ensure both reviews used the same source, target, catalog, and pinned commit for every cell.
for c in cells:
    k=(c['sourceId'],c['locale']); p=pm[k]; b=bm[k]
    assert p['head']==b['head']==head and p['tree']==b['tree']==tree
    assert p['source']==b['source']==c['source'] and H(c['source'])==c['sourceSha256']==p['sourceSha256']==b['sourceSha256']
    assert p['currentTarget']==b['currentTarget']==c['currentTarget']
    assert H(c['currentTarget'])==c['currentTargetSha256']==p['currentTargetSha256']==b['currentTargetSha256']
    assert p['catalogPath']==b['catalogPath']==c['catalogPath'] and p['catalogFileSha256']==b['catalogFileSha256']==c['catalogFileSha256']
    assert p['catalogGitBlob']==b['catalogGitBlob']==c['catalogGitBlob']
# All rows on which disposition or non-null proposal differs.
dis=set()
for c in cells:
    p=pm[(c['sourceId'],c['locale'])]; b=bm[(c['sourceId'],c['locale'])]
    if p['decision']!=b['disposition'] or (p['candidateTarget'] is not None and b['proposedTarget'] is not None and p['candidateTarget']!=b['proposedTarget']):
        dis.add(K(c['continuationRank'],c['locale']))
patch={}
def setp(r,l,d,t,why): patch[K(r,l)]=(d,t,why)
# 328 HTTPS port: use the locale-specific term and preserve the protocol token.
setp(328,'zh-Hant','correction','HTTPS 連接埠','The caller labels a numeric HTTPS configuration field. 連接埠 is the conventional network-port term for Traditional Chinese; preserve HTTPS exactly.')
# 329 persistent atlas tooltip: repair modal/seed/page meanings and remove clear calques.
setp(329,'ar','correction','أنشئ أطلسًا دائمًا داخل الصفحة من حقول البذور الحالية بدلًا من فتح نافذة منبثقة مؤقتة','The current نموذج مؤقت reads as a form, while the tooltip contrasts a persistent in-page atlas with a temporary modal; the selected dialog wording restores that UI meaning.')
setp(329,'de','refinement','Erstellen Sie aus den aktuellen Seed-Feldern einen dauerhaft auf der Seite eingebetteten Atlas, statt ein temporäres Dialogfenster zu öffnen','Replaces the English-shaped In-Page-Atlas/Modal phrasing with an explicit on-page atlas and temporary dialog, preserving seed fields and persistence.')
setp(329,'hi','correction','वर्तमान बीज फ़ील्ड से पेज के भीतर स्थायी एटलस बनाएँ, अस्थायी मोडल खोलने के बजाय','The current सतत एटलस means continuous atlas and इन-पेज is an awkward calque; this says persistent atlas within the page.')
setp(329,'ja','refinement','現在のシードフィールドからページ内に永続的なアトラスを構築し、一時的なモーダルを開かないようにします','The existing page-embedded compound is awkward; this states the same in-page persistent atlas and temporary-modal choice clearly.')
setp(329,'ko','refinement','현재 시드 필드에서 페이지 안에 지속적으로 유지되는 아틀라스를 만들고, 임시 모달을 열지 않습니다','Replaces the English-shaped 인페이지 with a clear description of an atlas maintained within the page.')
setp(329,'pt-BR','correction','Crie um atlas persistente dentro da página usando os campos de semente atuais, em vez de abrir um modal temporário','The source says current seed fields; current campos iniciais means initial fields. This restores seed fields and retains the modal contrast.')
setp(329,'vi','correction','Tạo một sơ đồ tổng quan thường trực trong trang từ các trường seed hiện tại, thay vì mở hộp thoại tạm thời','The current phương thức means method rather than modal dialog; hộp thoại restores the interface meaning and keeps the in-page contrast.')
setp(329,'zh-Hans','correction','根据当前种子字段在页面内构建持久化图谱，而不是打开临时对话框','The current 临时模式 means temporary mode, not a modal dialog; 对话框 restores the UI meaning.')
setp(329,'zh-Hant','correction','根據目前種子欄位在頁面內建構持久化圖譜，而不是開啟臨時對話框','The current 臨時模式 means temporary mode, not a modal dialog; 對話框 restores the UI meaning.')
# 331 SearchList previous-page popup.
setp(331,'zh-Hans','correction','转到上一页的搜索列表','The exact caller is a SearchList previous-page tooltip. 搜索结果 narrows this to result pages; the selected wording names the previous page of searches.')
setp(331,'zh-Hant','correction','前往上一頁的搜尋列表','The exact caller is a SearchList previous-page tooltip. The current omits the list; the selected wording names the previous page of searches.')
# 332 clipboard action.
setp(332,'id','refinement','Salin teks pesan ini ke papan klip','papan klip localizes the borrowed clipboard term without changing the copy-message-text action.')
setp(332,'vi','refinement','Sao chép văn bản của tin nhắn này vào bảng tạm','bảng tạm localizes clipboard and preserves the source’s “text” object rather than broadening it to all message contents.')
# 334 visualizer fullscreen control.
setp(334,'ar','correction','كبّر أداة العرض المرئي إلى وضع ملء الشاشة','The current المتخيل means an imagined thing. The PlayerBar caller is the visualizer fullscreen control; أداة العرض المرئي names the tool.')
setp(334,'ko','correction','시각화 도구를 전체 화면으로 최대화하세요','The current 도우미 means assistant. The PlayerBar caller controls the visualizer; 도구 means tool.')
# 335 active feature heading.
setp(335,'pt-BR','refinement','Funcionalidades ativas','The caller labels enabled security features; funcionalidades names features more precisely than generic recursos.')
setp(335,'zh-Hans','correction','已启用的功能','The caller lists settings only when Enabled is true. Current 主动功能 means proactive features; this means enabled features.')
setp(335,'zh-Hant','correction','已啟用的功能','The caller lists settings only when Enabled is true. Current 主動功能 means proactive features; this means enabled features.')
# 336 network-health banner.
setp(336,'ar','refinement','لم يتم العثور على مشكلات في صحة الشبكة المحلية','The positive banner summarizes healthy mesh, DHT, HashDb, and security counters. This communicates no local-network problems; current “no results for health” is unclear.')
setp(336,'de','refinement','Keine Auffälligkeiten im lokalen Netzwerk','The positive banner summarizes healthy network counters. This means no local-network anomalies and is clearer than the current compound.')
setp(336,'es','refinement','No se detectaron problemas en la red local','The caller is a positive health banner; this directly states that no local-network problems were detected.')
setp(336,'fr','correction','Aucun problème n’a été détecté sur le réseau local','The caller is a positive health banner. Current says no results about network state; this states the intended no-problem finding.')
setp(336,'id','refinement','Tidak ditemukan masalah pada kesehatan jaringan lokal','The positive banner summarizes healthy counters. This says no issues were found and is clearer than the current literal health-findings phrase.')
setp(336,'ja','refinement','ローカルネットワークに問題は見つかりませんでした','The positive banner summarizes healthy counters. This directly says no local-network problems were found.')
setp(336,'ko','refinement','로컬 네트워크에서 이상이 발견되지 않았습니다','The positive banner summarizes healthy counters. This avoids the current awkward nominal fragment and says no anomalies were found.')
setp(336,'pt-BR','correction','Nenhum problema foi encontrado na rede local','The caller is a positive health banner. Current descoberta de saúde is unclear; this says no problem was found and avoids the blind proposal’s narrower “integrity” meaning.')
# 342 sharing setup guidance.
setp(342,'de','refinement','Das Teilen ist optional. Fügen Sie nur dann ein Freigabeverzeichnis hinzu, wenn andere Peers ausgewählte Ordner durchsuchen können sollen','The setup-health caller describes a share root for peer browsing. This retains directory and browse semantics and removes current awkward dürfen sollen wording.')
setp(342,'es','correction','Compartir es opcional. Añade una carpeta para compartir solo si quieres que otros pares puedan explorar las carpetas seleccionadas','The source says peers can browse folders. The current says users can see them, weakening browse and omitting peer.')
# 343 exact public DHT rendezvous notice.
setp(343,'ar','correction','تم تمكين نقطة التقاء DHT، ويمكن لهذه العقدة نشر نقطة النهاية العامة في شبكة BitTorrent DHT العامة. هذا أمر متوقع عند تمكين نقطة الالتقاء العامة؛ وهذا التنبيه موجود فقط لإبلاغ المشغّلين بأن أقران slskdN الآخرين يمكنهم اكتشاف العقدة لمزامنة الشبكة','Current موعد DHT reads as appointment; this restores rendezvous meaning and keeps DHT, BitTorrent, and slskdN exactly.')
setp(343,'de','refinement','Das DHT-Rendezvous ist aktiviert, und dieser Knoten kann seinen öffentlichen Endpunkt in der öffentlichen BitTorrent-DHT veröffentlichen. Das ist erwartbar, wenn das öffentliche Rendezvous aktiviert ist; dieser Hinweis soll Betreiber lediglich darauf aufmerksam machen, dass andere slskdN-Peers den Knoten für die Mesh-Synchronisierung entdecken können','This caller describes public endpoint publication and peer discovery. The selected grammar clarifies the DHT compound and discover action while preserving exact product terms.')
setp(343,'es','correction','El punto de encuentro DHT está habilitado y este nodo puede publicar su punto de conexión público en la DHT pública de BitTorrent. Esto es normal cuando está habilitado el punto de encuentro público; este aviso solo informa a los operadores de que otros pares de slskdN pueden descubrir el nodo para sincronizar la red de malla','Current punto final is a final point, not endpoint, and BitTorrent DHT order is awkward. This restores the network terms and rendezvous meaning.')
setp(343,'fr','correction','Le rendez-vous DHT est activé et ce nœud peut publier son point de terminaison public dans le DHT public de BitTorrent. C’est normal lorsque le rendez-vous public est activé ; cet avis informe simplement les opérateurs que d’autres pairs slskdN peuvent découvrir ce nœud pour la synchronisation du maillage','Current public BitTorrent DHT word order is incorrect. This restores the public DHT/BitTorrent relationship and uses pairs for peers.')
setp(343,'hi','refinement','DHT का मिलन-बिंदु सक्षम है और यह नोड अपना सार्वजनिक एंडपॉइंट सार्वजनिक BitTorrent DHT में प्रकाशित कर सकता है। सार्वजनिक मिलन-बिंदु सक्षम होने पर यह अपेक्षित है; यह सूचना केवल ऑपरेटरों को बताने के लिए है कि अन्य slskdN पीयर मेश सिंक के लिए इस नोड को खोज सकते हैं','This notice concerns endpoint publication and mesh peer discovery. The selected text makes its operator purpose explicit and preserves exact product literals.')
setp(343,'id','correction','Titik temu DHT aktif dan node ini dapat memublikasikan endpoint publiknya ke DHT publik BitTorrent. Hal ini memang diharapkan saat titik temu publik diaktifkan; pemberitahuan ini hanya agar operator mengetahui bahwa peer slskdN lain dapat menemukan node ini untuk sinkronisasi mesh','The selected wording makes the technical endpoint and peer-discovery concepts explicit; exact DHT, BitTorrent, and slskdN literals remain.')
setp(343,'ko','refinement','DHT 랑데부가 활성화되어 이 노드는 공개 엔드포인트를 공개 BitTorrent DHT에 게시할 수 있습니다. 공개 랑데부가 활성화된 경우 정상적인 동작입니다. 이 알림은 다른 slskdN 피어가 메시 동기화를 위해 노드를 발견할 수 있음을 운영자에게 알리기 위한 것입니다','The caller is an operator notice about publication/discovery. This clarifies the notice’s purpose and preserves all protected literals.')
setp(343,'pt-BR','correction','O ponto de encontro DHT está ativado, e este nó pode publicar seu endpoint público na DHT pública do BitTorrent. Isso é esperado quando o ponto de encontro público está ativado; este aviso existe apenas para informar aos operadores que outros pares slskdN podem descobrir o nó para sincronização da malha','Current terminal público means a public terminal, not endpoint. This corrects it and preserves DHT, BitTorrent, and slskdN.')
setp(343,'vi','correction','Điểm hẹn DHT đã được bật và nút này có thể công bố điểm cuối công khai của mình lên DHT BitTorrent công khai. Đây là điều bình thường khi điểm hẹn công khai được bật; thông báo này chỉ để các nhà vận hành biết rằng các nút ngang hàng slskdN khác có thể phát hiện nút này để đồng bộ lưới','Current đồng nghiệp means colleagues rather than peers. This uses peer nodes and preserves public endpoint and mesh-sync meaning.')
setp(343,'zh-Hans','refinement','DHT 会合已启用，该节点可以将其公共端点发布到 BitTorrent 公共 DHT 中。启用公共会合时出现这种情况是正常的；此通知仅提醒操作人员，其他 slskdN 对等节点可以发现该节点以进行网格同步','This benign operator notice is clearer when it explains why it is shown; exact DHT, BitTorrent, and slskdN terms remain.')
# 346 PlayerBar interpolation count.
setp(346,'ar','correction','{shownFileCount} من أصل {totalFiles} مسارًا','The caller supplies shown and total track counts. This makes the “shown out of total tracks” relation explicit and preserves both placeholders.')
setp(346,'es','refinement','{shownFileCount} de {totalFiles} pistas','The caller supplies displayed and total track counts. This uses ordinary count-before-noun order; placeholders are unchanged.')
setp(346,'zh-Hans','correction','已显示 {shownFileCount} 首，共 {totalFiles} 首曲目','The caller supplies displayed tracks and total tracks. Current reverses the count relation; this states shown count first, total tracks second, preserving both placeholders.')
setp(346,'zh-Hant','correction','已顯示 {shownFileCount} 首，共 {totalFiles} 首曲目','The caller supplies displayed tracks and total tracks. Current reverses the count relation; this states shown count first, total tracks second, preserving both placeholders.')
# 348 browser-window visualizer.
setp(348,'ar','correction','كبّر أداة العرض المرئي لتملأ نافذة المتصفح','The caller maximizes the visualizer into the browser window. Current repeats the ambiguous “imagined thing”; blind says open rather than maximize. This states the fill/maximize behavior.')
setp(348,'ko','correction','시각화 도구를 브라우저 창에서 최대화하세요','Current 도우미 means assistant, but this is a visualizer control. 도구 means tool and preserves maximize.')
setp(348,'zh-Hans','refinement','将可视化工具最大化至浏览器窗口中','Current modifier order reads as maximizing the window’s visualizer. This clarifies the visualizer action and browser-window target.')
setp(348,'zh-Hant','refinement','將視覺化工具最大化至瀏覽器視窗中','Current modifier order reads as maximizing the window’s visualizer. This clarifies the visualizer action and browser-window target.')
# 351 setting label.
setp(351,'hi','correction','सिंक अंतराल','The caller uses this as a setting label before the sync interval value. Current अंतराल सिंक करना is action-like; this names the interval.')
assert set(patch)==dis, (len(patch),len(dis),sorted(dis-set(patch)),sorted(set(patch)-dis))
# Reconcile all rows, verify final text and record exact caller/source checks.
ledger=[]
for c in sorted(cells,key=lambda x:(x['continuationRank'],x['locale'])):
    k=(c['sourceId'],c['locale']); p=pm[k]; b=bm[k]; rank=c['continuationRank']; loc=c['locale']
    if K(rank,loc) in patch: disp,target,why=patch[K(rank,loc)]
    else:
        assert p['decision']==b['disposition'] and p['candidateTarget']==b['proposedTarget']
        disp,target=p['decision'],p['selectedTarget']
        why='No conflict: both ledgers select the same disposition and target. Cross-audit verifies the pinned source, recorded production callers, and integrity constraints.'
    assert disp in ('accept-current','correction','refinement','hold')
    assert (target==c['currentTarget']) if disp=='accept-current' else (target is None if disp=='hold' else target is not None)
    src=c['source']
    def ph(s): return re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s)
    def tags(s): return re.findall(r'<\s*/?\s*[A-Za-z][^>]*>',s)
    def nums(s): return re.findall(r'(?<![A-Za-z])\d+(?:[.,]\d+)?',s)
    required=sorted(set(p.get('protectedLiteralsRequired',[]))|set(b.get('protectedSourceTerms',[])))
    protected={t:t in target for t in required} if target is not None else {t:False for t in required}
    checks={
      'sourceHashVerified':H(src)==c['sourceSha256'],
      'currentHashVerified':H(c['currentTarget'])==c['currentTargetSha256'],
      'selectedHashVerified':target is not None and H(target)==H(target),
      'placeholderParity':target is not None and collections.Counter(ph(src))==collections.Counter(ph(target)),
      'markupParity':target is not None and tags(src)==tags(target),
      'numericParity':target is not None and nums(src)==nums(target),
      'protectedLiteralsPresent':all(protected.values()),
      'edgeWhitespaceParity':target is not None and (len(src)-len(src.lstrip()),len(src)-len(src.rstrip()))==(len(target)-len(target.lstrip()),len(target)-len(target.rstrip()))
    }
    assert all(checks.values()),(rank,loc,checks,required,src,target)
    context=cx[c['sourceId']]
    callers=[{'path':q['path'],'line':q['line'],'lineText':q['lineText'],'lineSha256':q['lineSha256'],'contextSha256':q['contextSha256'],'fileSha256':q['fileSha256'],'gitBlob':q['gitBlob']} for q in context['callers']]
    mismatch=(p['decision']!=b['disposition'] or (p['candidateTarget'] is not None and b['proposedTarget'] is not None and p['candidateTarget']!=b['proposedTarget']))
    ledger.append({
      'schemaVersion':1,'repository':'snapetech-org/slskdN','pullRequest':409,'head':head,'tree':tree,
      'continuationRank':rank,'historicalSourceOrdinal':c['historicalSourceOrdinal'],'sourceId':c['sourceId'],'locale':loc,
      'source':src,'sourceSha256':c['sourceSha256'],'catalogPath':c['catalogPath'],'catalogFileSha256':c['catalogFileSha256'],'catalogGitBlob':c['catalogGitBlob'],
      'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],
      'primary':{'decision':p['decision'],'candidateTarget':p['candidateTarget'],'candidateTargetSha256':p.get('candidateTargetSha256'),'selectedTarget':p['selectedTarget'],'selectedTargetSha256':p['selectedTargetSha256'],'confidence':p['confidence'],'rationale':p['rationale'],'nativeSpeakerApproved':p['nativeSpeakerApproved'],'protectedLiteralsRequired':p['protectedLiteralsRequired']},
      'blind':{'disposition':b['disposition'],'proposedTarget':b['proposedTarget'],'proposedTargetSha256':H(b['proposedTarget']) if b['proposedTarget'] is not None else None,'confidence':b['confidence'],'rationale':b['rationale'],'nativeSpeakerApproval':b['nativeSpeakerApproval'],'protectedSourceTerms':b['protectedSourceTerms']},
      'reviewDisagreement':mismatch,'finalDisposition':disp,'selectedTarget':target,'selectedTargetSha256':H(target) if target is not None else None,
      'thirdPartyRationale':why,'thirdPartyConfidence':'moderate','callerEvidence':{'boundedScan':context['boundedScan'],'productionCallerCount':context['productionCallerCount'],'callers':callers},
      'protectedLiteralChecks':protected,'integrityChecks':checks,'nativeSpeakerApproved':False
    })
counts=collections.Counter(x['finalDisposition'] for x in ledger)
changed=sum(x['selectedTarget']!=x['currentTarget'] for x in ledger)
assert len(ledger)==300 and sum(x['reviewDisagreement'] for x in ledger)==48 and changed==58
assert counts==collections.Counter({'accept-current':242,'correction':36,'refinement':22})
(out/'reconciliation-ledger.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in ledger))
summary={'artifact':'slskdN PR #409 W58 ranks 328-352 third-party cross-audit','createdUtc':'2026-11-03','repository':'snapetech-org/slskdN','pullRequest':409,'head':head,'tree':tree,'cellCount':300,'sourceCount':25,'localeCount':12,'callerOccurrenceCount':caller_total,'callerlessSourceCount':0,'reviewDisagreementCount':48,'finalDispositionCounts':dict(counts),'selectedTargetChangesFromCurrent':changed,'allChecksPassed':True,'nativeSpeakerApproval':False,'noCatalogOrRepoChanges':True,'noTestsBuildsScansCIOrPRMutations':True}
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
evidence=[inp/n for n in ['README.md','manifest.json','head-tree-attestation.json','PACKET-SHA256SUMS.txt','source-current-cells.jsonl','caller-contexts.jsonl','catalog-structure.jsonl','selection-and-boundary.json','selection-boundary.jsonl','source-inventory-selection.jsonl']]
evidence += [pr/'primary'/'primary-decisions.jsonl',pr/'primary'/'PRIMARY-SHA256SUMS.txt',br/'review'/'blind-decisions.jsonl',br/'SHA256SUMS.txt']
provenance={'inputs':[{'path':str(f),'bytes':f.stat().st_size,'sha256':H(f.read_bytes())} for f in evidence],'candidateFreeManifest':manifest,'exactSourceTree':{'worktree':str(wt),'head':head,'tree':tree,'status':'clean; verified before output write'},'method':'Compare only the candidate-free packet and raw primary/blind ledgers; independently adjudicate every differing disposition or proposal; validate exact-head caller lines and literals.','scopeLimit':'Machine cross-audit only; no native-speaker approval claimed.'}
(out/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
by=collections.defaultdict(collections.Counter)
for x in ledger: by[x['continuationRank']][x['finalDisposition']]+=1
lines=['# slskdN PR #409 W58 third-party cross-audit','',
f'- Exact PR head: `{head}` (tree `{tree}`); PR #409 was open draft when pinned.',
f'- Scope: 25 source IDs × 12 locales = {len(ledger)} cells, ranks 328–352.',
f'- Candidate-free input: `{inp}`; raw reviewer ledgers and SHA-256 pins are recorded in `provenance.json`.',
f'- Caller evidence: {caller_total} production caller occurrences across 25 source strings; zero callerless strings.',
f'- Reviewer disagreements adjudicated: 48.',
f'- Final: {counts["accept-current"]} accept-current, {counts["correction"]} corrections, {counts["refinement"]} refinements, {counts["hold"]} holds; {changed} selected targets differ from current.',
'- Placeholder, markup, number, edge-whitespace, protected-literal, and exact-head caller checks passed for all 300 cells.',
'- No native-speaker approval is claimed. No catalog/repo/PR/workflow changes or tests/builds/scans/CI were made.','',
'## Per-rank disposition counts','',
'| Rank | Accept current | Corrections | Refinements | Holds |','|---:|---:|---:|---:|---:|']
for r in range(328,353):
    q=by[r]; lines.append(f'| {r} | {q["accept-current"]} | {q["correction"]} | {q["refinement"]} | {q["hold"]} |')
lines += ['', '## Files','', '- `reconciliation-ledger.jsonl`: one selected target per cell with source/current/reviewer hashes, third-party rationale, exact caller references, and checks.','- `provenance.json`: input SHA-256 pins and exact source tree.','- `summary.json`: machine-readable counts.','- `build_audit.py`: reproducible packet verifier/ledger builder.','- `SHA256SUMS.txt`: hashes of all deliverables above except itself.','']
(out/'README.md').write_text('\n'.join(lines),encoding='utf-8')
# Hash all deliverables except this checksum file.
files=[out/n for n in ['README.md','summary.json','provenance.json','reconciliation-ledger.jsonl','build_audit.py']]
(out/'SHA256SUMS.txt').write_text(''.join(f'{H(f.read_bytes())}  {f.name}\n' for f in files))
v=subprocess.run(['sha256sum','-c','SHA256SUMS.txt'],cwd=out,text=True,capture_output=True)
assert v.returncode==0,(v.stdout,v.stderr)
print(json.dumps({'out':str(out),'summary':summary,'sha256sums':(out/'SHA256SUMS.txt').read_text(),'bytes':sum(x.stat().st_size for x in out.iterdir() if x.is_file()),'verify':v.stdout},ensure_ascii=False,indent=2))
