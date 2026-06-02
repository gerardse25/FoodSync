import { useAuth } from "@/src/context/AuthContext";
import { router } from "expo-router";
import { ArrowLeft, CircleAlert, Eye, EyeOff } from "lucide-react-native";
import React, { useRef, useState } from "react";
import {
  Alert,
  Platform,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-aware-scroll-view";
import { SafeAreaView } from "react-native-safe-area-context";
import { authService } from "../../services/authService";

export default function LoginScreen() {
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState("");

  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [passwordError, setPasswordError] = useState("");

  const passwordInputRef = useRef<TextInput>(null);

  const [isLoading, setIsLoading] = useState(false);

  const { checkSession } = useAuth();

  const isValidEmail = (email: string) => {
    const trimmedEmail = email.trim();
    if (trimmedEmail.length > 128) return false;
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

  const isValidPassword = (password: string) => {
    return password.length >= 6;
  };

  const handlePasswordEndEditing = (text: string) => {
    if (!isValidPassword(text)) {
      setPasswordError("La contrasenya ha de tenir almenys 6 caràcters");
    } else {
      setPasswordError("");
    }
  };


  const handleLogin = async () => {
    let isValid = true;

    if (!isValidEmail(email)) {
      setEmailError("Correu no vàlid");
      isValid = false;
    }
    if (!isValidPassword(password)) {
      setPasswordError("Revisa la teva contrasenya");
      isValid = false;
    }

    if (!isValid) return;

    setIsLoading(true);

    try {
      await authService.login(email.trim(), password);
      await checkSession();
    } catch (error: any) {
      if (Platform.OS !== "web") {
        Alert.alert("Error de inici de sessió", error);
      }
    } finally {
      setIsLoading(false);
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
        {/* Cabecera con Botón de Atrás */}
        <View className="px-4 pt-6 pb-4">
          <TouchableOpacity
            className="w-10 h-10 rounded-xl flex items-center justify-center active:bg-gray-200"
            onPress={() => router.back()}
          >
            <ArrowLeft color="#1F2937" size={24} />
          </TouchableOpacity>
        </View>

        {/* Contenido Principal */}
        <View className="flex-1 px-6 pt-4">
          <Text className="text-3xl font-bold mb-2 text-gray-900">
            Benvingut de nou
          </Text>
          <Text className="text-gray-500 mb-8">
            Inicia sessió en la teva compte de FoodSync per continuar
          </Text>

          <View className="space-y-5">
            {/* Input: Email */}
            <View className="space-y-2">
              <Text className="font-medium text-gray-900">
                Correu electrònic
              </Text>
              <TextInput
                value={email}
                onChangeText={(text) => {
                  setEmail(text);
                  if (emailError) setEmailError("");
                }}
                onEndEditing={(e) => handleEmailEndEditing(e.nativeEvent.text)}
                placeholder="correu@email.com"
                placeholderTextColor="#9CA3AF"
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
                className="h-14 px-4 rounded-2xl bg-gray-100 text-base"
              />
              {emailError ? (
                <View className="flex-row gap-2 items-center">
                  <CircleAlert color="#ef4444" size={16} />
                  <Text className="text-red-500 text-sm">{emailError}</Text>
                </View>
              ) : null}
            </View>
            {/* Input: Password */}
            <View className="space-y-2 mt-4">
              <View className="flex-row justify-between items-center">
                <Text className="font-medium text-gray-900">Contrasenya</Text>
                <TouchableOpacity>
                  <Text
                    className="text-sm font-medium text-emerald-500"
                    onPress={() => router.push("/(auth)/forgotPassword")}
                  >
                    Has oblidat la contrasenya?
                  </Text>
                </TouchableOpacity>
              </View>

              <View className="justify-center">
                <TextInput
                  ref={passwordInputRef}
                  value={password}
                  onChangeText={(text) => {
                    setPassword(text);
                    if (passwordError) setPasswordError("");
                  }}
                  onEndEditing={(e) =>
                    handlePasswordEndEditing(e.nativeEvent.text)
                  }
                  placeholder="Introdueix la teva contrasenya"
                  placeholderTextColor="#9CA3AF"
                  secureTextEntry={!showPassword}
                  autoCapitalize="none"
                  autoCorrect={false}
                  style={{
                    lineHeight: 16,
                    fontSize: 14,
                    textAlignVertical: "center",
                  }}
                  className="h-14 pl-4 pr-12 rounded-2xl bg-gray-100 text-base leading-5"
                />

                {/* Botón del ojito*/}
                <TouchableOpacity
                  className="absolute right-4"
                  onPress={() => {
                    setShowPassword(!showPassword);
                    passwordInputRef.current?.focus();
                  }}
                >
                  {showPassword ? (
                    <EyeOff color="#9CA3AF" size={24} />
                  ) : (
                    <Eye color="#9CA3AF" size={24} />
                  )}
                </TouchableOpacity>
              </View>

              {passwordError ? (
                <View className="flex-row gap-2 items-center mt-1">
                  <CircleAlert color="#ef4444" size={16} />
                  <Text className="text-red-500 text-sm">{passwordError}</Text>
                </View>
              ) : null}
            </View>
            {/* Botón de Inicio de Sesión */}
            <TouchableOpacity
              className={`w-full h-12 rounded-xl flex items-center justify-center mt-4 shadow-sm ${
                isLoading
                  ? "bg-emerald-400"
                  : "bg-emerald-500 active:bg-emerald-600"
              }`}
              onPress={handleLogin}
              disabled={isLoading}
            >
              <Text className="text-white text-base font-bold">
                {isLoading ? "Iniciant sessió..." : "Iniciar sessió"}
              </Text>
            </TouchableOpacity>
          </View>

          {/* Enlace al Registro */}
          <View className="mt-6 flex-row justify-center items-center pb-8">
            <Text className="text-gray-500">No tens compte? </Text>
            <TouchableOpacity
              onPress={() => router.replace("/(auth)/register")}
            >
              <Text className="text-emerald-500 font-bold">Regístrat</Text>
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAwareScrollView>
    </SafeAreaView>
  );
}
