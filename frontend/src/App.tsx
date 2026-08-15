import { Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Home } from "@/pages/Home";
import { Entidades } from "@/pages/Entidades";
import { EntidadDetalle } from "@/pages/EntidadDetalle";
import { Funcionarios } from "@/pages/Funcionarios";
import { NuevosFuncionarios } from "@/pages/NuevosFuncionarios";
import { Metodologia } from "@/pages/Metodologia";
import { Regiones } from "@/pages/Regiones";
import { Autoridades } from "@/pages/Autoridades";
import { Personas } from "@/pages/Personas";
import { Salarios } from "@/pages/Salarios";
import { Ordenes } from "@/pages/Ordenes";
import { Contratos } from "@/pages/Contratos";
import { Sanciones } from "@/pages/Sanciones";
import { Trayectorias } from "@/pages/Trayectorias";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/entidades" element={<Entidades />} />
        <Route path="/entidad/:id" element={<EntidadDetalle />} />
        <Route path="/funcionarios" element={<Funcionarios />} />
        <Route path="/nuevos" element={<NuevosFuncionarios />} />
        <Route path="/ordenes" element={<Ordenes />} />
        <Route path="/contratos" element={<Contratos />} />
        <Route path="/sanciones" element={<Sanciones />} />
        <Route path="/salarios" element={<Salarios />} />
        <Route path="/personas" element={<Personas />} />
        <Route path="/trayectorias" element={<Trayectorias />} />
        <Route path="/autoridades" element={<Autoridades />} />
        <Route path="/regiones" element={<Regiones />} />
        <Route path="/metodologia" element={<Metodologia />} />
      </Routes>
    </Layout>
  );
}
