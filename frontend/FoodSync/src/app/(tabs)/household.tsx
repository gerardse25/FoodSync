import { Copy, Crown, Home, Users } from "lucide-react-native";
import React, { useState } from "react";
import {
  Alert,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  Platform,
  Image,
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
        avatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e",
      },
      {
        id: "2",
        name: "Usuario2",
        email: "usuario2@example.com",
        role: "member",
        avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330",
      },
      {
        id: "3",
        name: "Usuario3",
        email: "usuario3@example.com",
        role: "member",
        avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e",
      },
    ],
  };

  const [currentHousehold, setCurrentHousehold] = useState<any>(null);
  const [isJoining, setIsJoining] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [inviteCode, setInviteCode] = useState("");
  const [householdName, setHouseholdName] = useState("");

  // function for generate a random code
  const generateRandomCode = () => {
    return Math.floor(100000 + Math.random() * 900000).toString();
  };

  const handleCreateHousehold = () => {
    if (householdName.trim().length < 2) {
      Alert.alert(
        "Nombre muy corto",
        "El nombre del hogar debe tener al menos 2 caracteres.",
      );
      return;
    } else if (householdName.trim().length > 20) {
      Alert.alert(
        "Nombre muy largo",
        "El nombre del hogar no puede exceder los 20 caracteres.",
      );
      return;
    }

    // simulation for create a new household
    const newHousehold = {
      id: Date.now().toString(),
      name: householdName.trim(),
      code: generateRandomCode(),
      createdBy: "Usuario",
      members: [
        {
          id: "1",
          name: "Usuario (Tú)",
          email: "usuario@gmail.com",
          role: "owner",
          avatar:
            "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e",
        },
      ],
    };

    setCurrentHousehold(newHousehold);
    setIsCreating(false);
    setHouseholdName("");

    const message = `¡Hogar "${newHousehold.name}" creado con éxito!`;
    if (Platform.OS === "web") {
      window.alert(message);
    } else {
      Alert.alert("¡Éxito!", message);
    }
  };

  const handleVerifyCode = () => {
    const cleanCode = inviteCode.trim().toUpperCase();

    if (cleanCode === mockHouseholdData.code) {
      setCurrentHousehold(mockHouseholdData);
      setIsJoining(false);
      setInviteCode("");
      if (Platform.OS === "web") {
        window.alert("¡Código correcto!");
      } else {
        Alert.alert(
          "¡Código correcto!",
          `Bienvenido a ${mockHouseholdData.name}`,
        );
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

          {/* initial state: choose between joining or creating */}
          {!isJoining && !isCreating && (
            <>
              <Text className="text-2xl font-bold text-gray-900 mb-3 text-center">
                Aún no tienes un hogar
              </Text>
              <Text className="text-gray-500 text-center mb-10 text-base px-4">
                Únete a un hogar existente con un código o crea uno nuevo para
                compartir tu inventario.
              </Text>

              <TouchableOpacity
                className="w-full bg-emerald-500 py-4 rounded-2xl active:bg-emerald-600 mb-4 shadow-sm"
                onPress={() => setIsJoining(true)}
              >
                <Text className="text-white font-bold text-center text-lg">
                  Unirse con un código
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                className="w-full bg-white border-2 border-emerald-500 py-4 rounded-2xl active:bg-emerald-50"
                onPress={() => setIsCreating(true)}
              >
                <Text className="text-emerald-600 font-bold text-center text-lg">
                  Crear nuevo hogar
                </Text>
              </TouchableOpacity>
            </>
          )}

          {/* create a new household state */}
          {isCreating && (
            <View className="w-full">
              <Text className="text-2xl font-bold text-gray-900 mb-2 text-center">
                Crear hogar
              </Text>
              <Text className="text-gray-500 text-center mb-6">
                ¿Cómo se llamará tu nuevo hogar?
              </Text>

              <TextInput
                className="w-full bg-white border border-gray-200 rounded-2xl px-4 py-4 text-xl mb-6 text-center tracking-widest font-bold text-gray-900 shadow-sm leading-6"
                placeholder="Nombre (ej: Casa Playa)"
                placeholderTextColor="#9CA3AF"
                value={householdName}
                onChangeText={setHouseholdName}
                autoFocus
              />

              <TouchableOpacity
                className={`w-full py-4 rounded-2xl mb-3 shadow-sm ${
                  householdName.length >= 2
                    ? "bg-emerald-500"
                    : "bg-emerald-400"
                }`}
                onPress={handleCreateHousehold}
                disabled={householdName.length < 2}
              >
                <Text className="text-white font-bold text-center text-lg">
                  Crear ahora
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                className="w-full bg-white border-2 border-emerald-500 py-4 rounded-2xl active:bg-emerald-50"
                onPress={() => {
                  setIsCreating(false);
                  setHouseholdName("");
                }}
              >
                <Text className="text-gray-500 font-bold text-center text-lg">
                  Cancelar
                </Text>
              </TouchableOpacity>
            </View>
          )}

          {/* ESTADO: Uniéndose a Hogar (tu código anterior) */}
          {isJoining && (
            <View className="w-full">
              <Text className="text-2xl font-bold text-gray-900 mb-2 text-center">
                Unirse
              </Text>
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
                autoFocus
              />

              <TouchableOpacity
                className={`w-full py-4 rounded-2xl mb-3 shadow-sm ${
                  inviteCode.length === 6
                    ? "bg-emerald-500 active:bg-emerald-600"
                    : "bg-emerald-400"
                }`}
                onPress={handleVerifyCode}
                disabled={inviteCode.length !== 6}
              >
                <Text className="text-white font-bold text-center text-lg">
                  Validar código
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
      </SafeAreaView>
    );
  }

  // Main household screen when user is part of a household
  return (
    <SafeAreaView className="flex-1 bg-[#F8FAF8]">
      {/* header */}
      <View className="px-6 pt-6 pb-4 bg-white border-b border-gray-200 flex-row items-center justify-between">
        <Text className="text-2xl font-bold text-gray-900">Tu Hogar</Text>
      </View>

      <ScrollView className="flex-1" contentContainerStyle={{ padding: 24 }}>
        <View className="p-6 bg-emerald-50 border border-emerald-100 rounded-3xl mb-6">
          <View className="flex-row items-center gap-4 mb-5">
            <View className="w-14 h-14 bg-emerald-500 rounded-2xl flex items-center justify-center">
              <Users color="white" size={28} />
            </View>
            <View>
              <Text className="font-bold text-xl text-gray-900">
                {currentHousehold.name}
              </Text>
              <Text className="text-emerald-600 font-medium">
                {currentHousehold.members.length} miembros
              </Text>
            </View>
          </View>

          <View className="bg-white rounded-2xl p-4 flex-row items-center justify-between border border-emerald-50">
            <View>
              <Text className="text-xs text-gray-500 mb-1">
                Código de invitación
              </Text>
              <Text className="font-bold text-xl tracking-widest text-gray-900">
                {currentHousehold.code}
              </Text>
            </View>
            <TouchableOpacity
              className="bg-gray-100 px-3 py-2 rounded-xl"
              onPress={copyInviteCode}
            >
              <Copy color="#4B5563" size={16} />
            </TouchableOpacity>
          </View>
        </View>

        <Text className="text-lg font-bold text-gray-900 mb-4">Miembros</Text>
        {currentHousehold.members.map((member: any) => (
          <View
            key={member.id}
            className="flex-row items-center justify-between p-4 bg-white rounded-2xl mb-4 border border-gray-100"
          >
            <View className="flex-row items-center gap-3">
              <Image
                source={{ uri: member.avatar }}
                className="w-12 h-12 rounded-full"
              />
              <View>
                <View className="flex-row items-center gap-1">
                  <Text className="font-bold text-gray-900">{member.name}</Text>
                  {member.role === "owner" && (
                    <Crown color="#F59E0B" size={14} />
                  )}
                </View>
                <Text className="text-xs text-gray-500">{member.email}</Text>
              </View>
            </View>
            <View
              className={`px-2 py-1 rounded-md ${member.role === "owner" ? "bg-emerald-100" : "bg-gray-100"}`}
            >
              <Text className="text-[10px] font-bold uppercase text-gray-600">
                {member.role === "owner" ? "Admin" : "Miembro"}
              </Text>
            </View>
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}
