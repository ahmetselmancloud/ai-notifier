"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabase";

type ClaimResult = "idle" | "success" | "error";

function ClaimPageContent() {
  const searchParams = useSearchParams();
  const code = searchParams.get("code") ?? "";
  const [email, setEmail] = useState("");
  const [linkSent, setLinkSent] = useState(false);
  const [claimResult, setClaimResult] = useState<ClaimResult>("idle");

  useEffect(() => {
    if (!code) return;

    async function claimCode(userId: string) {
      const { data: updatedRows, error } = await supabase
        .from("pairing_codes")
        .update({ status: "claimed", claimed_by_user_id: userId })
        .eq("code", code)
        .eq("status", "pending")
        .select("desktop_instance_id");

      // RLS, USING ilkesini karşılamayan bir satırı sessizce 0 satır olarak
      // döner (hata FIRLATMAZ) — bu yüzden hem error hem boş sonucu kontrol
      // etmek gerekiyor, aksi halde arayüz yanlışlıkla "başarılı" gösterebilir.
      if (error || !updatedRows || updatedRows.length === 0) {
        console.error("[ai-notifier] claim güncellemesi başarısız:", error, updatedRows);
        setClaimResult("error");
        return;
      }

      await supabase.from("devices").insert({
        user_id: userId,
        desktop_instance_id: updatedRows[0].desktop_instance_id,
      });

      setClaimResult("success");
    }

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        claimCode(session.user.id);
      }
    });

    const { data: authListener } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        claimCode(session.user.id);
      }
    });

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, [code]);

  async function sendMagicLink(e: React.FormEvent) {
    e.preventDefault();
    await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${window.location.origin}/pair/claim?code=${code}` },
    });
    setLinkSent(true);
  }

  if (!code) {
    return <p>Eksik eşleştirme kodu.</p>;
  }

  if (claimResult === "success") {
    return <p>✅ Eşleştirme başarılı! Masaüstünüze dönebilirsiniz.</p>;
  }

  if (claimResult === "error") {
    return <p>❌ Kod geçersiz veya süresi dolmuş. Masaüstünde yeni bir kod oluşturun.</p>;
  }

  if (linkSent) {
    return <p>E-postanıza bir giriş linki gönderdik. Linke tıklayın.</p>;
  }

  return (
    <main style={{ fontFamily: "sans-serif", textAlign: "center", padding: "2rem" }}>
      <h1>AI-Notifier ile Eşleştir</h1>
      <form onSubmit={sendMagicLink}>
        <input
          type="email"
          required
          placeholder="E-posta adresiniz"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <button type="submit">Giriş linki gönder</button>
      </form>
    </main>
  );
}

export default function ClaimPage() {
  return (
    <Suspense fallback={<p>Yükleniyor...</p>}>
      <ClaimPageContent />
    </Suspense>
  );
}
