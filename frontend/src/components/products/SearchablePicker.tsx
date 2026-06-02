import { Search, X } from "lucide-react-native";
import React, { useState } from "react";
import {
  FlatList,
  Modal,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

interface Option {
  label: string;
  value: string;
}

interface SearchablePickerProps {
  visible: boolean;
  onClose: () => void;
  onSelect: (option: Option) => void;
  options: Option[];
  placeholder?: string;
  title?: string;
}

export default function SearchablePicker({
  visible,
  onClose,
  onSelect,
  options = [],
  placeholder = "Buscar...",
  title = "Selecciona una opción",
}: SearchablePickerProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const safeOptions = Array.isArray(options) ? options : [];
  const filteredOptions = safeOptions.filter((opt) =>
    opt.label
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .includes(
        searchQuery
          .toLowerCase()
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, ""),
      ),
  );

  const handleSelect = (option: Option) => {
    setSearchQuery("");
    onSelect(option);
    onClose();
  };

  return (
    <Modal visible={visible} animationType="slide" transparent={true}>
      <SafeAreaView className="flex-1 bg-black/50 justify-end">
        <View className="bg-[#F8FAF8] h-[70%] rounded-t-3xl overflow-hidden shadow-lg mt-auto">
          <View className="flex-row items-center justify-between px-6 py-4 bg-white border-b border-gray-200">
            <Text className="text-lg font-bold text-gray-900">{title}</Text>
            <TouchableOpacity
              onPress={onClose}
              className="p-2 bg-gray-100 rounded-full"
            >
              <X color="#4B5563" size={20} />
            </TouchableOpacity>
          </View>

          <View className="px-6 py-4 bg-white">
            <View className="flex-row items-center bg-gray-100 rounded-xl px-4 h-12 border border-gray-200">
              <Search color="#9CA3AF" size={20} />
              <TextInput
                className="flex-1 ml-2 text-base text-gray-900"
                placeholder={placeholder}
                placeholderTextColor="#9CA3AF"
                value={searchQuery}
                onChangeText={setSearchQuery}
                autoCorrect={false}
              />
              {searchQuery.length > 0 && (
                <TouchableOpacity onPress={() => setSearchQuery("")}>
                  <X color="#9CA3AF" size={16} />
                </TouchableOpacity>
              )}
            </View>
          </View>

          <FlatList
            data={filteredOptions}
            keyExtractor={(item) => item.value}
            keyboardShouldPersistTaps="handled"
            contentContainerStyle={{ paddingHorizontal: 24, paddingBottom: 40 }}
            renderItem={({ item }) => (
              <TouchableOpacity
                className="py-4 border-b border-gray-200 active:bg-emerald-50 rounded-lg px-2"
                onPress={() => handleSelect(item)}
              >
                <Text className="text-base text-gray-800">{item.label}</Text>
              </TouchableOpacity>
            )}
            ListEmptyComponent={
              <Text className="text-center text-gray-500 mt-10">
                No se han encontrado categorías con &quot;{searchQuery}&quot;
              </Text>
            }
          />
        </View>
      </SafeAreaView>
    </Modal>
  );
}
