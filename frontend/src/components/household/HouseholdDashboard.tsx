import * as Clipboard from "expo-clipboard";
import { router } from "expo-router";
import {
  ArrowUpRight,
  Copy,
  DollarSign,
  LogOut,
  Users,
} from "lucide-react-native";
import React, { useState } from "react";
import { Alert, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { homeService } from "../../services/homeService";
import MemberItem from "./MemberItem";

interface HouseholdDashboardProps {
  household: any;
  session: any;
  onRefresh: () => void;
}

export default function HouseholdDashboard({
  household,
  session,
  onRefresh,
}: HouseholdDashboardProps) {
  const [isProcessing, setIsProcessing] = useState(false);
  const isOwner = household?.owner_id === session?.id;

  const copyInviteCode = async () => {
    if (household?.invite_code) {
      await Clipboard.setStringAsync(household.invite_code);
      Alert.alert(
        "Codi copiat",
        `El codi ${household.invite_code} s'ha copiat.`,
      );
    }
  };

  const handleLeaveHousehold = () => {
    const isTransferringOwnership = isOwner && household.members.length > 1;
    const message = isTransferringOwnership
      ? "Estàs segur? En sortir, la propietat de la llar passarà al membre més antic."
      : "Estàs segur que vols sortir de la llar? Perdràs l'accés a l'inventari.";

    Alert.alert("Sortir de la llar", message, [
      { text: "Cancel·lar", style: "cancel" },
      {
        text: "Sortir",
        style: "destructive",
        onPress: async () => {
          setIsProcessing(true);
          try {
            await homeService.leaveHome();
            onRefresh();
          } catch (error: any) {
            Alert.alert("Error", error);
          } finally {
            setIsProcessing(false);
          }
        },
      },
    ]);
  };

  const handleKickMember = (memberId: string, memberName: string) => {
    Alert.alert(
      "Expulsar membre",
      `Estàs segur que vols expulsar ${memberName}? Perdrà l'accés a tot l'inventari.`,
      [
        { text: "Cancel·lar", style: "cancel" },
        {
          text: "Expulsar",
          style: "destructive",
          onPress: async () => {
            setIsProcessing(true);
            try {
              await homeService.kickMember(memberId);
              onRefresh();
            } catch (error: any) {
              Alert.alert("Error", error);
            } finally {
              setIsProcessing(false);
            }
          },
        },
      ],
    );
  };

  return (
    <SafeAreaView className="flex-1 bg-[#F8FAF8]">
      <View className="px-6 pt-6 pb-4 bg-white border-b border-gray-200 flex-row items-center justify-between">
        <Text className="text-2xl font-bold text-gray-900">La meva llar</Text>
      </View>

      <ScrollView
        className="flex-1"
        contentContainerStyle={{ padding: 24 }}
        showsVerticalScrollIndicator={false}
      >
        <View className="p-6 bg-emerald-50 border border-emerald-100 rounded-3xl mb-6 shadow-sm">
          <View className="flex-row items-center gap-4 mb-5">
            <View className="w-14 h-14 bg-emerald-500 rounded-2xl flex items-center justify-center shadow-sm">
              <Users color="white" size={28} />
            </View>
            <View>
              <Text className="font-bold text-xl text-gray-900">
                {household.name}
              </Text>
              <Text className="text-emerald-600 font-medium">
                {household.members?.length || household.member_count} membres
              </Text>
            </View>
          </View>

          {isOwner ? (
            <View className="bg-white/90 rounded-2xl p-4 flex-row items-center justify-between border border-emerald-50">
              <View>
                <Text className="text-xs text-gray-500 mb-1 font-medium">
                  Codi actual
                </Text>
                <Text className="font-bold text-xl tracking-widest text-gray-900">
                  {household.invite_code}
                </Text>
              </View>
              <TouchableOpacity
                className="flex-row items-center bg-gray-100 px-3 py-2 rounded-xl active:bg-gray-200"
                onPress={copyInviteCode}
              >
                <Copy color="#4B5563" size={16} />
                <Text className="font-semibold text-gray-700 ml-2">Copiar</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View className="bg-white/90 rounded-2xl p-3 border border-emerald-50">
              <Text className="text-xs text-gray-500 text-center">
                Demana el codi a l&apos;administrador per convidar més gent.
              </Text>
            </View>
          )}
        </View>

        <View className="mb-8">
          <Text className="text-lg font-bold text-gray-900 mb-4 px-1">
            Membres de la llar
          </Text>
          <View className="space-y-3 gap-3">
            {household.members?.map((member: any) => (
              <MemberItem
                key={member.user_id}
                member={member}
                isOwner={isOwner}
                isCurrentUser={member.user_id === session?.id}
                onKick={() => handleKickMember(member.user_id, member.username)}
              />
            ))}
          </View>
        </View>

        <View className="mt-2 mb-8">
          <Text className="text-lg font-bold text-gray-900 mb-4 px-1">
            Accions ràpides
          </Text>

          <TouchableOpacity
            className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 flex-row items-center"
            activeOpacity={0.85}
            onPress={() => router.push("/(tabs)/expenses")}
          >
            <View className="w-14 h-14 rounded-2xl bg-emerald-50 items-center justify-center mr-4">
              <DollarSign color="#10B981" size={24} />
            </View>

            <View className="flex-1">
              <Text className="text-lg font-bold text-gray-900">
                Veure despeses
              </Text>
              <Text className="text-sm text-gray-500 mt-1">
                Consulta i reparteix les despeses compartides de la llar
              </Text>
            </View>

            <View className="w-10 h-10 rounded-full bg-gray-100 items-center justify-center">
              <ArrowUpRight color="#6B7280" size={18} />
            </View>
          </TouchableOpacity>
        </View>

        <View className="space-y-3 gap-3">
          <TouchableOpacity
            className={`flex-row items-center justify-center p-4 bg-red-100 rounded-2xl border border-red-200 active:bg-red-100 ${
              isProcessing ? "opacity-50" : ""
            }`}
            onPress={handleLeaveHousehold}
            disabled={isProcessing}
          >
            <LogOut color="#EF4444" size={20} />
            <Text className="ml-2 font-bold text-red-600 text-base">
              {isProcessing ? "Processant..." : "Sortir de la llar"}
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
