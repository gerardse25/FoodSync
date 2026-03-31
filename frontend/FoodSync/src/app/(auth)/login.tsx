import { router } from "expo-router";
import { ArrowLeft, Eye, EyeOff } from "lucide-react-native";
import React, { useRef, useState } from "react";
import { Text, TextInput, TouchableOpacity, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-aware-scroll-view";
import { SafeAreaView } from "react-native-safe-area-context";

export default function LoginScreen() {
  const [email, setEmail] = useState("");

  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const passwordInputRef = useRef<TextInput>(null);

  // Aquí definimos nuestro usuario para simular la autenticación. En una app real, esto vendría de una base de datos o servicio de autenticación.
  const usersDB = [
    {
      email: "usuario@gmail.com",
      password: "Usuario123!",
    },
  ];

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
            Bienvenido de nuevo
          </Text>
          <Text className="text-gray-500 mb-8">
            Inicia sesión en tu cuenta de FoodSync para continuar
          </Text>

          <View className="space-y-5">
            {/* Input: Email */}
            <View className="space-y-2">
              <Text className="font-medium text-gray-900">
                Correo electrónico
              </Text>
              <TextInput
                value={email}
                onChangeText={(text) => {
                  setEmail(text);
                }}
                placeholder="correo@email.com"
                placeholderTextColor="#9CA3AF"
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
                className="h-14 px-4 rounded-2xl bg-gray-100 text-base"
              />
            </View>

            {/* Input: Password */}
            <View className="space-y-2 mt-4">
              <View className="flex-row justify-between items-center">
                <Text className="font-medium text-gray-900">Contraseña</Text>
                <TouchableOpacity>
                  <Text className="text-sm font-medium text-emerald-500">
                    ¿Olvidaste tu contraseña?
                  </Text>
                </TouchableOpacity>
              </View>

              <View className="justify-center">
                <TextInput
                  ref={passwordInputRef}
                  value={password}
                  onChangeText={(text) => {
                    setPassword(text);
                  }}
                  placeholder="Introduce tu contraseña"
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

            </View>

            {/* Botón de Inicio de Sesión */}
            <TouchableOpacity
              className="w-full h-12 bg-emerald-500 rounded-xl flex items-center justify-center mt-8 active:bg-emerald-600 shadow-sm"
            >
              <Text className="text-white text-base font-semibold">
                Iniciar sesión
              </Text>
            </TouchableOpacity>
          </View>

          {/* Enlace al Registro */}
          <View className="mt-6 flex-row justify-center items-center pb-8">
            <Text className="text-gray-500">¿No tienes cuenta? </Text>
            <TouchableOpacity onPress={() => router.push("/(auth)/register")}>
              <Text className="text-emerald-500 font-bold">Regístrate</Text>
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAwareScrollView>
    </SafeAreaView>
  );
}
