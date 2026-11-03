#!/usr/bin/env python3
"""Portable exact-head verifier for the slskdN PR #409 W70 cross-audit."""
import argparse,collections,hashlib,json,re,subprocess
from pathlib import Path

HEAD="335a96a9ec125b30c20c31be219da4e27db1ab03"
TREE="7168de556608115be3b7e16b9ceb30b977df904b"
WINDOW="W70"
BRANCH="codex/slskdn-oidc-tooltip-localization-20261030"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
DEFAULT_REPO=Path("/home/keith/Documents/code/task-scratch/slskdn-pr409-w69-apply-20261103/repo")
PH=re.compile(r"\{[^{}]+\}")
TAG=re.compile(r"</?[A-Za-z][^>]*>")
NUM=re.compile(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])")
PROT_RE=re.compile(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}|[A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])")
EXTRA_PROT=("Wishlist","Soulseek","Discogs","Pod")

def req(ok,msg):
    if not ok: raise SystemExit("FAIL: "+msg)
def sha(data):
    if isinstance(data,str): data=data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()
def readj(p):return json.loads(p.read_text(encoding="utf-8"))
def readjl(p):return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
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
def git(repo,*args):return subprocess.check_output(["git","-C",str(repo),*args])
def verify_manifest_dir(path,checksum_name):
    manifest=readj(path/"manifest.json")
    listed={x["path"]:x for x in manifest["files"]}
    actual={p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file()}-{"manifest.json",checksum_name}
    req(set(listed)==actual,"packet manifest inventory "+str(path))
    for name,item in listed.items():
        p=path/name
        size=item.get("bytes",item.get("byteCount"))
        req(p.is_file() and sha(p.read_bytes())==item["sha256"] and p.stat().st_size==size,"packet manifest hash "+str(path/name))
    entries={}
    for line in (path/checksum_name).read_text(encoding="utf-8").splitlines():
        m=re.fullmatch(r"([0-9a-f]{64})  (.+)",line);req(m is not None,"malformed checksum "+str(path))
        h,name=m.groups();req(name not in entries,"duplicate checksum "+str(path/name));entries[name]=h
    expected=actual|{"manifest.json"}
    req(set(entries)==expected,"packet checksum inventory "+str(path))
    for name,h in entries.items():req(sha((path/name).read_bytes())==h,"packet checksum mismatch "+str(path/name))
    return manifest
def verify_unmanifested_sums(path,checksum_name):
    entries={}
    for line in (path/checksum_name).read_text(encoding="utf-8").splitlines():
        m=re.fullmatch(r"([0-9a-f]{64})  (.+)",line);req(m is not None,"malformed outer checksum "+str(path))
        h,n=m.groups();req(n not in entries,"duplicate outer checksum "+str(path/n));entries[n]=h
        q=path/n;req(q.is_file() and sha(q.read_bytes())==h,"outer checksum mismatch "+str(path/n))
    actual={p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file()}-{checksum_name}
    unlisted={n for n in actual-set(entries)}
    req(unlisted<={n for n in actual if Path(n).name in ("SHA256SUMS.txt","PACKET-SHA256SUMS.txt")},"outer checksum unlisted files "+str(path)+": "+repr(sorted(unlisted)))
    return len(entries)
def compare_trees(left,right):
    a={p.relative_to(left).as_posix():p for p in left.rglob("*") if p.is_file()}
    b={p.relative_to(right).as_posix():p for p in right.rglob("*") if p.is_file()}
    req(set(a)==set(b),"packet copy file inventory "+str(left))
    for n in a:req(a[n].read_bytes()==b[n].read_bytes(),"packet copy byte mismatch "+n)
    return len(a)
def verify_root_sums(root):
    entries={}
    for line in (root/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        m=re.fullmatch(r"([0-9a-f]{64})  (.+)",line);req(m is not None,"root checksum line malformed")
        h,n=m.groups();req(n not in entries,"duplicate root checksum");entries[n]=h
        p=root/n;req(p.is_file() and sha(p.read_bytes())==h,"root checksum mismatch "+n)
    actual={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}-{"SHA256SUMS.txt"}
    req(set(entries)==actual,"root checksum inventory mismatch")
    manifest=readj(root/"manifest.json")
    listed={x["path"]:x for x in manifest["files"]}
    req(set(listed)==actual-{"manifest.json"},"root manifest inventory mismatch")
    for n,item in listed.items():
        p=root/n;req(sha(p.read_bytes())==item["sha256"] and p.stat().st_size==item["byteCount"],"root manifest hash "+n)
    return manifest
def verify(root,repo,run_blind=True):
    root=root.resolve();repo=repo.resolve()
    manifest=verify_root_sums(root)
    req((manifest["repository"],manifest["pullRequest"],manifest["window"],manifest["head"],manifest["tree"],manifest["sealed"])==("snapetech-org/slskdN",409,WINDOW,HEAD,TREE,True),"root manifest pin")
    cfdir=root/"candidate-free-packet"/"input"; pdir=root/"primary-packet"/"primary-review"; bdir=root/"blind-packet"
    cm=verify_manifest_dir(cfdir,"PACKET-SHA256SUMS.txt")
    pm=verify_manifest_dir(pdir,"SHA256SUMS.txt")
    bm=verify_manifest_dir(bdir,"SHA256SUMS.txt")
    top_primary_sum_count=None
    req((cm["head"],cm["tree"],cm["cellCount"],cm["priorHeldCellsReattested"])==(HEAD,TREE,300,140),"candidate-free manifest pin")
    req((pm["head"],pm["tree"],pm["cellCount"],pm["sealed"])==(HEAD,TREE,300,True),"primary manifest pin")
    req((bm["head"],bm["tree"],bm["window"]["cellCount"],bm["priorHoldReattestationCount"])==(HEAD,TREE,300,140),"blind manifest pin")
    req(pm["inputManifestSha256"]==sha((cfdir/"manifest.json").read_bytes()),"primary input manifest pin")
    req(bm["candidateFreeInputManifestSha256"]==sha((cfdir/"manifest.json").read_bytes()),"blind input manifest pin")
    orig=Path("/home/keith/Documents/code/task-scratch")
    cf_orig=orig/"slskdn-pr409-w70-ranks628-652-candidate-free-20261103"
    p_orig=orig/"slskdn-pr409-w70-ranks628-652-primary-20261103"
    b_orig=orig/"slskdn-pr409-w70-blind-20261103"
    ncf=compare_trees(cf_orig,root/"candidate-free-packet")
    np=compare_trees(p_orig,root/"primary-packet")
    nb=compare_trees(b_orig,root/"blind-packet")
    req((git(repo,"rev-parse","HEAD").decode().strip(),git(repo,"rev-parse","HEAD^{tree}").decode().strip(),git(repo,"status","--porcelain=v1").decode())==(HEAD,TREE,""),"pinned repo head/tree/clean status")
    before=readj(root/"live-PR-attestation-before.json");after=readj(root/"live-PR-attestation-after.json")
    for live in (before,after):
        req((live["repository"],live["pullRequest"],live["state"],live["isDraft"],live["branch"],live["head"],live["tree"])==("snapetech-org/slskdN",409,"OPEN",True,BRANCH,HEAD,TREE),"live PR state/head/tree")
        req(live["branchRef"]==HEAD and live["pullRef"]==HEAD,"live branch/pull refs")
        req(live["baseRefName"]=="main","live base branch")
    req(before["baseRefDivergence"]==after["prReportedBaseDivergence"],"PR-reported base divergence")
    req(before["baseRefDivergence"]["aheadBy"]==142 and before["baseRefDivergence"]["behindBy"]==0,"PR-reported base divergence value")
    req(after["baseRefOid"]==before["baseRefOid"] and after["baseRefName"]=="main","PR-reported base pin")
    req(after["remoteBaseBranchTip"]==manifest["remoteBaseBranchTip"],"remote main tip attestation")
    req(after["currentMainTipDivergence"]==manifest["baseRefDivergence"],"current main divergence attestation")
    req(after["prReportedBaseDivergence"]==manifest["prReportedBaseDivergence"],"PR-reported divergence manifest")
    req(manifest["baseTipDriftObserved"] is True and after["currentMainTipDivergence"]=={"aheadBy":142,"behindBy":4,"mergeBase":"f25d263a2a7cdb2c8f76c40c346cb10f749a9356","status":"diverged"},"current main divergence record")
    req(before["prBodySha256"]==after["prBodySha256"] and before["prBodyBytes"]==after["prBodyBytes"],"PR body changed during cross")

    input_manifest=readj(cfdir/"manifest.json")
    sel=readj(cfdir/"selection-and-boundary.json")
    inv_raw=git(repo,"show",f"HEAD:{input_manifest['sourceInventoryPath']}")
    req(sha(inv_raw)==input_manifest["sourceInventorySha256"]==sel["sourceInventorySha256"],"pinned source inventory hash")
    req((cfdir/"source-inventory-pinned.jsonl").read_bytes()==inv_raw,"copied source inventory differs from pinned tree")
    inventory=[json.loads(x) for x in inv_raw.decode("utf-8").splitlines() if x.strip()]
    req(len(inventory)==6176,"source inventory row count")
    eligible=[x for x in inventory if not x["excluded"] and not x["inW49"] and x["localeCoverage"]==12]
    wanted=[x for x in eligible if 628<=x["continuationRank"]<=652]
    selected_inventory=readjl(cfdir/"source-inventory-selection.jsonl")
    req(len(wanted)==25 and selected_inventory==wanted,"deterministic selected source order")
    req([x["remainingQueueRank"] for x in wanted]==list(range(528,553)),"remaining queue rank order")
    req((sel["previousWindowFinalContinuationRank"],sel["previousWindowFinalSourceId"],sel["nextUnselectedContinuationRank"],sel["nextUnselectedSourceId"])==(627,"src_27df4fc0d90249cf",653,"src_2919fe8558c441c9"),"selection boundary metadata")
    prior_ids=readjl(cfdir/"prior-selected-id-exclusions.jsonl")
    req(len(prior_ids)==1732 and len({x["sourceId"] for x in prior_ids})==1732,"prior selected/excluded IDs")
    selected_ids={x["sourceId"] for x in wanted}
    req(not selected_ids & {x["sourceId"] for x in prior_ids},"current window overlaps prior selected IDs")
    req(input_manifest["priorHeldCellsReattested"]==140,"candidate-free prior hold count")

    catalog_rows=readjl(cfdir/"catalog-structure.jsonl")
    req(len(catalog_rows)==12,"catalog structure count")
    catalogs={};catinfo={}
    ordered_hash=input_manifest["orderedCatalogKeySha256"]
    for item in catalog_rows:
        path=item["catalogPath"]
        raw=(repo/path).read_bytes()
        blob=git(repo,"rev-parse",f"HEAD:{path}").decode().strip()
        data=json.loads(raw.decode("utf-8"))
        key_hash=sha(("\n".join(data.keys())+"\n").encode("utf-8"))
        req((len(raw),sha(raw),blob,len(data),sum(bool(v) for v in data.values()),key_hash)==(item["bytes"],item["sha256"],item["gitBlob"],item["entryCount"],item["nonemptyValueCount"],item["orderedKeySha256"]),"catalog source pin "+item["locale"])
        req(len(data)==6176 and key_hash==ordered_hash,"catalog ordered key hash "+item["locale"])
        catalogs[item["locale"]]=data;catinfo[item["locale"]]=item
    source_by_rank={x["continuationRank"]:x for x in wanted}
    contexts={x["continuationRank"]:x for x in readjl(cfdir/"caller-contexts.jsonl")}
    req(len(contexts)==25,"caller context row count")
    current_rows=readjl(cfdir/"source-current-cells.jsonl")
    c_map={(x["continuationRank"],x["locale"]):x for x in current_rows}
    req(len(c_map)==300,"candidate-free cell count")
    src_ids={x["sourceId"] for x in wanted}
    for key,c in c_map.items():
        rank,locale=key;src=source_by_rank[rank];ctx=contexts[rank]
        req((c["sourceId"],c["source"],c["sourceSha256"],c["catalogKey"],c["continuationRank"],c["remainingQueueRank"])==(src["sourceId"],src["source"],src["sourceSha256"],src["source"],rank,src["remainingQueueRank"]),"source/inventory row "+str(key))
        req(sha(c["source"])==c["sourceSha256"] and c["sourceId"]==src["sourceId"],"source hash/identity "+str(key))
        cat=catalogs[locale]
        target=cat.get(c["catalogKey"])
        req(isinstance(target,str) and target==c["currentTarget"] and sha(target)==c["currentTargetSha256"],"current target catalog preimage "+str(key))
        ci=catinfo[locale]
        req((c["catalogPath"],c["catalogFileSha256"],c["catalogGitBlob"])==(ci["catalogPath"],ci["sha256"],ci["gitBlob"]),"cell catalog pin "+str(key))
        st,ct=tokens(c["source"]),tokens(c["currentTarget"])
        req(c["sourceProtectedLiterals"]==st["protectedLiterals"] and c["sourceNumericTokens"]==st["numeric"] and c["currentNumericTokens"]==ct["numeric"],"cell source/current token evidence "+str(key))
        req(c["placeholderEvidence"]=={"sourceTokens":st["placeholders"],"currentTokens":ct["placeholders"],"matches":st["placeholders"]==ct["placeholders"]},"placeholder baseline evidence "+str(key))
        req(c["markupEvidence"]=={"sourceTags":st["markup"],"currentTags":ct["markup"],"matches":st["markup"]==ct["markup"]},"markup baseline evidence "+str(key))
        req(c["protectedLiteralEvidence"]["sourceTokens"]==st["protectedLiterals"] and c["protectedLiteralEvidence"]["matches"]==all(c["currentTarget"].count(t)>=c["source"].count(t) for t in st["protectedLiterals"]),"protected baseline evidence "+str(key))
        req(c["containsCandidate"] is False and c["verdict"] is None,"candidate-free cell marker "+str(key))
        req(ctx["sourceId"]==c["sourceId"] and ctx["sourceSha256"]==c["sourceSha256"] and ctx["productionCallerCount"]>0,"caller context source identity "+str(key))
        caller_refs=[{"path":x["path"],"line":x["line"],"lineSha256":x["lineSha256"],"fileSha256":x["fileSha256"],"gitBlob":x["gitBlob"]} for x in ctx["callers"]]
        req(c["callerRefs"]==caller_refs,"caller ref input "+str(key))
        req(c["callerContextSha256"]==sha(canon([x["context"] for x in ctx["callers"]])),"caller context hash "+str(key))
        for caller in ctx["callers"]:
            path=caller["path"]; raw_file=(repo/path).read_bytes()
            blob=git(repo,"rev-parse",f"HEAD:{path}").decode().strip()
            lines=raw_file.decode("utf-8").splitlines(); idx=caller["line"]-1
            req(len(raw_file)==caller["fileBytes"] and sha(raw_file)==caller["fileSha256"] and blob==caller["gitBlob"],"caller file hash/blob "+path)
            req(0<=idx<len(lines) and lines[idx]==caller["lineText"] and sha(lines[idx].encode())==caller["lineSha256"],"caller exact line "+path+":"+str(caller["line"]))
            start=max(0,idx-3);end=min(len(lines),idx+4)
            expected_context=[{"line":n+1,"text":lines[n]} for n in range(start,end)]
            req(caller["context"]==expected_context and sha(canon(expected_context))==caller["contextSha256"],"caller line context hash "+path+":"+str(caller["line"]))
    req(sum(x["productionCallerCount"] for x in contexts.values())==43,"caller reference count")
    baseline=collections.Counter()
    for key,c in c_map.items():
        st,ct=tokens(c["source"]),tokens(c["currentTarget"])
        baseline["placeholder"]+=st["placeholders"]!=ct["placeholders"]
        baseline["markup"]+=st["markup"]!=ct["markup"]
        baseline["numeric"]+=st["numeric"]!=ct["numeric"]
        baseline["protectedLiteral"]+=not all(c["currentTarget"].count(x)>=c["source"].count(x) for x in st["protectedLiterals"])
    req(dict(baseline)=={"placeholder":0,"markup":0,"numeric":1,"protectedLiteral":2},"baseline mismatch counts")

    primary_rows=readjl(pdir/"primary-ledger.jsonl");blind_rows=readjl(bdir/"blind-ledger.jsonl")
    pm={(x["continuationRank"],x["locale"]):x for x in primary_rows};bm={(x["continuationRank"],x["locale"]):x for x in blind_rows}
    ledger=readjl(root/"cross-audit-ledger.jsonl")
    req(len(ledger)==len(pm)==len(bm)==300,"cross/review cell count")
    expected_order=sorted(c_map,key=lambda k:(k[0],LOCALES.index(k[1])))
    req([(x["continuationRank"],x["locale"]) for x in ledger]==expected_order,"cross cell order")
    target_diffs=[];disp_diffs=[];disp_only=[];changed=[];shared=[];final=collections.Counter();selection=collections.Counter();final_fail=collections.Counter()
    for row in ledger:
        key=(row["continuationRank"],row["locale"]);c=c_map[key];p=pm[key];b=bm[key]
        req((row["head"],row["tree"],row["window"])==(HEAD,TREE,WINDOW),"cross cell pin "+str(key))
        req(row["source"]==c["source"]==p["source"]==b["source"] and row["sourceId"]==c["sourceId"]==p["sourceId"]==b["sourceId"],"source identity/content "+str(key))
        req(row["sourceSha256"]==c["sourceSha256"]==p["sourceSha256"]==b["sourceSha256"]==sha(row["source"]),"source hash "+str(key))
        req(row["currentTarget"]==c["currentTarget"]==p["currentTarget"]==b["currentTarget"] and row["currentTargetSha256"]==c["currentTargetSha256"]==p["currentTargetSha256"]==b["currentTargetSha256"]==sha(row["currentTarget"]),"current target preimage "+str(key))
        for f in ("catalogKey","catalogPath","catalogFileSha256","catalogGitBlob","callerContextSha256","callerRefs","continuationRank","remainingQueueRank","locale"):
            req(row[f]==c[f]==p[f]==b[f],"catalog/caller/order preimage "+str(key)+" "+f)
        req(row["primary"]["disposition"]==p["disposition"] and row["primary"]["selectedTarget"]==p["selectedTarget"] and row["primary"]["selectedTargetSha256"]==p["selectedTargetSha256"] and row["primary"]["rationale"]==p["rationale"],"primary evidence "+str(key))
        req(row["blind"]["disposition"]==b["disposition"] and row["blind"]["selectedTarget"]==b["selectedTarget"] and row["blind"]["selectedTargetSha256"]==b["selectedTargetSha256"] and row["blind"]["rationale"]==b["rationale"],"blind evidence "+str(key))
        td=p["selectedTarget"]!=b["selectedTarget"];dd=p["disposition"]!=b["disposition"]
        req(row["primaryBlindTargetDisagreement"]==td and row["primaryBlindDispositionDisagreement"]==dd,"difference flags "+str(key))
        selected=row["selectedTarget"];source=row["selectionSource"]
        req(row["selectedTargetSha256"]==sha(selected),"selected exact hash "+str(key))
        if source=="primary":req(td and selected==p["selectedTarget"] and row["crossAuditDisposition"]==p["disposition"],"primary selection "+str(key))
        elif source=="blind":req(td and selected==b["selectedTarget"] and row["crossAuditDisposition"]==b["disposition"],"blind selection "+str(key))
        else:req(source=="consensus" and p["selectedTarget"]==b["selectedTarget"]==selected,"consensus selection "+str(key))
        req((selected==c["currentTarget"])==(row["crossAuditDisposition"]=="accept-current"),"cross disposition "+str(key))
        inv=source_by_rank[key[0]]
        req(row["sourceInventoryRow"]==inv,"source inventory selected row "+str(key))
        req(row["callerContext"]==contexts[key[0]] and row["callerContextSha256"]==c["callerContextSha256"] and row["callerRefs"]==c["callerRefs"],"caller evidence "+str(key))
        expected_audit=token_audit(c["source"],c["currentTarget"],selected)
        req(row["tokenAudit"]==expected_audit and all(expected_audit["checks"].values()),"cross token/literal audit "+str(key))
        req(row["auditRationale"] and len(row["auditRationale"])>=45,"cross rationale missing "+str(key))
        if td:target_diffs.append(row)
        if dd:disp_diffs.append(row)
        if dd and not td:disp_only.append(row)
        if row["selectedTargetSha256"]!=row["currentTargetSha256"]:changed.append(row)
        if p["selectedTarget"]==b["selectedTarget"] and selected!=c["currentTarget"]:shared.append(row)
        final[row["crossAuditDisposition"]]+=1;selection[source]+=1
        for name,ok in expected_audit["checks"].items():
            category={"placeholdersPreserved":"placeholder","markupPreserved":"markup","numericTokensPreserved":"numeric","protectedLiteralsPreserved":"protectedLiteral"}[name]
            final_fail[category]+=not ok
    req((len(target_diffs),len(disp_diffs),len(disp_only),len(shared),len(changed))==(92,70,2,5,97),"reconciliation counts")
    decisions=readjl(root/"reconciliation-decisions.jsonl")
    dmap={(x["continuationRank"],x["locale"]):x for x in decisions}
    req(len(dmap)==92 and set(dmap)=={(x["continuationRank"],x["locale"]) for x in target_diffs},"decision map coverage")
    for row in target_diffs:
        d=dmap[(row["continuationRank"],row["locale"])]
        req(d["selectionSource"]==row["selectionSource"] and d["reason"] and row["selectionSource"] in ("primary","blind"),"reconciliation decision evidence")
    req(readjl(root/"target-disagreements.jsonl")==target_diffs and readjl(root/"disposition-only-disagreements.jsonl")==disp_only and readjl(root/"changed-selections.jsonl")==changed,"derived reconciliation inventories")
    req(dict(final)=={"accept-current":203,"correction":47,"refinement":50},"cross disposition totals")
    req(not any(final_fail.values()),"selected token/literal mismatch")

    holds=readjl(cfdir/"prior-held-cell-reattestation.jsonl")
    hold_summary=readj(cfdir/"prior-held-cell-reattestation-summary.json")
    blind_holds=readjl(bdir/"prior-hold-reattestation.jsonl")
    cross_holds=readjl(root/"carried-hold-reattestation.jsonl")
    psummary=readj(pdir/"summary.json")
    req(len(holds)==len(blind_holds)==len(cross_holds)==140,"carried hold counts")
    req(hold_summary["allTargetHashesMatchPrior"] and hold_summary["allCurrentCallerAndCatalogEvidenceRepinned"],"candidate-free hold summary")
    req(psummary["carriedHoldsReattested"]==140 and psummary["carriedHoldsUnchanged"] is True,"primary hold summary")
    hm={(x["continuationRank"],x["locale"],x["sourceId"]):x for x in blind_holds}
    cross_hm={(x["continuationRank"],x["locale"],x["sourceId"]):x for x in cross_holds}
    req(len(cross_hm)==140,"unique cross carried hold cells")
    for x in holds:
        key=(x["continuationRank"],x["locale"],x["sourceId"]);b=hm[key];z=cross_hm[key]
        req(x["matchesPriorCurrentValue"] and x["status"]=="reattested-unchanged","input hold retention "+str(key))
        req(x["priorTargetSha256"]==x["currentTargetSha256"] and sha(x["currentTarget"])==x["currentTargetSha256"],"input held target hash "+str(key))
        req(b["matchesPriorCurrentValue"] and b["targetTextOmitted"] is True and b["priorTargetSha256"]==x["currentTargetSha256"],"blind held target hash "+str(key))
        req(z["priorTargetSha256"]==z["currentTargetSha256"]==x["currentTargetSha256"] and z["matchesPriorCurrentValue"] and z["targetTextIncluded"] is False,"cross hash-only hold "+str(key))
        for f in ("priorWindow","sourceSha256","currentCallerContextSha256","currentCallerCount","currentCatalogPath","currentCatalogFileSha256","currentCatalogGitBlob","holdReason"):
            req(z[f]==x[f],"hold metadata "+str(key)+" "+f)
        req(len(x["currentCallerRefs"])==x["currentCallerCount"],"held caller ref count "+str(key))
        for caller in x["currentCallerRefs"]:
            path=caller["path"]; raw_file=(repo/path).read_bytes()
            blob=git(repo,"rev-parse",f"HEAD:{path}").decode().strip()
            lines=raw_file.decode("utf-8").splitlines(); idx=caller["line"]-1
            req(sha(raw_file)==caller["fileSha256"] and blob==caller["gitBlob"],"held caller file hash/blob "+path)
            req(0<=idx<len(lines) and sha(lines[idx].encode())==caller["lineSha256"],"held caller line hash "+path+":"+str(caller["line"]))
    summary=readj(root/"cross-audit-summary.json")
    req(summary["crossDispositionCounts"]==dict(final) and summary["primaryBlindTargetDisagreements"]==92 and summary["primaryBlindDispositionDisagreements"]==70 and summary["dispositionOnlyDisagreements"]==2 and summary["selectedTargetChanges"]==97 and summary["retainedCurrent"]==203 and summary["newWindowHolds"]==0,"cross summary counts")
    req(summary["carryForwardHoldsReattested"]==140 and summary["priorSelectedIdsExcluded"]==1732 and summary["sourceInventoryRows"]==6176,"lineage/source summary")
    req(summary["baselineTokenMismatches"]==dict(baseline) and not any(summary["selectedTokenMismatchCounts"].values()),"summary token status")
    nested=readj(root/"nested-verifier-results.json")
    req(nested["candidateFree"]["pass"] and nested["primary"]["pass"] and nested["blind"]["pass"],"recorded nested verifier pass")
    req(nested["candidateFree"]["result"]["cells"]==300 and nested["primary"]["result"]["proposalCount"]==48 and nested["blind"]["resultText"].startswith("PASS: 300 blind-reviewed cells;"),"recorded nested verifier summaries")
    blind_rerun=False
    if run_blind:
        cmd=["python3",str(root/"blind-packet"/"verify_blind.py"),str(cfdir)]
        r=subprocess.run(cmd,cwd=root,text=True,capture_output=True)
        req(r.returncode==0 and r.stdout.startswith("PASS: 300 blind-reviewed cells;"),"blind verifier rerun "+r.stdout+r.stderr)
        blind_rerun=True
    return {"result":"PASS","head":HEAD,"tree":TREE,"cells":len(ledger),"crossDispositionCounts":dict(final),"targetDisagreements":len(target_diffs),"dispositionDisagreements":len(disp_diffs),"dispositionOnly":len(disp_only),"selectedChanges":len(changed),"sharedChanged":len(shared),"carriedHolds":len(cross_holds),"priorIdsExcluded":len(prior_ids),"catalogsReattested":len(catalog_rows),"callerFilesAndLinesReattested":sum(x["productionCallerCount"] for x in contexts.values()),"sourceInventoryRowsReattested":len(inventory),"baselineTokenMismatches":dict(baseline),"selectedTokenFailures":dict(final_fail),"packetCopyFilesCompared":{"candidateFree":ncf,"primary":np,"blind":nb},"blindVerifierRerun":blind_rerun,"repoCleanAtExactHead":True}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,default=Path(__file__).resolve().parent)
    ap.add_argument("--repo",type=Path,default=DEFAULT_REPO)
    ap.add_argument("--skip-blind",action="store_true")
    a=ap.parse_args()
    print(json.dumps(verify(a.root,a.repo,not a.skip_blind),ensure_ascii=False,indent=2))
if __name__=="__main__":main()
