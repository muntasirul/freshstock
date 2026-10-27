export type Product = {
  id: string;
  department: string;
  store: string;
  lead_time: number;
  shelf_life: number;
  on_hand: number;
  daily_average: number;
  forecast: number;
  target_stock: number;
  order_quantity: number;
  days_cover: number | null;
  source: string;
  quantile: number | null;
  explanation: string;
};

export type ForecastMetric = {
  mae: number;
  wape: number | null;
  pinball_loss?: number;
  observed_quantile_coverage?: number;
};

export type Overview = {
  as_of: string | null;
  products: Product[];
  history: { date: string; sales: number }[];
  summary: { products: number; stock_units: number; suggested_units: number; reorder_count: number };
  metrics: {
    validation: Record<string, ForecastMetric>;
    test: Record<string, ForecastMetric>;
  } | null;
  model_version: string | null;
  model_horizon: number | null;
  notice: string;
};

export type Order = {
  id: string;
  status: string;
  created_at: string;
  items: { product_id: string; quantity: number }[];
};

export type Simulation = {
  results: {
    policy: string;
    cost: number;
    fill_rate: number | null;
    expired_units: number;
    unmet_units: number;
    closing_units: number;
    outstanding_units: number;
  }[];
  lead_time: number;
  shelf_life: number;
  notice: string;
};

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(
      typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail),
    );
  }
  return response.json();
}
