import {
  LogOut,
} from "lucide-react-native";
import {
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

export default function SettingsScreen() {



  return (
    <SafeAreaView className="flex-1 bg-[#F8FAF8]">
      {/* Cabecera */}
      <View className="px-6 pt-6 pb-4 bg-white border-b border-gray-200">
        <Text className="text-2xl font-bold text-gray-900">Ajustes</Text>
      </View>

      <ScrollView
        className="flex-1"
        contentContainerStyle={{ padding: 24, paddingBottom: 40 }}
        showsVerticalScrollIndicator={false}
      >

        {/* Logout button */}
        <View className="space-y-4 gap-4">
          <TouchableOpacity
            className="w-full flex-row items-center justify-center h-14 bg-white border border-red-200 rounded-2xl shadow-sm active:bg-red-50"
          >
            <LogOut color="#ef4444" size={20} />
            <Text className="text-red-500 font-semibold text-base ml-2">
              Cerrar sesión
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}