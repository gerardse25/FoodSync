import { Stack, useRouter, useSegments } from "expo-router";
import { useEffect } from "react";
import { Text, View } from "react-native";
import "../../global.css";
import { AuthProvider, useAuth } from "../context/AuthContext";

const RootLayoutNav = () => {
  const { session, isLoading, hasHome } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;

    const isAuthGroup = segments?.[0] === "(auth)";
    const isIndex = !segments?.length;

    const isPublicScreen = isAuthGroup || isIndex;

    if (!session && !isPublicScreen) {
      router.replace("/");
    } else if (session && isPublicScreen) {
      if (hasHome) {
        router.replace("/(tabs)/dashboard");
      } else {
        router.replace("/(tabs)/household");
      }
    }
  }, [session, isLoading, segments, hasHome]);
  return (
    <View style={{ flex: 1 }}>
      <Stack screenOptions={{ headerShown: false }} />

      {isLoading && (
        <View className="absolute top-0 bottom-0 left-0 right-0 z-50 flex-1 justify-center items-center bg-[#F8FAF8]">
          <Text className="text-emerald-500 font-bold text-lg">
            Carregant FoodSync...
          </Text>
        </View>
      )}
    </View>
  );
};

export default function RootLayout() {
  return (
    <AuthProvider>
      <RootLayoutNav />
    </AuthProvider>
  );
}
