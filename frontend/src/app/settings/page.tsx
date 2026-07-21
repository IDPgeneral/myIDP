"use client";

import { ProtectedPage } from "@/components/protected-page";
export default function SettingsPage(){return <ProtectedPage><section className="page-heading"><div><p className="eyebrow">Administração</p><h1>Ajustes</h1><p>Catálogo, conexões e ações operacionais são validados pelo backend.</p></div></section><section className="panel"><p>O portal está em acesso direto, sem login. Nenhum segredo é exibido ou editado pelo frontend.</p></section></ProtectedPage>}
