import { Home, Settings } from "lucide-react-native";
import React, { useState } from "react";
import {
  Alert,
  Platform,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

// Mock data
const mockHouse = {
  id: "1",
  name: "Familia LIS",
  code: "123456",
};

export default function HouseholdScreen() {
  const [currentHousehold, setCurrentHousehold] = useState<
    typeof mockHouse | null
  >(null);

  const [isJoining, setIsJoining] = useState(false);
  const [inviteCode, setInviteCode] = useState("");

  // function for verify the code
  const handleVerifyCode = () => {
    const cleanCode = inviteCode.trim().toUpperCase();

    if (cleanCode === mockHouse.code) {
      setCurrentHousehold(mockHouse);
      setIsJoining(false);
      setInviteCode("");

      if (Platform.OS === "web") {
        window.alert("¡Código correcto!");
      } else {
        Alert.alert("¡Código correcto!", `Bienvenido a ${mockHouse.name}`);
      }
    } else {
      if (Platform.OS === "web") {
        window.alert("Código incorrecto.");
      } else {
        Alert.alert(
          "Código incorrecto",
          "El código introducido no es válido. Comprueba que esté bien escrito.",
        );
      }
    }
  };

  if (!currentHousehold) {
    return (
      <SafeAreaView className="flex-1 bg-[#F8FAF8] justify-center ">
        <View className="px-6 pt-6 pb-4 bg-white border-b border-gray-200 flex-row items-center justify-between">
          <Text className="text-2xl font-bold text-gray-900">Hogar</Text>
        </View>
        <ScrollView
          className="flex-1 px-6 "
          contentContainerStyle={{
            flexGrow: 1,
            justifyContent: "center",
            alignItems: "center",
            paddingHorizontal: 24,
          }}
          showsVerticalScrollIndicator={false}
        >
          <View className="items-center w-full ">
            <View className="w-24 h-24 bg-emerald-100 rounded-full flex items-center justify-center mb-6">
              <Home color="#10B981" size={48} />
            </View>

            <Text className="text-2xl font-bold text-gray-900 mb-3 text-center">
              Aún no tienes un hogar
            </Text>

            {!isJoining ? (
              //Initial state: options to join or create
              <>
                <Text className="text-gray-500 text-center mb-10 text-base px-4">
                  Únete a un hogar existente con un código de invitación o crea
                  uno nuevo para empezar a organizarte.
                </Text>

                <TouchableOpacity
                  className="w-full bg-emerald-500 py-4 rounded-2xl active:bg-emerald-600 mb-4 shadow-sm"
                  onPress={() => setIsJoining(true)}
                >
                  <Text className="text-white font-bold text-center text-lg">
                    Unirse con un código
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity className="w-full bg-white border-2 border-emerald-500 py-4 rounded-2xl active:bg-emerald-50">
                  <Text className="text-emerald-600 font-bold text-center text-lg">
                    Crear nuevo hogar
                  </Text>
                </TouchableOpacity>
              </>
            ) : (
              //joining state
              <View className="w-full mt-2">
                <Text className="text-gray-700 font-semibold mb-4 ml-1 text-center">
                  Introduce el código de 6 caracteres:
                </Text>

                <TextInput
                  className="w-full bg-white border border-gray-200 rounded-2xl px-4 py-4 text-xl mb-6 text-center tracking-widest uppercase font-bold text-gray-900 shadow-sm"
                  placeholder="Ej: 123456"
                  placeholderTextColor="#9CA3AF"
                  value={inviteCode}
                  onChangeText={setInviteCode}
                  autoCapitalize="characters"
                  autoCorrect={false}
                  maxLength={6}
                />

                <TouchableOpacity
                  className={`w-full py-4 rounded-2xl mb-3 shadow-sm ${
                    inviteCode.length > 0
                      ? "bg-emerald-500 active:bg-emerald-600"
                      : "bg-emerald-400"
                  }`}
                  onPress={handleVerifyCode}
                  disabled={inviteCode.length === 0}
                >
                  <Text className="text-white font-bold text-center text-lg">
                    Confirmar
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  className="w-full bg-white border-2 border-emerald-500 py-4 rounded-2xl active:bg-emerald-50"
                  onPress={() => {
                    setIsJoining(false);
                    setInviteCode("");
                  }}
                >
                  <Text className="text-gray-500 font-bold text-center text-lg">
                    Volver atrás
                  </Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }
  // Main household screen when user is part of a household
  return (
    <SafeAreaView className="flex-1 bg-[#F8FAF8]">
      {/* header */}
      <View className="px-6 pt-6 pb-4 bg-white border-b border-gray-200 flex-row items-center justify-between">
        <Text className="text-2xl font-bold text-gray-900">Hogar</Text>
      </View>

      <ScrollView
        className="flex-1"
        contentContainerStyle={{ padding: 24, paddingBottom: 40 }}
        showsVerticalScrollIndicator={false}
      >
        <Text className="text-2xl font-bold text-gray-900 mb-2">
          Bienvenido a {currentHousehold.name}
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}
