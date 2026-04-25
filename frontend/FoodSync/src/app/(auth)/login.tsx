import { router } from "expo-router";
import { ArrowLeft, CircleAlert, Eye, EyeOff } from "lucide-react-native";
import React, { useRef, useState } from "react";
import {
  Text,
  TextInput,
  TouchableOpacity,
  View,
  Alert,
  Platform,
} from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-aware-scroll-view";
import { SafeAreaView } from "react-native-safe-area-context";

export default function LoginScreen() {
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState("");

  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [passwordError, setPasswordError] = useState("");

  const passwordInputRef = useRef<TextInput>(null);

  // Aquí definimos nuestro usuario para simular la autenticación. En una app real, esto vendría de una base de datos o servicio de autenticación.
  const usersDB = [
    {
      email: "usuario@gmail.com",
      password: "Usuario123!",
    },
  ];

  /**
   * Validación de formato de email
   */
  const isValidEmail = (email: string) => {
    const trimmedEmail = email.trim();
    if (trimmedEmail.length > 128) return false;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(trimmedEmail);
  };

  const handleEmailEndEditing = (text: string) => {
    if (!isValidEmail(text)) {
      setEmailError("Correo no válido");
    } else {
      setEmailError("");
    }
  };

  /*
   * Validación de contraseña (mínimo 6 caracteres para login)
   */
  const isValidPassword = (password: string) => {
    return password.length >= 6;
  };

  const handlePasswordEndEditing = (text: string) => {
    if (!isValidPassword(text)) {
      setPasswordError("La contraseña debe tener al menos 6 caracteres");
    } else {
      setPasswordError("");
    }
  };

  /**
   * Lógica de Inicio de Sesión
   */
  const handleLogin = () => {
    let isValid = true;

    // Validar Email
    if (!isValidEmail(email)) {
      setEmailError("Correo no válido");
      isValid = false;
    } else {
      setEmailError("");
    }

    // Validar Contraseña (mínimo 6 caracteres para login)
    if (!isValidPassword(password)) {
      setPasswordError("La contraseña debe tener al menos 6 caracteres");
      isValid = false;
    } else {
      setPasswordError("");
    }

    const messageInValid =
      "Por favor, revisa los campos. Asegúrate de que el correo y la contraseña sean correctos.";

    // Si los datos no son válidos, mostramos un alert de error
    if (!isValid) {
      if (Platform.OS === "web") {
        window.alert(messageInValid);
      } else {
        Alert.alert(
          "Error en los datos",
          messageInValid,
          [
            {
              text: "OK",
            },
          ],
          { cancelable: false },
        );
      }
      return; // Detener la ejecución de la función si hay errores
    } else {
      // Si los datos son válidos, procedemos a verificar el usuario
      const userFound = usersDB.find(
        (user) => user.email === email.trim() && user.password === password,
      );

      const messageLogin = "Bienvenido a FoodSync";
      const messageIncorrectLogin = "Correo o contraseña incorrectos";

      if (userFound) {
        if (Platform.OS === "web") {
          window.alert(messageLogin);
          router.replace("/(tabs)/settings");
        } else {
          // Si el usuario está en la base de datos, mostramos el alert de éxito
          Alert.alert(
            "Inicio de sesión exitoso",
            messageLogin,
            [
              {
                text: "OK",
                onPress: () => router.replace("/(tabs)/household"),
              },
            ],
            { cancelable: false },
          );
        }
      } else {
        if (Platform.OS === "web") {
          window.alert(messageIncorrectLogin);
        } else {
          // Si no se encuentra el usuario, mostramos el alert de error
          Alert.alert(
            "Error al hacer inicio de sesión",
            messageIncorrectLogin,
            [
              {
                text: "OK",
              },
            ],
            { cancelable: false },
          );
        }
      }
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
                  if (emailError) setEmailError("");
                }}
                onEndEditing={(e) => handleEmailEndEditing(e.nativeEvent.text)}
                placeholder="correo@email.com"
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
                    if (passwordError) setPasswordError("");
                  }}
                  onEndEditing={(e) =>
                    handlePasswordEndEditing(e.nativeEvent.text)
                  }
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

              {passwordError ? (
                <View className="flex-row gap-2 items-center mt-1">
                  <CircleAlert color="#ef4444" size={16} />
                  <Text className="text-red-500 text-sm">{passwordError}</Text>
                </View>
              ) : null}
            </View>

            {/* Botón de Inicio de Sesión */}
            <TouchableOpacity
              className="w-full h-12 bg-emerald-500 rounded-xl flex items-center justify-center mt-8 active:bg-emerald-600 shadow-sm"
              onPress={handleLogin}
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
