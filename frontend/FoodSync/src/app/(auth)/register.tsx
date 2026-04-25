import { router } from "expo-router";
import {
  ArrowLeft,
  Check,
  CircleAlert,
  Eye,
  EyeOff,
} from "lucide-react-native";
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

export default function RegisterScreen() {
  const [name, setName] = useState("");
  const [nameError, setNameError] = useState("");

  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState("");

  const [password, setPassword] = useState("");
  const [passwordStarted, setPasswordStarted] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [passwordError, setPasswordError] = useState("");

  const [confirmPassword, setConfirmPassword] = useState("");
  const [confirmPasswordStarted, setConfirmPasswordStarted] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [confirmPasswordError, setConfirmPasswordError] = useState("");

  /*
  function that controls if the name is in the correct format:
- between 2 and 16 characters
- no spaces at the beginning or end
  */

  const isValidName = (name: string) => {
    const trimmedName = name.trim();
    return trimmedName.length >= 2 && trimmedName.length <= 16;
  };

  const handleNameEndEditing = (text: string) => {
    if (!isValidName(text)) {
      setNameError("El nombre debe tener entre 2 y 16 caracteres");
    } else {
      setNameError("");
    }
  };

  /*
  function that controls if the email is in the correct format:
  - not longer than 128 characters
  - no spaces at the beginning or end
  - contains an "@" symbol
  - contains a "." after the "@" symbol
  --future--
  when we have the db we will chceck if the email is not already in use, and if it is, we will
  show an error message saying "This email is already in use"
  */
  const isValidEmail = (email: string) => {
    const trimmedEmail = email.trim();
    if (trimmedEmail.length === 0 || trimmedEmail.length > 128) {
      return false;
    }
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

  /*function that controls if the password is in the correct format:
- between 6 and 32 characters
- at least one uppercase letter
- at least one lowercase letter
- at least one number 
- at least one special character (!@#$%^&*()-+)
  */

  const getPasswordChecks = (password: string) => {
    const hasValidLength = password.length >= 6 && password.length <= 32;
    const hasUppercase = /[A-Z]/.test(password);
    const hasLowercase = /[a-z]/.test(password);
    const hasNumber = /\d/.test(password);
    const hasSpecialChar = /[!@#$%^&*()-+]/.test(password);

    return {
      length: hasValidLength,
      upper: hasUppercase,
      lower: hasLowercase,
      number: hasNumber,
      special: hasSpecialChar,
    };
  };

  const validatePassword = (pass: string): string => {
    const checks = getPasswordChecks(pass);

    if (!checks.length) {
      return "Debe tener entre 6 y 32 caracteres";
    }
    if (!checks.upper) {
      return "Debe contener al menos una mayúscula";
    }
    if (!checks.lower) {
      return "Debe contener al menos una minúscula";
    }
    if (!checks.number) {
      return "Debe contener un número";
    }
    if (!checks.special) {
      return "Debe contener un carácter especial (!@#$%^&*()-+)";
    }

    return "";
  };

  const handlePasswordEndEditing = (text: string) => {
    setPasswordStarted(true);
    const errorMsg = validatePassword(text);
    setPasswordError(errorMsg);
  };

  const handleConfirmPasswordEndEditing = (text: string) => {
    setConfirmPasswordStarted(true);
    if (text === "" || text !== password) {
      setConfirmPasswordError("Las contraseñas no coinciden o están vacías");
    } else {
      setConfirmPasswordError("");
    }
  };

  const checks = getPasswordChecks(password);

  const handleRegister = () => {
    let isValid = true;

    const nameValid = isValidName(name);
    if (!nameValid) {
      setNameError("El nombre debe tener entre 2 y 16 caracteres");
      isValid = false;
    } else {
      setNameError("");
    }

    const emailValid = isValidEmail(email);
    if (!emailValid) {
      setEmailError("Correo no válido");
      isValid = false;
    } else {
      setEmailError("");
    }

    const passwordErrorMsg = validatePassword(password);
    setPasswordStarted(true);
    if (passwordErrorMsg) {
      setPasswordError(passwordErrorMsg);
      isValid = false;
    } else {
      setPasswordError("");
    }

    setConfirmPasswordStarted(true);
    const passwordsMatch = password === confirmPassword && password.length > 0;
    if (!passwordsMatch) {
      setConfirmPasswordError("Las contraseñas no coinciden o están vacías");
      isValid = false;
    } else {
      setConfirmPasswordError("");
    }

    const successMessage =
      "¡Registro Exitoso! Tu cuenta ha sido creada correctamente.";
    const errorMessage =
      "Error en el registro. Por favor, corrige los errores antes de registrarte.";

    if (isValid) {
      if (Platform.OS === "web") {
        window.alert(successMessage);
      } else {
        Alert.alert(
          "¡Registro Exitoso!",
          "Tu cuenta ha sido creada correctamente.",
          [
            {
              text: "Continuar",
              onPress: () => router.replace("/(tabs)/settings"),
            },
          ],
        );
      }
    } else {
      if (Platform.OS === "web") {
        window.alert(errorMessage);
      } else {
        Alert.alert(
          "Error en el registro",
          "Por favor, corrige los errores antes de registrarte.",
        );
      }
    }
  };

  type PasswordItemProps = {
    isValid: boolean;
    text: string;
  };

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
        {/* Botón de Atrás */}
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
                  if (nameError) setNameError("");
                }}
                onEndEditing={(e) => handleNameEndEditing(e.nativeEvent.text)}
                placeholder="John Doe"
                placeholderTextColor="#9CA3AF"
                autoCapitalize="words"
                textContentType="name"
                className="h-14 px-4 rounded-2xl bg-gray-100 text-base "
              />
              {/* Muestra el error del nombre si existe */}
              {nameError ? (
                <View className="flex-row gap-2 items-center">
                  <CircleAlert color="#ef4444" size={16} />
                  <Text className="text-red-500 text-sm">{nameError}</Text>
                </View>
              ) : null}
            </View>

            {/* Input: Email */}
            <View className="space-y-2 mt-4">
              <Text className="font-medium text-gray-900">Correo</Text>
              <TextInput
                value={email}
                onChangeText={(text) => {
                  setEmail(text);
                  if (emailError && isValidEmail(text)) setEmailError("");
                }}
                onEndEditing={(e) => handleEmailEndEditing(e.nativeEvent.text)}
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
              {/* Muestra el error del correo si existe */}
              {emailError ? (
                <View className="flex-row gap-2 items-center">
                  <CircleAlert color="#ef4444" size={16} />
                  <Text className="text-red-500 text-sm">{emailError}</Text>
                </View>
              ) : null}
            </View>

            {/* Input: Password */}
            <View className="space-y-2 mt-4">
              <Text className="font-medium text-gray-900">Contraseña</Text>
              {/* Contenedor ojo */}
              <View className="justify-center align-middle">
                <TextInput
                  ref={passwordInputRef}
                  value={password}
                  onChangeText={(text) => {
                    setPassword(text);
                    if (!passwordStarted) setPasswordStarted(true);
                  }}
                  onEndEditing={(e) =>
                    handlePasswordEndEditing(e.nativeEvent.text)
                  }
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

              {passwordStarted && (
                <View className="mt-2 space-y-1">
                  <PasswordItem
                    isValid={checks.length}
                    text="Debe tener entre 6 y 32 caracteres"
                  />
                  <PasswordItem
                    isValid={checks.upper}
                    text="Al menos una letra mayúscula"
                  />
                  <PasswordItem
                    isValid={checks.lower}
                    text="Al menos una letra minúscula"
                  />
                  <PasswordItem
                    isValid={checks.number}
                    text="Al menos un número"
                  />
                  <PasswordItem
                    isValid={checks.special}
                    text="Al menos un caracter especial (!@#$%^&*()-+)"
                  />
                </View>
              )}
            </View>

            {/* Input: Confirm Password */}
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

                    if (text !== password) {
                      setConfirmPasswordError("Las contraseñas no coinciden");
                    } else {
                      setConfirmPasswordError("");
                    }
                  }}
                  onEndEditing={(e) =>
                    handleConfirmPasswordEndEditing(e.nativeEvent.text)
                  }
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

            {confirmPasswordStarted && confirmPasswordError ? (
              <View className="mt-2 space-y-1">
                <View className="flex-row items-center gap-2">
                  <CircleAlert color="#ef4444" size={16} />
                  <Text className="text-red-500 text-sm">
                    {confirmPasswordError}
                  </Text>
                </View>
              </View>
            ) : null}

            <Text className="text-xs text-gray-500 pt-2 mt-2">
              Al registrarte, aceptas nuestros Términos de Servicio y Política
              de Privacidad
            </Text>

            {/* Botón de Registro */}
            <TouchableOpacity
              className="w-full h-12 bg-emerald-500 rounded-xl flex items-center justify-center mt-6 active:bg-emerald-600"
              onPress={handleRegister}
            >
              <Text className="text-white text-base font-semibold">
                Crear una cuenta
              </Text>
            </TouchableOpacity>
          </View>

          {/* Enlace al Login */}
          <View className="mt-6 flex-row justify-center items-center pb-8">
            <Text className="text-gray-500">¿Ya tienes una cuenta? </Text>
            <TouchableOpacity onPress={() => router.replace("/(auth)/login")}>
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
