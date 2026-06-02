import { router } from "expo-router";
import { ArrowLeft, Lock } from "lucide-react-native";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { authService } from "../../services/authService";

export default function ChangePasswordScreen() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleUpdatePassword = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      Alert.alert("Camps buits", "Si us plau, omple tots els camps.");
      return;
    }

    if (newPassword.length < 6 || newPassword.length > 32) {
      Alert.alert(
        "Contrasenya invàlida",
        "La nova contrasenya ha de tenir entre 6 i 32 caràcters.",
      );
      return;
    }

    if (/\s/.test(newPassword)) {
      Alert.alert(
        "Contrasenya invàlida",
        "La contrasenya no pot contenir espais interns.",
      );
      return;
    }

    if (newPassword !== confirmPassword) {
      Alert.alert(
        "Error de coincidència",
        "La nova contrasenya i la confirmació no coincideixen.",
      );
      return;
    }

    setIsSubmitting(true);
    try {
      await authService.changePassword(currentPassword, newPassword);
      Alert.alert("¡Èxit!", "La contrasenya s'ha actualitzat correctament.", [
        { text: "D'acord", onPress: () => router.back() },
      ]);
    } catch (error: any) {
      Alert.alert("Error", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <SafeAreaView edges={["top"]} className="flex-1 bg-[#F8FAF8]">
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <View className="flex-row items-center px-6 py-4 border-b border-gray-100 bg-white">
          <TouchableOpacity onPress={() => router.back()} className="p-2 -ml-2">
            <ArrowLeft color="#1F2937" size={24} />
          </TouchableOpacity>
          <Text className="text-xl font-bold text-gray-900 ml-2">
            Canviar contrasenya
          </Text>
        </View>

        <ScrollView
          className="flex-1 px-6 pt-6"
          contentContainerStyle={{ paddingBottom: 60 }}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          <Text className="text-sm text-gray-500 font-medium mb-6">
            Introdueix la teva contrasenya actual i la nova per fer
            l&apos;actualització de seguretat.
          </Text>

          <View className="space-y-5">
            {/* Contrasenya Actual */}
            <View className="space-y-2">
              <Text className="font-bold text-gray-700 text-sm">
                Contrasenya actual
              </Text>
              <View className="h-14 px-4 rounded-2xl bg-white border border-gray-200 flex-row items-center">
                <Lock color="#9CA3AF" size={20} />
                <TextInput
                  className="flex-1 text-base text-gray-900 ml-2 h-full"
                  placeholder="••••••••"
                  secureTextEntry
                  value={currentPassword}
                  onChangeText={setCurrentPassword}
                  editable={!isSubmitting}
                />
              </View>
            </View>

            {/* Nova Contrasenya */}
            <View className="space-y-2">
              <Text className="font-bold text-gray-700 text-sm">
                Nova contrasenya
              </Text>
              <View className="h-14 px-4 rounded-2xl bg-white border border-gray-200 flex-row items-center">
                <Lock color="#9CA3AF" size={20} />
                <TextInput
                  className="flex-1 text-base text-gray-900 ml-2 h-full"
                  placeholder="Mínim 6 caràcters"
                  secureTextEntry
                  value={newPassword}
                  onChangeText={setNewPassword}
                  editable={isSubmitting}
                />
              </View>
            </View>

            {/* Confirmar Nova Contrasenya */}
            <View className="space-y-2">
              <Text className="font-bold text-gray-700 text-sm">
                Confirmar nova contrasenya
              </Text>
              <View className="h-14 px-4 rounded-2xl bg-white border border-gray-200 flex-row items-center">
                <Lock color="#9CA3AF" size={20} />
                <TextInput
                  className="flex-1 text-base text-gray-900 ml-2 h-full"
                  placeholder="Repeteix la contrasenya"
                  secureTextEntry
                  value={confirmPassword}
                  onChangeText={setConfirmPassword}
                  editable={isSubmitting}
                />
              </View>
            </View>
          </View>

          {/* Botó d'acció */}
          <TouchableOpacity
            className="w-full h-14 bg-emerald-500 rounded-2xl items-center justify-center shadow-sm active:bg-emerald-600 mt-10"
            onPress={handleUpdatePassword}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text className="text-white font-bold text-lg">
                Actualitzar contrasenya
              </Text>
            )}
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
