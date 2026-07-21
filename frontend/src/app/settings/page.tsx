"use client";

import { ProtectedPage } from "@/components/protected-page";
export default function SettingsPage(){return <ProtectedPage><section className="page-heading"><div><p className="eyebrow">Administração</p><h1>Ajustes</h1><p>Catálogo, usuários autorizados e ações administrativas são validados pelo backend.</p></div></section><section className="panel"><p>Use as APIs administrativas para importar o catálogo e gerenciar usuários. Nenhum segredo é editado pelo portal.</p></section></ProtectedPage>}
