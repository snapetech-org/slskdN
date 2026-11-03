#!/usr/bin/env python3
"""Build SeerrNG-style third-party cross-audit evidence for slskdN W70."""
import collections,hashlib,json,re
from pathlib import Path

OUT=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w70-cross-audit-20261103")
CF=OUT/"candidate-free-packet"/"input"
PRIMARY_DIR=OUT/"primary-packet"/"primary-review"
BLIND_DIR=OUT/"blind-packet"
HEAD="335a96a9ec125b30c20c31be219da4e27db1ab03"
TREE="7168de556608115be3b7e16b9ceb30b977df904b"
WINDOW="W70"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
PH=re.compile(r"\{[^{}]+\}")
TAG=re.compile(r"</?[A-Za-z][^>]*>")
NUM=re.compile(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])")
PROT_RE=re.compile(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])")
EXTRA_PROT=("Wishlist","Soulseek","Discogs","Pod")

PICK={}
def picks(rank,locales,source):
    for locale in locales: PICK[(rank,locale)]=source
picks(628,["es"],"primary")
picks(628,["zh-Hans","zh-Hant"],"blind")
picks(629,LOCALES,"blind")
picks(630,["ar"],"primary")
picks(631,["ar","hi"],"primary")
picks(631,["de","es","fr","id","ko","pt-BR","vi"],"blind")
picks(633,["ar","fr"],"primary")
picks(633,["ja","ko","zh-Hans","zh-Hant"],"blind")
picks(634,["vi"],"blind")
picks(635,["id"],"primary")
picks(635,["ar","de","hi","ja","ko","zh-Hans","zh-Hant"],"blind")
picks(636,["ar","es","hi","id","pt-BR","vi","zh-Hans","zh-Hant"],"blind")
picks(637,["hi"],"primary")
picks(638,["hi","id"],"blind")
picks(639,["ar","es","fr","hi","id","ko","pt-BR","vi","zh-Hans","zh-Hant"],"blind")
picks(640,["ar","de","es","fr","hi","id","pt-BR"],"blind")
picks(640,["vi","zh-Hans","zh-Hant"],"primary")
picks(642,["id"],"blind")
picks(645,["vi"],"blind")
picks(646,["pt-BR"],"blind")
picks(649,LOCALES,"primary")
picks(650,["ar","id","ko"],"primary")
picks(650,["vi"],"blind")
picks(651,["pt-BR","vi"],"blind")

CONTEXT={
628:"This is the positive status emitted after source-feed integration settings are saved to YAML.",
629:"The caller branches on the user's hated-interest choice, adds the dynamic interest value to the preference list, and clears the entry. The wording should describe a disliked interest in that list.",
630:"The caller composes algorithm, F1 score, this connector, and the Precision score in one statistic. The leading comma separates the two metrics.",
631:"This tooltip describes the three native MilkDrop select options and their behaviors: Efficient reduces GPU load, Balanced caps at 60 FPS, and Full leaves rendering uncapped.",
633:"Ten production callers place this connector between a displayed page/range and a total. It must form a natural count relation or use compact pagination punctuation.",
634:"The library-health report inserts a formatted count of quarantineReviews.length; this is a count label for quarantine review previews.",
635:"The caller appends report.realmId directly after this fragment and then a period, so the translation must compose with that realm identifier.",
636:"This rich-text fragment follows semicolon-prefixed confidence and provenance fragments in a list description; its leading punctuation must fit that sequence and retain the {reasons} placeholder.",
637:"This is the expand button's tooltip. Its click handler calls setCollapsed(false), which opens the player drawer.",
638:"This network status header names the Soulseek Type-1 Obfuscation feature; the message below reports its status, mode, and type.",
639:"After building organization input and setting preview items, the caller emits this status for a dry run; it is a prepared simulation, not a completed tag/organization operation.",
640:"This is a toggle for shareProbeMediaAttributes. The helper says it probes shared audio for bitrate, duration, and sample metadata during share scans.",
642:"This is a numeric form field bound to httpsPort, not a harbor or generic port description.",
645:"This paragraph describes browser-local experience preferences; hiding the player stops current playback and clears the local queue.",
646:"This label appears above a dropdown populated from Contacts.",
649:"Two callers show a toast error when the trimmed artist ID is empty; MBID is the required Artist MusicBrainz identifier.",
650:"This heading appears only when run.corpusMatches has entries and labels the list rendered immediately below it.",
651:"This PlayerToolButton calls next and is labelled Next local track; it plays the next item in the local queue.",
}
WHY={
628:"I selected the target that removes the duplicated or awkward source-feed calque while preserving the positive saved-to-YAML status.",
629:"I selected the blind wording because the caller's hated flag means the user marked an interest as unwanted; it avoids describing the interest itself as hateful and preserves {interest}.",
630:"I selected the primary Arabic punctuation because the localized Arabic comma keeps the F1 and Precision values separate in this concatenated statistic.",
631:"I selected the clearer of the two reviewed explanations of the three preset effects, preserving GPU, FPS, MilkDrop and the exact 60 value. Where I chose localized descriptors, they read as setting behaviors; elsewhere the blind text avoids the current malformed behavior descriptions.",
633:"I selected the wording that composes naturally with the surrounding range and total; the slash variants omit embedded spaces because the caller already inserts spaces.",
634:"I selected the shorter Vietnamese phrasing because it removes a nested review-of-quarantine construction while preserving the formatted preview count.",
635:"I selected a phrase that composes with the directly appended realm ID. The Hindi/Chinese/Japanese/Korean label forms name the realm; Indonesian needs the preposition for.",
636:"I selected semicolon punctuation to match the neighboring semicolon-prefixed status fragments, rather than the current middle-dot separator.",
637:"I selected the explicit expansion verb because the click handler sets the drawer to expanded; it does not merely resize it.",
638:"I selected the obfuscation/data-hiding term because Type-1 names a network obfuscation mode, not ambiguity.",
639:"I selected the wording that explicitly presents a prepared simulation for the named playlist, matching the dry-run status emitted before any changes are applied.",
640:"I selected wording that says to inspect/probe attributes of shared media, matching the checkbox and its shared-audio metadata help.",
642:"I selected the technical Port label because this is the HTTPS port-number input; the current harbor translation is wrong.",
645:"I selected wording that clearly means stopping the content currently playing, not stopping detection.",
646:"I selected the natural source-from-contacts construction for the label above the contact picker.",
649:"I selected the primary word order that clearly marks the artist's MBID as the required value, matching the empty-field toast.",
650:"I selected the clearer heading for the corpus-match results list shown below the heading.",
651:"I selected the player-specific verb for playing audio and the next queue item, matching the button action.",
}
CHOICE={}
for k,source in PICK.items():
    if k==(628,"es"): CHOICE[k]="The Spanish wording uses flujo de origen instead of retaining the English word feed."
    elif k in ((628,"zh-Hans"),(628,"zh-Hant")): CHOICE[k]="The selected Chinese form reads as a saved source-information-feed integration status."
    elif k[0]==631 and source=="primary": CHOICE[k]="The selected localized description keeps the effects in grammatical setting language and preserves all protected product/technical literals."
    elif k[0]==631: CHOICE[k]="The selected description names the source options and explicitly gives each setting's load/frame-rate behavior."
    elif k==(633,"ar"): CHOICE[k]="من أصل expresses a displayed range out of its total."
    elif k==(633,"fr"): CHOICE[k]="sur is the natural range-over-total connector in these ten numeric layouts."
    elif k[0]==633: CHOICE[k]="The bare slash gives the caller's existing spaces the correct single-space layout."
    elif k==(635,"id"): CHOICE[k]="The primary target supplies untuk so the following realm ID completes the phrase."
    elif k[0]==635: CHOICE[k]="The selected target forms a labeled or modified realm phrase immediately before the appended realm ID."
    elif k[0]==640 and source=="primary": CHOICE[k]="The selected primary term better conveys probe/check behavior for the attribute-scanning toggle in this locale."
    elif k[0]==640: CHOICE[k]="The blind target clearly makes shared media the object whose attributes are inspected."
    elif k[0]==649: CHOICE[k]="The primary form uses the clearer artist-possession relation and follows the source's concise validation style."
    elif k[0]==650 and source=="primary": CHOICE[k]="The selected target names matches/results, consistent with the heading over the populated corpusMatches list."
    elif k[0]==650: CHOICE[k]="The selected blind heading is the more natural Vietnamese label for the match list."
    else: CHOICE[k]=WHY[k[0]]

def rj(p):return json.loads(p.read_text(encoding="utf-8"))
def rjl(p):return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def sha(b):return hashlib.sha256(b if isinstance(b,bytes) else b.encode("utf-8")).hexdigest()
def writej(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def writejl(p,x):p.write_text("".join(json.dumps(y,ensure_ascii=False,sort_keys=True)+"\n" for y in x),encoding="utf-8")
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
def protected(s):
    found=set(PROT_RE.findall(s))
    for x in EXTRA_PROT:
        if re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",s):found.add(x)
    return sorted(found)
def tokens(s):return {"placeholders":sorted(set(PH.findall(s))),"markup":TAG.findall(s),"numeric":NUM.findall(s),"protectedLiterals":protected(s)}
def token_audit(src,cur,target):
    s,c,t=tokens(src),tokens(cur),tokens(target)
    return {"source":s,"current":c,"selected":t,"checks":{
      "placeholdersPreserved":s["placeholders"]==t["placeholders"],
      "markupPreserved":s["markup"]==t["markup"],
      "numericTokensPreserved":s["numeric"]==t["numeric"],
      "protectedLiteralsPreserved":all(cur.count(x)<=target.count(x) for x in s["protectedLiterals"]) and all(target.count(x)>=src.count(x) for x in s["protectedLiterals"]),
    }}

def main():
    cf_rows=rjl(CF/"source-current-cells.jsonl"); pr_rows=rjl(PRIMARY_DIR/"primary-ledger.jsonl"); bl_rows=rjl(BLIND_DIR/"blind-ledger.jsonl")
    ctx={x["continuationRank"]:x for x in rjl(CF/"caller-contexts.jsonl")}
    inventory={x["continuationRank"]:x for x in rjl(CF/"source-inventory-selection.jsonl")}
    C={(x["continuationRank"],x["locale"]):x for x in cf_rows}
    P={(x["continuationRank"],x["locale"]):x for x in pr_rows}
    B={(x["continuationRank"],x["locale"]):x for x in bl_rows}
    if len(C)!=300 or len(P)!=300 or len(B)!=300 or set(C)!=set(P) or set(C)!=set(B):raise SystemExit("FAIL: 300-cell coverage")
    if len(PICK)!=92:raise SystemExit(f"FAIL: explicit disagreement map count {len(PICK)}")
    ledger=[]
    for key in sorted(C,key=lambda x:(x[0],LOCALES.index(x[1]))):
        c,p,b=C[key],P[key],B[key]
        for field in ("sourceId","source","sourceSha256","currentTarget","currentTargetSha256","catalogKey","catalogPath","catalogFileSha256","catalogGitBlob","callerContextSha256","callerRefs","continuationRank","remainingQueueRank","locale"):
            if not(c[field]==p[field]==b[field]):raise SystemExit(f"FAIL: input preimage disagreement {key} field {field}")
        if sha(c["source"])!=c["sourceSha256"] or sha(c["currentTarget"])!=c["currentTargetSha256"]:raise SystemExit(f"FAIL: source/current hash {key}")
        if c["containsCandidate"] is not False or p["containsCandidate"] is not False or b["containsCandidate"] is not False:raise SystemExit(f"FAIL: candidate contamination {key}")
        td=p["selectedTarget"]!=b["selectedTarget"]
        dd=p["disposition"]!=b["disposition"]
        if td:
            source=PICK.get(key)
            if not source:raise SystemExit(f"FAIL: missing target reconciliation {key}")
            if source=="primary":target=p["selectedTarget"];disp=p["disposition"]
            elif source=="blind":target=b["selectedTarget"];disp=b["disposition"]
            else:raise SystemExit(f"FAIL: invalid selection source {key}")
        else:
            source="consensus";target=p["selectedTarget"]
            if target==c["currentTarget"]:disp="accept-current"
            elif p["disposition"]==b["disposition"]:disp=p["disposition"]
            elif "correction" in (p["disposition"],b["disposition"]):disp="correction"
            else:disp="refinement"
        if (target==c["currentTarget"])!=(disp=="accept-current"):raise SystemExit(f"FAIL: target/disposition {key}")
        th=sha(target)
        if source=="primary" and th!=p["selectedTargetSha256"]:raise SystemExit(f"FAIL: selected primary target hash {key}")
        if source=="blind" and th!=b["selectedTargetSha256"]:raise SystemExit(f"FAIL: selected blind target hash {key}")
        audit=token_audit(c["source"],c["currentTarget"],target)
        if not all(audit["checks"].values()):raise SystemExit(f"FAIL: token/literal checks {key}: {audit['checks']}")
        context=ctx[key[0]]
        if context["sourceId"]!=c["sourceId"] or context["sourceSha256"]!=c["sourceSha256"] or context["productionCallerCount"]<1:raise SystemExit(f"FAIL: caller-context preimage {key}")
        if c["callerContextSha256"]!=sha(canon([x["context"] for x in context["callers"]])):raise SystemExit(f"FAIL: caller context hash {key}")
        if c["callerRefs"]!=[{"path":x["path"],"line":x["line"],"lineSha256":x["lineSha256"],"fileSha256":x["fileSha256"],"gitBlob":x["gitBlob"]} for x in context["callers"]]:raise SystemExit(f"FAIL: caller refs {key}")
        if td:
            rationale=f"{CONTEXT[key[0]]} {WHY[key[0]]} {CHOICE[key]} Primary proposal ({p['disposition']}): {p['selectedTarget']} — {p['rationale']} Blind proposal ({b['disposition']}): {b['selectedTarget']} — {b['rationale']} The cross-audit selects the {source} target after comparing both proposals with the current value and pinned caller evidence."
        elif dd:
            rationale=f"{CONTEXT[key[0]]} Both reviews chose the same exact target; their disposition labels differ. I classify the shared change as {disp} because the current value does not express the caller-visible operation as clearly as the shared proposal. Primary rationale: {p['rationale']} Blind rationale: {b['rationale']}"
        elif target!=c["currentTarget"]:
            rationale=f"{CONTEXT.get(key[0],'The pinned source and direct caller are included below.')} Primary and blind agree on the exact target and its rationale, so the cross-audit retains their shared selection."
        else:
            rationale="Primary and blind both retain the exact current target; no review difference is present."
        row={
          "schema":"slskdn-cross-audit-cell/v1","repository":"snapetech-org/slskdN","pullRequest":409,"window":WINDOW,"head":HEAD,"tree":TREE,
          "continuationRank":key[0],"remainingQueueRank":c["remainingQueueRank"],"sourceId":c["sourceId"],"source":c["source"],"sourceSha256":c["sourceSha256"],
          "locale":key[1],"catalogKey":c["catalogKey"],"catalogPath":c["catalogPath"],"catalogFileSha256":c["catalogFileSha256"],"catalogGitBlob":c["catalogGitBlob"],
          "currentTarget":c["currentTarget"],"currentTargetSha256":c["currentTargetSha256"],
          "primary":{"disposition":p["disposition"],"selectedTarget":p["selectedTarget"],"selectedTargetSha256":p["selectedTargetSha256"],"rationale":p["rationale"]},
          "blind":{"disposition":b["disposition"],"selectedTarget":b["selectedTarget"],"selectedTargetSha256":b["selectedTargetSha256"],"rationale":b["rationale"]},
          "primaryBlindTargetDisagreement":td,"primaryBlindDispositionDisagreement":dd,
          "crossAuditDisposition":disp,"selectedTarget":target,"selectedTargetSha256":th,"selectionSource":source,"auditRationale":rationale,
          "sourceInventoryRow":inventory[key[0]],"callerContextSha256":c["callerContextSha256"],"callerRefs":c["callerRefs"],"callerContext":context,
          "tokenAudit":audit,
        }
        ledger.append(row)
    target_diffs=[x for x in ledger if x["primaryBlindTargetDisagreement"]]
    disp_diffs=[x for x in ledger if x["primaryBlindDispositionDisagreement"]]
    disp_only=[x for x in disp_diffs if not x["primaryBlindTargetDisagreement"]]
    changed=[x for x in ledger if x["selectedTargetSha256"]!=x["currentTargetSha256"]]
    shared=[x for x in ledger if x["primary"]["selectedTarget"]==x["blind"]["selectedTarget"] and x["selectedTargetSha256"]!=x["currentTargetSha256"]]
    if {(x["continuationRank"],x["locale"]) for x in target_diffs}!=set(PICK):raise SystemExit("FAIL: reconciliation map not equal to target differences")
    if (len(target_diffs),len(disp_diffs),len(disp_only),len(shared),len(changed))!=(92,70,2,5,97):raise SystemExit(f"FAIL: counts target={len(target_diffs)} disposition={len(disp_diffs)} dispositionOnly={len(disp_only)} shared={len(shared)} changed={len(changed)}")
    prior=rjl(CF/"prior-held-cell-reattestation.jsonl")
    psummary=rj(PRIMARY_DIR/"summary.json")
    blindholds=rjl(BLIND_DIR/"prior-hold-reattestation.jsonl")
    hm={(x["continuationRank"],x["locale"],x["sourceId"]):x for x in blindholds}
    carries=[]
    for x in prior:
        key=(x["continuationRank"],x["locale"],x["sourceId"]); bh=hm[key]
        if not x["matchesPriorCurrentValue"] or x["status"]!="reattested-unchanged" or bh.get("priorTargetSha256")!=x["currentTargetSha256"] or bh.get("matchesPriorCurrentValue") is not True or bh.get("targetTextOmitted") is not True:raise SystemExit(f"FAIL: carried hold hash evidence {key}")
        carries.append({"priorWindow":x["priorWindow"],"continuationRank":x["continuationRank"],"sourceId":x["sourceId"],"sourceSha256":x["sourceSha256"],"locale":x["locale"],"priorDisposition":x["priorDisposition"],"priorTargetSha256":x["priorTargetSha256"],"currentTargetSha256":x["currentTargetSha256"],"matchesPriorCurrentValue":True,"currentCallerContextSha256":x["currentCallerContextSha256"],"currentCallerCount":x["currentCallerCount"],"currentCatalogPath":x["currentCatalogPath"],"currentCatalogFileSha256":x["currentCatalogFileSha256"],"currentCatalogGitBlob":x["currentCatalogGitBlob"],"primaryVerifierReattested":True,"blindVerifierReattested":True,"blindTargetHashMatches":True,"targetTextIncluded":False,"holdReason":x["holdReason"]})
    if len(carries)!=140:raise SystemExit("FAIL: carried hold count")
    base=collections.Counter(); final=collections.Counter()
    for row in ledger:
        c=C[(row["continuationRank"],row["locale"])]
        src,cur,tgt=row["source"],row["currentTarget"],row["selectedTarget"]
        st,ct,tt=tokens(src),tokens(cur),tokens(tgt)
        base["placeholder"]+=st["placeholders"]!=ct["placeholders"]
        base["markup"]+=st["markup"]!=ct["markup"]
        base["numeric"]+=st["numeric"]!=ct["numeric"]
        base["protectedLiteral"]+=not all(cur.count(x)>=src.count(x) for x in st["protectedLiterals"])
        checks=row["tokenAudit"]["checks"]
        final["placeholder"]+=not checks["placeholdersPreserved"]
        final["markup"]+=not checks["markupPreserved"]
        final["numeric"]+=not checks["numericTokensPreserved"]
        final["protectedLiteral"]+=not checks["protectedLiteralsPreserved"]
    if dict(base)!={"placeholder":0,"markup":0,"numeric":1,"protectedLiteral":2} or any(final.values()):raise SystemExit(f"FAIL: token baseline/final {dict(base)} {dict(final)}")
    writejl(OUT/"cross-audit-ledger.jsonl",ledger)
    writejl(OUT/"target-disagreements.jsonl",target_diffs)
    writejl(OUT/"disposition-only-disagreements.jsonl",disp_only)
    writejl(OUT/"changed-selections.jsonl",changed)
    writejl(OUT/"carried-hold-reattestation.jsonl",carries)
    decision_map=[{"continuationRank":k[0],"locale":k[1],"selectionSource":v,"reason":CHOICE[k]} for k,v in sorted(PICK.items(),key=lambda x:(x[0][0],LOCALES.index(x[0][1])))]
    writejl(OUT/"reconciliation-decisions.jsonl",decision_map)
    counts=collections.Counter(x["crossAuditDisposition"] for x in ledger)
    sources_count=collections.Counter(x["selectionSource"] for x in ledger)
    baseline_repairs=[
      {"continuationRank":631,"locale":"ar","kind":"protected-literal","missingCurrent":["GPU"],"selectedTargetPreserves":["GPU","MilkDrop","FPS"]},
      {"continuationRank":631,"locale":"hi","kind":"protected-literal","missingCurrent":["MilkDrop"],"selectedTargetPreserves":["GPU","MilkDrop","FPS"]},
      {"continuationRank":638,"locale":"ar","kind":"numeric-token","missingCurrent":["1"],"selectedTargetPreserves":["1","Soulseek"]},
    ]
    summary={
      "schema":"slskdn-cross-audit-summary/v1","repository":"snapetech-org/slskdN","pullRequest":409,"window":WINDOW,"head":HEAD,"tree":TREE,
      "sourceCount":25,"localeCount":12,"cellCount":300,
      "primaryDispositionCounts":dict(collections.Counter(x["disposition"] for x in pr_rows)),
      "blindDispositionCounts":dict(collections.Counter(x["disposition"] for x in bl_rows)),
      "crossDispositionCounts":dict(counts),"primaryBlindTargetDisagreements":len(target_diffs),
      "primaryBlindDispositionDisagreements":len(disp_diffs),"dispositionOnlyDisagreements":len(disp_only),
      "primaryBlindSharedChangedTargets":len(shared),"selectedTargetChanges":len(changed),"retainedCurrent":len(ledger)-len(changed),
      "newWindowHolds":0,"carryForwardHoldsReattested":len(carries),"carriedHoldLineage":{"W68":128,"W69":12},
      "priorSelectedIdsExcluded":1732,"sourceInventoryRows":6176,"firstContinuationRank":628,"lastContinuationRank":652,
      "firstRemainingQueueRank":528,"lastRemainingQueueRank":552,"nextUnselectedContinuationRank":653,"nextUnselectedSourceId":"src_2919fe8558c441c9",
      "productionCallerRows":25,"productionCallerReferences":43,
      "selectionSources":dict(sources_count),"targetDisagreementSelectionSources":dict(collections.Counter(x["selectionSource"] for x in target_diffs)),
      "baselineTokenMismatches":dict(base),"selectedTokenMismatchCounts":dict(final),"baselineTokenRepairs":baseline_repairs,
      "pinnedSourceCatalogCallerPreimagesReattested":True,"noRelevantSourceCatalogCallerDrift":True,
      "nativeSpeakerReviewPerformed":False,"browserReviewPerformed":False,"confidence":"moderate; source/caller review with no qualified native-speaker signoff",
    }
    writej(OUT/"cross-audit-summary.json",summary)
    report=(
      "# slskdN PR #409 W70 (ranks 628–652) third-party cross-audit\n\n"
      f"Pinned exact head {HEAD}, tree {TREE}; PR #409 remains OPEN/DRAFT on branch codex/slskdn-oidc-tooltip-localization-20261030. Base main is 142 commits ahead and 0 behind at the pinned compare point.\n\n"
      f"Primary reviewed 300 cells: {summary['primaryDispositionCounts']}. Blind reviewed 300: {summary['blindDispositionCounts']}. Cross-audit result: {dict(counts)}.\n\n"
      f"Primary and blind differ on {len(target_diffs)} selected target hashes and {len(disp_diffs)} dispositions; {len(disp_only)} are disposition-only. The cross-audit selects {len(changed)} exact-hash changes and retains {len(ledger)-len(changed)} current values. Both reviews shared {len(shared)} changed targets. No new window holds were added. All 140 carried holds remain hash-reattested unchanged (128 from W68 and 12 from W69).\n\n"
      "## Caller-based decisions\n\n"
      "- Rank 629 uses the caller's hated-interest branch as membership in the user's unwanted-interest list; the selected translations avoid describing the interest itself as hateful.\n"
      "- Rank 631 is a native MilkDrop quality tooltip. The select has Efficient, Balanced, Full, and Custom choices; the chosen text preserves the GPU/60 FPS effects and all protected literals.\n"
      "- Rank 633 is inserted between displayed ranges and totals in ten numeric interfaces. Cross choices use a natural range-total connector or a bare slash where the callsite supplies surrounding spaces.\n"
      "- Rank 635 has report.realmId concatenated directly after the fragment. Rank 636 appears among semicolon-prefixed list fragments; its selected punctuation follows those neighbors.\n"
      "- Rank 637's button sets the drawer expanded. Rank 639 is a prepared dry-run status before an operation is applied. Rank 640 is a toggle to probe shared-audio metadata.\n"
      "- Rank 642 labels an HTTPS number input. Rank 645 explicitly refers to current playback. Rank 646 labels a Contacts dropdown. Rank 649 is a toast for a blank artist ID. Rank 650 heads a populated corpus match list. Rank 651 invokes next-track playback.\n\n"
      "## Token and packet checks\n\n"
      "Candidate-free and primary packet verifiers passed at this exact head; the primary verifier re-ran the packet's exact quoted-literal production-caller check. The blind verifier passed all 300 cells. The cross ledger independently reattests direct caller file, line, context, source, catalog and target hashes from the pinned clean checkout without a broad source scan. The baseline has one numeric and two protected-literal mismatches; all three are repaired in selected targets. Selected placeholder, markup, numeric and protected-literal mismatch counts are zero.\n\n"
      "Candidate-free, primary and blind input packets are copied with their original manifests and checksums. Before/after live attestations require matching branch and pull refs at the exact head/tree; no repo/PR content is modified by this packet. No tests, builds, CI, browser review or workflow changes were performed. Qualified native-speaker review was not performed.\n"
    )
    (OUT/"reconciliation-report.md").write_text(report,encoding="utf-8")
    readme=(
      "# Portable slskdN W70 cross-audit packet\n\n"
      f"Third-party cross-audit evidence for snapetech-org/slskdN PR #409 at head {HEAD} / tree {TREE}, continuation ranks 628–652.\n\n"
      "The packet contains byte-preserved candidate-free, primary and blind packets; before/after live PR/ref attestations; a 300-cell exact-hash reconciliation ledger; all target and disposition disagreements; selected changes; 140 carried-hold attestations; and a portable verifier.\n\n"
      "Run the verifier with the pinned checkout (direct file/hash reattestation only):\n\n"
      "    python3 verify_cross_audit.py --repo /path/to/pinned/slskdN/checkout\n"
      "    sha256sum -c SHA256SUMS.txt\n\n"
      "The candidate-free and primary packet verifiers were run before cross reconciliation. No catalog values are applied by this packet. The hold ledger is hash-only; native-speaker and browser review were not performed.\n"
    )
    (OUT/"README.md").write_text(readme,encoding="utf-8")
    print(json.dumps({"result":"BUILT","cells":len(ledger),"targetDisagreements":len(target_diffs),"dispositionDisagreements":len(disp_diffs),"dispositionOnly":len(disp_only),"sharedChanged":len(shared),"selectedChanges":len(changed),"crossCounts":dict(counts),"baseline":dict(base),"final":dict(final),"carriedHolds":len(carries)},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
