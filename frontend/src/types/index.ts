export interface Provenance {
  source: string;
  source_url?: string;
  captured_at: string;
  updated_at?: string;
  confidence: number;
  method?: string;
}

export interface Entity {
  id: string;
  name: string;
  acronym?: string;
  sector?: string;
  level?: "nacional" | "regional" | "local";
  website?: string;
  transparency_url?: string;
  provenance?: Provenance[];
}

export interface CareerItem {
  position: string;
  entity: string;
  start_date: string;
  end_date?: string;
  status: string;
  remuneration_amount?: number;
  appointment_resolution?: string;
  appointment_res_url?: string;
}

export interface Official {
  id: string;
  full_name: string;
  career_history: CareerItem[];
  declarations: { period: string; assets_total?: number; income_total?: number; source_url?: string }[];
}

export interface NationalKpis {
  total_entities: number;
  total_persons: number;
  total_companies: number;
  total_contracts: number;
  total_contract_amount: number;
  total_budget_pim: number;
}

export interface GraphNode { id: string; label: string; name?: string; confidence?: number }
export interface GraphEdge { source: string; target: string; type: string; hypothesis?: boolean }
export interface GraphData { nodes: GraphNode[]; edges: GraphEdge[] }
