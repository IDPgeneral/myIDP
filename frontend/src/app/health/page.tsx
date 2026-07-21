"use client";

import { ProtectedPage } from "@/components/protected-page";
export default function HealthPage(){return <ProtectedPage><section className="page-heading"><div><p className="eyebrow">Disponibilidade</p><h1>Saúde</h1><p>Health checks armazenados com timeout, latência e status HTTP.</p></div></section><section className="panel"><p>O dashboard destaca o pior estado de cada produto. Abra o produto para ver todos os endpoints.</p></section></ProtectedPage>}
