import { router } from "expo-router";
import {
  ArrowLeft,
  Eye,
  EyeOff,
} from "lucide-react-native";
import React, { useRef, useState } from "react";
import { Text, TextInput, TouchableOpacity, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-aware-scroll-view";
import { SafeAreaView } from "react-native-safe-area-context";

export default function RegisterScreen() {
  const [name, setName] = useState("");

  const [email, setEmail] = useState("");

  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const [confirmPassword, setConfirmPassword] = useState("");
  const [confirmPasswordStarted, setConfirmPasswordStarted] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);


    const passwordInputRef = useRef<TextInput>(null);
  const confirmPasswordInputRef = useRef<TextInput>(null);


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
            Crear una cuenta
          </Text>
          <Text className="text-gray-500 mb-8">
            Comienza a reducir el desperdicio de alimentos hoy
          </Text>

          <View className="space-y-5">
            {/* Input: Full Name */}
            <View className="space-y-2">
              <Text className="font-medium text-gray-900">Nombre completo</Text>
              <TextInput
                value={name}
                onChangeText={(text) => {
                  setName(text);

                }}
                placeholder="John Doe"
                placeholderTextColor="#9CA3AF"
                className="h-14 px-4 rounded-2xl bg-gray-100 text-base "
              />
            </View>

            {/* Input: Email */}
            <View className="space-y-2 mt-4">
              <Text className="font-medium text-gray-900">Correo</Text>
              <TextInput
                value={email}
                onChangeText={setEmail}
                placeholder="correo@email.com"
                placeholderTextColor="#9CA3AF"
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
                textContentType="emailAddress"
                autoComplete="email"
                importantForAutofill="yes"
                className="h-14 px-4 rounded-2xl bg-gray-100 text-base"
              />
            </View>

            {/* Input: Password */}
            <View className="space-y-2 mt-4">
              <Text className="font-medium text-gray-900">Contraseña</Text>
              {/* Contenedor ojo */}
              <View className="justify-center align-middle">
                <TextInput
                  value={password}
                  onChangeText={(text) => {
                    setPassword(text);
                  }}
                  placeholder="Crea una contraseña"
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

                {/* Botón del ojito */}
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
            </View>

            <View className="space-y-2 mt-4">
              <Text className="font-medium text-gray-900">
                Confirma tu contraseña
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
                  placeholder="Repite tu contraseña"
                  placeholderTextColor="#9CA3AF"
                  secureTextEntry={!showConfirmPassword}
                  autoCapitalize="none"
                  autoCorrect={false}
                  style={{
                    lineHeight: 16,
                    fontSize: 14,
                    textAlignVertical: "center",
                  }}
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
            <Text className="text-xs text-gray-500 pt-2 mt-2">
              Al registrarte, aceptas nuestros Términos de Servicio y Política
              de Privacidad
            </Text>

            {/* Botón de Registro */}
            <TouchableOpacity
              className="w-full h-12 bg-emerald-500 rounded-xl flex items-center justify-center mt-6 active:bg-emerald-600"
            >
              <Text className="text-white text-base font-semibold">
                Crear una cuenta
              </Text>
            </TouchableOpacity>
          </View>

          {/* Enlace al Login */}
          <View className="mt-6 flex-row justify-center items-center pb-8">
            <Text className="text-gray-500">Ya tienes una cuenta? </Text>
            <TouchableOpacity >
              <Text className="text-emerald-500 font-medium">
                Iniciar sesión
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAwareScrollView>
    </SafeAreaView>
  );
}
