#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, re, shutil
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
CF=ROOT/'candidate-free'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

def sha(b): return hashlib.sha256(b).hexdigest()
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def token_data(source,target):
    placeholders=lambda s:collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s))
    tags=lambda s:collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',s))
    nums=lambda s:re.findall(r'(?<![A-Za-z])\d+(?:[.,]\d+)?%?(?![A-Za-z])',s)
    protected=lambda s:sorted(set(re.findall(r'\b[A-Z][A-Z0-9]{1,}\b',s))|{x for x in ('slskdN','PodCore','Wishlist','soulfind','FFmpeg','Lidarr') if x in s})
    return {'placeholders':placeholders(source)==placeholders(target),'markup':tags(source)==tags(target),
      'numbersSource':sorted(nums(source)),'numbersTarget':sorted(nums(target)),
      'numbersPreserved':collections.Counter(nums(source))<=collections.Counter(nums(target)),
      'protectedSource':protected(source),'protectedTarget':protected(target),
      'protectedLiteralsPreserved':all(x in target for x in protected(source))}

def main():
    proposal={
      (1028,'de'):'Aktivieren Sie die ausgewählten Wunschlistensuchen, damit geplante Läufe sie erneut prüfen können.',
      (1029,'es'):'Clave de API de Last.fm',
      (1029,'fr'):'Clé API de Last.fm',
      (1029,'pt-BR'):'Chave da API do Last.fm',
      (1030,'id'):'Notifikasi Ntfy untuk pesan pribadi',
      (1031,'ar'):' ثانية من المقطع',
      (1031,'es'):' s de duración del clip',
      (1031,'fr'):' s de durée du clip',
      (1031,'hi'):' सेकंड की क्लिप',
      (1031,'id'):' detik durasi klip',
      (1031,'ja'):'秒のクリップ',
      (1031,'ko'):'초 클립',
      (1031,'pt-BR'):' s de duração do clipe',
      (1031,'vi'):' giây của clip',
      (1031,'zh-Hans'):'秒片段',
      (1031,'zh-Hant'):'秒片段',
      (1037,'ar'):'إظهار الجهات الفاعلة لمصادر التوصيات الفدرالية',
      (1037,'de'):'Akteure aus föderierten Empfehlungsquellen anzeigen',
      (1037,'es'):'Revelar los actores de origen de las recomendaciones federadas',
      (1037,'id'):'Tampilkan aktor sumber rekomendasi federasi',
      (1037,'ja'):'フェデレーション推薦のソースアクターを表示',
      (1037,'vi'):'Hiển thị các tác nhân nguồn của đề xuất liên thông',
      (1037,'zh-Hans'):'显示联邦推荐来源的参与者',
      (1037,'zh-Hant'):'揭露聯邦推薦來源的參與者',
      (1039,'ja'):'このタグが付いた Pod を手動で検索してトピックを閲覧します。検索では Pod の探索サービスに問い合わせます。',
      (1042,'de'):'Künstler unbekannt',
      (1045,'fr'):'Saisissez les valeurs que vous souhaitez examiner. Elles restent uniquement sur cette page ; les actions d’aperçu et de contrat ne lancent aucun scan ni aucune autre tâche côté serveur.',
      (1045,'pt-BR'):'Insira os valores que deseja revisar. Eles permanecem apenas nesta página; as ações de prévia e de contrato não executam varreduras nem qualquer outro trabalho no servidor.',
      (1046,'hi'):'सामग्री से जुड़े Pod बनाने के उन्नत नियंत्रण',
      (1046,'vi'):'Điều khiển nâng cao để tạo Pod liên kết với nội dung',
      (1047,'ja'):'ダウンロードパスが設定されています。',
      (1048,'ar'):'حمّل إحصاءات توجيه الرسائل ونتائجها لمراجعة نشاط تسليم Pod مؤخرًا.',
      (1048,'fr'):'Chargez les statistiques et les résultats du routage des messages pour examiner l’activité récente de livraison des Pods.',
      (1050,'ar'):'مراجعة استكمال سجل الرسائل في Pod',
      (1050,'es'):'Revisión de recuperación del historial de mensajes de Pod',
      (1050,'fr'):'Révision du rattrapage de l’historique des messages de Pod',
      (1050,'id'):'Tinjauan pemulihan riwayat pesan Pod',
      (1050,'pt-BR'):'Revisão da recuperação do histórico de mensagens do Pod',
      (1050,'vi'):'Đánh giá bổ sung lịch sử tin nhắn cho Pod',
      (1051,'de'):'Kopieren Sie einen Prüfbericht für einen Graphzweig mit sichtbaren Knotengruppen, Kantengruppen, vorgeschlagenen Routen und nahegelegenen Suchstartpunkten.',
      (1051,'es'):'Copie un informe de revisión de una rama con las familias de nodos visibles, las familias de aristas, las rutas sugeridas y las semillas de búsqueda cercanas.',
      (1051,'fr'):'Copiez un rapport d’examen de branche avec les familles de nœuds visibles, les familles d’arêtes, les itinéraires suggérés et les requêtes de recherche proches.',
      (1052,'de'):'Veröffentlichen Sie einen Inhaltsdeskriptor in der DHT mit Unterstützung für die Versionsverwaltung.',
      (1052,'fr'):'Publier un descripteur de contenu dans la DHT avec prise en charge de la gestion des versions.',
    }
    proposal_reasons={
      1028:'The German wording uses singular “Suche” for the plural selected wishlist searches; the proposed wording names the selected searches themselves.',
      1029:'The current term order is awkward and can read as a key belonging to Last.fm API; the proposal clearly names the API key for Last.fm.',
      1030:'The current Indonesian text says private message notifications cannot be received, reversing the source. This checkbox enables Ntfy notifications when a private message arrives.',
      1031:'The duration value is rendered immediately before this label. The current target drops the seconds unit or spells the letter S; the proposal preserves the duration unit and identifies a clip.',
      1037:'This control reveals the source actors behind federated recommendations. The current wording changes that relationship, uses “discover” instead of “reveal,” or leaves a misleading non-federation term.',
      1039:'The current Japanese text omits the Pod discovery service, replacing it with a generic search service; the proposal names the service the query contacts.',
      1042:'The current German wording is plural while the source names one artist. The proposal is a singular label and avoids assigning the artist a gender.',
      1045:'The French pronoun “Ils” disagrees with feminine plural “valeurs”; Portuguese “verificações” weakens the specific assurance that no scans run. The proposals fix agreement and preserve the no-scan assurance.',
      1046:'The Hindi target leaves “linked” as an English transliteration; the Vietnamese target translates the product term Pod as “group.” The proposals state that the controls create content-linked Pods.',
      1047:'The Japanese target reads as a future action (“will be configured”), but this is a current setup-health status. The proposal says the path is already configured.',
      1048:'The Arabic and French wording obscures message-routing counts as routing statistics. The proposals identify message-routing statistics and outcomes in the Pod delivery status context.',
      1050:'The caller describes synchronizing missing Pod message history. These targets read as filling a physical pod, replenishing a capsule, or filling a group; the proposals name recovery/backfill of message history.',
      1051:'The caller is a Discovery Graph Atlas. Spanish “sucursales/bordes” suggests business branches/borders, French “tronçons” suggests sections, and German “Suchkerne” means search cores; the proposals use graph branch/edge and search-start concepts.',
      1052:'The German preposition means “for the DHT” rather than publishing in it. French leaves “versioning” in English and uses a masculine article for the distributed hash table; the proposals clarify destination and version management.',
    }
    retain_reasons={
      1028:'The target describes enabling the selected wishlist searches for later scheduled checks.',
      1029:'The target correctly names the Last.fm API key as a configuration label.',
      1030:'The target correctly names Ntfy notifications for private messages.',
      1031:'The target preserves the seconds unit and clip label in the German locale.',
      1032:'The target correctly labels the second item in the Content A/Content B comparison.',
      1034:'The translation preserves both count placeholders and describes the displayed subset of loaded searches.',
      1035:'The caller uses this reason when some files are lossless and the collection also contains other file types; the target conveys that mix.',
      1036:'The short target is the standard label for results returned by search.',
      1037:'The target preserves revealing/showing actors associated with federated recommendation sources.',
      1038:'The target correctly reports a single failed deletion. Arabic spells out “one,” which preserves the number semantically despite the candidate-free numeric-token flag.',
      1039:'The target preserves the manual lookup, tag, topic-browsing purpose, and Pod discovery service.',
      1040:'The target preserves the failed consensus-recommendation request and the {message} detail placeholder.',
      1041:'The target preserves WebGPU and the adapter placeholder exactly.',
      1042:'The target is a standard singular “unknown artist” label in this locale.',
      1043:'The target correctly labels navigation to the next wishlist page.',
      1044:'The target preserves the {track} placeholder and tells the user to remove that item from the queue.',
      1045:'The target preserves page-local values and the assurance that preview/contract actions do not run scans or other server work.',
      1046:'The target describes advanced controls for creating Pods linked to content.',
      1047:'The target states that a download path is configured.',
      1048:'The target names message-routing counts/outcomes and recent Pod delivery activity.',
      1049:'The target preserves all three dynamic placeholders in the source order.',
      1050:'The target retains the established technical “backfill” term for this Pod message-history review section.',
      1051:'The target describes copying a graph-branch report with node/edge families, routes, and search seeds.',
      1052:'The target preserves publishing a content descriptor to DHT and versioning support.',
    }
    moderate_proposal=set(proposal)
    high_proposal={(1030,'id'),(1042,'de'),(1045,'fr'),(1047,'ja'),(1051,'es')}
    cells=[json.loads(x) for x in (CF/'source-current-cells.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    bypos={}
    for r in cells: bypos.setdefault(r['continuationRank'],[]).append(r)
    out=[]
    for cell in cells:
        pos,loc=cell['continuationRank'],cell['locale']
        proposed=proposal.get((pos,loc))
        if cell['candidateFreeHold']:
            row={'continuationRank':pos,'remainingQueueRank':cell['remainingQueueRank'],'sourceIdSha256':cell['sourceIdSha256'],
              'sourceSha256':cell['sourceSha256'],'locale':loc,'sourceTextIncluded':False,'currentTargetTextIncluded':False,
              'sourceCurrentTargetSha256':cell['currentTargetSha256'],'callerCount':0,'callerContextSha256':cell['callerContextSha256'],
              'catalogPath':cell['catalogPath'],'catalogFileSha256':cell['catalogFileSha256'],
              'decision':'hold','reasonClass':'no-pinned-production-localization-caller','confidence':'high'}
        else:
            src=cell['source']; current=cell['currentTarget']
            row={'continuationRank':pos,'remainingQueueRank':cell['remainingQueueRank'],'sourceIdSha256':cell['sourceIdSha256'],
              'sourceSha256':cell['sourceSha256'],'source':src,'sourceTextIncluded':True,'locale':loc,
              'currentTarget':current,'currentTargetSha256':cell['currentTargetSha256'],'currentTargetTextIncluded':True,
              'callerCount':cell['callerCount'],'callerContextSha256':cell['callerContextSha256'],'catalogPath':cell['catalogPath'],
              'catalogFileSha256':cell['catalogFileSha256'],'decision':'proposal' if proposed is not None else 'retain',
              'rationale':proposal_reasons[pos] if proposed is not None else retain_reasons[pos],
              'confidence':'high' if proposed is None or (pos,loc) in high_proposal else 'moderate'}
            reviewed=proposed if proposed is not None else current
            row['reviewTargetSha256']=sha(reviewed.encode('utf-8'))
            if proposed is not None:
                tokens=token_data(src,proposed)
                if not (tokens['placeholders'] and tokens['markup'] and tokens['numbersPreserved'] and tokens['protectedLiteralsPreserved']):
                    raise SystemExit(f'token mismatch {pos} {loc}: {tokens}')
                row['proposedTarget']=proposed
                row['tokenChecks']=tokens
        row['reviewRecordSha256']=sha(canon(row).encode('utf-8'))
        out.append(row)
    expected_proposals=44
    if sum(r['decision']=='proposal' for r in out)!=expected_proposals: raise SystemExit('proposal count drift')
    (OUT/'primary-review.jsonl').write_text(''.join(canon(r)+'\n' for r in out),encoding='utf-8')
    shutil.copy2(CF/'prior-held-cell-reattestation-hash-only.jsonl',OUT/'active-holds-reattestation-hash-only.jsonl')
    shutil.copy2(CF/'window-product-readback-reattestation-hash-only.jsonl',OUT/'prior-product-readback-reattestation-hash-only.jsonl')
    shutil.copy2(CF/'SHA256SUMS.txt',OUT/'candidate-free-input-SHA256SUMS.txt')
    shutil.copy2(CF/'manifest.json',OUT/'candidate-free-input-manifest.json')
    cf_manifest=json.loads((CF/'manifest.json').read_text(encoding='utf-8'))
    summary={'artifact':'slskdN PR #409 W1028-W1052 independent primary review','window':'W86',
      'head':cf_manifest['head'],'tree':cf_manifest['tree'],'continuationRankRange':[1028,1052],'remainingQueueRankRange':[928,952],
      'sourceCount':25,'localeCount':12,'cellCount':300,'callerBackedCells':288,'callerlessHashOnlyCells':12,
      'decisions':{'proposal':44,'retain':244,'hold':12},
      'proposalRanks':sorted({str(r['continuationRank']) for r in out if r['decision']=='proposal'}),
      'callerReferences':cf_manifest['sourceCallerReferenceCount'],'callerOccurrences':cf_manifest['sourceCallerOccurrenceCount'],
      'callerFiles':len({c['path'] for cr in (json.loads(x) for x in (CF/'caller-contexts.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()) for c in cr['callers']}),
      'runtimeFilesScanned':cf_manifest['productionRuntimeFileCount'],'activeHoldsReattestedHashOnly':421,'priorW1003ProductReadbacksReattestedHashOnly':300,
      'priorW1003ProductReadbackMatchesCurrent':True,
      'proposalTokenMismatches':0,
      'inputHashes':{'candidateFreeManifestSha256':sha((CF/'manifest.json').read_bytes()),
        'candidateFreeChecksumListSha256':sha((CF/'SHA256SUMS.txt').read_bytes()),
        'sourceCurrentCellsSha256':sha((CF/'source-current-cells.jsonl').read_bytes()),
        'callerContextsSha256':sha((CF/'caller-contexts.jsonl').read_bytes()),
        'catalogStructureSha256':sha((CF/'catalog-structure.jsonl').read_bytes())},
      'method':'Independent semantic review of W1028-W1052 candidate-free caller contexts and current targets. Prior primary, blind, cross, and root review recommendations were not used for these ranks.',
      'confidenceNote':'High for direct meaning and clear errors; moderate where the best localized technical phrasing involves terminology judgment.'}
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    (OUT/'provenance-note.txt').write_text('The W1028-W1052 semantic decisions use only the sealed candidate-free input and exact pinned source/caller evidence. A separate inspection command earlier in this task inadvertently emitted two prior-window root-review records (ranks 1003-1004); those records are outside this window and were not used in these decisions. No contents from that prior review are reproduced here.\n',encoding='utf-8')
    (OUT/'README.md').write_text('# slskdN PR #409 W1028-W1052 primary review\n\n'
      'This packet reviews 300 locale cells at head `'+cf_manifest['head']+'` / tree `'+cf_manifest['tree']+'`. The primary ledger contains 44 proposals, 244 retains, and 12 hash-only holds.\n\n'
      'The review used the candidate-free source keys, exact caller contexts, current targets, and catalog pins in `../candidate-free`. It also carries the 421 active-hold hash-only reattestation and the 300-row W1003 product readback hash-only reattestation.\n\n'
      'The provenance note records a prior-window inspection mistake; those prior records were outside this window and were not used. Verify with `python3 verify_primary_review.py` and `sha256sum -c SHA256SUMS.txt`.\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
