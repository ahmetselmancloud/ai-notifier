import { useEffect, useState } from "react";
import { Linking, SafeAreaView, Text, TextInput, Button, StyleSheet } from "react-native";
import { getMessaging, getToken, requestPermission } from "@react-native-firebase/messaging";
import { supabase } from "./lib/supabase";

function extractCodeFromUrl(url: string): string | null {
  const match = url.match(/[?&]code=([^&]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

async function handleIncomingUrl(url: string | null) {
  if (!url) return;
  const code = extractCodeFromUrl(url);
  if (code) {
    await supabase.auth.exchangeCodeForSession(code);
  }
}

export default function App() {
  const [email, setEmail] = useState("");
  const [linkSent, setLinkSent] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    const { data: authListener } = supabase.auth.onAuthStateChange(
      async (_event, session) => {
        if (!session) return;
        await registerFcmToken(session.user.id);
      }
    );

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        registerFcmToken(session.user.id);
      }
    });

    // Uygulama kapalıyken bir e-posta linkiyle açıldıysa (soğuk başlangıç).
    Linking.getInitialURL().then(handleIncomingUrl);
    // Uygulama zaten açıkken bir e-posta linkiyle öne getirildiyse.
    const linkingSubscription = Linking.addEventListener("url", (event) => {
      handleIncomingUrl(event.url);
    });

    return () => {
      authListener.subscription.unsubscribe();
      linkingSubscription.remove();
    };
  }, []);

  async function registerFcmToken(userId: string) {
    const messaging = getMessaging();
    await requestPermission(messaging);
    const token = await getToken(messaging);
    const { error } = await supabase
      .from("devices")
      .update({ fcm_token: token })
      .eq("user_id", userId);

    setStatus(error ? "FCM token kaydedilemedi: " + error.message : "Bağlandı, bildirimler açık.");
  }

  async function sendMagicLink() {
    await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: "ainotifier://login-callback" },
    });
    setLinkSent(true);
  }

  if (status) {
    return (
      <SafeAreaView style={styles.container}>
        <Text>{status}</Text>
      </SafeAreaView>
    );
  }

  if (linkSent) {
    return (
      <SafeAreaView style={styles.container}>
        <Text>E-postana bir giriş linki gönderdik. Linke tıkla.</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>AI-Notifier</Text>
      <TextInput
        style={styles.input}
        placeholder="E-posta adresiniz"
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
      />
      <Button title="Giriş linki gönder" onPress={sendMagicLink} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: 24 },
  title: { fontSize: 24, marginBottom: 16, textAlign: "center" },
  input: { borderWidth: 1, borderColor: "#ccc", borderRadius: 8, padding: 12, marginBottom: 12 },
});
