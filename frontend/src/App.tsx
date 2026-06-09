import { Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Home } from "@/pages/Home";
import { Entidades } from "@/pages/Entidades";
import { EntidadDetalle } from "@/pages/EntidadDetalle";
import { Funcionarios } from "@/pages/Funcionarios";
import { Metodologia } from "@/pages/Metodologia";
import { Regiones } from "@/pages/Regiones";
import { Autoridades } from "@/pages/Autoridades";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/entidades" element={<Entidades />} />
        <Route path="/entidad/:id" element={<EntidadDetalle />} />
        <Route path="/funcionarios" element={<Funcionarios />} />
        <Route path="/autoridades" element={<Autoridades />} />
        <Route path="/regiones" element={<Regiones />} />
        <Route path="/metodologia" element={<Metodologia />} />
      </Routes>
    </Layout>
  );
}
