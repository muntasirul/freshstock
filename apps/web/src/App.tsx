import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  ArrowDownToLine, ArrowRight, BarChart3, Box, Check, ChevronRight,
  CircleHelp, FlaskConical, LayoutDashboard, Leaf, LoaderCircle,
  Package, Plus, RefreshCw, Search, ShoppingBag, SlidersHorizontal,
  Sparkles, TrendingUp, UploadCloud, X,
} from "lucide-react";
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api, type Order, type Overview, type Product, type Simulation } from "./api";

type Page = "Overview" | "Inventory" | "Model lab" | "Data imports";
const pages = [
  { name: "Overview" as Page, icon: LayoutDashboard },
  { name: "Inventory" as Page, icon: Package },
  { name: "Model lab" as Page, icon: FlaskConical },
  { name: "Data imports" as Page, icon: ArrowDownToLine },
];
const number = (value: number) => new Intl.NumberFormat("en", { maximumFractionDigits: 1 }).format(value);
const percent = (value: number | null | undefined) => value == null ? "n/a" : `${(value * 100).toFixed(1)}%`;
const shortDate = (value: string) =>
  new Date(`${value}T12:00:00`).toLocaleDateString("en", { month: "short", day: "numeric" });

export default function App() {
  const [page, setPage] = useState<Page>("Overview");
  const [data, setData] = useState<Overview | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState<Record<string, number> | null>(null);
  const [saving, setSaving] = useState(false);
  const [selected, setSelected] = useState<Product | null>(null);
  const [history, setHistory] = useState<{ date: string; sales: number }[]>([]);
  const [shelfLife, setShelfLife] = useState(7);
  const [penalty, setPenalty] = useState(2);
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [simulating, setSimulating] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const orderKey = useRef("");

  async function refresh() {
    setLoading(true);
    setError("");
    try {
      const [overview, savedOrders] = await Promise.all([
        api<Overview>("/overview"), api<Order[]>("/orders"),
      ]);
      setData(overview);
      setOrders(savedOrders);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load the workspace.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, []);
  useEffect(() => {
    if (!selected) return;
    let ignore = false;
    setHistory([]);
    api<{ date: string; sales: number }[]>(`/products/${selected.id}/history`)
      .then((result) => { if (!ignore) setHistory(result); })
      .catch((cause) => { if (!ignore) setError(String(cause)); });
    return () => { ignore = true; };
  }, [selected]);
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !saving) { setDraft(null); setSelected(null); }
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [saving]);

  function openDraft() {
    if (!data) return;
    orderKey.current = crypto.randomUUID();
    setDraft(Object.fromEntries(data.products.filter((p) => p.order_quantity > 0).map(
      (p) => [p.id, p.order_quantity],
    )));
  }

  async function saveDraft(event: FormEvent) {
    event.preventDefault();
    if (!draft) return;
    setSaving(true);
    try {
      await api("/orders", {
        method: "POST",
        body: JSON.stringify({
          idempotency_key: orderKey.current,
          items: Object.entries(draft)
            .filter(([, quantity]) => quantity > 0)
            .map(([product_id, quantity]) => ({ product_id, quantity })),
        }),
      });
      setDraft(null);
      setNotice("Purchase draft saved. No order has been sent to a supplier.");
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to save the draft.");
    } finally { setSaving(false); }
  }

  async function runSimulation(event: FormEvent) {
    event.preventDefault();
    setSimulating(true);
    setError("");
    try {
      setSimulation(await api<Simulation>("/simulations", {
        method: "POST",
        body: JSON.stringify({ shelf_life: shelfLife, lost_sale_penalty: penalty }),
      }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Simulation failed.");
    } finally { setSimulating(false); }
  }

  async function importSales(event: FormEvent) {
    event.preventDefault();
    if (!importFile) return;
    setImporting(true);
    setError("");
    try {
      const result = await api<{ inserted: number; skipped: number; note: string }>("/imports/sales", {
        method: "POST",
        headers: { "Content-Type": "text/csv" },
        body: await importFile.text(),
      });
      setNotice(`${result.inserted} rows added, ${result.skipped} unchanged. ${result.note}`);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Import failed.");
    } finally { setImporting(false); }
  }

  const products = data?.products.filter((p) => p.id.toLowerCase().includes(query.toLowerCase())) ?? [];
  const test = data?.metrics?.test;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="FreshStock home">
          <span className="brand-icon"><Leaf size={22} /></span> freshstock<span className="brand-dot">.</span>
        </a>
        <div className="workspace-card">
          <span className="store-avatar"><ShoppingBag size={19} /></span>
          <div><strong>M5 Market</strong><span>California · Store CA_1</span></div>
          <ChevronRight size={16} />
        </div>
        <p className="nav-label">WORKSPACE</p>
        <nav aria-label="Main navigation">
          {pages.map(({ name, icon: Icon }) => (
            <button key={name} className={`nav-item ${page === name ? "active" : ""}`}
              onClick={() => { setPage(name); setQuery(""); }}>
              <Icon size={19} />{name}
              {name === "Inventory" && data && <span className="nav-count">{data.summary.products}</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note"><Sparkles size={18} /><strong>A little foresight.<br />A lot less guesswork.</strong>
            <p>Make room for better inventory decisions.</p></div>
          <a className="help-link" href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">
            <CircleHelp size={17} /> API documentation <ArrowRight size={15} />
          </a>
          <div className="profile"><span>FS</span><div><strong>Local workspace</strong><small>Single-user demo</small></div>
            <span className="online-dot" /></div>
        </div>
      </aside>

      <div className="main-shell">
        <header className="topbar">
          <div>Workspace <ChevronRight size={14} /> <strong>{page}</strong></div>
          <span className="environment"><span /> Historical data demo</span>
        </header>
        <main>
          <div className="page-heading">
            <div><p className="eyebrow">YOUR INVENTORY, AHEAD OF THE CURVE</p>
              <h1>{page === "Overview" ? "A clearer view of what's next." : page}</h1>
              <p className="subtitle">{page === "Overview" ? "Turn demand into a plan. Keep the right products on your shelves."
                : page === "Inventory" ? "Review stock, understand demand, and prepare your next purchase."
                : page === "Model lab" ? "Look beyond the forecast. See how each policy performs."
                : "Bring your daily sales into one consistent workspace."}</p>
            </div>
            <button className="button secondary icon-button" onClick={() => void refresh()} disabled={loading}>
              <RefreshCw size={16} className={loading ? "spin" : ""} /> Refresh
            </button>
          </div>
          {error && <div className="alert error" role="alert">{error}<button aria-label="Dismiss error" onClick={() => setError("")}><X size={16} /></button></div>}
          {notice && <div className="alert success" role="status"><Check size={17} />{notice}<button aria-label="Dismiss notification" onClick={() => setNotice("")}><X size={16} /></button></div>}
          {loading && !data ? <div className="empty"><LoaderCircle className="spin" /> Loading your workspace...</div>
            : !data || data.products.length === 0 ? <div className="empty"><Box size={36} /><h2>Your workspace is ready for data.</h2>
              <p>Prepare the M5 dataset, then restart the API to load your store.</p>
              <code>uv run freshstock prepare</code></div>
            : <>
              <div className="context-line"><span className="context-dot" /> {data.summary.products} products connected
                <span className="divider">/</span> Snapshot: {data.as_of}
                <span className="context-source">{data.model_version ? "Model trained" : "Seasonal baseline"}</span>
              </div>

              {(page === "Overview" || page === "Inventory") && <>
                {page === "Overview" && <>
                  <section className="hero-card">
                    <div><span className="hero-tag"><Sparkles size={14} /> YOUR NEXT MOVE</span>
                      <h2>A thoughtful order starts here.</h2>
                      <p>{data.summary.reorder_count} products could use a top-up based on their demand targets.<br />
                        Review {number(data.summary.suggested_units)} suggested units before creating your draft.</p>
                      <button className="button light" onClick={openDraft} disabled={!data.summary.reorder_count}>
                        Review recommendations <ArrowRight size={16} />
                      </button>
                    </div>
                    <div className="hero-art" aria-hidden="true">
                      <div className="art-ring ring-one" /><div className="art-ring ring-two" />
                      <div className="art-box box-back"><Leaf size={46} /></div>
                      <div className="art-box box-front"><Package size={48} strokeWidth={1.2} /></div>
                      <span className="art-badge"><TrendingUp size={15} /> Demand-led planning</span>
                    </div>
                  </section>
                  <section className="stat-grid" aria-label="Inventory summary">
                    <Stat label="Products tracked" value={number(data.summary.products)} note="One store, food categories" icon={<Box size={18} />} />
                    <Stat label="Units on hand" value={number(data.summary.stock_units)} note="Simulated opening inventory" icon={<Package size={18} />} />
                    <Stat label="Suggested purchase" value={number(data.summary.suggested_units)} note="Units across current recommendations" icon={<ShoppingBag size={18} />} />
                    <Stat label="Forecast WAPE" value={percent(test?.point.wape)} note={test ? `${data.model_horizon}-day demand · held-out test` : "Train a model to evaluate"} icon={<TrendingUp size={18} />} />
                  </section>
                  <div className="chart-layout">
                    <section className="panel demand-panel"><div className="panel-heading"><div><h2>Demand at a glance</h2><p>Observed unit sales across your store</p></div><span className="pill neutral">Last 8 weeks</span></div>
                      <SalesChart values={data.history} />
                    </section>
                    <section className="panel insight-panel"><span className="insight-icon"><Leaf size={23} /></span>
                      <p className="eyebrow">A NOTE ON YOUR DATA</p><h2>Good decisions start<br />with honest assumptions.</h2>
                      <p>These are real historical sales. Inventory levels and shelf lives are demo assumptions.</p>
                      <div className="insight-foot"><span>Explore the evidence</span><button aria-label="Open model lab" onClick={() => setPage("Model lab")}><ArrowRight size={18} /></button></div>
                    </section>
                  </div>
                </>}
                <section className="panel table-panel">
                  <div className="panel-heading"><div><h2>{page === "Inventory" ? "Your product inventory" : "Plan your next purchase"}</h2><p>Demand targets account for supplier lead time.</p></div>
                    <div className="table-actions"><label className="search"><Search size={16} /><input aria-label="Search products" placeholder="Find a product..." value={query} onChange={(e) => setQuery(e.target.value)} /></label>
                      <button className="button primary" onClick={openDraft} disabled={!data.summary.reorder_count}><Plus size={16} /> Create draft</button></div>
                  </div>
                  <div className="table-scroll"><table><thead><tr>
                    <th>Product</th><th>On hand</th><th>Daily demand</th><th>Lead time</th><th>Suggested order</th><th>Status</th><th><span className="sr-only">Details</span></th>
                  </tr></thead><tbody>{products.map((product) => <tr key={product.id}>
                    <td><button className="product-link" onClick={() => setSelected(product)}><span className="product-icon"><Package size={19} /></span><span><strong>{product.id}</strong><small>{product.department.replaceAll("_", " ")} · {product.source}</small></span></button></td>
                    <td>{number(product.on_hand)} <span className="muted">units</span></td>
                    <td>{number(product.daily_average)} <span className="muted">/ day</span></td>
                    <td>{product.lead_time} days</td>
                    <td><strong>{product.order_quantity ? `+${number(product.order_quantity)}` : "0"}</strong> <span className="muted">units</span></td>
                    <td><span className={`pill ${product.order_quantity ? "amber" : "green"}`}><span />{product.order_quantity ? "Review order" : "At target"}</span></td>
                    <td><button className="detail-button" aria-label={`View ${product.id}`} onClick={() => setSelected(product)}><ChevronRight size={17} /></button></td>
                  </tr>)}</tbody></table></div>
                  {!products.length && <div className="empty small">No products match your search.</div>}
                  <div className="table-footer"><span>{products.length} products · Snapshot-based recommendations</span><span>Review before ordering <SlidersHorizontal size={14} /></span></div>
                </section>
                {page === "Inventory" && <section className="panel orders-panel"><div className="panel-heading"><div><h2>Purchase drafts</h2><p>Saved locally. Nothing is sent to suppliers.</p></div><span className="pill neutral">{orders.length} drafts</span></div>
                  {orders.length === 0 ? <p className="empty small">Your first purchase draft will appear here.</p> : orders.map((order) => <div className="order-row" key={order.id}><ShoppingBag size={18} /><div><strong>Draft {order.id.slice(0, 8)}</strong><small>{order.items.length} products · {order.items.reduce((sum, item) => sum + item.quantity, 0)} units</small></div><span className="pill neutral">{order.status}</span></div>)}
                </section>}
              </>}

              {page === "Model lab" && <>
                <section className="panel"><div className="panel-heading"><div><h2>Forecast performance</h2><p>Chronological test holdout · cumulative {data.model_horizon ?? 2}-day demand</p></div><span className="pill green">Actual measured results</span></div>
                  {test ? <div className="table-scroll"><table><thead><tr><th>Model</th><th>MAE (units)</th><th>WAPE</th><th>Pinball loss</th></tr></thead><tbody>
                    {Object.entries(test).map(([name, metrics]) => <tr key={name}><td><strong>{name === "seasonal_baseline" ? "Seasonal baseline" : `LightGBM ${name}`}</strong></td><td>{number(metrics.mae)}</td><td>{percent(metrics.wape)}</td><td>{metrics.pinball_loss == null ? "Not applicable" : number(metrics.pinball_loss)}</td></tr>)}
                  </tbody></table></div> : <p className="empty small">Train a model to view measured results.</p>}
                  <p className="footnote">Lower error is better. Forecast quality and inventory savings are separate measurements. Overlapping target windows are not independent samples.</p>
                </section>
                <section className="panel simulation-panel"><div className="panel-heading"><div><h2>What if things changed?</h2><p>Compare ordering policies using the same historical demand.</p></div><FlaskConical size={22} /></div>
                  <form className="scenario-form" onSubmit={(e) => void runSimulation(e)}>
                    <label>Shelf life after arrival<span className="input-unit"><input type="number" min="1" max="90" value={shelfLife} onChange={(e) => setShelfLife(Number(e.target.value))} required /><span>days</span></span></label>
                    <label>Lost-sale penalty<span className="input-unit"><input type="number" min="0" max="1000" step="0.1" value={penalty} onChange={(e) => setPenalty(Number(e.target.value))} required /><span>per unit</span></span></label>
                    <button className="button primary" disabled={simulating || !test}>{simulating ? <LoaderCircle size={16} className="spin" /> : <FlaskConical size={16} />} Run comparison</button>
                  </form>
                  {simulation && <><div className="table-scroll"><table><thead><tr><th>Policy</th><th>Simulated cost</th><th>Fill rate</th><th>Expired units</th><th>Unmet demand</th><th>Closing / in transit</th></tr></thead><tbody>
                    {simulation.results.map((result) => <tr key={result.policy}><td><strong>{result.policy}</strong></td><td>{number(result.cost)}</td><td>{percent(result.fill_rate)}</td><td>{number(result.expired_units)}</td><td>{number(result.unmet_units)}</td><td>{number(result.closing_units)} / {number(result.outstanding_units)}</td></tr>)}
                  </tbody></table></div><p className="footnote">{simulation.notice}</p></>}
                </section>
                <div className="method-note"><BarChart3 size={21} /><div><strong>Keep the comparison fair.</strong><p>All policies share a demand stream, cost assumptions, and a 14-day warm-up. Lower cost needs to be considered alongside customer fill rate.</p></div></div>
              </>}

              {page === "Data imports" && <section className="panel import-panel"><div className="panel-heading"><div><h2>Import daily sales</h2><p>CSV files up to 2 MB. Existing identical records are safely skipped.</p></div></div>
                <form onSubmit={(e) => void importSales(e)}><label className="upload-zone"><UploadCloud size={34} /><strong>Choose a sales CSV</strong><span>{importFile ? importFile.name : "One row per product and date"}</span><input type="file" accept=".csv,text/csv" onChange={(e) => setImportFile(e.target.files?.[0] ?? null)} required /></label>
                  <div className="import-help"><h3>Required format</h3><pre>product_id,date,quantity{"\n"}{data.products[0]?.id},YYYY-MM-DD,12</pre><p>Use existing product identifiers and whole-unit sales. Conflicting records are rejected; the entire import is rolled back.</p><p>New sales dates make saved model forecasts stale. The dashboard then uses a seasonal baseline until matching forecasts are generated. Imports do not update demo stock.</p></div>
                  <button className="button primary" disabled={!importFile || importing}>{importing ? <LoaderCircle className="spin" size={16} /> : <UploadCloud size={16} />} Validate and import</button>
                </form>
              </section>}
              <footer><span><Leaf size={14} /> FreshStock · A little more foresight.</span><span>Historical sales · Simulated inventory · Local demo</span></footer>
            </>}
        </main>
      </div>

      {draft && <div className="modal-backdrop"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="draft-title">
        <div className="panel-heading"><div><h2 id="draft-title">Review purchase draft</h2><p>Adjust quantities before saving. Set a quantity to 0 to omit it.</p></div><button aria-label="Close draft" className="detail-button" disabled={saving} onClick={() => setDraft(null)}><X /></button></div>
        <form onSubmit={(e) => void saveDraft(e)}><div className="draft-items">{Object.entries(draft).map(([id, quantity]) => <label key={id}><span>{id}</span><input aria-label={`Quantity for ${id}`} type="number" min="0" max="100000" step="1" value={quantity} onChange={(e) => setDraft({ ...draft, [id]: Number(e.target.value) })} required /></label>)}</div>
          <p className="footnote">This saves a draft only. Inventory and supplier orders are unchanged.</p>
          <button className="button primary" disabled={saving || !Object.values(draft).some((quantity) => quantity > 0)}>{saving ? <LoaderCircle className="spin" size={16} /> : <Check size={16} />} Save draft</button></form>
      </section></div>}
      {selected && <div className="modal-backdrop"><section className="modal wide" role="dialog" aria-modal="true" aria-labelledby="product-title">
        <div className="panel-heading"><div><p className="eyebrow">PRODUCT DETAIL</p><h2 id="product-title">{selected.id}</h2></div><button aria-label="Close product details" className="detail-button" onClick={() => setSelected(null)}><X /></button></div>
        <SalesChart values={history} />
        <div className="product-details"><div><small>Current stock</small><strong>{number(selected.on_hand)} units</strong></div><div><small>Demand target</small><strong>{number(selected.target_stock)} units</strong></div><div><small>Forecast source</small><strong>{selected.source}</strong></div><div><small>Protection horizon</small><strong>{selected.lead_time} days</strong></div></div>
        <p className="footnote">{selected.explanation}</p>
      </section></div>}
    </div>
  );
}

function Stat({ label, value, note, icon }: { label: string; value: string; note: string; icon: React.ReactNode }) {
  return <article className="stat-card"><div><span>{label}</span><span className="stat-icon">{icon}</span></div><strong>{value}</strong><p>{note}</p></article>;
}

function SalesChart({ values }: { values: { date: string; sales: number }[] }) {
  return <div className="sales-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={values} margin={{ top: 10, right: 12, left: -18, bottom: 0 }}>
    <defs><linearGradient id="salesFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#3d8d66" stopOpacity={0.2} /><stop offset="100%" stopColor="#3d8d66" stopOpacity={0.01} /></linearGradient></defs>
    <CartesianGrid strokeDasharray="3 4" vertical={false} stroke="#e8ece8" /><XAxis dataKey="date" tickFormatter={shortDate} minTickGap={38} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#849087" }} dy={8} />
    <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#849087" }} />
    <Tooltip labelFormatter={(value) => String(value)} contentStyle={{ borderRadius: 10, border: "1px solid #e4e9e3", fontSize: 12 }} />
    <Area type="monotone" dataKey="sales" name="Units sold" stroke="#438a64" strokeWidth={2} fill="url(#salesFill)" />
  </AreaChart></ResponsiveContainer></div>;
}
