"use client";

import { ProtectedPage } from "@/components/protected-page";
export default function DeploysPage(){return <ProtectedPage><section className="page-heading"><div><p className="eyebrow">Operações</p><h1>Deploys</h1><p>Os deploys recentes aparecem por produto após a sincronização Render.</p></div></section><section className="panel"><p>Abra um produto para consultar serviços e snapshots de deploy sem acessar diretamente a API Render.</p></section></ProtectedPage>}
