"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import QRCode from "qrcode";
import { supabase } from "@/lib/supabase";

function PairPageContent() {
  const searchParams = useSearchParams();
  const code = searchParams.get("code") ?? "";
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [claimed, setClaimed] = useState(false);

  useEffect(() => {
    if (!code) return;
    const claimUrl = `${window.location.origin}/pair/claim?code=${code}`;
    QRCode.toDataURL(claimUrl).then(setQrDataUrl);
  }, [code]);

  useEffect(() => {
    if (!code) return;

    const channel = supabase
      .channel(`pairing_codes_${code}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "pairing_codes",
          filter: `code=eq.${code}`,
        },
        (payload) => {
          if ((payload.new as { status: string }).status === "claimed") {
            setClaimed(true);
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [code]);

  if (!code) {
    return <p>Eksik eşleştirme kodu.</p>;
  }

  return (
    <main style={{ fontFamily: "sans-serif", textAlign: "center", padding: "2rem" }}>
      <h1>AI-Notifier Cihaz Eşleştirme</h1>
      {claimed ? (
        <p>✅ Eşleştirildi! Masaüstü uygulamasına dönebilirsiniz.</p>
      ) : (
        <>
          <p>Bu kodu telefonunuzla okutun:</p>
          <h2 style={{ fontSize: "2rem", letterSpacing: "0.3em" }}>{code}</h2>
          {qrDataUrl && (
            <img src={qrDataUrl} alt="Eşleştirme QR kodu" width={240} height={240} />
          )}
          <p>Bekleniyor...</p>
        </>
      )}
    </main>
  );
}

export default function PairPage() {
  return (
    <Suspense fallback={<p>Yükleniyor...</p>}>
      <PairPageContent />
    </Suspense>
  );
}
