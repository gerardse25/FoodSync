import { router, useLocalSearchParams } from "expo-router";
import {
  ArrowLeft,
  Check,
  CircleAlert,
  Eye,
  EyeOff,
} from "lucide-react-native";
import React, { useRef, useState } from "react";
import { Alert, Text, TextInput, TouchableOpacity, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-aware-scroll-view";
import { SafeAreaView } from "react-native-safe-area-context";
import { authService } from "../../services/authService";

export default function ResetPasswordScreen() {
  const { token } = useLocalSearchParams();

  const [password, setPassword] = useState("");
  const [passwordStarted, setPasswordStarted] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const [confirmPassword, setConfirmPassword] = useState("");
  const [confirmPasswordStarted, setConfirmPasswordStarted] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [isLoading, setIsLoading] = useState(false);

  const passwordInputRef = useRef<TextInput>(null);
  const confirmPasswordInputRef = useRef<TextInput>(null);

  const getPasswordChecks = (pass: string) => {
    return {
      length: pass.length >= 6 && pass.length <= 32,
      upper: /[A-Z]/.test(pass),
      lower: /[a-z]/.test(pass),
      number: /\d/.test(pass),
      special: /[!@#$%^&*()-+]/.test(pass),
    };
  };

  const checks = getPasswordChecks(password);
  const isPasswordValid =
    checks.length &&
    checks.upper &&
    checks.lower &&
    checks.number &&
    checks.special;

  const passwordsMatch = password === confirmPassword;
  const showConfirmError =
    confirmPasswordStarted && confirmPassword.length > 0 && !passwordsMatch;

  const handleReset = async () => {
    if (isLoading) return;

    setPasswordStarted(true);
    setConfirmPasswordStarted(true);

    if (!isPasswordValid) {
      Alert.alert(
        "Contrasenya invàlida",
        "Revisa els requisits de la contrasenya.",
      );
      return;
    }

    if (!passwordsMatch) {
      Alert.alert("Error", "Les contrasenyes no coincideixen.");
      return;
    }

    try {
      setIsLoading(true);
      await authService.resetPassword(token as string, password);

      Alert.alert(
        "¡Èxit!",
        "La teva contrasenya s'ha restablert correctament. Ara pots iniciar sessió.",
        [
          {
            text: "Anar a Login",
            onPress: () => router.replace("/(auth)/login"),
          },
        ],
      );
    } catch (error: any) {
      Alert.alert("Error", error);
    } finally {
      setIsLoading(false);
    }
  };

  type PasswordItemProps = {
    isValid: boolean;
    text: string;
  };

  // Componente visual de la lista (Verde/Rojo)
  const PasswordItem = ({ isValid, text }: PasswordItemProps) => {
    const Icon = isValid ? Check : CircleAlert;
    const iconColor = isValid ? "#22c55e" : "#ef4444";
    const textColor = isValid ? "#1eb455" : "#ef4444";

    return (
      <View className="flex-row items-center gap-2">
        <Icon color={iconColor} size={16} />
        <Text style={{ color: textColor }} className="text-sm">
          {text}
        </Text>
      </View>
    );
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
        {/* Botón de Atrás */}
        <View className="px-4 pt-6 pb-4">
          <TouchableOpacity
            className="w-10 h-10 rounded-xl flex items-center justify-center active:bg-gray-200"
            onPress={() => router.replace("/(auth)/login")}
          >
            <ArrowLeft color="#1F2937" size={24} />
          </TouchableOpacity>
        </View>

        {/* Contenido Principal */}
        <View className="flex-1 px-6 pt-4">
          <Text className="text-3xl font-bold mb-2 text-gray-900">
            Nova contrasenya
          </Text>
          <Text className="text-gray-500 mb-8">
            Crea una contrasenya segura per restablir el teu compte.
          </Text>

          <View className="space-y-5">
            {/* Input: Password */}
            <View className="space-y-2 mt-4">
              <Text className="font-medium text-gray-900">
                Nova contrasenya
              </Text>
              <View className="justify-center align-middle">
                <TextInput
                  ref={passwordInputRef}
                  value={password}
                  onChangeText={(text) => {
                    setPassword(text);
                    if (!passwordStarted) setPasswordStarted(true);
                  }}
                  placeholder="Introdueix la teva nova contrasenya"
                  placeholderTextColor="#9CA3AF"
                  secureTextEntry={!showPassword}
                  autoCapitalize="none"
                  autoCorrect={false}
                  className="h-14 pl-4 pr-12 rounded-2xl bg-gray-100 text-base leading-5"
                />

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

              {/* Lista interactiva de validación */}
              {passwordStarted && (
                <View className="mt-2 space-y-1">
                  <PasswordItem
                    isValid={checks.length}
                    text="Ha de tenir entre 6 i 32 caràcters"
                  />
                  <PasswordItem
                    isValid={checks.upper}
                    text="Almenys una lletra majúscula"
                  />
                  <PasswordItem
                    isValid={checks.lower}
                    text="Almenys una lletra minúscula"
                  />
                  <PasswordItem
                    isValid={checks.number}
                    text="Almenys un número"
                  />
                  <PasswordItem
                    isValid={checks.special}
                    text="Almenys un caracter especial (!@#$%^&*()-+)"
                  />
                </View>
              )}
            </View>

            {/* Input: Confirm Password */}
            <View className="space-y-2 mt-4">
              <Text className="font-medium text-gray-900">
                Confirma la nova contrasenya
              </Text>
              <View className="justify-center align-middle">
                <TextInput
                  ref={confirmPasswordInputRef}
                  value={confirmPassword}
                  onChangeText={(text) => {
                    setConfirmPassword(text);
                    if (!confirmPasswordStarted)
                      setConfirmPasswordStarted(true);
                  }}
                  placeholder="Repeteix la teva contrasenya"
                  placeholderTextColor="#9CA3AF"
                  secureTextEntry={!showConfirmPassword}
                  autoCapitalize="none"
                  autoCorrect={false}
                  className="h-14 pl-4 pr-12 rounded-2xl bg-gray-100 text-base leading-5"
                />
                <TouchableOpacity
                  className="absolute right-4"
                  onPress={() => {
                    setShowConfirmPassword(!showConfirmPassword);
                    confirmPasswordInputRef.current?.focus();
                  }}
                >
                  {showConfirmPassword ? (
                    <EyeOff color="#9CA3AF" size={24} />
                  ) : (
                    <Eye color="#9CA3AF" size={24} />
                  )}
                </TouchableOpacity>
              </View>
            </View>

            {/* Error en tiempo real de contraseñas no coincidentes */}
            {showConfirmError && (
              <View className="mt-2 space-y-1">
                <View className="flex-row items-center gap-2">
                  <CircleAlert color="#ef4444" size={16} />
                  <Text className="text-red-500 text-sm">
                    Les contrasenyes no coincideixen
                  </Text>
                </View>
              </View>
            )}

            {/* Botón de Restablecer */}
            <TouchableOpacity
              className={`w-full h-12 rounded-xl flex items-center justify-center mt-8 shadow-sm ${
                isLoading || !isPasswordValid || !passwordsMatch
                  ? "bg-emerald-300"
                  : "bg-emerald-500 active:bg-emerald-600"
              }`}
              onPress={handleReset}
              disabled={isLoading || !isPasswordValid || !passwordsMatch}
            >
              <Text className="text-white text-base font-bold">
                {isLoading ? "Restablint..." : "Restablir contrasenya"}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAwareScrollView>
    </SafeAreaView>
  );
}
