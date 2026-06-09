import csv, collections, statistics as st, unicodedata

def norm(s):
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode()
    return " ".join(s.upper().split())

# 1) determine most-recent period per id_entidad
latest=collections.defaultdict(lambda:(-1,-1))  # id -> (anio,mes)
rows=[]
with open("data/funcionarios.csv",newline="") as f:
    for row in csv.DictReader(f):
        if row["regimen"]!="CAS": continue
        try: a=int(row["anio"]); m=int(row["mes"])
        except: continue
        rows.append(row)
        if (a,m)>latest[row["id_entidad"]]: latest[row["id_entidad"]]=(a,m)

# 2) collect CAS salaries for latest period only
ent=collections.defaultdict(lambda:{"name":"","sal":[],"per":None,"url":""})
for row in rows:
    i=row["id_entidad"]
    a=int(row["anio"]); m=int(row["mes"])
    if (a,m)!=latest[i]: continue
    try: v=float(row["total_ingreso_mensual"] or 0)
    except: v=0.0
    e=ent[i]; e["name"]=row["entidad"]; e["per"]=f"{a}-{m:02d}"; e["url"]=row["fuente_url"]
    if v>0: e["sal"].append(v)

def pct(xs,p):
    if not xs: return ""
    xs=sorted(xs); k=int(p*(len(xs)-1)); return round(xs[k],2)

out="salariosperu_cuadro.proposed.csv"
with open(out,"w",newline="") as f:
    w=csv.writer(f)
    w.writerow(["entidad_norm","id_entidad_pt","entidad_pt","regimen","periodo_pt",
                "n_personas_pt","ingreso_mediana_pt","ingreso_p25_pt","ingreso_p75_pt","masa_mensual_pt",
                "n_convocatorias_cas","salario_oferta_mediana_cas","gap_oferta_vs_ejecutado","fuente_pt_url"])
    for i,e in sorted(ent.items(),key=lambda kv:-sum(kv[1]["sal"])):
        sal=e["sal"]
        if not sal: continue
        med=round(st.median(sal),2)
        w.writerow([norm(e["name"]),i,e["name"],"CAS",e["per"],
                    len(sal),med,pct(sal,.25),pct(sal,.75),round(sum(sal),2),
                    "","","",e["url"]])
print("escrito:",out,"entidades:",sum(1 for e in ent.values() if e["sal"]))
