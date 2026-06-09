import csv, collections
# Per (id_entidad, regimen) — and detect duplicate entidad names per id collisions
by_id = collections.defaultdict(lambda: {"names":set(),"n":0,"sum":0.0,"cas":0,"cas_sum":0.0})
sig = collections.defaultdict(list)  # (n,round(sum)) -> ids  to spot dup blocks
cas_salary=[]
with open("data/funcionarios.csv", newline="") as f:
    r=csv.DictReader(f)
    for row in r:
        i=row["id_entidad"]; b=by_id[i]
        b["names"].add(row["entidad"]); b["n"]+=1
        try: v=float(row["total_ingreso_mensual"] or 0)
        except: v=0.0
        b["sum"]+=v
        if row["regimen"]=="CAS":
            b["cas"]+=1; b["cas_sum"]+=v
            if v>0: cas_salary.append(v)

# signature collisions (likely scrape dup)
for i,b in by_id.items():
    sig[(b["n"],round(b["sum"]))].append(i)
collisions={k:v for k,v in sig.items() if len(v)>1 and k[0]>50}
print("Bloques con misma (n,masa) -> posibles duplicados de scrape:",len(collisions))
for (n,s),ids in sorted(collisions.items(),key=lambda kv:-kv[0][0])[:6]:
    print(f"  n={n} masa=S/{s:,.0f} -> {len(ids)} id_entidad distintos: {ids[:6]}{'...' if len(ids)>6 else ''}")

# CAS salary distribution (the joinable universe with SalariosPeru)
cas_salary.sort()
import statistics as st
N=len(cas_salary)
def pct(p): return cas_salary[int(p*N)] if N else 0
print(f"\nCAS con sueldo>0: {N}  media=S/{st.mean(cas_salary):,.0f}  mediana=S/{st.median(cas_salary):,.0f}")
print(f"  p10=S/{pct(.10):,.0f} p25=S/{pct(.25):,.0f} p75=S/{pct(.75):,.0f} p90=S/{pct(.90):,.0f} max=S/{cas_salary[-1]:,.0f}")

# rango salarial buckets (como tabla de SalariosPeru)
buckets=[(0,1500),(1500,2500),(2500,4000),(4000,6000),(6000,10000),(10000,1e12)]
labels=["< 1.5k","1.5k-2.5k","2.5k-4k","4k-6k","6k-10k","> 10k"]
cnt=collections.Counter()
for v in cas_salary:
    for (lo,hi),lab in zip(buckets,labels):
        if lo<=v<hi: cnt[lab]+=1; break
print("\nDistribucion CAS por rango salarial (cuadro estilo SalariosPeru):")
for lab in labels:
    print(f"  {lab:>10}: {cnt[lab]:>6} ({100*cnt[lab]/N:4.1f}%)")
