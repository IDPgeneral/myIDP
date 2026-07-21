import Link from "next/link";
import { relativeTime, shortSha, textValue } from "@/lib/format";
import type { ProductSummary } from "@/types/idp";
import { StatusBadge } from "./status-badge";

export function ProductCard({ product }: { product: ProductSummary }) {
  const deployStatus = product.last_deploy?.status;
  const ciStatus = product.ci?.conclusion ?? product.ci?.status;
  return (
    <article className="product-card">
      <div className="card-heading">
        <div>
          <p className="eyebrow">Produto</p>
          <h2>{product.name}</h2>
        </div>
        <StatusBadge status={product.status} />
      </div>
      <p className="card-description">{product.description ?? "Sem descrição cadastrada."}</p>
      <div className="provider-grid">
        <div><span>GitHub</span><StatusBadge status={product.github_status} /></div>
        <div><span>Render</span><StatusBadge status={product.render_status} /></div>
        <div><span>Supabase</span><StatusBadge status={product.supabase_status} /></div>
      </div>
      <dl className="metric-list">
        <div><dt>Último commit</dt><dd>{shortSha(product.last_commit?.sha)}</dd></div>
        <div><dt>Último deploy</dt><dd>{textValue(deployStatus)}</dd></div>
        <div><dt>CI</dt><dd>{textValue(ciStatus)}</dd></div>
        <div><dt>Health</dt><dd>{product.health?.http_status ? `${product.health.http_status} · ${product.health.status}` : product.health?.status ?? "—"}</dd></div>
      </dl>
      <div className="card-footer">
        <span>Sincronizado: {relativeTime(product.last_sync_at)}</span>
        <span className={product.alert_count ? "alert-count active" : "alert-count"}>{product.alert_count} alerta(s)</span>
        <Link href={`/products/${product.slug}`}>Abrir produto →</Link>
      </div>
    </article>
  );
}
