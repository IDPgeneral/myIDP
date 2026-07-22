"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ProtectedPage } from "@/components/protected-page";
import { StatusBadge } from "@/components/status-badge";
import { ErrorState, LoadingState } from "@/components/loading-state";
import { useAuth } from "@/components/auth-provider";
import { ApiError, apiFetch } from "@/lib/api";
import { relativeTime, shortSha, textValue } from "@/lib/format";
import type { ProductSummary } from "@/types/idp";

export default function DeploysPage() {
  const { session } = useAuth();
  const [products, setProducts] = useState<ProductSummary[] | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    if (!session) return;
    apiFetch<ProductSummary[]>(session.access_token, "/api/products")
      .then(setProducts)
      .catch((reason) => setError(reason instanceof ApiError ? reason : new ApiError("Falha ao carregar operações.", 500, null)));
  }, [session]);

  return <ProtectedPage>
    <section className="page-heading"><div><p className="eyebrow">Operações</p><h1>Central de operações</h1><p>Escolha um produto para publicar, reiniciar, acompanhar o deploy e validar a saúde.</p></div></section>
    {error ? <ErrorState message={error.message} correlationId={error.correlationId} /> : products === null ? <LoadingState /> : <div className="product-grid">{products.map((product) => <article className="product-card" key={product.id}>
      <div className="card-heading"><div><p className="eyebrow">{product.owner}</p><h2>{product.name}</h2></div><StatusBadge status={product.status} /></div>
      <dl className="metric-list"><div><dt>Render</dt><dd><StatusBadge status={product.render_status} /></dd></div><div><dt>Deploy</dt><dd>{textValue(product.last_deploy?.status)}</dd></div><div><dt>Commit</dt><dd><code>{shortSha(product.last_commit?.sha)}</code></dd></div><div><dt>CI</dt><dd>{textValue(product.ci?.conclusion ?? product.ci?.status)}</dd></div></dl>
      <footer className="card-footer"><span>Sincronizado {relativeTime(product.last_sync_at)}</span><Link href={`/products/${product.slug}`}>Abrir operações →</Link></footer>
    </article>)}</div>}
  </ProtectedPage>;
}
