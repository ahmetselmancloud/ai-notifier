// Faz 0'da (docs/superpowers/specs/2026-09-17-browser-extension-design.md bölüm 2)
// claude.ai, chatgpt.com, gemini.google.com ve chat.deepseek.com gerçek DOM'a karşı
// doğrulandı (2026-09-17).
// chatgpt.com ve gemini.google.com selektörleri aria-label metnine dayanır, bu da tarayıcı/hesap
// arayüz dili Türkçe dışına değişirse kırılır (claude.ai'nin data-testid'si dilden bağımsızdır).
const SITE_CONFIGS = {
  "claude.ai": {
    siteName: "Claude (Web)",
    isGenerating: () =>
      document.querySelector('[data-testid="chat-input-stop"]') !== null,
  },
  "chatgpt.com": {
    siteName: "ChatGPT (Web)",
    isGenerating: () =>
      document.querySelector('[aria-label="Oluşturmayı durdur"]') !== null,
  },
  "gemini.google.com": {
    siteName: "Gemini (Web)",
    isGenerating: () =>
      document.querySelector('[aria-label="Yanıtı durdur"]') !== null,
  },
  "chat.deepseek.com": {
    // DeepSeek gönder/durdur butonunda aria-label ve data-testid yok, sınıf adları jenerik
    // (ds-button--circle). Durdur ikonu (yuvarlak kare) ile gönder ikonu (ok) farklı SVG path'lere
    // sahip; "2.65954" durdur ikonunun path'ine özgü, stabil bir alt dize. DeepSeek ikon setini
    // değiştirirse bu kırılır.
    siteName: "DeepSeek (Web)",
    isGenerating: () => {
      const button = document.querySelector(
        'div[role="button"].ds-button--primary.ds-button--circle'
      );
      const path = button && button.querySelector("svg path");
      return !!path && (path.getAttribute("d") || "").includes("2.65954");
    },
  },
};

function currentSiteConfig() {
  const host = location.hostname.replace(/^www\./, "");
  return SITE_CONFIGS[host] || null;
}

let lastReportedState = null;

function computeState(config) {
  return config.isGenerating() ? "generating" : "done";
}

function reportState(siteName, state) {
  if (state === lastReportedState) {
    return;
  }
  lastReportedState = state;
  // Background service worker henüz uyanmamışsa veya geçici olarak
  // erişilemezse chrome.runtime.sendMessage reddedilen bir promise döner;
  // bu beklenen bir durumdur, konsolu kirletmemesi için yutulur.
  chrome.runtime.sendMessage({ type: "state", site: siteName, state: state }).catch(() => {});
}

function startObserving() {
  const config = currentSiteConfig();
  if (!config) {
    return;
  }

  const observer = new MutationObserver(() => {
    reportState(config.siteName, computeState(config));
  });
  observer.observe(document.body, { childList: true, subtree: true });

  reportState(config.siteName, computeState(config));
}

startObserving();
