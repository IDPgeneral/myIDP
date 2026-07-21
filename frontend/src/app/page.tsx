"use client";

import { useEffect, useState } from "react";
import { ProtectedPage } from "@/components/protected-page";
import { ProductCard } from "@/components/product-card";
import { EmptyState, ErrorState, LoadingState } from "@/components/loading-state";
import { useAuth } from "@/components/auth-provider";
import { ApiError, apiFetch } from "@/lib/api";
import type { ProductSummary } from "@/types/idp";

export default function DashboardPage() {
  const { session } = useAuth();
  const [products, setProducts] = useState<ProductSummary[] | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    if (!session) return;
    apiFetch<ProductSummary[]>(session.access_token, "/api/products")
      .then(setProducts)
      .catch((reason) => setError(reason instanceof ApiError ? reason : new ApiError("Falha inesperada.", 500, null)));
  }, [session]);

  return <ProtectedPage>
    <section className="page-heading"><div><p className="eyebrow">Visão geral</p><h1>Estado dos produtos</h1><p>Prioridade para falhas de conexão, serviços indisponíveis e deploys com erro.</p></div></section>
    {error ? <ErrorState message={error.message} correlationId={error.correlationId} /> : products === null ? <LoadingState /> : products.length === 0 ? <EmptyState title="Nenhum produto cadastrado" description="Execute as migrations e importe o catálogo YAML." /> : <div className="product-grid">{products.map((product) => <ProductCard key={product.id} product={product} />)}</div>}
  </ProtectedPage>;
}
