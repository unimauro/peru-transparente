import csv, collections, sys
path = sys.argv[1] if len(sys.argv)>1 else "data/funcionarios.csv"
agg = collections.defaultdict(lambda: {"n":0,"sum":0.0,"id":None})
regimenes=collections.Counter()
periodos=collections.Counter()
n=0; nonzero=0
with open(path, newline="") as f:
    r=csv.DictReader(f)
    cols=r.fieldnames
    for row in r:
        n+=1
        ent=row["entidad"]
        a=agg[ent]
        a["id"]=row["id_entidad"]
        a["n"]+=1
        regimenes[row["regimen"]]+=1
        periodos[(row["anio"],row["mes"])]+=1
        try:
            v=float(row["total_ingreso_mensual"] or 0)
            a["sum"]+=v
            if v>0: nonzero+=1
        except: pass
print("columnas:",cols)
print("filas datos:",n,"| con total>0:",nonzero,"| entidades distintas:",len(agg))
print("\nregimenes:",dict(regimenes.most_common()))
print("\nperiodos top:",periodos.most_common(8))
print("\nTOP 15 entidades por #personas:")
for ent,a in sorted(agg.items(),key=lambda kv:-kv[1]["n"])[:15]:
    print(f"  id={a['id']:>6} n={a['n']:>6} masa=S/{a['sum']:>14,.0f}  {ent[:50]}")
with open("data/_funcionarios_por_entidad.csv","w",newline="") as out:
    w=csv.writer(out)
    w.writerow(["id_entidad","entidad","n_personas","masa_salarial_mensual_pen","sueldo_promedio_pen"])
    for ent,a in sorted(agg.items(),key=lambda kv:-kv[1]["sum"]):
        prom = a["sum"]/a["n"] if a["n"] else 0
        w.writerow([a["id"],ent,a["n"],round(a["sum"],2),round(prom,2)])
print("\nGuardado: data/_funcionarios_por_entidad.csv")
