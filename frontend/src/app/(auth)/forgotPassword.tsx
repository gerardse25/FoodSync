import { router } from "expo-router";
import { ArrowLeft, CircleAlert, KeyRound, Mail } from "lucide-react-native";
import React, { useState } from "react";
import { Text, TextInput, TouchableOpacity, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-aware-scroll-view";
import { SafeAreaView } from "react-native-safe-area-context";
import { authService } from "../../services/authService";

export default function ForgotPasswordScreen() {
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState("");

  const [isLoading, setIsLoading] = useState(false);
  const [isSent, setIsSent] = useState(false);

  const isValidEmail = (email: string) => {
    const trimmedEmail = email.trim();
    if (trimmedEmail.length === 0 || trimmedEmail.length > 128) return false;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(trimmedEmail);
  };

  const handleEmailEndEditing = (text: string) => {
    if (!isValidEmail(text)) {
      setEmailError("Correu no vàlid");
    } else {
      setEmailError("");
    }
  };

  const handleRecover = async () => {
    if (!isValidEmail(email)) {
      setEmailError("Correu no vàlid");
      return;
    }

    setIsLoading(true);

    try {
      await authService.requestPasswordReset(email.trim().toLowerCase());
    } catch (error) {
      console.log("Petició feta (error silenciat per privacitat):", error);
    } finally {
      setIsLoading(false);
      setIsSent(true); 
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-[#F8FAF8]">
      <KeyboardAwareScrollView
        contentContainerStyle={{ flexGrow: 1, paddingBottom: 40 }}
        keyboardShouldPersistTaps="handled"
        enableOnAndroid={true}
        extraScrollHeight={40}
        showsVerticalScrollIndicator={false}
      >
        {/* Cabecera */}
        <View className="px-4 pt-6 pb-4">
          <TouchableOpacity
            className="w-10 h-10 rounded-xl flex items-center justify-center active:bg-gray-200"
            onPress={() => router.back()}
            disabled={isLoading}
          >
            <ArrowLeft color="#1F2937" size={24} />
          </TouchableOpacity>
        </View>

        {/* Contenido Principal */}
        <View className="flex-1 px-6 pt-4">
          {!isSent ? (
            <>
              <Text className="text-3xl font-bold mb-2 text-gray-900">
                Recuperar contrasenya
              </Text>
              <Text className="text-gray-500 mb-8">
                Introdueix el teu correu electrònic i t&apos;enviarem les
                instruccions per restablir-la.
              </Text>

              <View className="space-y-5">
                <View className="space-y-2">
                  <Text className="font-medium text-gray-900">
                    Correu electrònic
                  </Text>
                  <View
                    className={`h-14 px-4 rounded-2xl bg-white border flex-row items-center  ${emailError ? "border-red-500" : "border-gray-200"}`}
                  >
                    <Mail
                      color={emailError ? "#EF4444" : "#9CA3AF"}
                      size={20}
                    />
                    <TextInput
                      value={email}
                      onChangeText={(text) => {
                        setEmail(text);
                        if (emailError && isValidEmail(text)) setEmailError("");
                      }}
                      onEndEditing={(e) =>
                        handleEmailEndEditing(e.nativeEvent.text)
                      }
                      placeholder="correu@email.com"
                      placeholderTextColor="#9CA3AF"
                      keyboardType="email-address"
                      autoCapitalize="none"
                      autoCorrect={false}
                      className="h-14 px-4 w-full text-base"
                      editable={!isLoading}
                    />
                  </View>
                  {emailError ? (
                    <View className="flex-row gap-2 items-center">
                      <CircleAlert color="#ef4444" size={16} />
                      <Text className="text-red-500 text-sm">{emailError}</Text>
                    </View>
                  ) : null}
                </View>

                <TouchableOpacity
                  className={`w-full h-12 rounded-xl flex items-center justify-center mt-4 shadow-sm ${
                    isLoading
                      ? "bg-emerald-400"
                      : "bg-emerald-500 active:bg-emerald-600"
                  }`}
                  onPress={handleRecover}
                  disabled={isLoading}
                >
                  <Text className="text-white text-base font-bold">
                    {isLoading ? "Enviant..." : "Recuperar contrasenya"}
                  </Text>
                </TouchableOpacity>
              </View>
            </>
          ) : (
            <View className="flex-1 items-center justify-center pt-8">
              <View className="items-center px-2 space-y-4 mb-8">
                <View className="w-20 h-20 rounded-full bg-emerald-50 items-center justify-center mb-2">
                  <KeyRound color="#10B981" size={36} />
                </View>
                <Text className="text-3xl font-bold text-gray-900 text-center">
                  Instruccions enviades
                </Text>
                <Text className="text-gray-500 text-center leading-5 px-4 mt-2">
                  Si el correu està registrat, rebràs un missatge amb els passos
                  per restablir la contrasenya d&apos;immediat.
                </Text>
              </View>

              <TouchableOpacity
                className="w-full h-12 rounded-xl flex items-center justify-center mt-4 shadow-sm bg-gray-900 active:bg-black"
                onPress={() => router.replace("/(auth)/login")}
              >
                <Text className="text-white text-base font-bold">
                  Tornar a l&apos;inici de sessió
                </Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      </KeyboardAwareScrollView>
    </SafeAreaView>
  );
}
