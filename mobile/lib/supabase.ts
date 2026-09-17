import { createClient } from "@supabase/supabase-js";

// Native bir depolama modülü (AsyncStorage) gerektirmemek için basit bir
// bellek-içi depolama kullanılıyor — zaten derlenmiş development build'e
// yeni bir native modül eklemek yeniden bulut derlemesi gerektirirdi.
// Bunun bedeli: oturum uygulama kapatılınca sıfırlanır (MVP için kabul
// edilebilir, tek seferlik giriş + FCM token kaydı yeterli).
const memoryStorage: Record<string, string> = {};

const inMemoryStorageAdapter = {
  getItem: (key: string) => Promise.resolve(memoryStorage[key] ?? null),
  setItem: (key: string, value: string) => {
    memoryStorage[key] = value;
    return Promise.resolve();
  },
  removeItem: (key: string) => {
    delete memoryStorage[key];
    return Promise.resolve();
  },
};

export const supabase = createClient(
  "https://wvhlikiiqrculbpvphxk.supabase.co",
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind2aGxpa2lpcXJjdWxicHZwaHhrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk1ODM4NzMsImV4cCI6MjEwNTE1OTg3M30.f2Qztv7xssStlPUAmGGCPAsHYuo-cv9aImBDpThmQs0",
  {
    auth: {
      storage: inMemoryStorageAdapter,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false,
      flowType: "pkce",
    },
  }
);
