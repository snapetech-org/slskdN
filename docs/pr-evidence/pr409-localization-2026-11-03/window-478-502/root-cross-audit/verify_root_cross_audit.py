#!/usr/bin/env python3
"""Verify the W64 independent root cross-audit from a repository checkout.

This verifier uses only sibling evidence packets and immutable Git commit objects.
It does not query GitHub, mutable refs, PR text, or task scratch paths.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import subprocess

X=Path(__file__).resolve().parent
W=X.parent
REPO=Path(subprocess.check_output(["git","-C",str(W),"rev-parse","--show-toplevel"],text=True).strip())
I=W/"candidate-free-input"
P=W/"primary-review"
B=W/"independent-blind-review"
PRE="3cc9db334cfb1693dd6bd93bb83cfeba65930adb"
PRE_TREE="9d40e239e7e717a81bd176d143d1ce067fe026a1"
APPLIED="1d45cb002e206b0f611e27d3a17f4663aefc6eb7"
APPLIED_TREE="dec2f192c0dce1c8eb1c6caab35cb29fb1c5005d"
IMAN="4f428c69b3abec8db8ad9d7796f5c9a6e9e6da9234361cc644721b932de05456"
ISUM="2064eb36dcd2bc27344f73c57b62e8e3078d087da115fe04d52348a30855e5c8"
PSUM="0cce03a378a71f9250586c8d99005ab3bc7a78c9d112739698f6f0123bfa2139"
BSUM="9525a2322f1ab0c820d0abbade8ad302a9d5f2dc87725b9ffad194095f68ec30"
PH=re.compile(r"\{[^{}\r\n]+\}")
MK=re.compile(r"</?[A-Za-z][^<>]*?/?>")
NUM=re.compile(r"(?<!\w)[+-]?\d+(?:[.,]\d+)?%?(?!\w)")

def sha(data):
    return hashlib.sha256(data).hexdigest()

def text_sha(text):
    return sha(text.encode("utf-8"))

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def git(*args):
    return subprocess.check_output(["git","-C",str(REPO),*args])

def git_text(*args):
    return git(*args).decode("utf-8")

def git_blob(rev,path):
    return git_text("rev-parse",f"{rev}:{path}").strip()

def git_file(rev,path):
    return git("show",f"{rev}:{path}")

def verify_sums(folder,name):
    result=subprocess.run(["sha256sum","-c",name],cwd=folder,text=True,capture_output=True)
    assert result.returncode==0,(str(folder),result.stdout,result.stderr)
    return result.stdout.strip().splitlines()

# All sibling packet sums are immutable inputs; the window list covers this packet too.
verify_sums(I,"PACKET-SHA256SUMS.txt")
verify_sums(P,"SHA256SUMS.txt")
verify_sums(B,"SHA256SUMS.txt")
verify_sums(X,"SHA256SUMS.txt")
verify_sums(W,"SHA256SUMS.txt")
assert sha((I/"manifest.json").read_bytes())==IMAN
assert sha((I/"PACKET-SHA256SUMS.txt").read_bytes())==ISUM
assert sha((P/"SHA256SUMS.txt").read_bytes())==PSUM
assert sha((B/"SHA256SUMS.txt").read_bytes())==BSUM

# Pin both commits from local Git objects rather than mutable branch or PR state.
assert git_text("rev-parse",f"{PRE}^{{tree}}").strip()==PRE_TREE
assert git_text("rev-parse",f"{APPLIED}^{{tree}}").strip()==APPLIED_TREE
commit_lines=git_text("cat-file","-p",APPLIED).splitlines()
assert f"tree {APPLIED_TREE}" in commit_lines
assert f"parent {PRE}" in commit_lines
pins=load_json(X/"pinned-git-objects.json")
assert pins["preApplication"]=={"commit":PRE,"tree":PRE_TREE}
assert pins["applied"]=={"commit":APPLIED,"tree":APPLIED_TREE,"parents":[PRE]}

manifest=load_json(I/"manifest.json")
input_summary=load_json(I/"selection-and-boundary.json")
primary_summary=load_json(P/"summary.json")
blind_summary=load_json(B/"summary.json")
summary=load_json(X/"summary.json")
provenance=load_json(X/"provenance.json")
assert (manifest["head"],manifest["tree"],manifest["cellCount"],manifest["sourceCount"],manifest["localeCount"])==(PRE,PRE_TREE,300,25,12)
assert primary_summary["head"]==blind_summary["head"]==PRE
assert primary_summary["tree"]==blind_summary["tree"]==PRE_TREE
assert summary["preApplicationHead"]==PRE and summary["preApplicationTree"]==PRE_TREE
assert summary["currentAppliedHead"]==APPLIED and summary["currentAppliedTree"]==APPLIED_TREE
assert summary["candidateFreeManifestJsonSha256"]==IMAN
assert summary["candidateFreeChecksumListSha256"]==ISUM
assert summary["primaryChecksumListSha256"]==PSUM
assert summary["blindChecksumListSha256"]==BSUM
assert summary["previousW64BodyClassificationClaim"]=={"correction":79,"refinement":7}
assert summary["independentAuditClassification"]=={"correction":76,"refinement":10}
assert provenance["classificationOnlyDifferenceFromPriorBodyClaim"]["selectedTargetSetMatchesAppliedReadback"] is True

inputs=load_jsonl(I/"source-current-cells.jsonl")
primary=load_jsonl(P/"review-decisions.jsonl")
blind=load_jsonl(B/"blind-ledger.jsonl")
root=load_jsonl(X/"cross-audit-decisions.jsonl")
disagreements=load_jsonl(X/"disagreements.jsonl")
updates=load_jsonl(X/"root-selected-updates.jsonl")
readback=load_jsonl(X/"applied-current-readback.jsonl")
contexts=load_jsonl(I/"caller-contexts.jsonl")
prior_holds=load_jsonl(I/"prior-held-cell-reattestation.jsonl")
structure=load_jsonl(I/"catalog-structure.jsonl")
assert len(inputs)==len(primary)==len(blind)==len(root)==len(readback)==300
assert len(contexts)==25 and len(prior_holds)==86 and len(structure)==12

def key(row):
    return (row["continuationRank"],row["locale"])

maps=[{key(row):row for row in rows} for rows in (inputs,primary,blind,root,readback)]
im,pm,bm,rm,am=maps
assert all(len(mapping)==300 for mapping in maps)
context_by_rank={row["continuationRank"]:row for row in contexts}
assert len(context_by_rank)==25

# Check source/caller pins against the pre-application source tree object.
source_files={}
for context in contexts:
    rank=context["continuationRank"]
    pass
    assert context["sourceSha256"]==text_sha(context["source"])
    assert len(context["callers"])==context["productionCallerCount"]
    for caller in context["callers"]:
        path=caller["path"]
        if path not in source_files:
            raw=git_file(PRE,path)
            assert git_blob(PRE,path)==caller["gitBlob"],(path,"pinned caller blob")
            assert sha(raw)==caller["fileSha256"],(path,"pinned caller file")
            source_files[path]=raw.decode("utf-8").splitlines()
        lines=source_files[path]
        line_no=caller["line"]
        assert 1<=line_no<=len(lines)
        assert lines[line_no-1]==caller["lineText"]
        assert text_sha(lines[line_no-1])==caller["lineSha256"]
        start=max(1,line_no-3)
        end=min(len(lines),line_no+3)
        expected=[{"line":n,"text":lines[n-1]} for n in range(start,end+1)]
        assert caller["context"]==expected,(rank,path,line_no,"caller context differs from pinned source")
        assert text_sha(caller["lineText"])==caller["lineSha256"]

# The additional exact snippets support the audio fingerprint and DHT lookup readings.
extra=load_json(X/"additional-pinned-source-context.json")
assert extra["contextBlocks"]
for block in extra["contextBlocks"]:
    assert block["head"]==PRE and block["tree"]==PRE_TREE
    raw=git_file(PRE,block["path"])
    assert git_blob(PRE,block["path"])==block["gitBlob"]
    assert sha(raw)==block["fileSha256"]
    lines=raw.decode("utf-8").splitlines()
    for item in block["lines"]:
        assert lines[item["line"]-1]==item["text"]
        assert text_sha(item["text"])==item["lineSha256"]

# Load pinned pre-application and applied catalogs from Git, then compare every value.
pre_catalogs={}
applied_catalogs={}
structure_by_locale={row["locale"]:row for row in structure}
catalog_paths={row["locale"]:row["catalogPath"] for row in inputs}
assert len(catalog_paths)==12
for locale,path in catalog_paths.items():
    pre_raw=git_file(PRE,path)
    applied_raw=git_file(APPLIED,path)
    pre_obj=json.loads(pre_raw.decode("utf-8"))
    applied_obj=json.loads(applied_raw.decode("utf-8"))
    struct=structure_by_locale[locale]
    assert struct["catalogPath"]==path
    assert sha(pre_raw)==struct["sha256"]
    assert git_blob(PRE,path)==struct["gitBlob"]
    assert len(pre_obj)==len(applied_obj)==struct["entryCount"]==6176
    assert list(pre_obj.keys())==list(applied_obj.keys())
    pre_catalogs[locale]=pre_obj
    applied_catalogs[locale]=applied_obj

locale_readback={}
for row in readback:
    locale=row["locale"]
    catalog=applied_catalogs[locale]
    path=catalog_paths[locale]
    raw=git_file(APPLIED,path)
    assert row["appliedHead"]==APPLIED and row["appliedTree"]==APPLIED_TREE
    assert row["catalogPath"]==path
    assert row["appliedCatalogGitBlob"]==git_blob(APPLIED,path)
    assert row["appliedCatalogFileSha256"]==sha(raw)
    if locale in locale_readback:
        prior=locale_readback[locale]
        assert prior["appliedCatalogGitBlob"]==row["appliedCatalogGitBlob"]
        assert prior["appliedCatalogFileSha256"]==row["appliedCatalogFileSha256"]
    else:
        locale_readback[locale]=row
assert len(locale_readback)==12
assert set(pins["catalogs"])==set(locale_readback)
for locale,pin in pins["catalogs"].items():
    row=locale_readback[locale]
    assert pin=={"path":row["catalogPath"],"gitBlob":row["appliedCatalogGitBlob"],"fileSha256":row["appliedCatalogFileSha256"]}

counts=Counter()
target_disagreements=0
disposition_disagreements=0
union_keys=set()
target_map={}
status_exception_count=0
raw_protected_mismatch_count=0
for k,cell in im.items():
    p=pm[k]; b=bm[k]; r=rm[k]; a=am[k]
    rank,locale=k
    caller=context_by_rank[rank]
    assert r["continuationRank"]==p["continuationRank"]==b["continuationRank"]==a["continuationRank"]==rank
    assert r["preApplicationHead"]==b["head"]==PRE
    assert r["preApplicationTree"]==b["tree"]==PRE_TREE
    for field in ("sourceId","source","sourceSha256","locale","catalogPath","catalogFileSha256","catalogGitBlob","currentTarget","currentTargetSha256","callerContextSha256"):
        assert p[field]==b[field]==cell[field],(k,field)
    assert p["catalogKey"]==cell["catalogKey"]
    assert r["sourceId"]==p["sourceId"]==b["sourceId"]==cell["sourceId"]
    assert r["source"]==cell["source"] and r["sourceSha256"]==cell["sourceSha256"]==text_sha(cell["source"])
    assert r["locale"]==locale and r["catalogKey"]==cell["catalogKey"]
    assert r["catalogPath"]==cell["catalogPath"]==catalog_paths[locale]
    assert r["preApplicationCatalogGitBlob"]==cell["catalogGitBlob"]==git_blob(PRE,cell["catalogPath"])
    assert r["preApplicationCatalogFileSha256"]==cell["catalogFileSha256"]==sha(git_file(PRE,cell["catalogPath"]))
    assert r["preApplicationTarget"]==cell["currentTarget"]==p["currentTarget"]==b["currentTarget"]
    assert r["preApplicationTargetSha256"]==text_sha(r["preApplicationTarget"])==cell["currentTargetSha256"]
    assert pre_catalogs[locale][cell["catalogKey"]]==cell["currentTarget"]
    assert text_sha(p["selectedTarget"])==p["selectedTargetSha256"]
    assert text_sha(b["blindTarget"])==b["blindTargetSha256"]
    assert r["primaryTarget"]==p["selectedTarget"] and r["primaryTargetSha256"]==p["selectedTargetSha256"]
    assert r["blindTarget"]==b["blindTarget"] and r["blindTargetSha256"]==b["blindTargetSha256"]
    assert r["primaryDisposition"]==p["disposition"] and r["blindDisposition"]==b["disposition"]
    assert r["callerContextSha256"]==cell["callerContextSha256"]==p["callerContextSha256"]==b["callerContextSha256"]
    assert r["productionCallerCount"]==caller["productionCallerCount"]==len(caller["callers"])
    assert r["callerReferences"]==[{"path":c["path"],"line":c["line"],"lineText":c["lineText"],"lineSha256":c["lineSha256"],"contextSha256":c["contextSha256"],"fileSha256":c["fileSha256"],"gitBlob":c["gitBlob"],"context":c["context"]} for c in caller["callers"]]
    for review in (p,b):
        refs=review.get("callerRefs",review.get("callerReferences",[]))
        assert len(refs)==len(caller["callers"])
        for ref in refs:
            match=next(c for c in caller["callers"] if c["path"]==ref["path"] and c["line"]==ref["line"])
            assert ref["lineSha256"]==match["lineSha256"]
            assert ref["fileSha256"]==match["fileSha256"]
            assert ref["gitBlob"]==match["gitBlob"]
    assert r["rootTargetSha256"]==text_sha(r["rootTarget"])
    assert r["rootTarget"]==a["appliedTarget"]==applied_catalogs[locale][cell["catalogKey"]]
    assert r["appliedTargetSha256"]==a["appliedTargetSha256"]==text_sha(r["rootTarget"])
    assert r["appliedCatalogGitBlob"]==a["appliedCatalogGitBlob"]==git_blob(APPLIED,cell["catalogPath"])
    assert r["appliedCatalogFileSha256"]==a["appliedCatalogFileSha256"]==sha(git_file(APPLIED,cell["catalogPath"]))
    assert r["appliedMatchesRoot"] is True
    assert PH.findall(r["rootTarget"])==PH.findall(cell["source"])
    assert MK.findall(r["rootTarget"])==MK.findall(cell["source"])
    assert NUM.findall(r["rootTarget"])==NUM.findall(cell["source"])
    assert r["placeholderChecks"]["rootMatchesSource"] is True
    assert r["markupChecks"]["rootMatchesSource"] is True
    assert r["numericChecks"]["rootMatchesSource"] is True
    literals=cell["sourceProtectedLiterals"]
    assert r["protectedLiteralChecks"]["sourceLiterals"]==literals
    raw_match=all(literal in r["rootTarget"] for literal in literals)
    if not raw_match:
        raw_protected_mismatch_count+=1
    localized=r["protectedLiteralChecks"]["localizedStatusException"]
    if localized:
        status_exception_count+=1
        assert rank==501 and r["rootDisposition"]=="accept-current"
        assert "interfaceText" in r["protectedLiteralChecks"]["exceptionRationale"]
    else:
        assert raw_match
    assert r["protectedLiteralChecks"]["rootProtectedCheckResolved"] is True
    assert r["rootDisposition"] in {"accept-current","correction","refinement","hold"}
    counts[r["rootDisposition"]]+=1
    assert r["changedFromPreApplication"]==(r["rootTarget"]!=r["preApplicationTarget"])
    if r["rootDisposition"] in {"accept-current","hold"}:
        assert r["rootTarget"]==r["preApplicationTarget"]
    else:
        assert r["rootTarget"]!=r["preApplicationTarget"]
    if caller["productionCallerCount"]==0:
        assert rank==486 and r["rootDisposition"]=="hold"
    else:
        assert r["rootDisposition"]!="hold"
    target_map[(cell["catalogPath"],cell["catalogKey"])]=r["rootTarget"]
    if p["selectedTarget"]!=b["blindTarget"] or p["disposition"]!=b["disposition"]:
        union_keys.add(k)
    target_disagreements+=int(p["selectedTarget"]!=b["blindTarget"])
    disposition_disagreements+=int(p["disposition"]!=b["disposition"])

assert target_disagreements==79
assert disposition_disagreements==53
assert len(union_keys)==83
assert counts==Counter({"accept-current":202,"correction":76,"refinement":10,"hold":12})
assert raw_protected_mismatch_count==11 and status_exception_count==12

disagreement_map={key(row):row for row in disagreements}
assert len(disagreement_map)==83 and set(disagreement_map)==union_keys
for k,row in disagreement_map.items():
    rootrow=rm[k]
    for field in ("sourceId","preApplicationTarget","primaryTarget","primaryDisposition","blindTarget","blindDisposition","rootTarget","rootDisposition","resolutionSource","rootRationale","productionCallerCount"):
        assert row[field]==rootrow[field],(k,field)

updates_map={key(row):row for row in updates}
changed_keys={k for k,row in rm.items() if row["changedFromPreApplication"]}
assert len(updates_map)==86 and changed_keys==set(updates_map)
for k,u in updates_map.items():
    r=rm[k]
    assert u["sourceId"]==r["sourceId"] and u["locale"]==r["locale"]
    assert u["catalogPath"]==r["catalogPath"]
    assert u["preApplicationTarget"]==r["preApplicationTarget"]
    assert u["selectedTarget"]==r["rootTarget"]==r["appliedTarget"]
    assert u["selectedTargetSha256"]==r["rootTargetSha256"]
    assert u["selectedTargetSha256"]==text_sha(u["selectedTarget"])

# Recheck each catalog's entire ordered key/value map, not only the 300 target cells.
non_target_changes=0
for locale,path in catalog_paths.items():
    before=pre_catalogs[locale]
    after=applied_catalogs[locale]
    assert list(before.keys())==list(after.keys())
    for catalog_key,value in before.items():
        selected=target_map.get((path,catalog_key))
        expected=selected if selected is not None else value
        assert after[catalog_key]==expected,(locale,catalog_key,"applied catalog differs from selected targets")
        non_target_changes+=int(selected is None and after[catalog_key]!=value)
assert non_target_changes==0

# Reattest the 86 pre-existing holds against the applied Git tree.
for held in prior_holds:
    assert held["priorDisposition"]=="hold"
    assert held["matchesPriorCurrentValue"] is True
    assert held["priorTargetSha256"]==held["currentTargetSha256"]
    path=held["currentCatalogPath"]
    locale=next(loc for loc,p in catalog_paths.items() if p==path)
    value=applied_catalogs[locale][held["source"]]
    assert value==held["currentTarget"]
    assert text_sha(value)==held["currentTargetSha256"]
assert len(prior_holds)==summary["priorHeldCellsReattestedAndPreserved"]==86
assert sum(row["continuationRank"]==486 and row["rootDisposition"]=="hold" for row in root)==12
assert summary["callerlessHeldCells"]==12 and summary["callerlessHeldRank"]==486
assert summary["rootDispositions"]==dict(counts)
assert summary["primaryBlindTargetDisagreements"]==79
assert summary["primaryBlindDispositionDisagreementRows"]==53
assert summary["reviewDisagreementRows"]==83
assert summary["selectedUpdates"]==86 and summary["appliedTargetsMatchRoot"]==300
assert summary["unresolvedProtectedLiteralMismatches"]==0
assert summary["nativeSpeakerApproval"] is False
assert summary["exactHeadBrowserReview"] is False
assert summary["previousW64BodyClassificationClaim"]=={"correction":79,"refinement":7}
assert summary["independentAuditClassification"]=={"correction":76,"refinement":10}
assert summary["classificationOnlyDifferenceFromPriorBodyClaim"] is True
assert summary["allSelectedTargetsMatchAppliedReadback"] is True

print(json.dumps({"result":"PASS","verificationMode":"immutable Git objects and sibling evidence packets only","preApplicationHead":PRE,"preApplicationTree":PRE_TREE,"appliedHead":APPLIED,"appliedTree":APPLIED_TREE,"appliedParent":PRE,"cells":300,"primaryBlindTargetDisagreements":target_disagreements,"primaryBlindDispositionDisagreements":disposition_disagreements,"unionDisagreementRows":len(union_keys),"rootDispositions":dict(counts),"selectedTargets":len(updates_map),"exactGitReadback":300,"nonTargetCatalogChanges":0,"callerlessRank486Holds":12,"priorHoldsPreserved":86,"placeholderMarkupNumericMismatches":0,"rawProtectedMismatches":raw_protected_mismatch_count,"justifiedLocalizedStatusExceptions":status_exception_count,"livePRQueries":0},ensure_ascii=False,indent=2))
