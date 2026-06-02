import { Crown, UserMinus } from "lucide-react-native";
import React from "react";
import { Image, Text, TouchableOpacity, View } from "react-native";

interface MemberItemProps {
  member: any;
  isOwner: boolean;
  isCurrentUser: boolean;
  onKick: () => void;
}

export default function MemberItem({
  member,
  isOwner,
  isCurrentUser,
  onKick,
}: MemberItemProps) {
  const isMemberOwner = member.role === "owner";

  return (
    <View className="flex-row items-center justify-between p-4 bg-white rounded-2xl border border-gray-100 shadow-sm">
      <View className="flex-row items-center gap-3">
        <Image
          source={{
            uri: `https://ui-avatars.com/api/?name=${member.username}&background=10B981&color=fff&bold=true`,
          }}
          className="w-12 h-12 rounded-full"
        />
        <View>
          <View className="flex-row items-center gap-1.5">
            <Text className="font-bold text-base text-gray-900">
              {member.username}
            </Text>
            {isMemberOwner && <Crown color="#F59E0B" size={16} />}
            {isCurrentUser && (
              <Text className="text-xs text-gray-500 ml-1">(Tu)</Text>
            )}
          </View>
          <Text className="text-xs text-gray-400 mt-0.5">
            S&apos;ha afegit el{" "}
            {new Date(member.joined_at).toLocaleDateString()}
          </Text>
        </View>
      </View>

      <View className="flex-row items-center gap-2">
        <View
          className={`px-2.5 py-1 rounded-lg ${isMemberOwner ? "bg-emerald-100" : "bg-gray-100"}`}
        >
          <Text
            className={`text-xs font-bold uppercase ${isMemberOwner ? "text-emerald-700" : "text-gray-600"}`}
          >
            {isMemberOwner ? "Admin" : "Miembro"}
          </Text>
        </View>

        {isOwner && !isCurrentUser && (
          <TouchableOpacity
            className="bg-red-50 p-2 rounded-lg border border-red-100 active:bg-red-100 ml-1"
            onPress={onKick}
          >
            <UserMinus color="#EF4444" size={16} />
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}
