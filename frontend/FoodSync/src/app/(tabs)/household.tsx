import {
  Copy,
  Home,
  Settings,
  Users,
} from "lucide-react-native";
import React, { useState } from "react";
import {
  Alert,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import * as Clipboard from "expo-clipboard";

export default function HouseholdScreen() {
  // Datos de prueba
  const mockHouseholdData = {
    id: "1",
    name: "LIS",
    code: "123456",
    createdBy: "Usuario",
    members: [
      {
        id: "1",
        name: "Usuario",
        email: "usuario@gmail.com",
        role: "owner",
      },
      {
        id: "2",
        name: "Usuario2",
        email: "usuario2@example.com",
        role: "member",
      },
      {
        id: "3",
        name: "Usuario3",
        email: "usuario3@example.com",
        role: "member",
      },
    ],
  };

  const [currentHousehold, setCurrentHousehold] = useState<typeof mockHouseholdData | null>(null);
  
  const [isJoining, setIsJoining] = useState(false);
  const [inviteCode, setInviteCode] = useState("");

  const handleVerifyCode = () => {
    const cleanCode = inviteCode.trim().toUpperCase();

    if (cleanCode === mockHouseholdData.code) {
      setCurrentHousehold(mockHouseholdData);
      setIsJoining(false);
      setInviteCode("");
      if (Platform.OS === "web") {
        window.alert("¡Código correcto!");
      } else {
        Alert.alert("¡Código correcto!", `Bienvenido a ${mockHouseholdData.name}`);
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


// function for copy the code to clipboard
  const copyInviteCode = async () => {
    if (currentHousehold?.code) {
      await Clipboard.setStringAsync(currentHousehold.code); 
      
      Alert.alert(
        "Código copiado",
        `El código ${currentHousehold.code} se ha copiado al portapapeles.`,
      );
    }
  };


  if (!currentHousehold) {
    return (
      <SafeAreaView className="flex-1 bg-[#F8FAF8] justify-center px-6">
        <View className="items-center w-full">
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
                Únete a un hogar existente con un código o crea uno nuevo para compartir tu inventario.
              </Text>

              <TouchableOpacity
                className="w-full bg-emerald-500 py-4 rounded-2xl active:bg-emerald-600 mb-4 shadow-sm"
                onPress={() => setIsJoining(true)}
              >
                <Text className="text-white font-bold text-center text-lg">Unirse con un código</Text>
              </TouchableOpacity>

              <TouchableOpacity 
                className="w-full bg-white border-2 border-emerald-500 py-4 rounded-2xl active:bg-emerald-50"
                onPress={() => Alert.alert("Próximamente", "La creación de hogares estará lista pronto.")}
              >
                <Text className="text-emerald-600 font-bold text-center text-lg">Crear nuevo hogar</Text>
              </TouchableOpacity>
            </>
          ) : (
              //joining state
            <View className="w-full mt-2">
              <Text className="text-gray-700 font-semibold mb-4 text-center">
                Introduce el código de invitación:
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
                  inviteCode.length > 0 ? "bg-emerald-500 active:bg-emerald-600" : "bg-emerald-400"
                }`}
                onPress={handleVerifyCode}
                disabled={inviteCode.length === 0}
              >
                <Text className="text-white font-bold text-center text-lg">Validar código</Text>
              </TouchableOpacity>

              <TouchableOpacity
                className="w-full py-4 rounded-2xl active:bg-gray-100"
                onPress={() => {
                  setIsJoining(false);
                  setInviteCode("");
                }}
              >
                <Text className="text-gray-500 font-bold text-center text-lg">Volver atrás</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
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
        {/* Tarjeta del Hogar */}
        <View className="p-6 bg-emerald-50 border border-emerald-100 rounded-3xl mb-6 shadow-sm">
          <View className="flex-row items-center gap-4 mb-5">
            <View className="w-14 h-14 bg-emerald-500 rounded-2xl flex items-center justify-center shadow-sm">
              <Users color="white" size={28} />
            </View>
            <View>
              <Text className="font-bold text-xl text-gray-900">{currentHousehold.name}</Text>
              <Text className="text-emerald-600 font-medium">{currentHousehold.members.length} miembros</Text>
            </View>
          </View>

          <View className="bg-white/90 rounded-2xl p-4 mb-3 flex-row items-center justify-between border border-emerald-50">
            <View>
              <Text className="text-xs text-gray-500 mb-1 font-medium">Código de invitación</Text>
              <Text className="font-bold text-xl tracking-widest text-gray-900">{currentHousehold.code}</Text>
            </View>
            <TouchableOpacity
              className="flex-row items-center bg-gray-100 px-3 py-2 rounded-xl active:bg-gray-200"
              onPress={copyInviteCode}
            >
              <Copy color="#4B5563" size={16}  />
              <Text className="font-semibold text-gray-700 ml-2">Copiar</Text>
            </TouchableOpacity>
          </View>

          <Text className="text-xs text-gray-500 text-center mt-1">
            Comparte este código para invitar a familiares a tu hogar
          </Text>
        </View>

      </ScrollView>
    </SafeAreaView>
  );
}