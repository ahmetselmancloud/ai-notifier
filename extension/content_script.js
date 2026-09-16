// Faz 0'da (docs/superpowers/specs/2026-09-17-browser-extension-design.md bölüm 2)
// sadece claude.ai gerçek DOM'a karşı doğrulandı. chatgpt.com selektörü TAHMİNİDİR.
const SITE_CONFIGS = {
  "claude.ai": {
    siteName: "Claude (Web)",
    isGenerating: () =>
      document.querySelector('[data-testid="chat-input-stop"]') !== null,
  },
  "chatgpt.com": {
    siteName: "ChatGPT (Web)",
    isGenerating: () =>
      Array.from(document.querySelectorAll("button")).some((button) =>
        (button.getAttribute("aria-label") || "")
          .toLowerCase()
          .includes("stop generating")
      ),
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
