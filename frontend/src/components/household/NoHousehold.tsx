import { Home } from "lucide-react-native";
import React, { useState } from "react";
import { Alert, Text, TextInput, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { homeService } from "../../services/homeService";

interface NoHouseholdProps {
  onSuccess: () => void;
}

export default function NoHousehold({ onSuccess }: NoHouseholdProps) {
  const [viewState, setViewState] = useState<"menu" | "joining" | "creating">(
    "menu",
  );
  const [inviteCode, setInviteCode] = useState("");
  const [homeName, setHomeName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleCreateHome = async () => {
    if (homeName.trim().length < 2) {
      Alert.alert("Error", "El nom ha de tenir almenys 2 caràcters.");
      return;
    }
    setIsSubmitting(true);
    try {
      await homeService.createHome(homeName.trim());
      onSuccess();
    } catch (error: any) {
      Alert.alert("Error al crear", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleJoinHome = async () => {
    if (inviteCode.trim().length === 0) return;
    setIsSubmitting(true);
    try {
      await homeService.joinHome(inviteCode.trim().toUpperCase());
      onSuccess();
    } catch (error: any) {
      Alert.alert("Codi incorrecte", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-[#F8FAF8] justify-center px-6">
      <View className="items-center w-full">
        <View className="w-24 h-24 bg-emerald-100 rounded-full flex items-center justify-center mb-6">
          <Home color="#10B981" size={48} />
        </View>

        <Text className="text-2xl font-bold text-gray-900 mb-3 text-center">
          Gestiona la teva llar
        </Text>

        {viewState === "menu" && (
          <>
            <Text className="text-gray-500 text-center mb-10 text-base px-4">
              Uneix-te a una llar existent amb un codi o crea una nova per
              compartir el teu inventari.
            </Text>
            <TouchableOpacity
              className="w-full bg-emerald-500 py-4 rounded-2xl active:bg-emerald-600 mb-4 shadow-sm"
              onPress={() => setViewState("joining")}
            >
              <Text className="text-white font-bold text-center text-lg">
                Unirse amb un codi
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              className="w-full bg-white border-2 border-emerald-500 py-4 rounded-2xl active:bg-emerald-50"
              onPress={() => setViewState("creating")}
            >
              <Text className="text-emerald-600 font-bold text-center text-lg">
                Crear nova llar
              </Text>
            </TouchableOpacity>
          </>
        )}

        {viewState === "joining" && (
          <View className="w-full mt-2">
            <Text className="text-gray-700 font-semibold mb-4 text-center">
              Introdueix el codi d&apos;invitació:
            </Text>
            <TextInput
              className="w-full bg-white border border-gray-200 rounded-2xl px-4 py-4 text-xl mb-6 text-center tracking-widest uppercase font-bold text-gray-900 shadow-sm"
              placeholder="Ej: A1B2C3D"
              placeholderTextColor="#9CA3AF"
              value={inviteCode}
              onChangeText={setInviteCode}
              autoCapitalize="characters"
              autoCorrect={false}
              maxLength={8}
              editable={!isSubmitting}
            />
            <TouchableOpacity
              className={`w-full py-4 rounded-2xl mb-3 shadow-sm ${inviteCode.length > 0 && !isSubmitting ? "bg-emerald-500 active:bg-emerald-600" : "bg-emerald-300"}`}
              onPress={handleJoinHome}
              disabled={inviteCode.length === 0 || isSubmitting}
            >
              <Text className="text-white font-bold text-center text-lg">
                {isSubmitting ? "Verificant..." : "Confirmar i entrar"}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              className="w-full py-4 rounded-2xl active:bg-gray-100"
              onPress={() => {
                setViewState("menu");
                setInviteCode("");
              }}
              disabled={isSubmitting}
            >
              <Text className="text-gray-500 font-bold text-center text-lg">
                Tornar enrere
              </Text>
            </TouchableOpacity>
          </View>
        )}

        {viewState === "creating" && (
          <View className="w-full mt-2">
            <Text className="text-gray-700 font-semibold mb-4 text-center">
              Com s&apos;anomenarà la teva llar?
            </Text>
            <TextInput
              className="w-full bg-white border border-gray-200 rounded-2xl px-4 py-4 text-lg mb-6 text-center font-bold text-gray-900 shadow-sm"
              placeholder="Ej: Familia López"
              placeholderTextColor="#9CA3AF"
              value={homeName}
              onChangeText={setHomeName}
              autoCapitalize="words"
              editable={!isSubmitting}
            />
            <TouchableOpacity
              className={`w-full py-4 rounded-2xl mb-3 shadow-sm ${homeName.length >= 2 && !isSubmitting ? "bg-emerald-500 active:bg-emerald-600" : "bg-emerald-300"}`}
              onPress={handleCreateHome}
              disabled={homeName.length < 2 || isSubmitting}
            >
              <Text className="text-white font-bold text-center text-lg">
                {isSubmitting ? "Creant..." : "Crear llar"}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              className="w-full py-4 rounded-2xl active:bg-gray-100"
              onPress={() => {
                setViewState("menu");
                setHomeName("");
              }}
              disabled={isSubmitting}
            >
              <Text className="text-gray-500 font-bold text-center text-lg">
                Tornar enrere
              </Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </SafeAreaView>
  );
}
