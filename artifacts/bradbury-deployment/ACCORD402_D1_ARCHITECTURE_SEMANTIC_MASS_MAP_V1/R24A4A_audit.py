from pathlib import Path
from collections import defaultdict
from datetime import datetime,timezone
from hashlib import sha256
import ast,json,sys

src=Path(sys.argv[1]); out=Path(sys.argv[2]); expected=sys.argv[3]
raw=src.read_bytes(); text=raw.decode(); assert sha256(raw).hexdigest()==expected
tree=ast.parse(text); parents={}
for n in ast.walk(tree):
    for c in ast.iter_child_nodes(n): parents[id(c)]=n

def dec(n):
    if isinstance(n,ast.Name): return n.id
    if isinstance(n,ast.Attribute):
        a=dec(n.value); return a+"."+n.attr if a else n.attr
    if isinstance(n,ast.Call): return dec(n.func)
    return ""

def pub(n):
    ds=[dec(x) for x in n.decorator_list]
    if any(x in ("gl.public.view","public.view") for x in ds): return "view"
    if any(x in ("gl.public.write","public.write") or x.startswith("gl.public.write.") or x.startswith("public.write.") for x in ds): return "write"
    return None

def seg(n): return ast.get_source_segment(text,n) or ""
def size(n): return len(seg(n).encode())
def qname(n):
    xs=[n.name] if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) else []
    c=n
    while id(c) in parents:
        c=parents[id(c)]
        if isinstance(c,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)): xs.append(c.name)
    return ".".join(reversed(xs))

protected={"_utf8","_int_u32","_int_u64","_u32_bytes","_u64_bytes","_str_bytes","_is_lower_hex64","_hex32","_bool_byte","_count_bytes","_sha256_hex","_criterion_bytes","_authority_bytes","_evidence_bytes","_service_hash","_policy_hash","_delivery_hash","_active_evidence_hash"}

owned_bytes=defaultdict(int); owned_count=defaultdict(int); strings=[]
for n in ast.walk(tree):
    if not (isinstance(n,ast.Constant) and isinstance(n.value,str)): continue
    owner="TOP_LEVEL"; c=n
    while id(c) in parents:
        c=parents[id(c)]
        if isinstance(c,(ast.FunctionDef,ast.AsyncFunctionDef)):
            owner=qname(c); break
    b=len(n.value.encode()); owned_bytes[owner]+=b; owned_count[owner]+=1
    strings.append({"line":getattr(n,"lineno",None),"owner":owner,"bytes":b,"preview":n.value[:120]})

functions=[]
for n in ast.walk(tree):
    if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)): continue
    q=qname(n); calls=[ast.unparse(x.func) for x in ast.walk(n) if isinstance(x,ast.Call)]
    functions.append({"qualname":q,"shortName":n.name,"line":n.lineno,"endLine":n.end_lineno,"sourceBytes":size(n),"publicKind":pub(n),"testBoundHelper":n.name in protected,"failCallCount":sum(1 for x in ast.walk(n) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=="_fail"),"stringLiteralBytesOwned":owned_bytes[q],"stringLiteralCountOwned":owned_count[q],"runNondetCallCount":sum("run_nondet" in x for x in calls)})
functions.sort(key=lambda x:(-x["sourceBytes"],x["qualname"]))

accord=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="Accord402")
methods=[n for n in accord.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
public=[n for n in methods if pub(n) is not None]; private=[n for n in methods if pub(n) is None]
helpers=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
classes=[n for n in tree.body if isinstance(n,ast.ClassDef)]
class_rows=[]
for n in classes:
    ds=[dec(x) for x in n.decorator_list]
    fields=[x.target.id for x in n.body if isinstance(x,ast.AnnAssign) and isinstance(x.target,ast.Name)]
    class_rows.append({"name":n.name,"line":n.lineno,"sourceBytes":size(n),"fieldCount":len(fields),"decorators":ds,"dataclassLike":any(x.endswith("dataclass") for x in ds)})
class_rows.sort(key=lambda x:(-x["sourceBytes"],x["name"]))

m={
"D1_SOURCE_BYTES":len(raw),
"PUBLIC_METHOD_COUNT":len(public),
"PUBLIC_METHOD_SOURCE_BYTES":sum(size(x) for x in public),
"PRIVATE_METHOD_COUNT":len(private),
"PRIVATE_METHOD_SOURCE_BYTES":sum(size(x) for x in private),
"TOP_LEVEL_HELPER_COUNT":len(helpers),
"TOP_LEVEL_HELPER_SOURCE_BYTES":sum(size(x) for x in helpers),
"TEST_BOUND_HELPER_COUNT":len(protected),
"TEST_BOUND_HELPER_SOURCE_BYTES":sum(size(x) for x in helpers if x.name in protected),
"TOP_LEVEL_CLASS_COUNT":len(classes),
"DATACLASS_SOURCE_BYTES":sum(r["sourceBytes"] for r in class_rows if r["dataclassLike"]),
"ALL_STRING_LITERAL_PAYLOAD_BYTES":sum(x["bytes"] for x in strings)
}
large=[x for x in functions if x["sourceBytes"]>=1000]
literal=[x for x in functions if x["stringLiteralBytesOwned"]>=300]
runtime=[x for x in functions if x["runNondetCallCount"]>0]
targets=[]
for r in functions:
    reason="TEST_BOUND_HELPER_PRESERVE_IDENTITY" if r["testBoundHelper"] else "GENLAYER_RUNTIME_CONSENSUS_SURFACE" if r["runNondetCallCount"] else "PUBLIC_METHOD_INTERNAL_ARCHITECTURE" if r["publicKind"] else "PRIVATE_OR_INTERNAL_STRUCTURAL_SURFACE"
    x=dict(r); x["reason"]=reason; targets.append(x)

for k,v in m.items(): print(f"{k}={v}")
print("LARGE_FUNCTION_COUNT_GE_1000_BYTES="+str(len(large)))
print("LITERAL_HEAVY_FUNCTION_COUNT_GE_300_LITERAL_BYTES="+str(len(literal)))
print("RUNTIME_NONDET_FUNCTION_COUNT="+str(len(runtime)))
for title,rows in [("TOP_ARCHITECTURE_MASS_TARGETS",targets[:25]),("TOP_LEVEL_CLASS_MASS",class_rows),("LARGE_FUNCTIONS_GE_1000_BYTES",large),("LITERAL_HEAVY_FUNCTIONS",sorted(literal,key=lambda x:(-x["stringLiteralBytesOwned"],x["qualname"]))),("GENLAYER_NONDET_RUNTIME_SURFACES",runtime),("TOP_STRING_LITERALS",sorted(strings,key=lambda x:(-x["bytes"],x["line"] or 0))[:20])]:
    print("\n"+title+"=")
    for r in rows: print(json.dumps(r,sort_keys=True))

classification="ARCHITECTURE_LEVEL_SEMANTIC_MASS_MAP_READY_FOR_MULTI_KILOBYTE_REFACTOR_SELECTION"
print("\nR24A4A_CLASSIFICATION="+classification)
record={"schema":"accord402.d1-architecture-semantic-mass-map.v1","createdAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),"d1CandidateSha256":expected,"metrics":m,"largeFunctions":large,"literalHeavyFunctions":literal,"runtimeNondetFunctions":runtime,"classRows":class_rows,"topStringLiterals":sorted(strings,key=lambda x:(-x["bytes"],x["line"] or 0))[:20],"architectureTargets":targets,"classification":classification,"candidateCreated":False,"testsExecuted":False,"sourceModified":False,"bradburyGasMeasured":False,"signingAuthorized":False,"broadcastAuthorized":False}
(out/"ARCHITECTURE_SEMANTIC_MASS_MAP.json").write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
summary=[f"{k}={v}" for k,v in m.items()]+["LARGE_FUNCTION_COUNT_GE_1000_BYTES="+str(len(large)),"LITERAL_HEAVY_FUNCTION_COUNT_GE_300_LITERAL_BYTES="+str(len(literal)),"RUNTIME_NONDET_FUNCTION_COUNT="+str(len(runtime)),"R24A4A_CLASSIFICATION="+classification]
(out/"ARCHITECTURE_SEMANTIC_MASS_MAP.txt").write_text("\n".join(summary)+"\n")
