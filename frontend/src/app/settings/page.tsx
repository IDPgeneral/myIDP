"use client";

import { ProtectedPage } from "@/components/protected-page";
export default function SettingsPage(){return <ProtectedPage><section className="page-heading"><div><p className="eyebrow">Administração</p><h1>Ajustes</h1><p>Catálogo, usuários autorizados e ações administrativas são validados pelo backend.</p></div></section><section className="panel"><p>O acesso usa Google via Supabase Auth. Nenhum segredo é exibido ou editado pelo frontend.</p></section></ProtectedPage>}
